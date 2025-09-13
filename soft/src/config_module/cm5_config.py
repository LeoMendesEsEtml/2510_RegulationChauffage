# -*- coding: utf-8 -*-
# file: soft/src/config_module/cm5_config.py
# Fournit:
#  - ADC_CHANNELS : [1, 2, 3, 4]
#  - build_hw()   : instancie LED, TMUX, ADC avec ton câblage fixe

from periphery import GPIO
from app.pins_cm5 import GPIO_CHIP_PATH, FRONT_LED
from app.hw_tmux1204 import Tmux1204
from app.adc_ads124s08 import Ads124s08

ADC_CHANNELS = [1, 2, 3, 4]

def build_hw():
    led = GPIO(GPIO_CHIP_PATH, FRONT_LED, "out")
    led.write(True)
    tmux = Tmux1204()
    adc = Ads124s08()
    hw = {}
    hw["led"] = led
    hw["tmux"] = tmux
    hw["adc"] = adc
    return hw
