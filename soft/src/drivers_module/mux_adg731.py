# coding: utf-8
# Validation des parametres
# Stockage des parametres
# Conversion us -> s pour sleep()
# Index de la carte active
# Configuration des broches CS
# Toutes en sortie, etat initial inactif (haut)
# Validation de l'index
# Validation de l'adresse
# Sequence de selection:
# 1. CS bas (echantillonne l'adresse)
# 2. Envoi de l'adresse (8 bits)
# 3. CS haut (applique la selection)
# 4. Delai pour stabilisation
# coding: utf-8
"""
Driver pour le multiplexeur analogique ADG731 d'Analog Devices.

Caracteristiques principales:
- Multiplexeur 32:1
- Interface serie compatible SPI
- Faible resistance RON (4 ohm typ.)
- Large plage de tension d'alimentation (+/-15V)
- Faible consommation (0.001uW typ.)

Particularites d'implementation:
- Interface: Utilise MOSI et SCLK du SPI
- MISO non utilise (pas de retour de donnees)
- Jusqu'a 4 circuits peuvent etre controles (CS1-CS4)
- L'adresse est echantillonnee sur front montant de CS

Reference: https://www.analog.com/en/products/adg731.html
"""

from time import sleep                # Pour les delais precis
from typing import List, Optional    # Pour le typage statique
from io_module.gpio_cm5 import GPIO         # Pour le controle des broches GPIO

class Adg731:
    """
    Controle d'un ou plusieurs multiplexeurs ADG731.
    Supporte jusqu'a 4 circuits en parallele.
    """
    
    def __init__(self, spi, cs_pins: List[int], gpio=GPIO, t_cs_us: float = 2):
        """
        Initialise l'interface avec le(s) ADG731.

        Args:
            spi: Instance du bus SPI configure
            cs_pins: Liste des broches GPIO pour CS [CS1..CS4]
            gpio: Interface GPIO a utiliser
            t_cs_us: Delai apres CS en microsecondes (min 20ns)

        Raises:
            ValueError: Si les parametres sont invalides
        """
        # Validation des parametres
        if not cs_pins:
            raise ValueError("La liste des broches CS ne peut pas etre vide")
        if t_cs_us < 0.02:  # 20ns minimum selon datasheet
            raise ValueError("Delai CS trop court (min 20ns)")
            
        # Stockage des parametres
        self.spi = spi                # Interface SPI
        self.cs_pins = cs_pins        # Liste des broches CS
        self.gpio = gpio              # Interface GPIO
        # Conversion us -> s pour sleep()
        self.t_cs = float(t_cs_us) / 1000000.0
        self._card = 0                # Index de la carte active

        # Configuration des broches CS
        # Toutes en sortie, etat initial inactif (haut)
        for cs in self.cs_pins:
            self.gpio.setup(cs, self.gpio.OUT, initial=1)

    def select_card(self, index: int) -> None:
        """
        Selectionne un circuit ADG731 via son CS.
        
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
        Active le CS du circuit selectionne (etat bas).
        L'adresse est echantillonnee sur ce front.
        """
        self.gpio.output(self.cs_pins[self._card], 0)

    def _cs_high(self) -> None:
        """
        Desactive le CS du circuit selectionne (etat haut).
        Le multiplexeur change de canal sur ce front.
        """
        self.gpio.output(self.cs_pins[self._card], 1)

    def set_channel(self, addr: int) -> None:
        """
        Selectionne un canal sur le multiplexeur actif.
        
        Args:
            addr: Numero du canal (0..31)
            
        Raises:
            ValueError: Si l'adresse est invalide
            
        Note: L'adresse est envoyee sur 8 bits mais seuls
              les 5 bits de poids faible sont utilises.
        """
        # Validation de l'adresse
        if not 0 <= addr <= 31:
            raise ValueError("L'adresse doit etre entre 0 et 31")

        # Sequence de selection:
        # 1. CS bas (echantillonne l'adresse)
        # 2. Envoi de l'adresse (8 bits)
        # 3. CS haut (applique la selection)
        # 4. Delai pour stabilisation
        self._cs_low()
        self.spi.xfer2([addr & 0xFF])  # Masque sur 8 bits
        self._cs_high()

        # Delai de stabilisation si configure
        if self.t_cs > 0.0:
            sleep(self.t_cs)

    def power_down(self) -> None:
        """
        Met le multiplexeur en haute impedance.
        
        Cette methode envoie une adresse invalide (0xFF)
        pour forcer tous les switchs en haute impedance.
        
        Note: Le comportement exact depend du cablage.
        """
        self._cs_low()
        self.spi.xfer2([0xFF])  # Adresse invalide
        self._cs_high()
        
        if self.t_cs > 0.0:
            sleep(self.t_cs)

    def nop(self) -> None:
        """
        Execute un cycle CS sans changer de canal.
        
        Utile pour:
        - Reappliquer la selection actuelle
        - Synchronisation
        - Test de communication
        """
        self._cs_low()
        self.spi.xfer2([0x00])  # Donnee sans effet
        self._cs_high()
        
        if self.t_cs > 0.0:
            sleep(self.t_cs)
