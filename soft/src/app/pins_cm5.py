# -*- coding: utf-8 -*-
# file: pins_cm5.py
"""
Mapping GPIO et SPI fixés (CM5 I/O) — ne pas mettre dans la config.
"""


# GPIO chip principal utilisé pour tous les accès GPIO
GPIO_CHIP_PATH = "/dev/gpiochip0"

# Sélection du multiplexeur ADG731 (CS = Chip Select)
MUX_CS_4          = 2   # Chip Select MUX canal 4
MUX_CS_3          = 3   # Chip Select MUX canal 3
MUX_CS_2          = 7   # Chip Select MUX canal 2
MUX_CS_1          = 8   # Chip Select MUX canal 1

# Broches non utilisées pour le multiplexeur SPI (dummy)
MUX_MOSI_DUMMY    = 10  # MOSI dummy, non utilisé (SPI0 MOSI sur spidev)
MUX_SCLK_DUMMY    = 11  # SCLK dummy, non utilisé

# Commande et mesure 24V sur CM5
CM_24V_OUT_1      = 13  # Sortie 24V canal 1
CM_24V_SENSE_1    = 14  # Sense 24V canal 1
CM_24V_OUT_2      = 15  # Sortie 24V canal 2
CM_24V_SENSE_2    = 16  # Sense 24V canal 2

# Relais de commande général
CMD_RELAY         = 17  # Commande du relais principal

# Chip Select ADC dummy (utilisé via spidev1.0)
CS_ADC_DUMMY      = 18  # CS ADC dummy, non utilisé directement

# Broches SPI ADC dummy (non utilisées, pour mapping complet)
SPI_MISO_ADC_DMY  = 19  # MISO ADC dummy
SPI_MOSI_ADC_DMY  = 20  # MOSI ADC dummy
SPI_SCLK_ADC_DMY  = 21  # SCLK ADC dummy

# Data Ready du convertisseur ADC
ADC_DRDY          = 22  # Data Ready (DRDY) du ADC

# Synchronisation démarrage ADC (non utilisé)
ADC_START_SYNC    = 23  # START/SYNC ADC, non utilisé (commande START via SPI)

# Sélection des entrées analogiques ADC
ADC_A0            = 24  # Sélection A0 ADC
ADC_A1            = 25  # Sélection A1 ADC

# LED façade (indicateur visuel)
FRONT_LED         = 27  # LED en façade

# SPI bus et devices
SPI0_BUS = 0        # Bus SPI0 (ADG731 éventuel)
SPI1_BUS = 1        # Bus SPI1 (ADS124S08 ADC)
SPI0_DEV0 = 0       # Device 0 sur SPI0
SPI0_DEV1 = 1       # Device 1 sur SPI0
SPI1_DEV0 = 0       # Device 0 sur SPI1 (/dev/spidev1.0 pour ADC)

# Vitesses de communication SPI
SPI_MUX_SPEED_HZ = 100000   # Vitesse SPI pour le multiplexeur
SPI_ADC_SPEED_HZ = 100000   # Vitesse SPI pour l'ADC
