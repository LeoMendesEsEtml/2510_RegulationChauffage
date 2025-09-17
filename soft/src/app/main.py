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
import requests
import json
import os
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
from front_led_management import create_led_indicator
from mesure_24v_dry_contact import test_24v_dry_contact, get_dry_contact_status

def start_webui_server():
    """Lance le serveur web dans un thread séparé"""
    try:
        import webui_server
        webui_server.app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
    except ImportError:
        print("[WEBUI] Module webui_server non trouvé")
    except Exception as e:
        print(f"[WEBUI] Erreur serveur web: {e}")

# Variable globale pour le contrôle du séquenceur
sequencer_running = False
stop_event = threading.Event()
force_sequence = threading.Event()

# Instance globale de gestion LED
led_indicator = None

def save_last_state(channel=None, resistance_ohm=None, temperature_c=None, temperature_sim_c=None, error=None):
    """Sauvegarde l'état actuel dans state/last_state.json"""
    try:
        state_dir = os.path.join(os.path.dirname(CURRENT_DIR), "state")
        os.makedirs(state_dir, exist_ok=True)
        state_path = os.path.join(state_dir, "last_state.json")
        
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "channel": channel,
            "resistance_ohm": resistance_ohm,
            "temperature_c": temperature_c,
            "temperature_sim_c": temperature_sim_c,
            "error": error
        }
        
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[STATE] Erreur sauvegarde état: {e}")

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

def show_error_and_continue(error_pattern, sleep_time=2):
    """Affiche une erreur temporairement puis remet en mode séquence"""
    global led_indicator
    if led_indicator:
        led_indicator.set_pattern(error_pattern)
    time.sleep(sleep_time)
    if led_indicator:
        led_indicator.set_pattern('sequence_running')  # Remettre en mode séquence

def run_measurement_sequence(cfg, mac_address, adc, tmux):
    """Exécute une séquence complète de mesures avec gestion d'erreurs LED"""
    global led_indicator
    print(f"\n[SEQUENCER] === NOUVELLE SÉQUENCE - {datetime.now().strftime('%H:%M:%S')} ===")
    
    # LED en mode séquence
    if led_indicator:
        led_indicator.set_pattern('sequence_running')
    
    sequence_success = True
    
    # 1. Récupération des paramètres API au début de la séquence
    from app.api_client import get_simulation_data
    try:
        simulation_data = get_simulation_data(mac_address)
        if simulation_data is None:
            print("[SIMULATION] Erreur: impossible de récupérer les paramètres API")
            if led_indicator:
                led_indicator.set_pattern('api_failed')
            return False
    except requests.exceptions.ConnectionError:
        print("[SIMULATION] Erreur: Pas de connexion Internet")
        if led_indicator:
            led_indicator.set_pattern('no_internet')
        return False
    except Exception as e:
        print(f"[SIMULATION] Erreur API critique: {e}")
        if led_indicator:
            led_indicator.set_pattern('api_failed')
        return False

    # 1.5. Test I/O 24V (contacts secs) - après API, avant mesures sondes
    test_24v_dry_contact()

    # 2. Traitement de chaque canal activé
    channels_processed = 0
    channels_failed = 0
    
    for entry in cfg["channels"]:
        ch = entry["channel"]
        sensor_name = entry["sensor"]
        enabled = entry.get("enabled", True)
        
        # Ignorer les canaux désactivés
        if not enabled:
            print(f"[CONFIG] Canal {ch} désactivé - ignoré")
            continue
        
        profile = get_profile(sensor_name)
        channels_processed += 1
        
        print(f"\n[MESURE] Canal {ch} - {sensor_name}")
        try:
            tmux.select_rref_ohm(profile["rref_ohm"])
            adc.configure_channel(ch, profile["pga_gain"], profile["idac_uA"])
            adc.read_gain()
            adc.read_ref()
            adc.read_inpmux()

            r = adc.measure_resistance(profile["rref_ohm"], profile["pga_gain"], cfg["timeout_s"])
            if r is None:
                print("[MESURE] Résistance: NaN - Erreur de mesure")
                channels_failed += 1
                show_error_and_continue('measure_failed')
                continue
            else:
                print(f"[MESURE] Résistance: {r:.6f} ohms")

            temperature = adc.measure_temperature(sensor_name, profile["rref_ohm"], profile["pga_gain"], cfg["timeout_s"])
            if temperature is None:
                print(f"[MESURE] Température non mesurable ou saturation détectée")
                channels_failed += 1
                show_error_and_continue('measure_failed')
                continue
            else:
                print(f"[MESURE] Température mesurée: {temperature:.2f}°C")
                
                # Sauvegarde de l'état avec la mesure
                save_last_state(channel=ch, resistance_ohm=r, temperature_c=temperature, error=None)
                
                # Envoi de la température mesurée vers l'API
                from app.api_client import send_temperature_measurement
                try:
                    if send_temperature_measurement(mac_address, temperature, ch):
                        print(f"[API] Température {temperature:.2f}°C envoyée avec succès pour le canal {ch}")
                    else:
                        print(f"[API] Erreur lors de l'envoi de la température pour le canal {ch}")
                        show_error_and_continue('api_failed', 1)
                except requests.exceptions.ConnectionError:
                    print(f"[API] Erreur connexion pour canal {ch}")
                    show_error_and_continue('no_internet', 1)
                except Exception as e:
                    print(f"[API] Erreur envoi canal {ch}: {e}")
                    show_error_and_continue('api_failed', 1)

            # 3. Calcul et application simulation
            print("[SIMULATION] Calcul et application...")
            simulation_data["temperature"] = temperature
            simulation_data["probe_type"] = sensor_name
            print(f"[SIMULATION] Paramètres: n={simulation_data['n']}, k_m={simulation_data['k_m']}")
            print(f"[SIMULATION] T_mes={temperature:.2f}°C, T_prev={simulation_data['forecast_temperature']:.2f}°C")

            t_sim = run_temperature_simulation(simulation_data)
            if t_sim is None:
                print("[SIMULATION] Erreur lors du calcul de T_sim")
                channels_failed += 1
                show_error_and_continue('measure_failed')
                continue
            print(f"[SIMULATION] Température simulée: {t_sim:.2f}°C")
            
            # Mise à jour de l'état avec la température simulée
            save_last_state(channel=ch, resistance_ohm=r, temperature_c=temperature, temperature_sim_c=t_sim, error=None)

            resistance_target = convert_temperature_to_resistance(t_sim, sensor_name)
            if resistance_target is None:
                print(f"[SIMULATION] Erreur conversion T_sim → résistance pour {sensor_name}")
                channels_failed += 1
                show_error_and_continue('measure_failed')
                continue
            print(f"[SIMULATION] Résistance cible: {resistance_target:.2f} ohms")

            resistance_sim = ResistanceSimulator()
            if resistance_sim.apply_resistance_simulation(resistance_target, ch, sensor_name):
                print(f"[SIMULATION] Résistance appliquée via MUX sur canal {ch} (sonde: {sensor_name})")
            else:
                print(f"[SIMULATION] Erreur lors de l'application MUX sur canal {ch}")
                channels_failed += 1
                show_error_and_continue('measure_failed')

            time.sleep(cfg["inter_measure_sleep_s"])
            
        except Exception as e:
            print(f"[ERREUR] Canal {ch}: {e}")
            channels_failed += 1
            show_error_and_continue('critical_error')
            continue

    # Évaluation globale de la séquence
    if channels_failed == 0:
        print(f"[SEQUENCER] Séquence réussie - {channels_processed} canaux traités")
        if led_indicator:
            led_indicator.set_pattern('normal')  # Retour LED normale après succès
        sequence_success = True
    elif channels_failed < channels_processed:
        print(f"[SEQUENCER] Séquence partielle - {channels_processed - channels_failed}/{channels_processed} canaux réussis")
        if led_indicator:
            led_indicator.set_pattern('measure_failed')
        sequence_success = True
    else:
        print(f"[SEQUENCER] Séquence échouée - Tous les canaux ont échoué")
        if led_indicator:
            led_indicator.set_pattern('critical_error')
        sequence_success = False
    
    print(f"[SEQUENCER] Séquence terminée - {datetime.now().strftime('%H:%M:%S')}")
    return sequence_success

