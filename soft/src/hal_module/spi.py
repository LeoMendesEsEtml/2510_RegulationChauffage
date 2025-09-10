"""
Module HAL SPI
Abstraction du bus SPI pour tous les drivers du projet.
Permet d'utiliser le SPI sans dépendance directe au matériel.
"""

import spidev
import logging
from typing import List, Optional, Union
from Metrology_module.exceptions import HardwareError, ConfigError

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HAL-SPI")

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
        self._speed = 1000000  # 1 MHz par défaut
        self.spi = spidev.SpiDev()

    def open(self):
        """Ouvre le bus SPI."""
        try:
            self.spi.open(self.bus, self.device)
            self._is_open = True
            logger.info(f"SPI ouvert sur bus {self.bus}, périphérique {self.device}")
        except FileNotFoundError:
            raise HardwareError(f"Le bus SPI {self.bus}, périphérique {self.device} n'existe pas.")
        except Exception as e:
            raise HardwareError(f"Erreur lors de l'ouverture du bus SPI : {e}")

    def configure(self, mode: int, speed: int):
        """
        Configure le mode et la vitesse SPI.
        
        Args:
            mode: Mode SPI (0, 1, 2, 3)
            speed: Vitesse SPI en Hz
            
        Raises:
            ConfigError: Si les paramètres sont invalides
        """
        if mode not in [self.MODE_0, self.MODE_1, self.MODE_2, self.MODE_3]:
            raise ConfigError(f"Mode SPI invalide : {mode}")
        if speed <= 0:
            raise ConfigError(f"Vitesse SPI invalide : {speed}")
        
        self.spi.mode = mode
        self.spi.max_speed_hz = speed
        self._mode = mode
        self._speed = speed
        logger.info(f"SPI configuré : mode={mode}, vitesse={speed} Hz")

    def transfer(self, data: List[int]) -> List[int]:
        """
        Transfère des données sur le bus SPI.
        
        Args:
            data: Liste d'octets à envoyer
            
        Returns:
            Liste d'octets reçus
            
        Raises:
            HardwareError: Si le bus SPI n'est pas ouvert
        """
        if not self._is_open:
            raise HardwareError("Le bus SPI n'est pas ouvert.")
        try:
            logger.debug(f"Transfert SPI : envoi {data}")
            response = self.spi.xfer2(data)
            logger.debug(f"Transfert SPI : réponse {response}")
            return response
        except Exception as e:
            raise HardwareError(f"Erreur lors du transfert SPI : {e}")

    def write_then_read(self, write_data: List[int], read_len: int) -> List[int]:
        """
        Écrit puis lit sur le bus SPI.
        
        Args:
            write_data: Liste d'octets à écrire
            read_len: Nombre d'octets à lire
            
        Returns:
            Liste d'octets reçus
            
        Raises:
            HardwareError: Si le bus SPI n'est pas ouvert
        """
        if not self._is_open:
            raise HardwareError("Le bus SPI n'est pas ouvert.")
        try:
            logger.debug(f"SPI write_then_read : envoi {write_data}, lecture {read_len} octets")
            self.spi.xfer2(write_data)  # Écrit les données
            response = self.spi.readbytes(read_len)  # Lit les données
            logger.debug(f"SPI write_then_read : réponse {response}")
            return response
        except Exception as e:
            raise HardwareError(f"Erreur lors de l'opération SPI write_then_read : {e}")

    def set_mode(self, mode: int):
        """Définit le mode SPI (0, 1, 2, 3)."""
        self.configure(mode, self._speed)

    def set_speed(self, speed: int):
        """Définit la vitesse SPI en Hz."""
        self.configure(self._mode, speed)

    def close(self):
        """Ferme le bus SPI."""
        if self._is_open:
            self.spi.close()
            self._is_open = False
            logger.info(f"SPI fermé sur bus {self.bus}, périphérique {self.device}")
