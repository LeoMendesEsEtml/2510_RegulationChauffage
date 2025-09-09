#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test LM70 avec support automatique pour simulateur et hardware réel.
Ce script fonctionnera aussi bien sur un PC que sur un Raspberry Pi.

Connexions (sur Raspberry Pi):
- LM70 MISO → GPIO 19
- LM70 SCLK → GPIO 21
- LM70 CS → GPIO 5
- LM70 VDD → 3.3V
- LM70 GND → GND
"""

import sys
import os
import time
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LM70-Test")

# Déterminer le chemin absolu du script
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir) if "src" in current_dir else current_dir

# Importer le module de mock automatique
sys.path.insert(0, src_dir)
try:
    from mock_imports import GPIO, spidev
    logger.info("Module d'importation automatique chargé avec succès")
except ImportError:
    logger.error("Impossible d'importer le module mock_imports.py")
    logger.error("Assurez-vous que le fichier mock_imports.py est présent dans le répertoire src")
    sys.exit(1)

def test_lm70():
    """Test de communication SPI avec le capteur LM70"""
    try:
        # Configuration GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configuration du GPIO CS pour le LM70
        LM70_CS_PIN = 5
        GPIO.setup(LM70_CS_PIN, GPIO.OUT, initial=GPIO.HIGH)
        
        # Configuration SPI pour le LM70
        spi = spidev.SpiDev()
        spi.open(1, 1)  # Bus 1, Device 1
        spi.max_speed_hz = 1000000  # 1MHz
        spi.mode = 0  # Mode 0: CPOL=0, CPHA=0
        spi.bits_per_word = 8
        
        logger.info("Configuration SPI et GPIO terminée")
        logger.info(f"Connexions: MISO→GPIO19, SCLK→GPIO21, CS→GPIO{LM70_CS_PIN}")
        
        # Fonction de lecture de la température
        def read_lm70_temp():
            try:
                GPIO.output(LM70_CS_PIN, GPIO.LOW)  # Active CS
                
                # Lecture de 2 octets
                resp = spi.xfer2([0x00, 0x00])
                
                # Traitement des données (format 11-bit)
                raw_value = ((resp[0] << 8) | resp[1]) >> 5
                
                # Debug
                logger.debug(f"Octets lus: 0x{resp[0]:02X} 0x{resp[1]:02X}, Valeur brute: 0x{raw_value:03X}")
                
                # Gestion du signe (complément à 2)
                if raw_value & 0x400:  # Bit de signe à 1
                    temp_c = -((~raw_value & 0x7FF) + 1) * 0.125
                else:
                    temp_c = raw_value * 0.125
                
                return temp_c
                
            finally:
                GPIO.output(LM70_CS_PIN, GPIO.HIGH)  # Désactive CS
        
        # Lecture de la température en continu
        try:
            logger.info("Démarrage des lectures de température (Ctrl+C pour arrêter)")
            count = 0
            temps = []
            
            while True:
                temp = read_lm70_temp()
                temps.append(temp)
                count += 1
                
                logger.info(f"Lecture {count}: {temp:.2f}°C")
                
                # Calcul des statistiques toutes les 5 mesures
                if count % 5 == 0 and count > 0:
                    avg = sum(temps[-5:]) / 5
                    min_val = min(temps[-5:])
                    max_val = max(temps[-5:])
                    logger.info(f"Stats (5 dernières): Min={min_val:.2f}°C, Moy={avg:.2f}°C, Max={max_val:.2f}°C")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            # Statistiques finales
            if temps:
                avg = sum(temps) / len(temps)
                min_val = min(temps)
                max_val = max(temps)
                logger.info("\nStatistiques finales:")
                logger.info(f"- Nombre de lectures: {len(temps)}")
                logger.info(f"- Température moyenne: {avg:.2f}°C")
                logger.info(f"- Température minimale: {min_val:.2f}°C")
                logger.info(f"- Température maximale: {max_val:.2f}°C")
                logger.info(f"- Variation: {max_val - min_val:.2f}°C")
            
            logger.info("Test terminé par l'utilisateur")
    
    except Exception as e:
        logger.error(f"Erreur lors du test LM70: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Nettoyage
        try:
            spi.close()
        except:
            pass
        
        try:
            GPIO.cleanup()
        except:
            pass
        
        logger.info("Ressources libérées")

if __name__ == "__main__":
    test_lm70()
