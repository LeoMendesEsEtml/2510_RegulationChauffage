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
import threading
import signal
import select
import sys
from datetime import datetime, timedelta
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

# Variable globale pour le contrôle du séquenceur
sequencer_running = False
stop_event = threading.Event()
force_sequence = threading.Event()

def signal_handler(sig, frame):
    """Gestionnaire pour arrêt propre avec Ctrl+C"""
    global sequencer_running
    print("\n[SEQUENCER] Arrêt demandé...")
    sequencer_running = False
    stop_event.set()

def input_monitor():
    """Thread pour surveiller les entrées utilisateur"""
    while sequencer_running and not stop_event.is_set():
        try:
            user_input = input()
            if user_input.strip().lower() in ['', 's', 'sequence', 'start']:
                print("[MANUAL] Séquence manuelle déclenchée !")
                force_sequence.set()
            elif user_input.strip().lower() in ['q', 'quit', 'exit']:
                print("[MANUAL] Arrêt demandé par l'utilisateur")
                signal_handler(signal.SIGINT, None)
                break
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            pass  # Ignore les erreurs d'entrée

def run_measurement_sequence(cfg, mac_address, adc, tmux):
    """Exécute une séquence complète de mesures"""
    print(f"\n[SEQUENCER] === NOUVELLE SÉQUENCE - {datetime.now().strftime('%H:%M:%S')} ===")
    
    # 1. Récupération des paramètres API au début de la séquence
    from app.api_client import get_simulation_data
    try:
        simulation_data = get_simulation_data(mac_address)
        if simulation_data is None:
            print("[SIMULATION] Erreur: impossible de récupérer les paramètres API")
            return False
    except Exception as e:
        print(f"[SIMULATION] Erreur API: {e}")
        return False

    # 2. Traitement de chaque canal activé
    for entry in cfg["channels"]:
        ch = entry["channel"]
        sensor_name = entry["sensor"]
        enabled = entry.get("enabled", True)
        
        # Ignorer les canaux désactivés
        if not enabled:
            print(f"[CONFIG] Canal {ch} désactivé - ignoré")
            continue
        
        profile = get_profile(sensor_name)
        
        print(f"\n[MESURE] Canal {ch} - {sensor_name}")
        try:
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
                
                # Envoi de la température mesurée vers l'API
                from app.api_client import send_temperature_measurement
                if send_temperature_measurement(mac_address, temperature, ch):
                    print(f"[API] Température {temperature:.2f}°C envoyée avec succès pour le canal {ch}")
                else:
                    print(f"[API] Erreur lors de l'envoi de la température pour le canal {ch}")

            # 3. Calcul et application simulation
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
            if resistance_sim.apply_resistance_simulation(resistance_target, ch, sensor_name):
                print(f"[SIMULATION] Résistance appliquée via MUX sur canal {ch} (sonde: {sensor_name})")
            else:
                print(f"[SIMULATION] Erreur lors de l'application MUX sur canal {ch}")

            time.sleep(cfg["inter_measure_sleep_s"])
            
        except Exception as e:
            print(f"[ERREUR] Canal {ch}: {e}")
            continue

    print(f"[SEQUENCER] Séquence terminée - {datetime.now().strftime('%H:%M:%S')}")
    return True

