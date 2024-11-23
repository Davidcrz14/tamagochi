import os

def ensure_directories():
    """Asegura que existan todas las carpetas necesarias"""
    directories = [
        'assets',
        'assets/icons',
        'styles',
        'models',
        'screens',
        'utils'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def verify_assets():
    """Verifica que existan los archivos necesarios"""
    required_files = {
        'assets/icons/feed.png': '🍽️',
        'assets/icons/play.png': '🎮',
        'assets/icons/sleep.png': '😴',
        'assets/icons/clean.png': '🧹',
        'assets/icons/hygiene.png': '🚿',
        'assets/icons/health.png': '❤️',
        'assets/icons/hunger.png': '🍖',
        'assets/icons/sleep.png': '💤',
        'assets/tamagotchi.png': '🐱'
    }

    missing_files = []
    for file_path, emoji in required_files.items():
        if not os.path.exists(file_path):
            missing_files.append(f"{file_path} ({emoji})")

    if missing_files:
        print("Archivos faltantes:")
        for file in missing_files:
            print(f"- {file}")
        print("\nPor favor, asegúrate de tener todos los archivos necesarios en las carpetas correspondientes.")
