# -*- coding: utf-8 -*-
"""
@file        main.py
@brief       Système de mesure et simulation de température.
@details     Ce module exécute des cycles de mesure ADC, convertit les valeurs
             en résistances puis en températures, récupère des paramètres via
             une API distante, calcule une température simulée, convertit
             cette température en résistance cible et applique la simulation
             via un multiplexeur matériel. Le module gère également un petit
             serveur web optionnel et un indicateur LED.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations

# Opérations système et manipulation de chemins
import os
# Accès à la table des chemins d'import et arguments
import sys

# Calculer le répertoire courant du module et le répertoire source parent
# Dossier contenant ce fichier
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Dossier parent, racine du paquet local
SRC_DIR = os.path.dirname(CURRENT_DIR)
# S'assurer que le dossier source est dans sys.path pour permettre les imports relatifs locaux
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# Fonctions temporelles (sleep, timestamps)
import time
# Parsing des arguments de la ligne de commande
import argparse
# Fonctions mathématiques utiles
import math
# Gestion multithread (input monitor, webui thread)
import threading
# Gestion des signaux système (Ctrl+C)
import signal
# Surveillance d'entrées/sockets si nécessaire
import select
# Client HTTP pour l'API distante
import requests
# Sérialisation/désérialisation JSON
import json
# Manipulation de dates et intervalles
from datetime import datetime, timedelta
# Abstraction GPIO (bibliothèque periphery)
from periphery import GPIO
# Constantes matérielles pour le CM5
from pins_cm5 import GPIO_CHIP_PATH, FRONT_LED, CMD_RELAY
# Utilitaire de chargement de configuration JSON
from app.config_loader import load_config
# Profils de capteurs et tables associées
from app.sensor_profiles import get_profile, SENSOR_TABLES
# Pilote du multiplexeur matériel TMUX1204
from hw_tmux1204 import Tmux1204
# Pilote ADC ADS124S08
from app.adc_ads124s08 import Ads124s08
# Conversion T -> R pour sondes
from app.temperature_conversion import convert_temperature_to_resistance
# Client API (fonctions d'accès réseau)
from api_client import ApiClient
# Moteur de simulation de température
from temperature_simulation import run_temperature_simulation
# Simulation/application de résistance via MUX
from resistance_simulation import ResistanceSimulator
# Création/gestion de l'indicateur LED frontal
from front_led_management import create_led_indicator
# Test des entrées 24V (contacts secs)
from mesure_24v_dry_contact import test_24v_dry_contact, get_dry_contact_status

def start_webui_server():
    """
    @brief   Lance le serveur web local dans un thread séparé.
    @details Import dynamique du module `webui.webui_server` et démarrage de
             l'application Flask/WSGI. Les exceptions sont interceptées et
             converties en messages sur la sortie standard pour ne pas
             interrompre le thread principal.
    @return  None
    """
    try:
        # Import retardé pour permettre l'exécution sans webui
        from webui import webui_server
        # Démarrage du serveur Flask avec les paramètres spécifiés
        webui_server.app.run(host="192.168.1.109", port=8080, debug=False, use_reloader=False)
    except ImportError:
        # Gestion du cas où le module webui_server n'est pas disponible
        print("[WEBUI] Module webui_server non trouvé")
    except Exception as e:
        # Gestion des autres erreurs du serveur web
        print(f"[WEBUI] Erreur serveur web: {e}")

# ---------------------------------------------------------------------------
# Variables globales pour le contrôle du séquenceur
# ---------------------------------------------------------------------------

# Drapeau global indiquant que le séquenceur tourne
sequencer_running = False
# Événement pour demander l'arrêt propre
stop_event = threading.Event()
# Événement pour forcer une exécution manuelle
force_sequence = threading.Event()

# Instance globale de gestion LED
# Instance globale du gestionnaire LED (ou None si non disponible)
led_indicator = None

def save_last_state(channel=None, resistance_ohm=None, temperature_c=None, temperature_sim_c=None, error=None):
    """
    @brief   Sauvegarde l'état courant et historique par canal dans un fichier JSON.
    @details Crée le dossier `state` si nécessaire, lit le fichier `last_state.json`
             existant, met à jour les informations du canal fourni et écrit le
             document au format JSON. Les erreurs internes sont capturées et
             affichées sur la sortie standard.

    @param   channel           Numéro du canal (ou None).
    @param   resistance_ohm    Résistance mesurée (ou None).
    @param   temperature_c     Température mesurée [°C] (ou None).
    @param   temperature_sim_c Température simulée [°C] (ou None).
    @param   error             Message d'erreur s'il y en a un (ou None).
    @return  None
    """
    try:
        # Répertoire de stockage
        state_dir = os.path.join(os.path.dirname(CURRENT_DIR), "state")
        # Crée le répertoire si absent
        os.makedirs(state_dir, exist_ok=True)
        # Chemin complet du fichier
        state_path = os.path.join(state_dir, "last_state.json")

        # Charger l'état existant depuis le fichier JSON
        try:
            # Lecture du fichier JSON existant
            with open(state_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Structure par défaut si inexistant
            existing_data = {"channels": {}}

        # S'assurer de la présence de la clé 'channels'
        if "channels" not in existing_data:
            existing_data["channels"] = {}

        # Mettre à jour les données du canal spécifique si fourni
        if channel is not None:
            existing_data["channels"][str(channel)] = {
                "timestamp": datetime.now().isoformat(),
                "resistance_ohm": resistance_ohm,
                "temperature_c": temperature_c,
                "temperature_sim_c": temperature_sim_c,
                "error": error,
            }
            # Affichage de confirmation de sauvegarde
            print(f"[STATE] Canal {channel} sauvegardé: {temperature_c}°C")

        # Mettre à jour les méta-données globales (dernière mesure)
        existing_data.update({
            "last_timestamp": datetime.now().isoformat(),
            "last_channel": channel,
            "last_resistance_ohm": resistance_ohm,
            "last_temperature_c": temperature_c,
            "last_temperature_sim_c": temperature_sim_c,
            "last_error": error,
        })

        # Écriture finale du fichier JSON
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Gestion des erreurs de sauvegarde
        print(f"[STATE] Erreur sauvegarde état: {e}")

def signal_handler(sig, frame):
    """
    @brief   Gestionnaire POSIX pour les signaux (Ctrl+C).
    @details Met le drapeau `sequencer_running` à False et déclenche
             l'événement `stop_event` pour demander un arrêt propre.
    @param   sig  Signal reçu (int).
    @param   frame Contexte d'exécution (non utilisé).
    @return  None
    """
    global sequencer_running
    # Affichage du message d'arrêt
    print("\n[SEQUENCER] Arrêt demandé...")
    # Arrêt du séquenceur
    sequencer_running = False
    # Déclenchement de l'événement d'arrêt
    stop_event.set()

def input_monitor():
    """
    @brief   Thread d'écoute des commandes utilisateur depuis stdin.
    @details Permet de forcer une séquence (touche Entrée ou 's') ou de
             demander l'arrêt ('q'). Les exceptions d'E/S sont gérées pour
             permettre la terminaison propre du thread.
    @return  None
    """
    # Boucle de surveillance des entrées utilisateur
    while sequencer_running and not stop_event.is_set():
        try:
            # Lit la ligne utilisateur
            user_input = input()
            # Vérification des commandes de déclenchement manuel
            if user_input.strip().lower() in ['', 's', 'sequence', 'start']:
                print("[MANUAL] Séquence manuelle déclenchée")
                # Déclenchement manuel
                force_sequence.set()
            # Vérification des commandes d'arrêt
            elif user_input.strip().lower() in ['q', 'quit', 'exit']:
                print("[MANUAL] Arrêt demandé par l'utilisateur")
                # Simule Ctrl+C
                signal_handler(signal.SIGINT, None)
                break
        except (EOFError, KeyboardInterrupt):
            break
        except Exception:
            # Ignorer les erreurs d'entrée pour rester résilient
            pass

def show_error_and_continue(error_pattern, sleep_time=2):
    """
    @brief   Affiche un motif LED d'erreur pendant un temps donné puis
             remet l'indicateur en mode 'sequence_running'.
    @param   error_pattern Nom du motif LED à afficher.
    @param   sleep_time    Durée d'affichage en secondes (par défaut 2s).
    @return  None
    """
    global led_indicator
    # Afficher l'erreur si l'indicateur LED est disponible
    if led_indicator:
        # Afficher l'erreur
        led_indicator.set_pattern(error_pattern)
    # Temporisation pour permettre la lecture
    time.sleep(sleep_time)
    # Revenir en mode séquence si l'indicateur LED est disponible
    if led_indicator:
        # Revenir en mode séquence
        led_indicator.set_pattern('sequence_running')

def run_measurement_sequence(cfg, mac_address, adc, tmux):
    """
    @brief   Exécute une séquence complète de mesures pour tous les canaux
             activés selon la configuration fournie.
    @details Pour chaque canal actif : sélection du rref, configuration ADC,
             lecture des valeurs, conversion en température, envoi API, calcul
             de la température simulée et application via le simulateur de
             résistance. Les motifs LED sont ajustés en fonction des erreurs.

    @param   cfg         Dictionnaire de configuration chargé depuis JSON.
    @param   mac_address Adresse MAC ou identifiant pour les appels API.
    @param   adc         Instance de l'ADC (Ads124s08).
    @param   tmux        Instance du multiplexeur (Tmux1204).
    @return  bool        True si la séquence est globalement considérée comme
                        réussie, False sinon.
    """
    global led_indicator
    # Affichage du début de séquence avec horodatage
    print(f"\n[SEQUENCER] Nouvelle séquence - {datetime.now().strftime('%H:%M:%S')}")

    # Rechargement de la configuration depuis le fichier JSON
    print(f"[CONFIG] Rechargement configuration...")
    # Chemin vers le fichier de configuration
    CONFIG_FILE = os.path.join(SRC_DIR, "config_module", "sensors.json")
    try:
        # Lecture et parsing du JSON - RECHARGEMENT COMPLET
        cfg = load_config(CONFIG_FILE)
        # Filtrage des canaux activés
        enabled_channels = [ch for ch in cfg.get("channels", []) if ch.get("enabled")]
        # Affichage du nombre de canaux actifs
        print(f"[CONFIG] Config rechargée: {len(enabled_channels)} canaux actifs")
        # Affichage du détail des canaux actifs
        for ch_info in enabled_channels:
            print(f"[CONFIG] Canal {ch_info['channel']}: {ch_info['sensor']}")
        
        # Affichage des paramètres de temporisation rechargés
        print(f"[CONFIG] Timeout ADC: {cfg.get('timeout_s', 180)}s")
        print(f"[CONFIG] Délai inter-mesure: {cfg.get('inter_measure_sleep_s', 0.1)}s")
        print(f"[CONFIG] Intervalle séquences: {cfg.get('sequence_interval_minutes', 5)} min")
        print(f"[CONFIG] Mode automatique: {cfg.get('auto_sequence', True)}")
        
    except Exception as e:
        # Gestion des erreurs de rechargement
        print(f"[CONFIG] Erreur rechargement: {e}")
        return False

    # Indiquer au gestionnaire LED que la séquence est en cours
    if led_indicator:
        led_indicator.set_pattern('sequence_running')

    # Valeur de retour agrégée
    sequence_success = True

    # Récupération des paramètres de simulation via l'API
    from app.api_client import get_simulation_data
    try:
        # Appel API pour récupérer les données de simulation
        simulation_data = get_simulation_data(mac_address)
        # Vérification de la validité des données
        if simulation_data is None:
            print("[SIMULATION] Erreur: impossible de récupérer les paramètres API")
            # Indication LED d'erreur API
            if led_indicator:
                led_indicator.set_pattern('api_failed')
            return False
    except requests.exceptions.ConnectionError:
        # Gestion des erreurs de connexion Internet
        print("[SIMULATION] Erreur: Pas de connexion Internet")
        # Indication LED de problème de connexion
        if led_indicator:
            led_indicator.set_pattern('no_internet')
        return False
    except Exception as e:
        # Gestion des autres erreurs API
        print(f"[SIMULATION] Erreur API critique: {e}")
        # Indication LED d'erreur API
        if led_indicator:
            led_indicator.set_pattern('api_failed')
        return False

    # Vérification des entrées 24V (contacts secs)
    test_24v_dry_contact()

    # Boucle de traitement des canaux
    # Compteur de canaux traités
    channels_processed = 0
    # Compteur de canaux en erreur
    channels_failed = 0

    # Boucle sur tous les canaux configurés
    for entry in cfg["channels"]:
        # Numéro du canal à traiter
        ch = entry["channel"]
        # Type de capteur configuré
        sensor_name = entry["sensor"]
        # État d'activation du canal
        enabled = entry.get("enabled", True)

        # Ignorer les canaux désactivés
        if not enabled:
            print(f"[CONFIG] Canal {ch} désactivé - ignoré")
            continue

        # Récupération du profil sonde
        profile = get_profile(sensor_name)
        # Incrément du compteur de canaux traités
        channels_processed += 1

        # Affichage du début de traitement du canal
        print(f"\n[MESURE] Canal {ch} - {sensor_name}")
        try:
            # Sélection de la résistance de référence et configuration ADC
            # Sélection de la résistance de référence via le multiplexeur
            tmux.select_rref_ohm(profile["rref_ohm"])
            # Configuration du canal ADC avec les paramètres du profil
            adc.configure_channel(ch, profile["pga_gain"], profile["idac_uA"])
            # Lecture et affichage du gain configuré
            adc.read_gain()
            # Lecture et affichage de la référence
            adc.read_ref()
            # Lecture et affichage du multiplexeur d'entrée
            adc.read_inpmux()

            # Mesure de la résistance
            # Mesure de la résistance avec les paramètres du profil
            r = adc.measure_resistance(profile["rref_ohm"], profile["pga_gain"], cfg["timeout_s"])
            # Vérification de la validité de la mesure
            if r is None:
                print("[MESURE] Résistance: NaN - Erreur de mesure")
                # Incrément du compteur d'erreurs
                channels_failed += 1
                # Affichage d'erreur LED et continuation
                show_error_and_continue('measure_failed')
                continue
            else:
                # Affichage de la résistance mesurée
                print(f"[MESURE] Résistance: {r:.6f} ohms")

            # Mesure de la température à partir de l'ADC
            # Mesure de la température avec conversion selon le type de sonde
            temperature = adc.measure_temperature(sensor_name, profile["rref_ohm"], profile["pga_gain"], cfg["timeout_s"])
            # Vérification de la validité de la mesure de température
            if temperature is None:
                print("[MESURE] Température non mesurable ou saturation détectée")
                # Incrément du compteur d'erreurs
                channels_failed += 1
                # Affichage d'erreur LED et continuation
                show_error_and_continue('measure_failed')
                continue
            else:
                # Affichage de la température mesurée
                print(f"[MESURE] Température mesurée: {temperature:.2f}°C")

                # Sauvegarde locale de l'état
                save_last_state(channel=ch, resistance_ohm=r, temperature_c=temperature, error=None)

                # Envoi de la mesure vers l'API distante
                from app.api_client import send_temperature_measurement
                try:
                    # Tentative d'envoi de la température vers l'API
                    if send_temperature_measurement(mac_address, temperature, ch):
                        print(f"[API] Température {temperature:.2f}°C envoyée avec succès pour le canal {ch}")
                    else:
                        print(f"[API] Erreur lors de l'envoi de la température pour le canal {ch}")
                        # Affichage court d'erreur API
                        show_error_and_continue('api_failed', 1)
                except requests.exceptions.ConnectionError:
                    # Gestion spécifique des erreurs de connexion
                    print(f"[API] Erreur connexion pour canal {ch}")
                    # Affichage court d'erreur de connexion
                    show_error_and_continue('no_internet', 1)
                except Exception as e:
                    # Gestion des autres erreurs d'envoi
                    print(f"[API] Erreur envoi canal {ch}: {e}")
                    # Affichage court d'erreur API
                    show_error_and_continue('api_failed', 1)

            # Calcul et application de la simulation
            print("[SIMULATION] Calcul et application...")
            
            # Vérification de cohérence entre sonde API et sonde canal
            api_probe_type = simulation_data.get("probe_type")
            if api_probe_type != sensor_name:
                print(f"[SIMULATION] ERREUR: Incohérence type de sonde!")
                print(f"[SIMULATION] Sonde API: '{api_probe_type}' vs Sonde Canal {ch}: '{sensor_name}'")
                print(f"[SIMULATION] La simulation est ignorée pour ce canal")
                channels_failed += 1
                show_error_and_continue('config_error')
                continue
            
            # Injection de la température mesurée dans les données de simulation
            simulation_data["temperature"] = temperature
            # Confirmation du type de sonde (déjà vérifié)
            print(f"[SIMULATION] Type de sonde validé: {sensor_name}")
            # Affichage des paramètres de simulation
            print(f"[SIMULATION] Paramètres: n={simulation_data['n']}, k_m={simulation_data['k_m']}")
            # Affichage des températures utilisées
            print(f"[SIMULATION] T_mes={temperature:.2f}°C, T_prev={simulation_data['forecast_temperature']:.2f}°C")

            # Calcul de la température simulée
            t_sim = run_temperature_simulation(simulation_data)
            # Vérification de la validité du calcul
            if t_sim is None:
                print("[SIMULATION] Erreur lors du calcul de T_sim")
                # Incrément du compteur d'erreurs
                channels_failed += 1
                # Affichage d'erreur LED et continuation
                show_error_and_continue('measure_failed')
                continue
            # Affichage de la température simulée
            print(f"[SIMULATION] Température simulée: {t_sim:.2f}°C")

            # Mise à jour de l'état avec la température simulée
            save_last_state(channel=ch, resistance_ohm=r, temperature_c=temperature, temperature_sim_c=t_sim, error=None)

            # Conversion de la température simulée en résistance cible
            resistance_target = convert_temperature_to_resistance(t_sim, sensor_name)
            # Vérification de la validité de la conversion
            if resistance_target is None:
                print(f"[SIMULATION] Erreur conversion T_sim → résistance pour {sensor_name}")
                # Incrément du compteur d'erreurs
                channels_failed += 1
                # Affichage d'erreur LED et continuation
                show_error_and_continue('measure_failed')
                continue
            # Affichage de la résistance cible calculée
            print(f"[SIMULATION] Résistance cible: {resistance_target:.2f} ohms")

            # Application de la résistance simulée via le multiplexeur
            resistance_sim = ResistanceSimulator()
            # Tentative d'application de la résistance via le MUX
            if resistance_sim.apply_resistance_simulation(resistance_target, ch, sensor_name):
                print(f"[SIMULATION] Résistance appliquée via MUX sur canal {ch} (sonde: {sensor_name})")
            else:
                print(f"[SIMULATION] Erreur lors de l'application MUX sur canal {ch}")
                # Incrément du compteur d'erreurs
                channels_failed += 1
                # Affichage d'erreur LED et continuation
                show_error_and_continue('measure_failed')

            # Pause entre canaux
            time.sleep(cfg["inter_measure_sleep_s"])

        except Exception as e:
            # Gestion des erreurs générales de traitement du canal
            print(f"[ERREUR] Canal {ch}: {e}")
            # Incrément du compteur d'erreurs
            channels_failed += 1
            # Affichage d'erreur critique LED et continuation
            show_error_and_continue('critical_error')
            continue

    # Évaluation finale de la séquence
    # Cas où aucun canal n'a échoué
    if channels_failed == 0:
        print(f"[SEQUENCER] Séquence réussie - {channels_processed} canaux traités")
        # Motif LED normal après succès
        if led_indicator:
            # Motif LED normal après succès
            led_indicator.set_pattern('normal')
        sequence_success = True
    # Cas où certains canaux ont échoué mais pas tous
    elif channels_failed < channels_processed:
        print(f"[SEQUENCER] Séquence partielle - {channels_processed - channels_failed}/{channels_processed} canaux réussis")
        # Indication LED d'erreur de mesure partielle
        if led_indicator:
            led_indicator.set_pattern('measure_failed')
        sequence_success = True
    # Cas où tous les canaux ont échoué
    else:
        print(f"[SEQUENCER] Séquence échouée - Tous les canaux ont échoué")
        # Indication LED d'erreur critique
        if led_indicator:
            led_indicator.set_pattern('critical_error')
        sequence_success = False

    # Affichage de fin de séquence avec horodatage
    print(f"[SEQUENCER] Séquence terminée - {datetime.now().strftime('%H:%M:%S')}")
    return sequence_success


# ---------------------------------------------------------------------------
# Fonctions utilitaires de rechargement dynamique
# ---------------------------------------------------------------------------

def reload_timing_config():
    """
    @brief   Recharge les paramètres de temporisation depuis le fichier de configuration.
    @details Lit uniquement les paramètres de temporisation pour mise à jour dynamique
             sans perturber le reste du système. Utilisé pour permettre la modification
             des intervalles de séquence et du mode automatique via l'interface web.

    @return  Tuple (auto_sequence, sequence_interval_minutes, success)
             où success indique si le rechargement a réussi.
    """
    try:
        # Chemin vers le fichier de configuration
        CONFIG_FILE = os.path.join(SRC_DIR, "config_module", "sensors.json")
        # Rechargement de la configuration complète
        cfg = load_config(CONFIG_FILE)
        
        # Extraction des paramètres de temporisation
        auto_sequence = cfg.get("auto_sequence", True)
        sequence_interval_minutes = cfg.get("sequence_interval_minutes", 5)
        
        # Log des paramètres rechargés
        print(f"[CONFIG] Paramètres rechargés - Auto: {auto_sequence}, Intervalle: {sequence_interval_minutes}min")
        
        return auto_sequence, sequence_interval_minutes, True
    except Exception as e:
        # Log d'erreur en cas d'échec
        print(f"[CONFIG] Erreur rechargement paramètres: {e}")
        # Retour avec valeurs par défaut
        return True, 5, False


# ---------------------------------------------------------------------------
# Point d'entrée principal du programme
# ---------------------------------------------------------------------------

def main():
    """
    @brief   Point d'entrée principal du programme.
    @details Parse les arguments de la ligne de commande, initialise le
             matériel (GPIO, ADC, MUX), le gestionnaire LED, et exécute le
             séquenceur en mode automatique ou manuel selon la configuration.
    @return  None
    """
    global sequencer_running, led_indicator

    # Analyse des options en ligne de commande
    # Création du parser d'arguments
    parser = argparse.ArgumentParser(description="Système de mesure et simulation de température")
    # Option pour le mode manuel
    parser.add_argument("--manual", action="store_true", help="Mode manuel (demande confirmation à chaque séquence)")
    # Option pour une exécution unique
    parser.add_argument("--once", action="store_true", help="Exécute une seule séquence puis s'arrête")
    # Option pour le serveur web
    parser.add_argument("--webui", action="store_true", help="Lance le serveur web sur le port 8080")
    # Parsing des arguments fournis
    args = parser.parse_args()

    # Affichage du titre du programme
    print("=== SYSTÈME DE MESURE ET SIMULATION ===")

    # Chargement de la configuration
    CONFIG_FILE = os.path.join(SRC_DIR, "config_module", "sensors.json")
    # Chargement initial de la configuration
    cfg = load_config(CONFIG_FILE)

    # Paramètres de séquence automatique
    # Récupération du mode automatique depuis la config
    auto_sequence = cfg.get("auto_sequence", True)
    # Récupération de l'intervalle entre séquences
    sequence_interval_minutes = cfg.get("sequence_interval_minutes", 5)

    # Présentation des canaux configurés
    # Filtrage des canaux activés
    enabled_channels = [entry for entry in cfg["channels"] if entry.get("enabled", True)]
    # Filtrage des canaux désactivés
    disabled_channels = [entry for entry in cfg["channels"] if not entry.get("enabled", True)]

    # Affichage du nombre de canaux activés
    print(f"[CONFIG] Canaux activés: {len(enabled_channels)}")
    # Affichage du détail des canaux activés
    for entry in enabled_channels:
        print(f"[CONFIG]   Canal {entry['channel']}: {entry['sensor']}")

    # Affichage des canaux désactivés s'il y en a
    if disabled_channels:
        print(f"[CONFIG] Canaux désactivés: {len(disabled_channels)}")
        # Affichage du détail des canaux désactivés
        for entry in disabled_channels:
            print(f"[CONFIG]   Canal {entry['channel']}: {entry['sensor']} (OFF)")

    # Affichage du mode choisi
    # Mode manuel demandé en ligne de commande
    if args.manual:
        print(f"[CONFIG] Mode: MANUEL (demande confirmation)")
    # Mode exécution unique
    elif args.once:
        print(f"[CONFIG] Mode: UNE SEULE FOIS")
    # Mode automatique configuré
    elif auto_sequence:
        print(f"[CONFIG] Mode: AUTOMATIQUE (toutes les {sequence_interval_minutes} minutes)")
        print(f"[CONFIG] Commandes disponibles pendant l'exécution:")
        print(f"[CONFIG]   - Appuyez sur ENTRÉE ou tapez 's' pour forcer une séquence")
        print(f"[CONFIG]   - Tapez 'q' pour quitter")
    # Mode manuel par configuration
    else:
        print(f"[CONFIG] Mode: MANUEL (auto_sequence=false dans config)")

    # Démarrage optionnel du serveur web en arrière-plan
    webui_thread = None
    # Vérification si le serveur web est demandé
    if args.webui:
        print(f"[WEBUI] Démarrage du serveur web sur http://localhost:8080")
        # Création du thread pour le serveur web
        webui_thread = threading.Thread(target=start_webui_server, daemon=True)
        # Démarrage du thread serveur web
        webui_thread.start()
        # Laisser le temps au serveur de monter
        time.sleep(2)

    # Affichage des motifs LED disponibles (référence)
    print(f"\n[LED] Patterns d'erreur disponibles:")
    print(f"[LED]   - NORMAL: LED allumée en continu")
    print(f"[LED]   - SEQUENCE: Clignotement continu pendant mesure")
    print(f"[LED]   - NO_INTERNET: 1 clignotement sur 10s (pas de connexion Internet)")
    print(f"[LED]   - API_FAILED: 2 clignotements sur 10s (erreur API/connexion)")
    print(f"[LED]   - MEASURE_FAILED: 3 clignotements sur 10s (erreur mesure ADC/résistance)")
    print(f"[LED]   - CRITICAL_ERROR: 4 clignotements sur 10s (erreur critique système)")
    print(f"[LED]   - CONFIG_ERROR: 5 clignotements sur 10s (erreur de configuration)")

    # Ligne vide pour la lisibilité
    print()

    # Installation du handler pour Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Initialisation du gestionnaire LED
    # Création de l'instance de gestion LED
    led_indicator = create_led_indicator(GPIO_CHIP_PATH, FRONT_LED)
    # Vérification de l'initialisation LED
    if led_indicator:
        print("[LED] Système LED initialisé - LED normale ON")
    else:
        print("[LED] Erreur : Impossible d'initialiser la LED")

    # Initialisation du matériel GPIO/ADC/MUX
    # Initialisation du relais de commande principal
    relay = GPIO(GPIO_CHIP_PATH, CMD_RELAY, "out")
    # Activer le relais principal
    relay.write(True)
    # Instance du multiplexeur
    tmux = Tmux1204()
    # Instance de l'ADC
    adc = Ads124s08()
    # Récupération de l'adresse MAC depuis la configuration
    mac_address = cfg.get("mac_address", "0030DEABCDEF")

    try:
        # Activation du séquenceur principal
        sequencer_running = True
        # Calcul du temps de la première séquence
        next_sequence_time = datetime.now()

        # Thread d'écoute utilisateur pour le mode automatique
        input_thread = None
        # Vérification si le thread d'écoute est nécessaire
        if auto_sequence and not args.manual and not args.once:
            # Création du thread de surveillance des entrées
            input_thread = threading.Thread(target=input_monitor, daemon=True)
            # Démarrage du thread de surveillance
            input_thread.start()
            print("[MANUAL] Thread de surveillance des entrées démarré")

        # Boucle principale du séquenceur
        # Boucle tant que le séquenceur est actif et pas d'arrêt demandé
        while sequencer_running and not stop_event.is_set():
            # Récupération du temps actuel
            current_time = datetime.now()

            # Initialisation des variables de contrôle
            should_run = False
            sequence_reason = ""

            # Déclenchement manuel depuis input_monitor
            # Vérification d'un déclenchement manuel
            if force_sequence.is_set():
                should_run = True
                sequence_reason = "MANUELLE"
                # Remise à zéro du flag de déclenchement manuel
                force_sequence.clear()
                # Rechargement des paramètres avant reprogrammation du cycle
                auto_sequence_updated, sequence_interval_minutes_updated, reload_success = reload_timing_config()
                if reload_success:
                    auto_sequence = auto_sequence_updated
                    sequence_interval_minutes = sequence_interval_minutes_updated
                # Reprogrammation du cycle automatique si applicable
                if auto_sequence and not args.manual:
                    # Recalcul du temps de prochaine séquence avec le nouvel intervalle
                    next_sequence_time = current_time + timedelta(minutes=sequence_interval_minutes)
                    print(f"[SEQUENCER] Cycle automatique redémarré - Prochaine séquence à: {next_sequence_time.strftime('%H:%M:%S')}")
            # Mode exécution unique
            elif args.once:
                should_run = True
                sequence_reason = "UNIQUE"
                # Arrêt après une exécution
                sequencer_running = False
            # Mode manuel interactif
            elif args.manual or not auto_sequence:
                print(f"[SEQUENCER] Appuyez sur Entrée pour lancer une séquence (Ctrl+C pour arrêter)...")
                try:
                    # Attente d'une entrée utilisateur
                    input()
                    should_run = True
                    sequence_reason = "MANUELLE"
                except EOFError:
                    break
            # Mode automatique basé sur l'horloge
            else:
                # Vérification si c'est l'heure d'une nouvelle séquence
                if current_time >= next_sequence_time:
                    should_run = True
                    sequence_reason = "AUTOMATIQUE"
                    # Programmation de la prochaine séquence
                    next_sequence_time = current_time + timedelta(minutes=sequence_interval_minutes)
                    print(f"[SEQUENCER] Prochaine séquence automatique programmée à: {next_sequence_time.strftime('%H:%M:%S')}")

            # Exécution de la séquence si déclenchée
            if should_run:
                # Rechargement des paramètres de temporisation avant séquence (si pas déjà fait)
                if sequence_reason != "MANUELLE":  # Pour les manuelles, déjà fait plus haut
                    print(f"[SEQUENCER] Rechargement paramètres temporisation...")
                    auto_sequence_updated, sequence_interval_minutes_updated, reload_success = reload_timing_config()
                    if reload_success:
                        # Sauvegarde de l'ancien intervalle pour comparaison
                        old_interval = sequence_interval_minutes
                        # Mise à jour des paramètres pour les prochains cycles
                        auto_sequence = auto_sequence_updated
                        sequence_interval_minutes = sequence_interval_minutes_updated
                        # Recalcul du prochain cycle si en mode automatique et intervalle modifié
                        if sequence_reason == "AUTOMATIQUE" and sequence_interval_minutes_updated != old_interval:
                            next_sequence_time = current_time + timedelta(minutes=sequence_interval_minutes)
                            print(f"[SEQUENCER] Intervalle mis à jour: {old_interval}min → {sequence_interval_minutes}min")
                
                print(f"[SEQUENCER] Démarrage séquence {sequence_reason} - {current_time.strftime('%H:%M:%S')}")
                # Appel de la fonction de séquence de mesure
                success = run_measurement_sequence(cfg, mac_address, adc, tmux)
                # Vérification du succès de la séquence
                if success:
                    print(f"[SEQUENCER] Séquence {sequence_reason} terminée avec succès")
                else:
                    print("[SEQUENCER] Erreur lors de la séquence")

            # Pause courte pour permettre la réactivité aux entrées
            # Pause seulement en mode automatique continu
            if auto_sequence and not args.manual and not args.once and sequencer_running:
                time.sleep(1)

    except KeyboardInterrupt:
        # Gestion de l'interruption par Ctrl+C
        print("\n[SEQUENCER] Arrêt demandé par l'utilisateur...")
    finally:
        # Arrêt du séquenceur
        sequencer_running = False
        # Déclenchement de l'événement d'arrêt
        stop_event.set()

        # Arrêt propre du thread d'entrée si actif
        # Vérification de l'existence et de l'activité du thread
        if input_thread and input_thread.is_alive():
            print("[MANUAL] Arrêt du thread de surveillance...")
            # Attente de la fin du thread avec timeout
            input_thread.join(timeout=1)

        # Tentatives de fermeture des périphériques matériels
        # Fermeture de l'ADC
        try:
            adc.close()
        except Exception:
            pass
        # Fermeture du multiplexeur
        try:
            tmux.close()
        except Exception:
            pass
        # Fermeture du gestionnaire LED
        try:
            if led_indicator:
                led_indicator.close()
        except Exception:
            pass
        # Désactivation et fermeture du relais
        try:
            relay.write(False)
            relay.close()
        except Exception:
            pass

        # Message final de confirmation d'arrêt
        print("[SEQUENCER] Système arrêté proprement")

# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
