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
        import RPi.GPIO as GPIO
        import spidev
    except ImportError as e:
        print(f"Erreur d'importation des modules réels: {e}")
        print("Installez-les avec: pip install RPi.GPIO spidev")
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
