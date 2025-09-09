#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'installation des dépendances pour le projet de régulation chauffage.
Ce script installe les packages nécessaires pour exécuter le projet.
"""
import sys
import subprocess
import platform
import os

def main():
    print("Installation des dépendances pour le projet de régulation chauffage")
    
    # Vérifier si nous sommes sur un Raspberry Pi
    is_raspberry_pi = False
    try:
        if platform.system() == "Linux":
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read()
                is_raspberry_pi = 'Raspberry Pi' in model
    except:
        pass
    
    # Liste des packages à installer
    packages = [
        'spidev',
        'numpy',
        'pyserial',
        'logging',
        'typing',
        'dataclasses'
    ]
    
    # Ajouter RPi.GPIO si nous sommes sur un Raspberry Pi
    if is_raspberry_pi:
        packages.append('RPi.GPIO')
    else:
        print("ATTENTION: Vous n'êtes pas sur un Raspberry Pi.")
        print("Le package RPi.GPIO ne peut pas être installé sur ce système.")
        print("Le code ne fonctionnera qu'en mode simulation.")
    
    # Installation des packages
    for package in packages:
        print(f"Installation du package {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"  ✓ {package} installé avec succès")
        except subprocess.CalledProcessError:
            print(f"  ✗ Erreur lors de l'installation de {package}")
    
    print("\nInstallation terminée.")
    print("Vous pouvez maintenant exécuter le projet.")

if __name__ == "__main__":
    main()
