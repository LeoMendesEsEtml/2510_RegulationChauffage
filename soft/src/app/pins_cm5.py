# -*- coding: utf-8 -*-
# file: pins_cm5.py
"""
Mapping GPIO et SPI fixés (CM5 I/O) — ne pas mettre dans la config.
"""

# GPIO chip
GPIO_CHIP_PATH = "/dev/gpiochip0"

# Lignes GPIO (numéros periphery) d'après ton tableau
MUX_CS_4          = 2
MUX_CS_3          = 3
MUX_CS_2          = 7
MUX_CS_1          = 8
MUX_MOSI_DUMMY    = 10     # non utilisé ici, SPI0 MOSI est sur spidev
MUX_SCLK_DUMMY    = 11
CM_24V_OUT_1      = 13
CM_24V_SENSE_1    = 14
CM_24V_OUT_2      = 15
CM_24V_SENSE_2    = 16
CMD_RELAY         = 17
CS_ADC_DUMMY      = 18     # CS via spidev1.0
SPI_MISO_ADC_DMY  = 19
SPI_MOSI_ADC_DMY  = 20
SPI_SCLK_ADC_DMY  = 21
ADC_DRDY          = 22
ADC_START_SYNC    = 23     # non utilisé, on pilote par commande START
ADC_A0            = 24
ADC_A1            = 25
FRONT_LED         = 27

# SPI devices fixés
SPI0_BUS = 0    # ADG731 éventuel
SPI1_BUS = 1    # ADS124S08
SPI0_DEV0 = 0
SPI0_DEV1 = 1
SPI1_DEV0 = 0   # /dev/spidev1.0 (ADC)

# Vitesses SPI
SPI_MUX_SPEED_HZ = 100000
SPI_ADC_SPEED_HZ = 100000
