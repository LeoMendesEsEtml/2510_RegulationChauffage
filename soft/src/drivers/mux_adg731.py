# -*- coding: utf-8 -*-
"""
Driver pour le multiplexeur analogique ADG731 d'Analog Devices.

Caractéristiques principales:
- Multiplexeur 32:1
- Interface série compatible SPI
- Faible résistance RON (4? typ.)
- Large plage de tension d'alimentation (±15V)
- Faible consommation (0.001?W typ.)

Particularités d'implémentation:
- Interface: Utilise MOSI et SCLK du SPI
- MISO non utilisé (pas de retour de données)
- Jusqu'à 4 circuits peuvent être contrôlés (CS1-CS4)
- L'adresse est échantillonnée sur front montant de CS

Référence: https://www.analog.com/en/products/adg731.html
"""

from time import sleep                # Pour les délais précis
from typing import List, Optional    # Pour le typage statique
from hw.gpio_cm5 import GPIO         # Pour le contrôle des broches GPIO

class Adg731:
    """
    Contrôle d'un ou plusieurs multiplexeurs ADG731.
    Supporte jusqu'à 4 circuits en parallèle.
    """
    
    def __init__(self, spi, cs_pins: List[int], gpio=GPIO, t_cs_us: float = 2):
        """
        Initialise l'interface avec le(s) ADG731.

        Args:
            spi: Instance du bus SPI configuré
            cs_pins: Liste des broches GPIO pour CS [CS1..CS4]
            gpio: Interface GPIO à utiliser
            t_cs_us: Délai après CS en microsecondes (min 20ns)

        Raises:
            ValueError: Si les paramètres sont invalides
        """
        # Validation des paramètres
        if not cs_pins:
            raise ValueError("La liste des broches CS ne peut pas être vide")
        if t_cs_us < 0.02:  # 20ns minimum selon datasheet
            raise ValueError("Délai CS trop court (min 20ns)")
            
        # Stockage des paramètres
        self.spi = spi                # Interface SPI
        self.cs_pins = cs_pins        # Liste des broches CS
        self.gpio = gpio              # Interface GPIO
        # Conversion µs -> s pour sleep()
        self.t_cs = float(t_cs_us) / 1000000.0
        self._card = 0                # Index de la carte active

        # Configuration des broches CS
        # Toutes en sortie, état initial inactif (haut)
        for cs in self.cs_pins:
            self.gpio.setup(cs, self.gpio.OUT, initial=1)

    def select_card(self, index: int) -> None:
        """
        Sélectionne un circuit ADG731 via son CS.
        
        Args:
            index: Index du circuit (0..len(cs_pins)-1)
            
        Raises:
            ValueError: Si l'index est hors limites
        """
        # Validation de l'index
        if not 0 <= index < len(self.cs_pins):
            raise ValueError(f"Index hors limites (0..{len(self.cs_pins)-1})")
        self._card = index

    def _cs_low(self) -> None:
        """
        Active le CS du circuit sélectionné (état bas).
        L'adresse est échantillonnée sur ce front.
        """
        self.gpio.output(self.cs_pins[self._card], 0)

    def _cs_high(self) -> None:
        """
        Désactive le CS du circuit sélectionné (état haut).
        Le multiplexeur change de canal sur ce front.
        """
        self.gpio.output(self.cs_pins[self._card], 1)

    def set_channel(self, addr: int) -> None:
        """
        Sélectionne un canal sur le multiplexeur actif.
        
        Args:
            addr: Numéro du canal (0..31)
            
        Raises:
            ValueError: Si l'adresse est invalide
            
        Note: L'adresse est envoyée sur 8 bits mais seuls
              les 5 bits de poids faible sont utilisés.
        """
        # Validation de l'adresse
        if not 0 <= addr <= 31:
            raise ValueError("L'adresse doit être entre 0 et 31")

        # Séquence de sélection:
        # 1. CS bas (échantillonne l'adresse)
        # 2. Envoi de l'adresse (8 bits)
        # 3. CS haut (applique la sélection)
        # 4. Délai pour stabilisation
        self._cs_low()
        self.spi.xfer2([addr & 0xFF])  # Masque sur 8 bits
        self._cs_high()

        # Délai de stabilisation si configuré
        if self.t_cs > 0.0:
            sleep(self.t_cs)

    def power_down(self) -> None:
        """
        Met le multiplexeur en haute impédance.
        
        Cette méthode envoie une adresse invalide (0xFF)
        pour forcer tous les switchs en haute impédance.
        
        Note: Le comportement exact dépend du câblage.
        """
        self._cs_low()
        self.spi.xfer2([0xFF])  # Adresse invalide
        self._cs_high()
        
        if self.t_cs > 0.0:
            sleep(self.t_cs)

    def nop(self) -> None:
        """
        Exécute un cycle CS sans changer de canal.
        
        Utile pour:
        - Réappliquer la sélection actuelle
        - Synchronisation
        - Test de communication
        """
        self._cs_low()
        self.spi.xfer2([0x00])  # Donnée sans effet
        self._cs_high()
        
        if self.t_cs > 0.0:
            sleep(self.t_cs)
