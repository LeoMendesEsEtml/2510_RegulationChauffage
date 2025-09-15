# -*- coding: utf-8 -*-
# file: main.py
"""
Main minimal:
- LED façade ON en permanence
- Lecture config JSON minimale
- Pour chaque canal déclaré: sélection Rref via TMUX, config ADC selon profil, mesure bloquante, print résistance [Ohm] uniquement.
"""
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import time
from periphery import GPIO
from pins_cm5 import GPIO_CHIP_PATH, FRONT_LED, CMD_RELAY
from app.config_loader import load_config
from app.sensor_profiles import get_profile
from hw_tmux1204 import Tmux1204
from adc_ads124s08 import Ads124s08

def main():
    CONFIG_FILE = os.path.join(SRC_DIR, "config_module", "sensors.json")
    cfg = load_config(CONFIG_FILE)

    # LED ON permanente
    led = GPIO(GPIO_CHIP_PATH, FRONT_LED, "out")
    led.write(True)
    relay = GPIO(GPIO_CHIP_PATH, CMD_RELAY, "out")
    relay.write(True)
    tmux = Tmux1204()
    adc = Ads124s08()

    try:
        while True:
            for entry in cfg["channels"]:
                ch = entry["channel"]
                sensor_name = entry["sensor"]
                profile = get_profile(sensor_name)

                input(f"Appuyez sur Entrée pour mesurer le canal {ch} ({sensor_name})...")

                # Sélection Rref
                tmux.select_rref_ohm(profile["rref_ohm"])

                # Configuration ADC pour le canal
                adc.configure_channel(ch, profile["pga_gain"], profile["idac_uA"])

                # Mesure bloquante
                idac1 = profile["idac_uA"] / 1e6  # Convert µA to A
                idac2 = profile["idac_uA"] / 1e6  # Assuming idac2 is the same as idac1
                r = adc.measure_resistance(profile["rref_ohm"], profile["pga_gain"], cfg["timeout_s"], idac1, idac2)

                if r is None:
                    print("NaN")
                else:
                    # Print uniquement la valeur de résistance
                    print("{:.6f}".format(r))

                time.sleep(cfg["inter_measure_sleep_s"])

            time.sleep(cfg["loop_sleep_s"])
    except KeyboardInterrupt:
        pass
    finally:
        try:
            adc.close()
        except Exception:
            pass
        try:
            tmux.close()
        except Exception:
            pass
        try:
            led.write(False)
            led.close()
        except Exception:
            pass
        try:
            relay.write(False)
            relay.close()
        except Exception:
            pass
if __name__ == "__main__":
    main()
