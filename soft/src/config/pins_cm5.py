
# -*- coding: utf-8 -*-
"""
Configuration des broches GPIO du CM5.

Ce module définit:
- Le mapping des broches GPIO
- Les configurations des interfaces SPI
- Les signaux de contrôle de l'ADC
- Les E/S diverses (LED, relais)

Architecture matérielle:
----------------------
1. Interfaces SPI :
   - SPI0 : Multiplexeur ADG731 (réseau résistif)
     * SCLK, MOSI uniquement (pas de MISO)
     * 4 CS pour sélection des cartes
   - SPI1 : ADC ADS124S08 (mesures)
     * SCLK, MOSI, MISO
     * 1 CS dédié

2. Contrôle ADC :
   - DRDY : Donnée prête
   - START_SYNC : Démarrage conversion
   - A0/A1 : Sélection référence

3. GPIO divers :
   - LED de statut
   - Relais de bypass

4. Contacts secs 24V :
   - Canal 1 :
     * CM_24V_OUT_1 (GPIO 13) : Sortie +24V
     * CM_24V_SENSE_1 (GPIO 14) : Entrée détection
   - Canal 2 :
     * CM_24V_OUT_2 (GPIO 15) : Sortie +24V
     * CM_24V_SENSE_2 (GPIO 16) : Entrée détection

Note: Tous les numéros de broches sont en mode BCM.
"""

from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class SPIConfig:
    """
    Configuration des broches pour une interface SPI.
    
    Attributs:
        sclk: Broche horloge SPI
        mosi: Broche données sortantes (Master Out)
        miso: Broche données entrantes (Master In), optionnelle
        cs: Liste des broches chip select
    
    Note: Le MISO est optionnel car certains périphériques
    comme l'ADG731 sont write-only.
    """
    sclk: int          # Serial Clock
    mosi: int          # Master Out Slave In
    miso: int = None   # Master In Slave Out (optionnel)
    cs: List[int] = None  # Liste des Chip Selects

@dataclass
class ADCConfig:
    """
    Configuration des broches de contrôle de l'ADC.
    
    Attributs:
        drdy: Signal Data Ready (conversion terminée)
        start_sync: Signal Start/Sync (démarrage conversion)
        ref_a0: Sélection référence A0 (configuration ref)
        ref_a1: Sélection référence A1 (configuration ref)
        
    L'ADS124S08 utilise ces signaux pour:
    - Indiquer quand les données sont prêtes (DRDY)
    - Synchroniser les conversions (START)
    - Configurer la référence de tension (A0/A1)
    """
    drdy: int          # Data Ready (entrée)
    start_sync: int    # Start/Sync (sortie)
    ref_a0: int        # Sélection référence A0 (sortie)
    ref_a1: int        # Sélection référence A1 (sortie)

# Ensemble des broches GPIO valides sur CM5
VALID_GPIO_PINS: Set[int] = set(range(0, 54))  # BCM 0-53

def validate_pin(pin: int, name: str) -> None:
    """
    Vérifie qu'un numéro de broche est valide.
    
    Args:
        pin: Numéro de broche BCM à vérifier
        name: Nom du signal pour le message d'erreur
        
    Raises:
        ValueError: Si le numéro est invalide
    """
    if pin not in VALID_GPIO_PINS:
        raise ValueError(f"Broche invalide pour {name}: {pin}")

# Configuration SPI0 pour multiplexeur ADG731
# Interface write-only pour sélection résistances
SPI0 = SPIConfig(
    sclk=11,    # SPI0_SCLK - Horloge 1MHz
    mosi=10,    # SPI0_MOSI - Données sortantes
    cs=[8, 7, 3, 2]  # CS[0:3] pour 4 cartes max
)

# Configuration SPI1 pour ADC ADS124S08
# Interface bidirectionnelle pour mesures
SPI1 = SPIConfig(
    sclk=25,    # SPI1_SCLK - Horloge 1MHz
    mosi=26,    # SPI1_MOSI - Config + contrôle
    miso=49,    # SPI1_SIO[1]
    cs=[50]     # SPI1_CSn[0] (via alt func A0)
)

# Configuration ADC
ADC = ADCConfig(
    drdy=46,        # Data Ready
    start_sync=47,  # Start/Sync
    ref_a0=45,      # Référence A0
    ref_a1=41       # Référence A1
)

# Autres broches
RELAY_PIN = 20
LED_PIN = 24

# Contacts secs 24V
CM_24V_OUT_1 = 13    # GPIO 13 - Sortie 24V canal 1
CM_24V_SENSE_1 = 14  # GPIO 14 - Entrée détection canal 1
CM_24V_OUT_2 = 15    # GPIO 15 - Sortie 24V canal 2
CM_24V_SENSE_2 = 16  # GPIO 16 - Entrée détection canal 2

# Construction du dictionnaire PINS
PINS = {
    # SPI0 (MUX)
    "MUX_SCLK": SPI0.sclk,
    "MUX_MOSI": SPI0.mosi,
    "MUX_CS_1": SPI0.cs[0],
    "MUX_CS_2": SPI0.cs[1],
    "MUX_CS_3": SPI0.cs[2],
    "MUX_CS_4": SPI0.cs[3],
    
    # SPI1 (ADC)
    "SPI_SCLK_ADC": SPI1.sclk,
    "SPI_MOSI_ADC": SPI1.mosi,
    "SPI_MISO_ADC": SPI1.miso,
    "CS_ADC": SPI1.cs[0],
    
    # ADC control
    "ADC_DRDY": ADC.drdy,
    "ADC_START_SYNC": ADC.start_sync,
    "ADC_A0": ADC.ref_a0,
    "ADC_A1": ADC.ref_a1,
    
    # Divers
    "CMD_RELAY": RELAY_PIN,
    "FRONT_LED": LED_PIN,
    
    # Contacts secs 24V
    "CM_24V_OUT_1": CM_24V_OUT_1,
    "CM_24V_SENSE_1": CM_24V_SENSE_1,
    "CM_24V_OUT_2": CM_24V_OUT_2,
    "CM_24V_SENSE_2": CM_24V_SENSE_2,
}

# Liste des chip selects du multiplexeur
PINS["mux_cs_list"] = SPI0.cs

# Validation de toutes les broches
for name, pin in PINS.items():
    validate_pin(pin, name)
