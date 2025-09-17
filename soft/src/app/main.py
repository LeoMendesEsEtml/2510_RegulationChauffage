# -*- coding: utf-8 -*-
# file: main.py
"""
Système de mesure et simulation de température

Logique complète :
1. Mesure ADC → résistance → température
2. Récupération paramètres API
3. Calcul température simulée
4. Conversion en résistance simulée
5. Application via MUX de simulation
"""
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import time
import argparse
import math
from periphery import GPIO
from pins_cm5 import GPIO_CHIP_PATH, FRONT_LED, CMD_RELAY
from app.config_loader import load_config
from app.sensor_profiles import get_profile, SENSOR_TABLES
from hw_tmux1204 import Tmux1204
from app.adc_ads124s08 import Ads124s08
from app.temperature_conversion import convert_temperature_to_resistance
from api_client import ApiClient
from temperature_simulation import run_temperature_simulation
from resistance_simulation import ResistanceSimulator

def main():
    """Logique principale : mesure + simulation"""
    parser = argparse.ArgumentParser(description="Système de mesure et simulation de température")
    parser.add_argument("--simulation", action="store_true", help="Active la simulation après mesure")
    args = parser.parse_args()
    
    print("=== SYSTÈME DE MESURE ET SIMULATION ===")
    
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
            print("\n--- Nouvelle séquence de simulation ---")
            # 1. Récupération des paramètres API au début de la séquence
            from app.api_client import get_simulation_data
            simulation_data = get_simulation_data("0030DEABCDEF")
            if simulation_data is None:
                print("[SIMULATION] Erreur: impossible de récupérer les paramètres API")
                break

            for entry in cfg["channels"]:
                ch = entry["channel"]
                sensor_name = entry["sensor"]
                profile = get_profile(sensor_name)

                input(f"Appuyez sur Entrée pour mesurer et simuler le canal {ch} ({sensor_name})...")

                print(f"[MESURE] Canal {ch} - {sensor_name}")
                tmux.select_rref_ohm(profile["rref_ohm"])
                adc.configure_channel(ch, profile["pga_gain"], profile["idac_uA"])
                adc.read_gain()
                adc.read_ref()
                adc.read_inpmux()

                r = adc.measure_resistance(profile["rref_ohm"], profile["pga_gain"], cfg["timeout_s"])
                if r is None:
                    print("[MESURE] Résistance: NaN")
                    continue
                else:
                    print(f"[MESURE] Résistance: {r:.6f} ohms")

                temperature = adc.measure_temperature(sensor_name, profile["rref_ohm"], profile["pga_gain"], cfg["timeout_s"])
                if temperature is None:
                    print(f"[MESURE] Température non mesurable ou saturation détectée")
                    continue
                else:
                    print(f"[MESURE] Température mesurée: {temperature:.2f}°C")

                # 2. Calcul et application simulation
                print("[SIMULATION] Calcul et application...")
                simulation_data["temperature"] = temperature
                simulation_data["probe_type"] = sensor_name
                print(f"[SIMULATION] Paramètres: n={simulation_data['n']}, k_m={simulation_data['k_m']}")
                print(f"[SIMULATION] T_mes={temperature:.2f}°C, T_prev={simulation_data['forecast_temperature']:.2f}°C")

                t_sim = run_temperature_simulation(simulation_data)
                if t_sim is None:
                    print("[SIMULATION] Erreur lors du calcul de T_sim")
                    continue
                print(f"[SIMULATION] Température simulée: {t_sim:.2f}°C")

                resistance_target = convert_temperature_to_resistance(t_sim, sensor_name)
                if resistance_target is None:
                    print(f"[SIMULATION] Erreur conversion T_sim → résistance pour {sensor_name}")
                    continue
                print(f"[SIMULATION] Résistance cible: {resistance_target:.2f} ohms")

                resistance_sim = ResistanceSimulator()
                if resistance_sim.apply_resistance_simulation(resistance_target, ch):
                    print(f"[SIMULATION] Résistance appliquée via MUX de simulation sur canal {ch}")
                else:
                    print(f"[SIMULATION] Erreur lors de l'application MUX sur canal {ch}")

                print()
                time.sleep(cfg["inter_measure_sleep_s"])

            print("Séquence terminée. Appuyez sur Entrée pour relancer une nouvelle séquence (API sera relue)...")
            input()
            time.sleep(cfg["loop_sleep_s"])
    except KeyboardInterrupt:
        print("\nArrêt demandé...")
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
