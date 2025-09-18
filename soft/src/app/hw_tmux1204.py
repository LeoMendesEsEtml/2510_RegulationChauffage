# -*- coding: utf-8 -*-
"""
@file        hw_tmux1204.py
@brief       Pilote pour multiplexeur TMUX1204 de sélection de résistance de référence.
@details     Ce module fournit un pilote pour contrôler le multiplexeur TMUX1204
             via les signaux de contrôle ADC_A1 et ADC_A0. Permet la sélection
             de quatre valeurs de résistance de référence (2.2k, 2.7k, 10k, 100k)
             selon une table de vérité définie.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations

# Bibliothèque pour la gestion des GPIO
from periphery import GPIO
# Importation des constantes matérielles
from pins_cm5 import GPIO_CHIP_PATH, ADC_A1, ADC_A0

# ---------------------------------------------------------------------------
# Classes principales
# ---------------------------------------------------------------------------

class Tmux1204:
    """
    @brief   Pilote pour le multiplexeur TMUX1204.
    @details Classe pour gérer la sélection de résistance de référence via
             le multiplexeur TMUX1204. Utilise deux signaux de contrôle
             (A1, A0) pour sélectionner parmi quatre valeurs de Rref selon
             la table de vérité :
             - A1=0, A0=0 : 2.2k ohms
             - A1=0, A0=1 : 2.7k ohms  
             - A1=1, A0=0 : 10k ohms
             - A1=1, A0=1 : 100k ohms
    """
    
    def __init__(self):
        """
        @brief   Initialise le pilote TMUX1204.
        @details Configure les GPIO pour les signaux de contrôle A1 et A0
                 en mode sortie. Utilise les constantes matérielles définies
                 dans le module pins_cm5.
        """
        # Initialisation des GPIO pour les sorties A1 et A0
        # GPIO pour A1
        self.gpio_a1 = GPIO(GPIO_CHIP_PATH, ADC_A1, "out")
        # GPIO pour A0
        self.gpio_a0 = GPIO(GPIO_CHIP_PATH, ADC_A0, "out")

    def close(self):
        """
        @brief   Ferme les interfaces GPIO.
        @details Ferme proprement les GPIO A1 et A0 pour libérer les
                 ressources système. Gère les erreurs de fermeture pour
                 éviter les exceptions lors du nettoyage.
        """
        # Fermeture des GPIO
        try:
            # Ferme le GPIO A1
            self.gpio_a1.close()
        except Exception:
            # Ignore les erreurs
            pass
        try:
            # Ferme le GPIO A0
            self.gpio_a0.close()
        except Exception:
            # Ignore les erreurs
            pass

    def set_bits(self, bit_a1, bit_a0):
        """
        @brief   Définit les bits de contrôle A1 et A0.
        @details Applique les niveaux logiques sur les signaux de contrôle
                 du multiplexeur. Convertit les valeurs numériques (0/1)
                 en niveaux logiques GPIO (False/True).

        @param   bit_a1 Valeur du bit A1 (0 ou 1).
        @param   bit_a0 Valeur du bit A0 (0 ou 1).
        """
        # Définit les bits A1 et A0 (0 ou 1)
        # Configuration du signal A1
        if bit_a1 == 0:
            # Écrit 0 sur A1
            self.gpio_a1.write(False)
        else:
            # Écrit 1 sur A1
            self.gpio_a1.write(True)
        # Configuration du signal A0
        if bit_a0 == 0:
            # Écrit 0 sur A0
            self.gpio_a0.write(False)
        else:
            # Écrit 1 sur A0
            self.gpio_a0.write(True)

    def select_rref_ohm(self, rref_ohm):
        """
        @brief   Sélectionne la résistance de référence Rref.
        @details Configure les signaux de contrôle selon la table de vérité
                 pour sélectionner la résistance de référence demandée.
                 Supporte quatre valeurs fixes : 2200, 2700, 10000, 100000 ohms.

        @param   rref_ohm Valeur de résistance de référence en ohms.

        @exception ValueError Si la valeur de Rref n'est pas supportée.

        @note    Table de vérité TMUX1204 :
                 - 2200 ohms  : A1=0, A0=0
                 - 2700 ohms  : A1=0, A0=1
                 - 10000 ohms : A1=1, A0=0
                 - 100000 ohms: A1=1, A0=1
        """
        # Sélectionne la résistance de référence Rref
        # Rref supportées: 2200, 2700, 10000, 100000
        # Vérification pour 2.2k ohms
        if rref_ohm == 2200:
            # A1=0, A0=0 pour 2.2k
            self.set_bits(0, 0)
        else:
            # Vérification pour 2.7k ohms
            if rref_ohm == 2700:
                # A1=0, A0=1 pour 2.7k
                self.set_bits(0, 1)
            else:
                # Vérification pour 10k ohms
                if rref_ohm == 10000:
                    # A1=1, A0=0 pour 10k
                    self.set_bits(1, 0)
                else:
                    # Vérification pour 100k ohms
                    if rref_ohm == 100000:
                        # A1=1, A0=1 pour 100k
                        self.set_bits(1, 1)
                    else:
                        # Erreur si Rref non valide
                        raise ValueError("Rref non supportée: " + str(rref_ohm))
