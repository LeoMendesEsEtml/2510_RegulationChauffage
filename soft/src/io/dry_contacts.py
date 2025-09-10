# -*- coding: utf-8 -*-
"""
Gestion des contacts secs 24V.

Ce module implemente la logique de test et de lecture des contacts secs 24V :
- Configuration des GPIO en entree/sortie
- Activation des sorties 24V
- Lecture des etats des contacts
- Interpretation des resultats

Architecture :
------------
Chaque canal comprend :
- Une sortie pour fournir le +24V via une resistance de pull-up
- Une entree pour detecter l'etat du contact via un diviseur resistif
  * Contact ferme = niveau bas (0V)
  * Contact ouvert = niveau haut (+3.3V)

Le circuit comprend :
- Un MOSFET N-canal (IRLML6344) en low-side pour la detection
- Un diviseur resistif et protection zener pour l'interface 24V/3.3V
"""

import time
from typing import Dict, Tuple
from hal_module.gpio import GPIO
from config_module.pins_cm5 import PINS

class DryContacts:
    """
    Gestionnaire des contacts secs 24V.
    
    Attributes:
        _gpio: Instance du controleur GPIO
        _channels: Dict contenant les paires de broches out/sense pour chaque canal
    """
    
    def __init__(self, gpio: GPIO):
        """
        Initialise le gestionnaire de contacts secs.
        
        Args:
            gpio: Instance du controleur GPIO
        """
        self._gpio = gpio
        self._channels = {
            1: (PINS["CM_24V_OUT_1"], PINS["CM_24V_SENSE_1"]),
            2: (PINS["CM_24V_OUT_2"], PINS["CM_24V_SENSE_2"])
        }
        
        # Configure les broches GPIO
        for out_pin, sense_pin in self._channels.values():
            # Sorties 24V
            self._gpio.setup(out_pin, GPIO.OUT)
            self._gpio.output(out_pin, GPIO.LOW)  # Desactive par defaut
            
            # Entrees de detection
            self._gpio.setup(sense_pin, GPIO.IN)

    def read_channel(self, channel: int) -> bool:
        """
        Lit l'etat d'un canal de contact sec.
        
        Args:
            channel: Numero du canal a lire (1 ou 2)
            
        Returns:
            True si le contact est ferme, False si ouvert
            
        Raises:
            ValueError: Si le numero de canal est invalide
        """
        if channel not in self._channels:
            raise ValueError(f"Canal invalide: {channel}")
            
        # Recupere les broches du canal
        out_pin, sense_pin = self._channels[channel]
        
        # Active la sortie 24V
        self._gpio.output(out_pin, GPIO.HIGH)
        
        # Attend la stabilisation du signal (100us)
        time.sleep(0.0001)
        
        # Lit l'etat de l'entree (inverse car niveau bas = contact ferme)
        state = not self._gpio.input(sense_pin)
        
        # Desactive la sortie
        self._gpio.output(out_pin, GPIO.LOW)
        
        return state

    def read_all_channels(self) -> Dict[int, bool]:
        """
        Lit l'etat de tous les canaux de contacts secs.
        
        Returns:
            Dict avec le numero de canal comme cle et l'etat comme valeur
            True = contact ferme, False = contact ouvert
        """
        return {
            channel: self.read_channel(channel)
            for channel in self._channels.keys()
        }
