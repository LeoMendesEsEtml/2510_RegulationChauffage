# -*- coding: utf-8 -*-
"""
Gestion des contacts secs 24V.

Ce module implémente la logique de test et de lecture des contacts secs 24V :
- Configuration des GPIO en entrée/sortie
- Activation des sorties 24V
- Lecture des états des contacts
- Interprétation des résultats

Architecture :
------------
Chaque canal comprend :
- Une sortie pour fournir le +24V via une résistance de pull-up
- Une entrée pour détecter l'état du contact via un diviseur résistif
  * Contact fermé = niveau bas (0V)
  * Contact ouvert = niveau haut (+3.3V)

Le circuit comprend :
- Un MOSFET N-canal (IRLML6344) en low-side pour la détection
- Un diviseur résistif et protection zener pour l'interface 24V/3.3V
"""

import time
from typing import Dict, Tuple
from hal.gpio import GPIO
from config.pins_cm5 import PINS

class DryContacts:
    """
    Gestionnaire des contacts secs 24V.
    
    Attributes:
        _gpio: Instance du contrôleur GPIO
        _channels: Dict contenant les paires de broches out/sense pour chaque canal
    """
    
    def __init__(self, gpio: GPIO):
        """
        Initialise le gestionnaire de contacts secs.
        
        Args:
            gpio: Instance du contrôleur GPIO
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
            self._gpio.output(out_pin, GPIO.LOW)  # Désactivé par défaut
            
            # Entrées de détection
            self._gpio.setup(sense_pin, GPIO.IN)

    def read_channel(self, channel: int) -> bool:
        """
        Lit l'état d'un canal de contact sec.
        
        Args:
            channel: Numéro du canal à lire (1 ou 2)
            
        Returns:
            True si le contact est fermé, False si ouvert
            
        Raises:
            ValueError: Si le numéro de canal est invalide
        """
        if channel not in self._channels:
            raise ValueError(f"Canal invalide: {channel}")
            
        # Récupère les broches du canal
        out_pin, sense_pin = self._channels[channel]
        
        # Active la sortie 24V
        self._gpio.output(out_pin, GPIO.HIGH)
        
        # Attend la stabilisation du signal (100µs)
        time.sleep(0.0001)
        
        # Lit l'état de l'entrée (inversé car niveau bas = contact fermé)
        state = not self._gpio.input(sense_pin)
        
        # Désactive la sortie
        self._gpio.output(out_pin, GPIO.LOW)
        
        return state

    def read_all_channels(self) -> Dict[int, bool]:
        """
        Lit l'état de tous les canaux de contacts secs.
        
        Returns:
            Dict avec le numéro de canal comme clé et l'état comme valeur
            True = contact fermé, False = contact ouvert
        """
        return {
            channel: self.read_channel(channel)
            for channel in self._channels.keys()
        }
