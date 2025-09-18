# -*- coding: utf-8 -*-
"""
@file        config_loader.py
@brief       Chargeur de configuration JSON pour le système de mesure.
@details     Ce module fournit une fonction simple pour charger et parser
             un fichier de configuration JSON contenant les paramètres
             des capteurs, timeouts et autres paramètres système.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations

# Sérialisation/désérialisation JSON
import json
# Opérations sur les chemins et fichiers
import os

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def load_config(path):
    """
    @brief   Charge un fichier de configuration JSON.
    @details Vérifie l'existence du fichier, l'ouvre en UTF-8 et parse
             le contenu JSON. Le format attendu inclut les timeouts,
             délais entre mesures et configuration des canaux de capteurs.

    @param   path Chemin vers le fichier de configuration JSON.

    @return  Dictionnaire Python contenant les données de configuration.

    @exception FileNotFoundError Si le fichier n'existe pas.
    @exception json.JSONDecodeError Si le fichier n'est pas un JSON valide.

    @example
      Format JSON attendu:
      {
        "timeout_s": 180,
        "inter_measure_sleep_s": 0.1,
        "loop_sleep_s": 1.0,
        "channels": [
          { "channel": 1, "sensor": "Ni1000 TK5000" }
        ]
      }
    """
    # Vérification de l'existence du fichier
    if os.path.exists(path) is False:
        # Lever une exception si le fichier n'existe pas
        raise FileNotFoundError("Config introuvable: " + str(path))
    # Ouverture et lecture du fichier JSON
    with open(path, "r", encoding="utf-8") as f:
        # Parsing du contenu JSON
        data = json.load(f)
    # Retour des données parsées
    return data
