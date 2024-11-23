from dataclasses import dataclass
from datetime import datetime, timedelta
import os
import random
from models.database import PetDatabase
import sqlite3


try:
    from mistralai import Mistral
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("MISTRAL_API_KEY")
    client = Mistral(api_key=api_key) if api_key else None
    model = "mistral-large-latest"
except ImportError:
    client = None
    model = None

@dataclass
class Pet:
    name: str
    hunger: int = 8000
    happiness: int = 8000
    energy: int = 8000
    hygiene: int = 8000
    age: int = 0
    last_update: datetime = datetime.now()
    is_alive: bool = True
    is_sleeping: bool = False
    sleep_start_time: datetime = None
    db: PetDatabase = None
    life_start_time: datetime = datetime.now()

    # Constantes para el manejo del tiempo
    MINUTES_PER_DAY = 24 * 60
    LIFESPAN_DAYS = 5
    SLEEP_DURATION = 5 * 60  # 5 minutos en segundos
    SLEEP_ENERGY_GAIN_PER_SECOND = 1.67  # Para llegar a 100% en 5 minutos
    current_state_image = "assets/estados/normal.png"  # Imagen por defecto

    # Umbrales para diferentes estados
    CRITICAL_THRESHOLD = 2000  # 25%
    LOW_THRESHOLD = 4000      # 50%
    GOOD_THRESHOLD = 6000     # 75%

    # Modificar las constantes de deterioro
    BASE_HUNGER_DECAY = (8, 15)    # Rango de deterioro por minuto
    BASE_ENERGY_DECAY = (6, 12)    # Más lento que el hambre
    BASE_HYGIENE_DECAY = (4, 10)   # Más lento que la energía
    BASE_HAPPINESS_DECAY = (3, 8)  # El más lento de todos

    def __post_init__(self):
        self.db = PetDatabase()
        try:
            stats = self.db.load_stats()
            if stats:
                self.hunger = stats['hunger']
                self.happiness = stats['happiness']
                self.energy = stats['energy']
                self.hygiene = stats['hygiene']
                self.age = stats['age']
                self.last_update = stats['last_update']
                self.is_alive = stats['is_alive']
                self.life_start_time = stats['life_start_time']
        except sqlite3.OperationalError:
            # Si hay un error al cargar los stats, mantener los valores por defecto
            pass

    def save_state(self):
        self.db.save_stats(self)

    def add_memory(self, category, content):
        self.db.add_memory(category, content)
        self.happiness = min(10000, self.happiness + 500)  # Aumenta felicidad al compartir memorias
        self.save_state()

    def get_relevant_memories(self, context):
        memories = self.db.get_memories()
        relevant_memories = []

        # Dividir el contexto en palabras para mejor búsqueda
        context_words = context.lower().split()

        keyword_mapping = {
            'nombre': ['nombre', 'llamo', 'llamas'],
            'gustos': ['gusta', 'gustos', 'prefieres', 'favorito'],
            'familia': ['familia', 'padres', 'hermanos', 'vives'],
        }

        for memory in memories:
            category = memory[1].lower()
            content = memory[2].lower()

            # Buscar coincidencias directas
            if any(word in content for word in context_words):
                relevant_memories.append(f"{category}: {memory[2]}")
                continue

            # Buscar por categorías y palabras clave
            for category_key, keywords in keyword_mapping.items():
                if any(keyword in context.lower() for keyword in keywords) and category_key.lower() == category:
                    relevant_memories.append(f"{category}: {memory[2]}")
                    break

        return relevant_memories

    def chat(self, message):
        # Aumentar felicidad por interacción
        self.happiness = min(10000, self.happiness + 100)
        self.save_state()

        # Buscar memorias relevantes
        relevant_memories = self.get_relevant_memories(message)

        # ... resto del código de interacción

    def update_stats(self):
        current_time = datetime.now()

        # Si está durmiendo, actualizar energía gradualmente
        if self.is_sleeping:
            time_slept = (current_time - self.sleep_start_time).total_seconds()
            if time_slept >= self.SLEEP_DURATION:
                self.wake_up()
                return

            # Calcular ganancia de energía
            energy_gain = int(time_slept * self.SLEEP_ENERGY_GAIN_PER_SECOND)
            self.energy = min(8000, self.energy + energy_gain)

            # Actualizar imagen de estado
            self.current_state_image = "assets/estados/durmiendo.png"
            return

        # Actualizar imagen basado en estado
        if self.energy < self.LOW_THRESHOLD:
            self.current_state_image = "assets/estados/sueño.png"
        else:
            self.current_state_image = "assets/estados/normal.png"

        minutes_passed = (current_time - self.last_update).total_seconds() / 60

        # Deterioro aleatorio dentro de los rangos establecidos
        hunger_decay = random.uniform(*self.BASE_HUNGER_DECAY)
        energy_decay = random.uniform(*self.BASE_ENERGY_DECAY)
        hygiene_decay = random.uniform(*self.BASE_HYGIENE_DECAY)
        happiness_decay = random.uniform(*self.BASE_HAPPINESS_DECAY)

        # Multiplicadores de deterioro basados en estados críticos
        if self.hunger < self.LOW_THRESHOLD:
            energy_decay *= 1.5
            happiness_decay *= 1.3

        if self.energy < self.LOW_THRESHOLD:
            hunger_decay *= 1.3
            happiness_decay *= 1.3

        if self.hygiene < self.LOW_THRESHOLD:
            happiness_decay *= 1.2

        # Aplicar deterioro
        self.hunger = max(0, self.hunger - int(minutes_passed * hunger_decay))
        self.energy = max(0, self.energy - int(minutes_passed * energy_decay))
        self.hygiene = max(0, self.hygiene - int(minutes_passed * hygiene_decay))
        self.happiness = max(0, self.happiness - int(minutes_passed * happiness_decay))

        # Verificar tiempo de vida
        age_days = (current_time - self.life_start_time).days
        if age_days >= self.LIFESPAN_DAYS:
            self.is_alive = False
            return

        self.last_update = current_time
        self.save_state()

    def check_critical_condition(self):
        # Muere si cualquier stat llega a 0 y se mantiene así por mucho tiempo
        critical_time = 120  # 2 horas de stats en 0 = muerte
        return (self.hunger <= 0 or self.happiness <= 0 or
                self.energy <= 0 or self.hygiene <= 0)

    def feed(self):
        if self.is_sleeping:
            return "Estoy durmiendo... ¡No me despiertes para comer!"

        if self.energy < self.CRITICAL_THRESHOLD:
            return "Estoy demasiado cansado... necesito dormir primero"

        if self.hunger >= 7900:  # Casi lleno
            return "¡Estoy lleno! No puedo comer más"

        # Modificar los valores para que sean más razonables
        food_amount = 2000  # 25% de incremento
        hygiene_reduction = 500  # Pequeña reducción de higiene
        energy_cost = 200  # Pequeño costo de energía

        self.hunger = min(8000, self.hunger + food_amount)
        self.energy = max(0, self.energy - energy_cost)
        self.hygiene = max(0, self.hygiene - hygiene_reduction)
        self.happiness = min(8000, self.happiness + 300)

        self.save_state()
        return None

    def play(self):
        if self.is_sleeping:
            return "Estoy durmiendo... ¡No me despiertes para jugar!"

        if self.energy < self.CRITICAL_THRESHOLD:
            return "Estoy demasiado cansado para jugar..."
        if self.hunger < self.CRITICAL_THRESHOLD:
            return "Tengo demasiada hambre para jugar..."

        if self.happiness >= 7900:
            return "¡Ya estoy muy feliz! Necesito descansar un poco"

        # Ajustar valores para que sean más balanceados
        happiness_gain = 1500  # Incremento significativo de felicidad
        energy_cost = 1000    # Costo significativo de energía
        hunger_cost = 800     # Costo significativo de hambre
        hygiene_cost = 500    # Pequeña reducción de higiene

        self.happiness = min(8000, self.happiness + happiness_gain)
        self.energy = max(0, self.energy - energy_cost)
        self.hunger = max(0, self.hunger - hunger_cost)
        self.hygiene = max(0, self.hygiene - hygiene_cost)

        self.save_state()
        return None

    def sleep(self):
        if self.is_sleeping:
            time_slept = (datetime.now() - self.sleep_start_time).total_seconds()
            remaining = self.SLEEP_DURATION - time_slept
            if remaining > 0:
                return f"Estoy durmiendo... Me faltan {int(remaining)} segundos para despertar"
            else:
                self.wake_up()
                return "¡Me acabo de despertar! Me siento con energía"

        if self.energy >= 7900:  # 99%
            return "No tengo sueño, ¡estoy lleno de energía!"

        if self.hunger < self.CRITICAL_THRESHOLD:
            return "No puedo dormir... tengo demasiada hambre"

        self.is_sleeping = True
        self.sleep_start_time = datetime.now()
        self.current_state_image = "assets/estados/durmiendo.png"
        return "Me voy a dormir por 5 minutos..."

    def wake_up(self):
        self.is_sleeping = False
        self.sleep_start_time = None
        self.current_state_image = "assets/estados/normal.png"
        if self.energy > self.GOOD_THRESHOLD:
            self.happiness = min(8000, self.happiness + 200)
        self.save_state()

    def clean(self):
        if self.is_sleeping:
            return "Estoy durmiendo... ¡No me despiertes para bañarme!"

        if self.energy < self.CRITICAL_THRESHOLD:
            return "Estoy demasiado cansado para bañarme..."

        if self.hygiene >= 7900:
            return "¡Ya estoy muy limpio! No necesito otro baño"

        # Ajustar valores para que sean más balanceados
        hygiene_gain = 3000   # Incremento significativo de higiene
        energy_cost = 500     # Pequeño costo de energía
        happiness_gain = 300  # Pequeño incremento de felicidad

        self.hygiene = min(8000, self.hygiene + hygiene_gain)
        self.energy = max(0, self.energy - energy_cost)
        self.happiness = min(8000, self.happiness + happiness_gain)

        self.save_state()
        return None

    def check_alive(self):
        if self.hunger <= 0 or self.happiness <= 0 or self.energy <= 0 or self.hygiene <= 0:
            self.is_alive = False

    def get_personality_response(self, user_message):
        if not client:
            return "Lo siento, no puedo procesar mensajes en este momento."
        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un Tamagotchi con una personalidad divertida y sarcástica. Responde a los mensajes del usuario de manera graciosa y un poco burlona, pero siempre amigable."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )
            return chat_response.choices[0].message.content
        except Exception as e:
            return f"Error al procesar el mensaje: {str(e)}"

    def get_evolution_response(self, user_message):
        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un Tamagotchi que evoluciona según el cuidado que recibe. Si te cuidan bien, te vuelves más amigable y positivo. Si te descuidan, respondes de manera más distante y triste. Decide cómo evolucionarás basándote en tu estado actual y el mensaje del usuario."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )
            return chat_response.choices[0].message.content
        except Exception as e:
            return f"Error al procesar el mensaje: {str(e)}"

    def get_ai_decision(self):
        # Calcular porcentajes
        hunger_percent = int(self.hunger / 100)
        happiness_percent = int(self.happiness / 100)
        energy_percent = int(self.energy / 100)
        hygiene_percent = int(self.hygiene / 100)

        # Solo alertar si alguna estadística está por debajo del 20%
        low_stats = []

        if hunger_percent <= 20:
            low_stats.append("tengo mucha hambre")
        if happiness_percent <= 20:
            low_stats.append("me siento muy triste")
        if energy_percent <= 20:
            low_stats.append("estoy muy cansado")
        if hygiene_percent <= 20:
            low_stats.append("necesito un baño")

        if not low_stats:
            return ""

        prompt = f"""
        Necesito expresar que: {', '.join(low_stats)}

        Instrucciones:
        - Menciona solo los estados críticos (por debajo del 20%)
        - Hazlo de forma natural y amigable
        - Sé breve pero expresivo
        """

        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """Eres un Tamagotchi que necesita expresar sus necesidades.
                        Comunica tus necesidades de forma natural y amigable, sin ser repetitivo.
                        Sé breve pero expresivo."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return chat_response.choices[0].message.content
        except Exception as e:
            return ""  # En caso de error, no mostrar mensaje

    def get_user_interaction_response(self, user_message):
        # Verificar si el mensaje pide información o acciones fuera del rol
        forbidden_topics = ['guerra', 'política', 'historia', 'matemáticas', 'ciencia']
        if any(topic in user_message.lower() for topic in forbidden_topics):
            return "¡Soy tu mascota virtual! Me encanta jugar y charlar contigo, pero no puedo ayudarte con eso. ¿Qué tal si jugamos o me cuentas sobre tu día?"

        # Obtener memorias relevantes
        relevant_memories = self.get_relevant_memories(user_message)
        memories_context = ""

        if relevant_memories:
            memories_context = "\n\nRecuerdos relevantes:\n" + "\n".join(relevant_memories)

        # Solo incluir stats si están bajos o si el usuario pregunta por ellos
        stats_context = ""
        stats_keywords = ['estado', 'como estas', 'stats', 'estadísticas', 'estadisticas']

        if any(keyword in user_message.lower() for keyword in stats_keywords):
            stats_context = f"""
            Mi estado actual es:
            - Hambre: {int(self.hunger/100)}%
            - Felicidad: {int(self.happiness/100)}%
            - Energía: {int(self.energy/100)}%
            - Higiene: {int(self.hygiene/100)}%
            """

        prompt = f"""
        Contexto de la conversación:
        - Mensaje del usuario: {user_message}
        {memories_context}
        {stats_context}

        Instrucciones:
        - Responde de manera natural y amigable, como un compañero
        - No menciones tus estadísticas a menos que te pregunten específicamente por ellas
        - Mantén un tono conversacional y empático
        - Si el usuario comparte información sobre su día, muestra interés y haz preguntas relevantes
        """

        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """Eres un Tamagotchi amigable y empático.
                        Mantienes conversaciones naturales sin mencionar tus estadísticas
                        a menos que te pregunten específicamente por ellas.
                        Cuando el usuario comparte información sobre su día, muestras
                        verdadero interés y haces preguntas relevantes para mantener la conversación."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return chat_response.choices[0].message.content
        except Exception as e:
            return f"Error al procesar el mensaje: {str(e)}"
