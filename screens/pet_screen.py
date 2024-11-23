from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar,
                           QHBoxLayout, QFrame, QSizePolicy)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
from models.pet import Pet

class StatWidget(QFrame):
    def __init__(self, name, value, icon_path=None):
        super().__init__()
        self.setObjectName("stat-container")
        layout = QVBoxLayout()
        layout.setSpacing(2)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)

        if icon_path:
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon_path).scaled(16, 16, Qt.KeepAspectRatio))
            header_layout.addWidget(icon_label)

        label = QLabel(name)
        label.setObjectName("stat-label")
        header_layout.addWidget(label)

        percent_value = int(value / 100)
        self.percent_label = QLabel(f"{percent_value}%")
        self.percent_label.setObjectName("percent-label")
        header_layout.addWidget(self.percent_label)

        layout.addLayout(header_layout)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(percent_value)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        layout.addWidget(self.progress)

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def update_value(self, value):
        percent_value = int(value / 100)
        self.progress.setValue(percent_value)
        self.percent_label.setText(f"{percent_value}%")

class PetScreen(QWidget):
    def __init__(self, pet: Pet):
        super().__init__()
        self.pet = pet

        # Crear el layout principal
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Contenedor principal
        content = QFrame()
        content.setObjectName("main-container")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Imagen del Tamagotchi
        self.image_label = QLabel()
        self.image_label.setObjectName("pet-image")
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Stats layout
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        left_stats = QVBoxLayout()
        right_stats = QVBoxLayout()
        left_stats.setSpacing(5)
        right_stats.setSpacing(5)

        self.hygiene_stat = StatWidget("Higiene", self.pet.hygiene, "assets/icons/hygiene.png")
        self.health_stat = StatWidget("Vida", self.pet.happiness, "assets/icons/health.png")
        self.hunger_stat = StatWidget("Hambre", self.pet.hunger, "assets/icons/hunger.png")
        self.sleep_stat = StatWidget("Sueño", self.pet.energy, "assets/icons/sleep.png")

        left_stats.addWidget(self.hygiene_stat)
        left_stats.addWidget(self.health_stat)
        right_stats.addWidget(self.hunger_stat)
        right_stats.addWidget(self.sleep_stat)

        stats_layout.addLayout(left_stats)
        stats_layout.addLayout(right_stats)

        layout.addLayout(stats_layout)
        content.setLayout(layout)
        main_layout.addWidget(content)
        self.setLayout(main_layout)

        # Inicializar la imagen
        self.update_image(self.pet.current_state_image)

    def update_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Escalar la imagen manteniendo proporción
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
            else:
                print(f"No se pudo cargar la imagen: {image_path}")
        except Exception as e:
            print(f"Error al actualizar la imagen: {e}")

    def update_stats(self):
        # Actualizar stats usando los valores reales (0-8000) y convirtiéndolos a porcentajes
        hygiene_percent = min(100, int((self.pet.hygiene / 8000) * 100))
        health_percent = min(100, int((self.pet.happiness / 8000) * 100))
        hunger_percent = min(100, int((self.pet.hunger / 8000) * 100))
        sleep_percent = min(100, int((self.pet.energy / 8000) * 100))

        self.hygiene_stat.update_value(hygiene_percent * 100)
        self.health_stat.update_value(health_percent * 100)
        self.hunger_stat.update_value(hunger_percent * 100)
        self.sleep_stat.update_value(sleep_percent * 100)

        # Actualizar imagen según el estado actual
        self.update_image(self.pet.current_state_image)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Actualizar tamaño de la imagen al redimensionar
        if self.image_label.pixmap():
            self.update_image(self.pet.current_state_image)
