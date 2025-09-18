# -*- coding: utf-8 -*-
"""
@file        pins_cm5.py
@brief       Mapping GPIO et SPI fixés pour la plateforme CM5.
@details     Ce module définit tous les assignements de broches GPIO et
             les paramètres SPI fixes pour la carte CM5. Ces constantes
             ne doivent pas être modifiées via la configuration utilisateur
             car elles correspondent au routage matériel de la carte.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""


# ---------------------------------------------------------------------------
# GPIO principal et configuration système
# ---------------------------------------------------------------------------

# Chemin du contrôleur GPIO principal sur le système Linux
GPIO_CHIP_PATH = "/dev/gpiochip0"


# ---------------------------------------------------------------------------
# Multiplexeur ADG731 - Chip Select
# ---------------------------------------------------------------------------

# Broches de sélection CS pour les 4 multiplexeurs ADG731
MUX_CS_4 = 2
# Broches de sélection CS pour les 3 multiplexeurs ADG731
MUX_CS_3 = 3
# Broches de sélection CS pour les 2 multiplexeurs ADG731
MUX_CS_2 = 7
# Broches de sélection CS pour les 1 multiplexeurs ADG731
MUX_CS_1 = 8


# ---------------------------------------------------------------------------
# Broches SPI multiplexeur (dummy)
# ---------------------------------------------------------------------------

# Broche MOSI dummy pour le multiplexeur (non utilisée directement)
MUX_MOSI_DUMMY = 10
# Broche SCLK dummy pour le multiplexeur (non utilisée directement)
MUX_SCLK_DUMMY = 11


# ---------------------------------------------------------------------------
# Commande et mesure 24V
# ---------------------------------------------------------------------------

# Sortie de commande 24V pour le canal 1
CM_24V_OUT_1 = 13
# Entrée de mesure (sense) 24V pour le canal 1
CM_24V_SENSE_1 = 14
# Sortie de commande 24V pour le canal 2
CM_24V_OUT_2 = 15
# Entrée de mesure (sense) 24V pour le canal 2
CM_24V_SENSE_2 = 16


# ---------------------------------------------------------------------------
# Relais de commande
# ---------------------------------------------------------------------------

# Broche de commande du relais principal de puissance
CMD_RELAY = 17


# ---------------------------------------------------------------------------
# ADC ADS124S08 - Configuration SPI
# ---------------------------------------------------------------------------

# Chip Select ADC dummy (géré par spidev1.0)
CS_ADC_DUMMY = 18
# Broche MISO ADC dummy (gérée par le driver SPI)
SPI_MISO_ADC_DMY = 19
# Broche MOSI ADC dummy (gérée par le driver SPI)
SPI_MOSI_ADC_DMY = 20
# Broche SCLK ADC dummy (gérée par le driver SPI)
SPI_SCLK_ADC_DMY = 21


# ---------------------------------------------------------------------------
# ADC ADS124S08 - Signaux de contrôle
# ---------------------------------------------------------------------------

# Signal Data Ready de l'ADC (interruption de fin de conversion)
ADC_DRDY = 22
# Signal START/SYNC de l'ADC (non utilisé, démarrage via SPI)
ADC_START_SYNC = 23


# ---------------------------------------------------------------------------
# ADC ADS124S08 - Sélection d'entrées
# ---------------------------------------------------------------------------

# Bit A0 de sélection du canal analogique de l'ADC
ADC_A0 = 24
# Bit A1 de sélection du canal analogique de l'ADC
ADC_A1 = 25


# ---------------------------------------------------------------------------
# Indicateurs visuels
# ---------------------------------------------------------------------------

# LED de façade pour indication d'état du système
FRONT_LED = 27


# ---------------------------------------------------------------------------
# Configuration des bus SPI
# ---------------------------------------------------------------------------

# Numéro du bus SPI0 (pour multiplexeurs éventuels)
SPI0_BUS = 0
# Numéro du bus SPI1 (pour ADC ADS124S08)
SPI1_BUS = 1


# ---------------------------------------------------------------------------
# Configuration des devices SPI
# ---------------------------------------------------------------------------

# Device 0 sur le bus SPI0
SPI0_DEV0 = 0
# Device 1 sur le bus SPI0
SPI0_DEV1 = 1
# Device 0 sur le bus SPI1 (correspond à /dev/spidev1.0 pour l'ADC)
SPI1_DEV0 = 0


# ---------------------------------------------------------------------------
# Vitesses de communication SPI
# ---------------------------------------------------------------------------

# Fréquence SPI pour la communication avec les multiplexeurs ADG731 [Hz]
SPI_MUX_SPEED_HZ = 100000
# Fréquence SPI pour la communication avec l'ADC ADS124S08 [Hz]
SPI_ADC_SPEED_HZ = 100000
