#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importation automatique des mocks RPi.GPIO et spidev si nécessaire.

Ce module détecte automatiquement si nous sommes sur un Raspberry Pi
et importe les versions réelles ou simulées des modules en conséquence.

Usage:
    from mock_imports import GPIO, spidev
"""

import sys
import platform
import os

# Détecter si nous sommes sur un Raspberry Pi
is_raspberry_pi = False
try:
    if platform.system() == "Linux":
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            is_raspberry_pi = 'Raspberry Pi' in model
except:
    pass

# Importer les modules réels ou les mocks
if is_raspberry_pi:
    print("Détection d'un Raspberry Pi - Utilisation des modules réels")
    try:
        import gpiod
        import spidev
        import logging
        
        logger = logging.getLogger("GPIO-Driver")
        
        # Création d'une classe de compatibilité GPIO pour gpiod
        class GPIO:
            OUT = 'out'
            IN = 'in'
            HIGH = 1
            LOW = 0
            BCM = 'bcm'
            BOARD = 'board'
            _mode = BCM
            _chip = None
            _lines = {}
            
            @staticmethod
            def setmode(mode):
                GPIO._mode = mode
                try:
                    GPIO._chip = gpiod.Chip('gpiochip0')
                    logger.info(f"GPIO chip ouvert: {GPIO._chip.name}")
                except Exception as e:
                    logger.error(f"Erreur lors de l'ouverture du chip GPIO: {e}")
                    raise
            
            @staticmethod
            def setwarnings(flag):
                pass
            
            @staticmethod
            def setup(channel, direction, initial=None):
                if GPIO._chip is None:
                    GPIO.setmode(GPIO.BCM)
                if initial is None:
                    initial = GPIO.LOW
                try:
                    line = GPIO._chip.get_line(channel)
                    line.request(consumer='test_lm70', type=gpiod.LINE_REQ_DIR_OUT)
                    GPIO._lines[channel] = line
                    line.set_value(initial)
                    logger.info(f"GPIO {channel} configuré en sortie, valeur initiale: {initial}")
                except Exception as e:
                    logger.error(f"Erreur lors de la configuration du GPIO {channel}: {e}")
                    raise
            
            @staticmethod
            def output(channel, value):
                if channel in GPIO._lines:
                    try:
                        GPIO._lines[channel].set_value(value)
                        logger.debug(f"GPIO {channel} mis à {value}")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'écriture sur le GPIO {channel}: {e}")
                        raise
                else:
                    raise RuntimeError(f"GPIO {channel} non configuré")
            
            @staticmethod
            def cleanup():
                if GPIO._chip:
                    for channel, line in GPIO._lines.items():
                        try:
                            line.release()
                            logger.info(f"GPIO {channel} libéré")
                        except Exception as e:
                            logger.error(f"Erreur lors de la libération du GPIO {channel}: {e}")
                    GPIO._lines.clear()
                    GPIO._chip = None
                    logger.info("Nettoyage GPIO terminé")
    except ImportError as e:
        print(f"Erreur d'importation des modules réels: {e}")
        print("Installez-les avec: sudo apt install -y python3-gpiod spidev")
        sys.exit(1)
else:
    print("Pas de Raspberry Pi détecté - Utilisation des modules simulés")
    # Importer les mocks
    module_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, module_dir)
    
    # Importer RPi_mock.py
    try:
        from RPi_mock import RPi
        GPIO = RPi.GPIO
        from RPi_mock import SpiDev as spidev_mock
        
        # Créer un module factice spidev
        class spidev:
            SpiDev = spidev_mock
        
        print("Modules simulés chargés avec succès")
    except ImportError as e:
        print(f"Erreur d'importation des modules simulés: {e}")
        sys.exit(1)
