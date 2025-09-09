"""
Module HAL SPI
Abstraction du bus SPI pour tous les drivers du projet.
Permet d'utiliser le SPI sans dépendance directe au matériel.
"""
from typing import List, Optional, Union
from Metrology.exceptions import HardwareError, ConfigError

class SpiBus:
    # Constantes pour les modes SPI
    MODE_0 = 0  # CPOL=0, CPHA=0
    MODE_1 = 1  # CPOL=0, CPHA=1
    MODE_2 = 2  # CPOL=1, CPHA=0
    MODE_3 = 3  # CPOL=1, CPHA=1
    
    def __init__(self, bus: int = 0, device: int = 0):
        """
        Initialise un bus SPI.
        
        Args:
            bus: Numéro du bus SPI
            device: Numéro du périphérique sur le bus
            
        Raises:
            ConfigError: Si les paramètres sont invalides
        """
        self.bus = bus
        self.device = device
        self._is_open = False
        self._mode = self.MODE_0
        self._speed = 1000000  # 1MHz par défaut

class SpiBus:
    def open(self):
        """Ouvre le bus SPI."""
        pass

    def configure(self, mode, speed):
        """Configure le mode et la vitesse SPI."""
        pass

    def transfer(self, data):
        """Transfère des données sur le bus SPI."""
        pass

    def write_then_read(self, write_data, read_len):
        """Écrit puis lit sur le bus SPI."""
        pass

    def set_mode(self, mode):
        """Définit le mode SPI (0, 1, 2, 3)."""
        pass

    def set_speed(self, speed):
        """Définit la vitesse SPI en Hz."""
        pass
