#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour diagnostiquer les problèmes d'importation dans le projet.
Ce script tente d'importer différents modules et rapporte les succès/échecs.
"""

import sys
import os
import importlib
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ImportTest")

# Ajouter le répertoire parent (src) au chemin Python
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
    logger.info(f"Ajout de {src_dir} au chemin Python")

logger.info(f"Chemin Python actuel: {sys.path}")

# Liste des modules à tester
modules_to_test = [
    "config.cm5_config",
    "config.pins_cm5",
    "config.settings",
    "config.system_config",
    "hal.spi",
    "hal.gpio",
    "hal.timer",
    "hw.gpio_cm5",
    "app.main"
]

# Tester chaque module
results = []
for module_name in modules_to_test:
    try:
        module = importlib.import_module(module_name)
        results.append((module_name, "SUCCESS", ""))
        logger.info(f"✓ Import réussi: {module_name}")
    except Exception as e:
        results.append((module_name, "FAILED", str(e)))
        logger.error(f"✗ Import échoué: {module_name} - Erreur: {str(e)}")

# Afficher le résumé
logger.info("\n=== RÉSUMÉ DES IMPORTATIONS ===")
success_count = sum(1 for r in results if r[1] == "SUCCESS")
logger.info(f"Total: {len(results)} modules testés")
logger.info(f"Succès: {success_count}")
logger.info(f"Échecs: {len(results) - success_count}")

# Si nécessaire, créer les fichiers __init__.py manquants
if len(results) - success_count > 0:
    logger.info("\nTentative de correction des problèmes d'importation...")
    directories = set()
    for module_name, status, _ in results:
        if status == "FAILED":
            parts = module_name.split('.')
            for i in range(1, len(parts)):
                dir_path = os.path.join(src_dir, *parts[:i])
                directories.add(dir_path)
    
    for directory in directories:
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            try:
                with open(init_file, 'w') as f:
                    f.write("# Auto-generated __init__.py file\n")
                logger.info(f"Créé: {init_file}")
            except Exception as e:
                logger.error(f"Impossible de créer {init_file}: {str(e)}")

    logger.info("\nVeuillez relancer le test pour voir si les problèmes sont résolus.")