def main():
    """Logique principale : mesure + simulation avec séquenceur automatique"""
    global sequencer_running
    
    parser = argparse.ArgumentParser(description="Système de mesure et simulation de température")
    parser.add_argument("--manual", action="store_true", help="Mode manuel (demande confirmation à chaque séquence)")
    parser.add_argument("--once", action="store_true", help="Exécute une seule séquence puis s'arrête")
    args = parser.parse_args()
    
    print("=== SYSTÈME DE MESURE ET SIMULATION ===")
    
    CONFIG_FILE = os.path.join(SRC_DIR, "config_module", "sensors.json")
    cfg = load_config(CONFIG_FILE)
    
    # Configuration du séquenceur
    auto_sequence = cfg.get("auto_sequence", True)
    sequence_interval_minutes = cfg.get("sequence_interval_minutes", 5)
    
    # Affichage des canaux configurés
    enabled_channels = [entry for entry in cfg["channels"] if entry.get("enabled", True)]
    disabled_channels = [entry for entry in cfg["channels"] if not entry.get("enabled", True)]
    
    print(f"[CONFIG] Canaux activés: {len(enabled_channels)}")
    for entry in enabled_channels:
        print(f"[CONFIG]   Canal {entry['channel']}: {entry['sensor']}")
    
    if disabled_channels:
        print(f"[CONFIG] Canaux désactivés: {len(disabled_channels)}")
        for entry in disabled_channels:
            print(f"[CONFIG]   Canal {entry['channel']}: {entry['sensor']} (OFF)")
    
    # Configuration du mode de fonctionnement
    if args.manual:
        print(f"[CONFIG] Mode: MANUEL (demande confirmation)")
    elif args.once:
        print(f"[CONFIG] Mode: UNE SEULE FOIS")
    elif auto_sequence:
        print(f"[CONFIG] Mode: AUTOMATIQUE (toutes les {sequence_interval_minutes} minutes)")
        print(f"[CONFIG] Commandes disponibles pendant l'exécution:")
        print(f"[CONFIG]   - Appuyez sur ENTRÉE ou tapez 's' pour forcer une séquence")
        print(f"[CONFIG]   - Tapez 'q' pour quitter")
    else:
        print(f"[CONFIG] Mode: MANUEL (auto_sequence=false dans config)")
    
    print()

    # Gestionnaire de signal pour arrêt propre
    signal.signal(signal.SIGINT, signal_handler)
    
    # LED ON permanente
    led = GPIO(GPIO_CHIP_PATH, FRONT_LED, "out")
    led.write(True)
    relay = GPIO(GPIO_CHIP_PATH, CMD_RELAY, "out")
    relay.write(True)
    tmux = Tmux1204()
    adc = Ads124s08()
    mac_address = cfg.get("mac_address", "0030DEABCDEF")

    try:
        sequencer_running = True
        next_sequence_time = datetime.now()
        
        # Démarrage du thread de surveillance des entrées utilisateur (mode auto seulement)
        input_thread = None
        if auto_sequence and not args.manual and not args.once:
            input_thread = threading.Thread(target=input_monitor, daemon=True)
            input_thread.start()
            print("[MANUAL] Thread de surveillance des entrées démarré")
        
        while sequencer_running and not stop_event.is_set():
            current_time = datetime.now()
            
            # Vérification si c'est le moment d'exécuter une séquence
            should_run = False
            sequence_reason = ""
            
            # Vérification du déclenchement manuel
            if force_sequence.is_set():
                should_run = True
                sequence_reason = "MANUELLE"
                force_sequence.clear()
            elif args.once:
                should_run = True
                sequence_reason = "UNIQUE"
                sequencer_running = False  # Arrêt après une séquence
            elif args.manual or not auto_sequence:
                print(f"[SEQUENCER] Appuyez sur Entrée pour lancer une séquence (Ctrl+C pour arrêter)...")
                try:
                    input()
                    should_run = True
                    sequence_reason = "MANUELLE"
                except EOFError:
                    break
            else:
                # Mode automatique
                if current_time >= next_sequence_time:
                    should_run = True
                    sequence_reason = "AUTOMATIQUE"
                    next_sequence_time = current_time + timedelta(minutes=sequence_interval_minutes)
                    print(f"[SEQUENCER] Prochaine séquence automatique programmée à: {next_sequence_time.strftime('%H:%M:%S')}")
            
            if should_run:
                print(f"[SEQUENCER] Démarrage séquence {sequence_reason} - {current_time.strftime('%H:%M:%S')}")
                success = run_measurement_sequence(cfg, mac_address, adc, tmux)
                if not success:
                    print("[SEQUENCER] Erreur lors de la séquence")
                else:
                    print(f"[SEQUENCER] Séquence {sequence_reason} terminée avec succès")
            
            # Attente avant vérification suivante (mode auto seulement)
            if auto_sequence and not args.manual and not args.once and sequencer_running:
                time.sleep(1)  # Vérification toutes les secondes pour réactivité manuelle
                
    except KeyboardInterrupt:
        print("\n[SEQUENCER] Arrêt demandé par l'utilisateur...")
    finally:
        sequencer_running = False
        stop_event.set()
        
        # Attente de fermeture du thread d'entrée
        if input_thread and input_thread.is_alive():
            print("[MANUAL] Arrêt du thread de surveillance...")
            input_thread.join(timeout=1)
        
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
        
        print("[SEQUENCER] Système arrêté proprement")

if __name__ == "__main__":
    main()
