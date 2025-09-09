#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test autonome pour le capteur de température LM70 en utilisant SPI.

Ce script peut être exécuté indépendamment pour tester la communication SPI
avec un capteur LM70, sans dépendre du reste du système.

Instructions:
1. Connecter le LM70:
   - MISO à GPIO 19 (SPI1_MISO)
   - SCLK à GPIO 21 (SPI1_SCLK)
   - CS à GPIO 5 (ou autre GPIO libre)
   - VDD à 3.3V ou 5V
   - GND à GND
2. Exécuter ce script directement: python test_lm70.py
"""

import time
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lm70_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LM70_Test")

try:
    # Option 1: Utiliser les modules du projet (si disponibles)
    use_project_modules = False
    
    if use_project_modules:
        logger.info("Utilisation des modules du projet")
        from hw.gpio_cm5 import GPIO
        from config.cm5_config import _open_spi
    else:
        # Option 2: Utiliser directement RPi.GPIO et spidev
        logger.info("Utilisation directe de RPi.GPIO et spidev")
        import RPi.GPIO as GPIO
        import spidev
        
        # Configuration du GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        def _open_spi(config):
            """Initialise et configure une interface SPI"""
            try:
                spi = spidev.SpiDev()
                spi.open(config["bus"], config["device"])
                spi.max_speed_hz = config["max_hz"]
                spi.mode = config["mode"]
                spi.bits_per_word = config["bits"]
                return spi
            except Exception as e:
                logger.error(f"Erreur configuration SPI: {str(e)}")
                raise

    # Test du LM70
    def test_lm70():
        """Fonction de test pour le capteur LM70"""
        # Configuration SPI pour le LM70
        lm70_config = {
            "bus": 0,            # Bus 0 sur CM5
            "device": 0,         # Device 0 sur CM5
            "max_hz": 1000000,   # 1MHz
            "mode": 0,           # Mode 0 (CPOL=0, CPHA=0)
            "bits": 8,           # 8 bits par mot
            "lsbfirst": False    # MSB first
        }
        
        # Configuration CS pour le LM70
        LM70_CS_PIN = 5          # GPIO libre
        GPIO.setup(LM70_CS_PIN, GPIO.OUT, initial=GPIO.HIGH)
        
        # Ouvre SPI pour le LM70
        spi_lm70 = _open_spi(lm70_config)
        
        try:
            logger.info("Démarrage du test du capteur LM70...")
            logger.info("Connexions: MISO->GPIO19, SCLK->GPIO21, CS->GPIO5")
            
            # Fonction de lecture de température
            def read_lm70_temp():
                try:
                    GPIO.output(LM70_CS_PIN, GPIO.LOW)  # Active CS
                    
                    # Lecture de 2 octets
                    resp = spi_lm70.xfer2([0x00, 0x00])
                    
                    # Traitement des données (format 11-bit)
                    raw_value = ((resp[0] << 8) | resp[1]) >> 5
                    
                    # Gestion du signe (complément à 2)
                    if raw_value & 0x400:  # Bit de signe à 1
                        temp_c = -((~raw_value & 0x7FF) + 1) * 0.125
                    else:
                        temp_c = raw_value * 0.125
                    
                    return temp_c
                
                finally:
                    GPIO.output(LM70_CS_PIN, GPIO.HIGH)  # Désactive CS
            
            # Test de lecture (10 mesures)
            temps = []
            for i in range(10):
                temp = read_lm70_temp()
                temps.append(temp)
                logger.info(f"Lecture {i+1}/10: {temp:.2f}°C")
                time.sleep(1)
            
            # Statistiques
            avg_temp = sum(temps) / len(temps)
            min_temp = min(temps)
            max_temp = max(temps)
            
            logger.info(f"Test terminé. Résultats:")
            logger.info(f"  - Température moyenne: {avg_temp:.2f}°C")
            logger.info(f"  - Température minimale: {min_temp:.2f}°C")
            logger.info(f"  - Température maximale: {max_temp:.2f}°C")
            logger.info(f"  - Variation: {max_temp - min_temp:.2f}°C")
            
        finally:
            # Nettoyage
            spi_lm70.close()
            GPIO.cleanup(LM70_CS_PIN)
            logger.info("Ressources libérées")
    
    # Exécution du test
    if __name__ == "__main__":
        test_lm70()
    
except Exception as e:
    logger.error(f"Erreur: {str(e)}")
    if hasattr(e, "__traceback__"):
        import traceback
        logger.error(traceback.format_exc())
