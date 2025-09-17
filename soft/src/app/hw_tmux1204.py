# -*- coding: utf-8 -*-
# fichier : hw_tmux1204.py
"""
TMUX1204 sélection Rref via ADC_A1 et ADC_A0.

Table exacte:
A1 A0 -> Rref
0  0  -> 2.2k
0  1  -> 2.7k
1  0  -> 10k
1  1  -> 100k
"""

from periphery import GPIO  # Bibliothèque pour la gestion des GPIO
from pins_cm5 import GPIO_CHIP_PATH, ADC_A1, ADC_A0  # Importation des constantes matérielles

# Classe pour gérer le multiplexeur TMUX1204
class Tmux1204:
    def __init__(self):
        # Initialisation des GPIO pour les sorties A1 et A0
        self.gpio_a1 = GPIO(GPIO_CHIP_PATH, ADC_A1, "out")  # GPIO pour A1
        self.gpio_a0 = GPIO(GPIO_CHIP_PATH, ADC_A0, "out")  # GPIO pour A0

    def close(self):
        # Fermeture des GPIO
        try:
            self.gpio_a1.close()  # Ferme le GPIO A1
        except Exception:
            pass  # Ignore les erreurs
        try:
            self.gpio_a0.close()  # Ferme le GPIO A0
        except Exception:
            pass  # Ignore les erreurs

    def set_bits(self, bit_a1, bit_a0):
        # Définit les bits A1 et A0 (0 ou 1)
        if bit_a1 == 0:
            self.gpio_a1.write(False)  # Écrit 0 sur A1
        else:
            self.gpio_a1.write(True)  # Écrit 1 sur A1
        if bit_a0 == 0:
            self.gpio_a0.write(False)  # Écrit 0 sur A0
        else:
            self.gpio_a0.write(True)  # Écrit 1 sur A0

    def select_rref_ohm(self, rref_ohm):
        # Sélectionne la résistance de référence Rref
        # Rref supportées: 2200, 2700, 10000, 100000
        if rref_ohm == 2200:
            self.set_bits(0, 0)  # A1=0, A0=0 pour 2.2k
        else:
            if rref_ohm == 2700:
                self.set_bits(0, 1)  # A1=0, A0=1 pour 2.7k
            else:
                if rref_ohm == 10000:
                    self.set_bits(1, 0)  # A1=1, A0=0 pour 10k
                else:
                    if rref_ohm == 100000:
                        self.set_bits(1, 1)  # A1=1, A0=1 pour 100k
                    else:
                        raise ValueError("Rref non supportée: " + str(rref_ohm))  # Erreur si Rref non valide
