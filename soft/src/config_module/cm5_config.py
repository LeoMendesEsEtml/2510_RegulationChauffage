# -*- coding: utf-8 -*-
"""
@file        cm5_config.py
@brief       Configuration matérielle pour plateforme CM5.
@details     Ce module fournit la configuration des canaux ADC et la fonction
             d'initialisation complète du matériel (LED, TMUX, ADC). Centralise
             la création des instances matérielles avec câblage fixe CM5.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

# Import de la bibliothèque GPIO pour contrôle matériel
from periphery import GPIO
# Import des définitions de pins spécifiques CM5
from app.pins_cm5 import GPIO_CHIP_PATH, FRONT_LED
# Import du driver multiplexeur TMUX1204
from app.hw_tmux1204 import Tmux1204
# Import du driver ADC ADS124S08
from app.adc_ads124s08 import Ads124s08


# ---------------------------------------------------------------------------
# Constantes de configuration matérielle
# ---------------------------------------------------------------------------

# Liste des canaux ADC disponibles sur la plateforme CM5
ADC_CHANNELS = [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Fonctions d'initialisation matérielle
# ---------------------------------------------------------------------------

def build_hw():
    """
    @brief   Initialise et configure tout le matériel CM5.
    @details Crée les instances des composants matériels avec configuration
             fixe: LED frontale, multiplexeur TMUX et ADC. Configure la LED
             en sortie et l'allume immédiatement pour indication système.

    @return  Dictionnaire contenant toutes les instances matérielles:
             - "led": Instance GPIO pour LED frontale
             - "tmux": Instance Tmux1204 pour sélection canaux
             - "adc": Instance Ads124s08 pour conversion analogique

    @warning LED allumée automatiquement pour indiquer système actif.
    """
    # Création de l'instance GPIO pour LED frontale en mode sortie
    led = GPIO(GPIO_CHIP_PATH, FRONT_LED, "out")
    # Allumage immédiat de la LED pour indication système démarré
    led.write(True)
    # Création de l'instance multiplexeur pour sélection des canaux
    tmux = Tmux1204()
    # Création de l'instance ADC pour conversions analogique-numérique
    adc = Ads124s08()
    # Création du dictionnaire de retour avec toutes les instances
    hw = {}
    # Ajout de l'instance LED au dictionnaire matériel
    hw["led"] = led
    # Ajout de l'instance TMUX au dictionnaire matériel
    hw["tmux"] = tmux
    # Ajout de l'instance ADC au dictionnaire matériel
    hw["adc"] = adc
    # Retour du dictionnaire complet des composants initialisés
    return hw
