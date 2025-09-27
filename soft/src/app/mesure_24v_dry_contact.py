# -*- coding: utf-8 -*-
"""
@file        mesure_24v_dry_contact.py
@brief       Module de test des entrées/sorties 24V pour contacts secs.
@details     Ce module fournit des fonctions pour tester et valider les
             contacts secs via les interfaces I/O 24V. Permet de détecter
             l'état des contacts (ouvert/fermé) sur deux canaux indépendants
             avec gestion des GPIO et temporisations appropriées.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations

# Fonctions temporelles pour les délais de stabilisation
import time
# Bibliothèque pour la gestion des GPIO
from periphery import GPIO
# Importation des constantes matérielles pour les chemins GPIO
from pins_cm5 import GPIO_CHIP_PATH

# ---------------------------------------------------------------------------
# Constantes du module
# ---------------------------------------------------------------------------

# Sortie 24V canal 1
CM_24V_OUT_1 = 13
# Sense 24V canal 1
CM_24V_SENSE_1 = 14
# Sortie 24V canal 2
CM_24V_OUT_2 = 15
# Sense 24V canal 2
CM_24V_SENSE_2 = 16

# ---------------------------------------------------------------------------
# Variables globales d'état
# ---------------------------------------------------------------------------

# 0=ouvert, 1=fermé
io_24v_ch1_ok = 0
# 0=ouvert, 1=fermé
io_24v_ch2_ok = 0

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def test_24v_dry_contact():
    """
    @brief   Test des contacts secs I/O 24V.
    @details Effectue un test complet des deux canaux de contacts secs 24V.
             Active séquentiellement chaque sortie et lit l'état du capteur
             correspondant pour déterminer si le contact est fermé ou ouvert.
             Met à jour les variables globales d'état et affiche les résultats.

    @return  Tuple contenant l'état des deux canaux (ch1_state, ch2_state).
             Valeurs: 0=ouvert, 1=fermé.

    @note    Utilise des temporisations pour la stabilisation des signaux.
    @note    CRITIQUE: GPIO sense configurés avec bias="disable" pour éviter 
             les pull-down internes qui faussent la mesure du diviseur résistif.
    """
    global io_24v_ch1_ok, io_24v_ch2_ok
    
    # Affichage du début du test
    print("\n[TEST-24V] === Test contacts secs I/O 24V ===")
    
    try:
        # Configuration GPIO
        # Configuration de la sortie 24V canal 1
        out1 = GPIO(GPIO_CHIP_PATH, CM_24V_OUT_1, "out")
        # Configuration immédiate à l'état OFF (MOSFET P: True = OFF)
        out1.write(True)
        # Configuration de la sortie 24V canal 2
        out2 = GPIO(GPIO_CHIP_PATH, CM_24V_OUT_2, "out")
        # Configuration immédiate à l'état OFF (MOSFET P: True = OFF)
        out2.write(True)
        # Configuration de l'entrée sense canal 1 (CRITIQUE: désactiver pull-down)
        sense1 = GPIO(GPIO_CHIP_PATH, CM_24V_SENSE_1, "in", bias="disable")
        # Configuration de l'entrée sense canal 2 (CRITIQUE: désactiver pull-down)
        sense2 = GPIO(GPIO_CHIP_PATH, CM_24V_SENSE_2, "in", bias="disable")
        
        # Test Canal 1
        # Mise au repos (MOSFET P: True = OFF)
        out1.write(True)
        # Temporisation de stabilisation
        time.sleep(0.01)
        # Activation (MOSFET P: False = ON)
        out1.write(False)
        # Stabilisation
        time.sleep(0.02)
        # Lecture de l'état du capteur
        state1 = sense1.read()
        # Désactivation (MOSFET P: True = OFF)
        out1.write(True)
        
        # Interprétation du résultat canal 1
        if state1:
            print("[TEST-24V] Canal 1: fermé")
            # Contact fermé détecté
            io_24v_ch1_ok = 1
        else:
            print("[TEST-24V] Canal 1: ouvert")
            # Contact ouvert détecté
            io_24v_ch1_ok = 0
        
        # Test Canal 2
        # Mise au repos (MOSFET P: True = OFF)
        out2.write(True)
        # Temporisation de stabilisation
        time.sleep(0.01)
        # Activation (MOSFET P: False = ON)
        out2.write(False)
        # Stabilisation
        time.sleep(0.02)
        # Lecture de l'état du capteur
        state2 = sense2.read()
        # Désactivation (MOSFET P: True = OFF)
        out2.write(True)
        
        # Interprétation du résultat canal 2
        if state2:
            print("[TEST-24V] Canal 2: fermé")
            # Contact fermé détecté
            io_24v_ch2_ok = 1
        else:
            print("[TEST-24V] Canal 2: ouvert")
            # Contact ouvert détecté
            io_24v_ch2_ok = 0
        
        # Nettoyage
        # Fermeture des GPIO de sortie
        out1.close()
        out2.close()
        # Fermeture des GPIO d'entrée
        sense1.close()
        sense2.close()
        
        # Affichage du résultat final
        print(f"[TEST-24V] Résultat: CH1={io_24v_ch1_ok}, CH2={io_24v_ch2_ok}")
        
        # Retour du tuple d'état
        return (io_24v_ch1_ok, io_24v_ch2_ok)
        
    except Exception as e:
        # Gestion des erreurs de test
        print(f"[TEST-24V] Erreur: {e}")
        # Remise à zéro des états en cas d'erreur
        io_24v_ch1_ok = 0
        io_24v_ch2_ok = 0
        # Retour d'état d'erreur
        return (0, 0)

def get_dry_contact_status():
    """
    @brief   Retourne l'état actuel des contacts secs.
    @details Fonction utilitaire qui retourne les derniers états mesurés
             des contacts secs sans effectuer de nouveau test. Utilise
             les variables globales mises à jour par test_24v_dry_contact().

    @return  Dictionnaire contenant l'état des deux canaux.
             Format: {"ch1": 0|1, "ch2": 0|1}
             Valeurs: 0=ouvert, 1=fermé.
    """
    # Retour du dictionnaire d'état des contacts
    return {
        "ch1": io_24v_ch1_ok,
        "ch2": io_24v_ch2_ok
    }