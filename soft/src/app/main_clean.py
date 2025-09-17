# -*- coding: utf-8 -*-
# file: main.py
"""
Main avec deux modes:
1. Mode normal: LED façade ON, lecture config JSON, mesures ADC
2. Mode simulation: Simulation de température selon cahier des charges

Usage:
- python main.py                    # Mode normal
- python main.py --simulation       # Mode simulation de température
"""
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import time
import argparse
from periphery import GPIO
from pins_cm5 import GPIO_CHIP_PATH, FRONT_LED, CMD_RELAY
from app.config_loader import load_config
from app.sensor_profiles import get_profile, SENSOR_TABLES
from hw_tmux1204 import Tmux1204
from app.adc_ads124s08 import Ads124s08

def simulation_mode():
    """Mode simulation de température"""
    print("=== MODE SIMULATION DE TEMPÉRATURE ===")
    
    # Utilisation des modules existants
    from api_client import ApiClient
    from temperature_simulation import run_temperature_simulation
    from resistance_simulation import ResistanceSimulator
    from app.temperature_conversion import convert_temperature_to_resistance
    
    # Initialisation du client API
    api_client = ApiClient()
    
    # Récupération des paramètres de simulation
    print("Récupération des paramètres de simulation...")
    simulation_data = api_client.get_simulation_parameters()
    
    if simulation_data is None:
        print("Erreur: impossible de récupérer les paramètres")
        return
    
    # Calcul de la température simulée
    print("\nCalcul de la température simulée...")
    t_sim = run_temperature_simulation(simulation_data)
    
    if t_sim is None:
        print("Erreur lors du calcul de la température simulée")
        return
    
    # Conversion en résistance
    print("\nConversion température -> résistance...")
    probe_type = simulation_data["probe_type"]
    resistance_target = convert_temperature_to_resistance(t_sim, probe_type)
    
    if resistance_target is None:
        print("Erreur lors de la conversion température -> résistance")
        return
    
    print(f"Résistance cible: {resistance_target:.2f} ohms")
    
    # Simulation de la résistance
    print("\nSimulation de la résistance...")
    resistance_sim = ResistanceSimulator()
    
    if resistance_sim.apply_resistance_simulation(resistance_target):
        print("Simulation appliquée avec succès")
    else:
        print("Erreur lors de l'application de la simulation")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Système de mesure et simulation de température"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Lance le mode simulation de température"
    )
    
    args = parser.parse_args()
    
    if args.simulation:
        simulation_mode()
        return
    
    # Mode normal (code original)
    print("=== MODE NORMAL: Mesures ADC ===")
    
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

                # Attente stabilisation
                time.sleep(0.1)

                # Lecture ADC
                adc_raw = adc.read_raw()
                print(f"ADC brut: {adc_raw}")

                # Conversion en ohms
                resistance_ohm = adc.convert_to_resistance(adc_raw, profile["rref_ohm"])
                print(f"Résistance: {resistance_ohm:.3f} ohms")

                # Conversion en température
                from app.temperature_conversion import convert_to_temperature
                temp = convert_to_temperature(resistance_ohm, sensor_name)
                if temp is not None:
                    print(f"Température: {temp:.2f}°C")
                else:
                    print("Erreur de conversion température")

                print()

    except KeyboardInterrupt:
        print("\nArrêt demandé...")
    finally:
        led.write(False)
        relay.write(False)
        print("LED et relais éteints")

if __name__ == "__main__":
    main()