# -*- coding: utf-8 -*-
# file: hw_tmux1204.py
"""
TMUX1204 sélection Rref via ADC_A1 et ADC_A0.

Table exacte:
A1 A0 -> Rref
0  0  -> 2.2k
0  1  -> 2.7k
1  0  -> 10k
1  1  -> 100k
"""

from periphery import GPIO
from pins_cm5 import GPIO_CHIP_PATH, ADC_A1, ADC_A0

class Tmux1204:
    def __init__(self):
        # Sorties
        self.gpio_a1 = GPIO(GPIO_CHIP_PATH, ADC_A1, "out")
        self.gpio_a0 = GPIO(GPIO_CHIP_PATH, ADC_A0, "out")

    def close(self):
        try:
            self.gpio_a1.close()
        except Exception:
            pass
        try:
            self.gpio_a0.close()
        except Exception:
            pass

    def set_bits(self, bit_a1, bit_a0):
        # bit_a1 et bit_a0 sont 0 ou 1
        if bit_a1 == 0:
            self.gpio_a1.write(False)
        else:
            self.gpio_a1.write(True)
        if bit_a0 == 0:
            self.gpio_a0.write(False)
        else:
            self.gpio_a0.write(True)

    def select_rref_ohm(self, rref_ohm):
        # Rref supportées: 2200, 2700, 10000, 100000
        if rref_ohm == 2200:
            self.set_bits(0, 0)
        else:
            if rref_ohm == 2700:
                self.set_bits(0, 1)
            else:
                if rref_ohm == 10000:
                    self.set_bits(1, 0)
                else:
                    if rref_ohm == 100000:
                        self.set_bits(1, 1)
                    else:
                        raise ValueError("Rref non supportée: " + str(rref_ohm))
