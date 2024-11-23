import sys
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QProgressBar, QHBoxLayout, QFrame, QComboBox, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QFont, QIcon, QPalette, QBrush, QColor, QPixmap
from PyQt5.QtCore import QTimer, Qt, QMetaObject, Q_ARG
from models.pet import Pet
import random
import os
from datetime import datetime
from screens.pet_screen import PetScreen
from utils.setup import ensure_directories, verify_assets
from dotenv import load_dotenv
from mistralai import Mistral

# Asegurarse de que las dependencias estén instaladas
try:
    load_dotenv()
except ImportError:
    print("Instalando dependencias necesarias...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mistralai"])
    from dotenv import load_dotenv
    from mistralai import Mistral

# Configurar Mistral solo si está disponible la API key
api_key = os.getenv("MISTRAL_API_KEY")
client = None
if api_key:
    client = Mistral(api_key=api_key)
    model = "mistral-large-latest"

class TamagotchiWindow(QWidget):
    def __init__(self, pet: Pet):
        super().__init__()
        self.pet = pet
        self.init_ui()
        self.setup_system_tray()

        # Timer para actualizar stats cada 30 segundos
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_pet_status)
        self.update_timer.start(30000)  # 30 segundos

        # Timer para actualizar stats durante el sueño
        self.sleep_timer = QTimer()
        self.sleep_timer.timeout.connect(self.update_sleep_status)
        self.sleep_timer.setInterval(1000)

    def setup_system_tray(self):
        # Crear icono de sistema
        self.tray_icon = QSystemTrayIcon(self)
        icon = QIcon("assets/icons/pet.png")
        self.tray_icon.setIcon(icon)
        self.setWindowIcon(icon)  # Agregar icono a la ventana principal

        # Crear menú del icono de sistema
        tray_menu = QMenu()

        # Agregar acción para mostrar/restaurar
        show_action = tray_menu.addAction("Mostrar")
        show_action.triggered.connect(self.restore_window)

        # Agregar separador
        tray_menu.addSeparator()

        stats_action = tray_menu.addAction("Ver estadísticas")
        stats_action.triggered.connect(self.show_stats_notification)

        # Agregar separador
        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Salir")
        quit_action.triggered.connect(self.close_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Conectar el doble clic en el icono para restaurar
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def restore_window(self):
        self.showNormal()
        self.activateWindow()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_window()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "Tamagotchi",
                "Tu mascota sigue viva en segundo plano! Haz doble clic en el icono para restaurar.",
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            self.close_application()

    def close_application(self):
        self.pet.save_state()
        self.tray_icon.hide()
        QApplication.quit()

    def show_stats_notification(self):
        stats_message = f"""
        Hambre: {int(self.pet.hunger/8000)}%
        Energía: {int(self.pet.energy/8000)}%
        Higiene: {int(self.pet.hygiene/8000)}%
        Felicidad: {int(self.pet.happiness/8000)}%
        """
        self.tray_icon.showMessage(
            "Estado de tu mascota",
            stats_message,
            QSystemTrayIcon.Information,
            3000
        )

    def init_ui(self):
        # Cargar estilos
        try:
            with open('styles/style.qss', 'r') as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error cargando estilos: {e}")

        # Crear layout principal con márgenes
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Agregar sección de memorias al principio
        memory_container = QFrame()
        memory_container.setObjectName("memory-container")
        memory_layout = QHBoxLayout()

        self.memory_category = QComboBox()
        self.memory_category.setObjectName("memory-category")
        self.memory_category.addItems(["Nombre", "Gustos", "Familia", "Otros"])
        memory_layout.addWidget(self.memory_category)

        self.memory_input = QLineEdit()
        self.memory_input.setObjectName("memory-input")
        self.memory_input.setPlaceholderText("Agregar un recuerdo...")
        memory_layout.addWidget(self.memory_input)

        add_memory_button = QPushButton("Guardar")
        add_memory_button.clicked.connect(self.add_memory)
        memory_layout.addWidget(add_memory_button)

        memory_container.setLayout(memory_layout)
        main_layout.addWidget(memory_container)

        # Contenedor para los botones de acción
        action_container = QFrame()
        action_container.setObjectName("action-container")
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        # Verificar que los iconos existan antes de usarlos
        icon_paths = {
            "feed": "assets/icons/feed.png",
            "play": "assets/icons/play.png",
            "sleep": "assets/icons/sleep.png",
            "clean": "assets/icons/clean.png"
        }

        buttons = [
            ("Alimentar", self.feed, icon_paths["feed"]),
            ("Jugar", self.play, icon_paths["play"]),
            ("Dormir", self.sleep, icon_paths["sleep"]),
            ("Limpiar", self.clean, icon_paths["clean"])
        ]

        for text, callback, icon_path in buttons:
            btn = QPushButton(text)
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
            btn.clicked.connect(callback)
            button_layout.addWidget(btn)

        action_container.setLayout(button_layout)
        main_layout.addWidget(action_container)

        self.pet_screen = PetScreen(self.pet)
        main_layout.addWidget(self.pet_screen)

        # Título
        title_label = QLabel("Tamagotchi IA")
        title_label.setObjectName("title")
        title_label.setFont(QFont("Arial", 24))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Mensajes de IA y entrada de usuario
        self.ai_message_label = QLabel()
        self.ai_message_label.setObjectName("ai-message")
        self.ai_message_label.setFont(QFont("Arial", 14))
        self.ai_message_label.setWordWrap(True)
        main_layout.addWidget(self.ai_message_label)

        chat_container = QFrame()
        chat_container.setObjectName("chat-container")
        chat_layout = QHBoxLayout()

        self.user_input = QLineEdit()
        self.user_input.setObjectName("chat-input")
        self.user_input.setPlaceholderText("Escribe un mensaje...")
        chat_layout.addWidget(self.user_input)

        interact_button = QPushButton("Enviar")
        interact_button.setObjectName("chat-button")
        interact_button.clicked.connect(self.interact)
        chat_layout.addWidget(interact_button)

        chat_container.setLayout(chat_layout)
        main_layout.addWidget(chat_container)

        self.setLayout(main_layout)

    def update_pet_status(self):
        self.pet.update_stats()
        self.pet_screen.update_stats()

        # Mostrar notificación si alguna estadística está crítica
        if (self.pet.hunger < self.pet.CRITICAL_THRESHOLD or
            self.pet.energy < self.pet.CRITICAL_THRESHOLD or
            self.pet.hygiene < self.pet.CRITICAL_THRESHOLD):
            self.tray_icon.showMessage(
                "¡Tu mascota te necesita!",
                "Algunas estadísticas están en estado crítico",
                QSystemTrayIcon.Warning,
                2000
            )

        if not self.pet.is_alive:
            self.handle_pet_death()
        else:
            self.check_critical_stats()

    def handle_pet_death(self):
        # Mostrar mensaje de muerte y deshabilitar interacciones
        self.ai_message_label.setText("Tu Tamagotchi ha fallecido... 😢")
        for button in self.findChildren(QPushButton):
            button.setEnabled(False)
        self.user_input.setEnabled(False)

        # Detener los timers
        self.update_timer.stop()
        self.sleep_timer.stop()

    def feed(self):
        result = self.pet.feed()
        if result:
            self.ai_message_label.setText(result)
        self.pet_screen.update_stats()

    def play(self):
        result = self.pet.play()
        if result:
            self.ai_message_label.setText(result)
        self.pet_screen.update_stats()

    def sleep(self):
        result = self.pet.sleep()
        if result:
            self.ai_message_label.setText(result)
            if "Me voy a dormir" in result:
                self.disable_buttons()
                self.sleep_timer.start()
            elif "despertar" in result:
                self.enable_buttons()
                self.sleep_timer.stop()
        self.pet_screen.update_stats()
        self.pet_screen.update_image(self.pet.current_state_image)

    def disable_buttons(self):
        for button in self.findChildren(QPushButton):
            if button.text() in ["Alimentar", "Jugar", "Limpiar"]:
                button.setEnabled(False)

    def enable_buttons(self):
        for button in self.findChildren(QPushButton):
            button.setEnabled(True)

    def clean(self):
        result = self.pet.clean()
        if result:
            self.ai_message_label.setText(result)
        self.pet_screen.update_stats()

    def update_ai_message(self):
        ai_message = self.pet.get_ai_decision()
        self.ai_message_label.setText(ai_message)

    def interact(self):
        user_message = self.user_input.text()
        if user_message.strip():  # Solo procesar si hay mensaje
            self.pet.chat(user_message)  # Actualizar felicidad por interacción
            interaction_thread = threading.Thread(target=self.get_interaction_response, args=(user_message,))
            interaction_thread.start()
            self.user_input.clear()
            self.pet_screen.update_stats()  # Actualizar stats después de la interacción

    def get_interaction_response(self, user_message):
        try:
            # Crear una nueva instancia de Pet para este hilo
            thread_pet = Pet(name=self.pet.name)
            response = thread_pet.get_user_interaction_response(user_message)
            QMetaObject.invokeMethod(self.ai_message_label, "setText",
                Qt.QueuedConnection, Q_ARG(str, response))
        except Exception as e:
            QMetaObject.invokeMethod(self.ai_message_label, "setText",
                Qt.QueuedConnection, Q_ARG(str, f"Error: {str(e)}"))

    def initiate_interaction(self):
        if random.random() < 0.5:  # 50% de probabilidad de iniciar interacción
            prompt = f"""
            Tu estado actual es:
            - Hambre: {self.pet.hunger}
            - Felicidad: {self.pet.happiness}
            - Energía: {self.pet.energy}
            - Higiene: {self.pet.hygiene}
            """
            interaction_thread = threading.Thread(target=self.get_initiate_interaction_response, args=(prompt,))
            interaction_thread.start()

    def get_initiate_interaction_response(self, prompt):
        try:
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un Tamagotchi. Tu personalidad es divertida y un poco sarcástica, pero siempre amigable. Genera un mensaje de 1-2 oraciones para iniciar una conversación."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            QMetaObject.invokeMethod(self.ai_message_label, "setText",
                Qt.QueuedConnection, Q_ARG(str, chat_response.choices[0].message.content))
        except Exception as e:
            QMetaObject.invokeMethod(self.ai_message_label, "setText",
                Qt.QueuedConnection, Q_ARG(str, f"Error: {str(e)}"))

    def add_memory(self):
        category = self.memory_category.currentText()
        content = self.memory_input.text()
        if content:
            self.pet.add_memory(category, content)
            self.memory_input.clear()
            self.pet_screen.update_stats()

    def check_critical_stats(self):
        ai_message = self.pet.get_ai_decision()
        if ai_message:  # Solo actualizar si hay un mensaje
            self.ai_message_label.setText(ai_message)

    def update_sleep_status(self):
        if self.pet.is_sleeping:
            self.pet.update_stats()
            self.pet_screen.update_stats()

            # Actualizar mensaje con tiempo restante
            time_slept = (datetime.now() - self.pet.sleep_start_time).total_seconds()
            remaining = self.pet.SLEEP_DURATION - time_slept
            if remaining > 0:
                self.ai_message_label.setText(f"Estoy durmiendo... Me faltan {int(remaining)} segundos para despertar")
        else:
            self.sleep_timer.stop()
            self.enable_buttons()
            self.ai_message_label.setText("¡Me acabo de despertar! Me siento con energía")

def main():
    ensure_directories()
    verify_assets()

    pet = Pet(name="Tami")
    app = QApplication(sys.argv)
    window = TamagotchiWindow(pet)
    window.show()

    # Eliminar o comentar el timer original de update_ai_message
    # timer = QTimer()
    # timer.timeout.connect(window.update_ai_message)
    # timer.start(30000)

    # Eliminar o comentar el timer de interacción aleatoria
    # interaction_timer = QTimer()
    # interaction_timer.timeout.connect(window.initiate_interaction)
    # interaction_timer.start(30000)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
