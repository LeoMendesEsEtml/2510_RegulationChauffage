#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Émulation de RPi.GPIO et spidev pour les tests hors Raspberry Pi.

Ce module fournit des versions simulées de RPi.GPIO et spidev
pour permettre le développement et le test sur un PC sans Raspberry Pi.

Usage:
    import sys
    sys.modules['RPi'] = __import__('RPi_mock')
    sys.modules['RPi.GPIO'] = RPi.GPIO
    sys.modules['spidev'] = __import__('spidev_mock')
"""

class GPIO:
    """Émulation de RPi.GPIO"""
    # Constantes
    BCM = 11
    BOARD = 10
    OUT = 0
    IN = 1
    HIGH = 1
    LOW = 0
    PUD_OFF = 0
    PUD_DOWN = 1
    PUD_UP = 2
    
    # État interne
    _mode = None
    _warnings = True
    _pins = {}
    
    @classmethod
    def setmode(cls, mode):
        """Définit le mode de numérotation des broches (BCM ou BOARD)"""
        cls._mode = mode
        print(f"[GPIO Mock] Mode défini: {'BCM' if mode == cls.BCM else 'BOARD'}")
    
    @classmethod
    def setwarnings(cls, flag):
        """Active ou désactive les avertissements"""
        cls._warnings = flag
        print(f"[GPIO Mock] Avertissements: {'activés' if flag else 'désactivés'}")
    
    @classmethod
    def setup(cls, pin, direction, initial=None, pull_up_down=None):
        """Configure une broche GPIO"""
        cls._pins[pin] = {
            'direction': direction,
            'value': initial if initial is not None else 0,
            'pull': pull_up_down
        }
        state = 'sortie' if direction == cls.OUT else 'entrée'
        pull = ''
        if pull_up_down == cls.PUD_UP:
            pull = ' avec pull-up'
        elif pull_up_down == cls.PUD_DOWN:
            pull = ' avec pull-down'
        
        print(f"[GPIO Mock] Broche {pin} configurée en {state}{pull}")
    
    @classmethod
    def output(cls, pin, value):
        """Définit la valeur d'une broche de sortie"""
        if pin not in cls._pins:
            if cls._warnings:
                print(f"[GPIO Mock] AVERTISSEMENT: Broche {pin} non configurée")
            cls._pins[pin] = {'direction': cls.OUT, 'value': 0, 'pull': None}
        
        if cls._pins[pin]['direction'] != cls.OUT and cls._warnings:
            print(f"[GPIO Mock] AVERTISSEMENT: Broche {pin} non configurée comme sortie")
        
        cls._pins[pin]['value'] = value
        print(f"[GPIO Mock] Broche {pin} = {value}")
    
    @classmethod
    def input(cls, pin):
        """Lit la valeur d'une broche d'entrée"""
        if pin not in cls._pins:
            if cls._warnings:
                print(f"[GPIO Mock] AVERTISSEMENT: Broche {pin} non configurée")
            return 0
        
        # Simulation de valeur (ici toujours 0 pour simplifier)
        value = cls._pins[pin]['value']
        print(f"[GPIO Mock] Lecture broche {pin} = {value}")
        return value
    
    @classmethod
    def cleanup(cls, pin=None):
        """Nettoie les ressources GPIO"""
        if pin is None:
            pins = list(cls._pins.keys())
            cls._pins = {}
            print(f"[GPIO Mock] Nettoyage de toutes les broches: {pins}")
        else:
            if pin in cls._pins:
                del cls._pins[pin]
                print(f"[GPIO Mock] Nettoyage de la broche {pin}")
            else:
                print(f"[GPIO Mock] La broche {pin} n'est pas configurée")

# Création du module RPi
class RPi:
    GPIO = GPIO

# Émulation de spidev
class SpiDev:
    """Émulation de spidev.SpiDev"""
    def __init__(self):
        self.bus = None
        self.device = None
        self.max_speed_hz = 1000000
        self.mode = 0
        self.bits_per_word = 8
        self._open = False
        print("[SPI Mock] Périphérique SPI créé")
    
    def open(self, bus, device):
        """Ouvre une connexion SPI"""
        self.bus = bus
        self.device = device
        self._open = True
        print(f"[SPI Mock] Bus SPI ouvert: bus={bus}, device={device}")
    
    def xfer(self, data):
        """Transfert SPI simple"""
        print(f"[SPI Mock] Transfert: {data}")
        # Simulation d'une réponse (température de 25°C pour LM70)
        # 25°C = 200 (0xC8) en format fixe point LM70
        # Format 16-bit: 0x00C8 >> 5 = 0x0006 (bits significatifs)
        # Donc les 2 octets seront: [0x00, 0xC8]
        return [0x00, 0xC8]
    
    def xfer2(self, data):
        """Transfert SPI avec CS maintenu actif"""
        print(f"[SPI Mock] Transfert2: {data}")
        # Même simulation que pour xfer
        return [0x00, 0xC8]
    
    def close(self):
        """Ferme la connexion SPI"""
        self._open = False
        print(f"[SPI Mock] Bus SPI fermé: bus={self.bus}, device={self.device}")