def main():
    """Logique principale : mesure + simulation avec séquenceur automatique et gestion LED"""
    global sequencer_running, led_indicator
    
    parser = argparse.ArgumentParser(description="Système de mesure et simulation de température")
    parser.add_argument("--manual", action="store_true", help="Mode manuel (demande confirmation à chaque séquence)")
    parser.add_argument("--once", action="store_true", help="Exécute une seule séquence puis s'arrête")
    parser.add_argument("--webui", action="store_true", help="Lance le serveur web sur le port 8080")
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
    
    # Démarrage optionnel du serveur web
    webui_thread = None
    if args.webui:
        print(f"[WEBUI] Démarrage du serveur web sur http://localhost:8080")
        webui_thread = threading.Thread(target=start_webui_server, daemon=True)
        webui_thread.start()
        time.sleep(2)  # Laisser le temps au serveur de démarrer
    
    # Affichage des patterns LED
    print(f"\n[LED] Patterns d'erreur disponibles:")
    print(f"[LED]   - NORMAL: LED allumée en continu")
    print(f"[LED]   - SEQUENCE: Clignotement continu pendant mesure")
    print(f"[LED]   - NO_INTERNET: 1 clignotement sur 10s (pas de connexion Internet)")
    print(f"[LED]   - API_FAILED: 2 clignotements sur 10s (erreur API/connexion)")
    print(f"[LED]   - MEASURE_FAILED: 3 clignotements sur 10s (erreur mesure ADC/résistance)")
    print(f"[LED]   - CRITICAL_ERROR: 4 clignotements sur 10s (erreur critique système)")
    print(f"[LED]   - CONFIG_ERROR: 5 clignotements sur 10s (erreur de configuration)")
    
    print()

    # Gestionnaire de signal pour arrêt propre
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialisation LED avec gestion d'erreur
    led_indicator = create_led_indicator(GPIO_CHIP_PATH, FRONT_LED)
    if led_indicator:
        print("[LED] Système LED initialisé - LED normale ON")
    else:
        print("[LED] Erreur : Impossible d'initialiser la LED")
    
    # Initialisation matériel
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
                if success:
                    print(f"[SEQUENCER] Séquence {sequence_reason} terminée avec succès")
                    # Pas de changement LED ici - laissons la séquence gérer sa propre LED
                else:
                    print("[SEQUENCER] Erreur lors de la séquence")
                    # LED d'erreur déjà activée dans run_measurement_sequence
            
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
            if led_indicator:
                led_indicator.close()
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
