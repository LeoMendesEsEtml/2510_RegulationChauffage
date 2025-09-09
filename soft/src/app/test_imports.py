#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier que les importations fonctionnent correctement.
Exécutez ce script pour valider la configuration de votre environnement Python.
"""

import sys
import os

# Affichage de l'environnement Python
print("="*80)
print(f"Version Python: {sys.version}")
print(f"Emplacement Python: {sys.executable}")
print(f"Répertoire courant: {os.getcwd()}")
print(f"Chemins Python: {sys.path}")
print("="*80)

# Ajouter le répertoire src au chemin Python
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)  # Remonte d'un niveau vers src
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
    print(f"Ajout de {src_dir} au chemin Python")

# Liste des modules à tester
modules_to_test = [
    "config.cm5_config",
    "drivers.mux_adg731",
    "drivers.adc_ads124s08",
    "Metrology.convert",
    "Metrology.sensor_profiles",
    "hw.gpio_cm5",
    "io.dry_contacts",
    "api.external",
    "control.regulation"
]

# Test d'importation de chaque module
print("\nTest d'importation des modules:")
print("-"*50)

success_count = 0
failed_modules = []

for module_name in modules_to_test:
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
        success_count += 1
    except ImportError as e:
        print(f"✗ {module_name}: {e}")
        failed_modules.append((module_name, str(e)))
    except Exception as e:
        print(f"! {module_name}: {e.__class__.__name__}: {e}")
        failed_modules.append((module_name, f"{e.__class__.__name__}: {e}"))

# Résumé
print("\nRésumé des tests:")
print("-"*50)
print(f"Modules testés: {len(modules_to_test)}")
print(f"Succès: {success_count}")
print(f"Échecs: {len(failed_modules)}")

if failed_modules:
    print("\nModules en échec:")
    for module, error in failed_modules:
        print(f"  - {module}: {error}")
    
    print("\nSuggestions de résolution:")
    print("1. Vérifiez que tous les fichiers __init__.py sont présents dans chaque répertoire")
    print("2. Dans PyCharm, marquez le répertoire 'src' comme 'Sources Root'")
    print("3. Vérifiez qu'il n'y a pas de conflit de noms avec des modules standards Python")
    print("4. Exécutez ce script depuis le répertoire parent de 'src'")
else:
    print("\nTous les modules ont été importés avec succès!")
    print("Votre configuration Python est correcte.")

print("\nFin des tests.")
