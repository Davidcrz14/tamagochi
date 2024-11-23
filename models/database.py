import sqlite3
from datetime import datetime
import threading

class PetDatabase:
    _local = threading.local()

    def __init__(self):
        self._get_conn()
        self.create_tables()

    def _get_conn(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect('pet_data.db')
        return self._local.conn

    def create_tables(self):
        cursor = self._get_conn().cursor()

        # Verificar si la tabla existe y tiene la columna life_start_time
        cursor.execute("PRAGMA table_info(pet_stats)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'pet_stats' not in columns:
            # Crear tabla si no existe
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS pet_stats (
                id INTEGER PRIMARY KEY,
                hunger INTEGER,
                happiness INTEGER,
                energy INTEGER,
                hygiene INTEGER,
                age INTEGER,
                last_update TEXT,
                is_alive BOOLEAN,
                life_start_time TEXT DEFAULT NULL
            )
            ''')
        elif 'life_start_time' not in columns:
            # Agregar columna life_start_time si no existe
            cursor.execute('ALTER TABLE pet_stats ADD COLUMN life_start_time TEXT DEFAULT NULL')

        # Tabla para las memorias del pet
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pet_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            content TEXT,
            created_at TEXT
        )
        ''')

        self._get_conn().commit()

    def save_stats(self, pet):
        cursor = self._get_conn().cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO pet_stats
        (id, hunger, happiness, energy, hygiene, age, last_update, is_alive, life_start_time)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pet.hunger, pet.happiness, pet.energy, pet.hygiene,
              pet.age, pet.last_update.isoformat(), pet.is_alive,
              pet.life_start_time.isoformat() if pet.life_start_time else None))
        self._get_conn().commit()

    def load_stats(self):
        cursor = self._get_conn().cursor()
        cursor.execute('SELECT * FROM pet_stats WHERE id = 1')
        row = cursor.fetchone()
        if row:
            return {
                'hunger': row[1],
                'happiness': row[2],
                'energy': row[3],
                'hygiene': row[4],
                'age': row[5],
                'last_update': datetime.fromisoformat(row[6]),
                'is_alive': bool(row[7]),
                'life_start_time': datetime.fromisoformat(row[8]) if row[8] else datetime.now()
            }
        return None

    def add_memory(self, category, content):
        cursor = self._get_conn().cursor()
        cursor.execute('''
        SELECT id FROM pet_memories WHERE category = ?
        ''', (category,))

        existing_memory = cursor.fetchone()

        if existing_memory:
            cursor.execute('''
            UPDATE pet_memories
            SET content = ?, created_at = ?
            WHERE category = ?
            ''', (content, datetime.now().isoformat(), category))
        else:
            cursor.execute('''
            INSERT INTO pet_memories (category, content, created_at)
            VALUES (?, ?, ?)
            ''', (category, content, datetime.now().isoformat()))

        self._get_conn().commit()

    def get_memories(self, category=None):
        cursor = self._get_conn().cursor()
        if category:
            cursor.execute('SELECT * FROM pet_memories WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT * FROM pet_memories')
        return cursor.fetchall()

    def close(self):
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            del self._local.conn
