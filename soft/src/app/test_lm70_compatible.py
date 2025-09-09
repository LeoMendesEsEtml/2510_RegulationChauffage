#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test LM70 avec support automatique pour simulateur et hardware réel.
Ce script fonctionnera aussi bien sur un PC que sur un Raspberry Pi.

Connexions matérielles spécifiques :
- LM70 MISO → GPIO 19 (SPI_MISO_ADC_GPIO)
- LM70 MOSI → GPIO 20 (SPI_MOSI_ADC_GPIO)
- LM70 SCLK → GPIO 21 (SPI_SCLK_ADC_GPIO)
- LM70 CS → GPIO 18 (GPIO libre)
"""

import logging
import os
import sys
import time
import spidev

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LM70-Test")

# Définition des GPIO SPI1
LM70_CS_GPIO = 18  # GPIO 18 utilisé comme CS
SPI_MOSI_ADC_GPIO = 20
SPI_MISO_ADC_GPIO = 19
SPI_SCLK_ADC_GPIO = 21

# Déterminer le chemin absolu du script
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir) if "src" in current_dir else current_dir

# Importer le module de mock automatique
sys.path.insert(0, src_dir)
try:
    from mock_imports import GPIO
    logger.info("Module d'importation automatique chargé avec succès")
except ImportError:
    logger.error("Impossible d'importer le module mock_imports.py")
    logger.error("Assurez-vous que le fichier mock_imports.py est présent dans le répertoire src")
    sys.exit(1)

# Configuration SPI pour le LM70
spi = spidev.SpiDev()
spi.open(1, 0)  # Bus 1, Device 0 (SPI1)
spi.max_speed_hz = 100000  # 100 kHz
spi.mode = 0  # Mode 0: CPOL=0, CPHA=0
spi.bits_per_word = 8

def test_lm70():
    """Test de communication SPI avec le capteur LM70"""
    try:
        # Configuration GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configuration du GPIO CS pour le LM70
        GPIO.setup(LM70_CS_GPIO, GPIO.OUT, initial=GPIO.HIGH)

        logger.info("Début du test LM70")
        
        while True:  # Boucle infinie pour tester en continu
            # Active CS
            GPIO.output(LM70_CS_GPIO, GPIO.LOW)
            
            # Envoi de données arbitraires sur MOSI
            resp = spi.xfer2([0xAA, 0xBB])
            
            # Désactive CS
            GPIO.output(LM70_CS_GPIO, GPIO.HIGH)

            logger.info(f"Données SPI reçues : {resp}")
            
            # Vérification des données reçues
            if len(resp) == 2:
                # Combine les 2 octets en un entier 16 bits
                raw_temp = (resp[0] << 8) | resp[1]
                
                # Les 3 bits les plus significatifs sont inutilisés
                temp_celsius = ((raw_temp >> 3) & 0x1FFF) * 0.03125
                
                logger.info(f"Température mesurée : {temp_celsius:.2f}°C")
            else:
                logger.warning("Données SPI invalides - vérifiez les connexions")
            
            # Délai pour éviter de saturer le bus SPI
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        logger.info("Test interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur lors du test LM70 : {e}")
    
    finally:
        GPIO.cleanup()
        spi.close()

if __name__ == "__main__":
    test_lm70()
