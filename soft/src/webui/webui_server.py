#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@file        webui_server.py
@brief       Serveur web pour interface utilisateur de configuration.
@details     Interface web Flask monopage pour lecture/écriture de la configuration
             sensors.json et affichage de l'état last_state.json. Fournit API REST
             complète pour gestion configuration canaux et monitoring système.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

# Import du module système pour gestion des chemins
import os
# Import du module JSON pour sérialisation des données
import json
# Import pour gestion des horodatages
from datetime import datetime
# Imports Flask pour serveur web et API REST
from flask import Flask, request, jsonify, send_from_directory


# ---------------------------------------------------------------------------
# Configuration des chemins et constantes
# ---------------------------------------------------------------------------

# Répertoire de base adapté pour Windows - chemin relatif au script
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Chemin vers le fichier de configuration des capteurs
CONFIG_PATH = os.path.join(BASE_DIR, "config_module", "sensors.json")
# Chemin vers le fichier d'état du système
STATE_PATH = os.path.join(BASE_DIR, "state", "last_state.json")
# Répertoire des fichiers statiques de l'interface web
WEBUI_DIR = os.path.dirname(__file__)

# Création de l'instance Flask avec configuration des fichiers statiques
app = Flask(__name__, static_folder=WEBUI_DIR, static_url_path='/static')


# ---------------------------------------------------------------------------
# Routes de l'interface web
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def serve_index():
    """
    @brief   Sert la page principale de l'interface web.
    @details Route racine qui retourne le fichier index.html depuis
             le répertoire webui pour affichage de l'interface utilisateur.

    @return  Fichier HTML de l'interface principale.
    """
    # Retour du fichier index.html depuis le répertoire webui
    return send_from_directory(WEBUI_DIR, "index.html")


# ---------------------------------------------------------------------------
# API REST pour gestion de la configuration
# ---------------------------------------------------------------------------

@app.route("/api/config", methods=["GET"])
def get_config():
    """
    @brief   Récupère la configuration actuelle des capteurs.
    @details Lecture du fichier sensors.json et retour des données
             de configuration en format JSON. Gère les erreurs de
             lecture et affiche des informations de débogage.

    @return  Configuration JSON ou message d'erreur avec code HTTP.
    """
    # Bloc de traitement avec gestion d'exceptions
    try:
        # Log de l'opération de lecture avec chemin complet
        print(f"[WEBUI] Lecture configuration depuis {CONFIG_PATH}")
        # Ouverture du fichier de configuration en UTF-8
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            # Chargement des données JSON depuis le fichier
            data = json.load(f)
        # Log du nombre de canaux chargés pour validation
        print(f"[WEBUI] Configuration chargée: {len(data.get('channels', []))} canaux")
        # Retour des données avec code HTTP 200 (succès)
        return jsonify(data), 200
    except Exception as e:
        # Log de l'erreur rencontrée lors de la lecture
        print(f"[WEBUI] Erreur lecture config: {e}")
        # Retour d'erreur avec code HTTP 500 (erreur serveur)
        return jsonify({"error": str(e)}), 500

@app.route("/api/config", methods=["PUT"])
def put_config():
    """
    @brief   Sauvegarde une nouvelle configuration des capteurs.
    @details Reçoit des données JSON, valide le contenu et sauvegarde
             dans sensors.json avec sauvegarde atomique via fichier temporaire.
             Affiche un résumé des changements principaux.

    @return  Statut de sauvegarde ou message d'erreur avec code HTTP.
    """
    # Bloc de traitement avec gestion d'exceptions
    try:
        # Récupération des données JSON depuis la requête HTTP
        payload = request.get_json(force=True, silent=False)
        # Log du nombre de canaux à sauvegarder
        print(f"[WEBUI] Sauvegarde configuration: {len(payload.get('channels', []))} canaux")
        
        # Section d'affichage des changements principaux de configuration
        if 'mac_address' in payload:
            # Log de la nouvelle adresse MAC si présente
            print(f"[WEBUI] MAC: {payload['mac_address']}")
        if 'auto_sequence' in payload:
            # Log du mode séquence automatique si présent
            print(f"[WEBUI] Auto séquence: {payload['auto_sequence']}")
        
        # Filtrage et affichage des canaux activés seulement
        enabled_channels = [ch for ch in payload.get('channels', []) if ch.get('enabled')]
        # Log des numéros de canaux activés pour validation
        print(f"[WEBUI] Canaux activés: {[ch['channel'] for ch in enabled_channels]}")
        
        # Création du chemin de fichier temporaire pour sauvegarde atomique
        tmp_path = CONFIG_PATH + ".tmp"
        # Ouverture du fichier temporaire en mode écriture UTF-8
        with open(tmp_path, "w", encoding="utf-8") as f:
            # Écriture des données JSON avec formatage lisible
            json.dump(payload, f, ensure_ascii=False, indent=2)
            # Force l'écriture vers le disque (buffer flush)
            f.flush()
            # Synchronisation système pour garantir l'écriture physique
            os.fsync(f.fileno())
        # Remplacement atomique du fichier de configuration
        os.replace(tmp_path, CONFIG_PATH)
        
        # Log de confirmation de sauvegarde réussie
        print(f"[WEBUI] Configuration sauvegardée dans {CONFIG_PATH}")
        # Retour de confirmation avec code HTTP 200 (succès)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        # Log de l'erreur rencontrée lors de la sauvegarde
        print(f"[WEBUI] Erreur sauvegarde config: {e}")
        # Retour d'erreur avec code HTTP 400 (requête invalide)
        return jsonify({"error": str(e)}), 400


# ---------------------------------------------------------------------------
# API REST pour monitoring de l'état système
# ---------------------------------------------------------------------------

@app.route("/api/last", methods=["GET"])
def get_last():
    """
    @brief   Récupère le dernier état du système de mesure.
    @details Lecture du fichier last_state.json contenant les dernières
             mesures, températures et statuts. Gère le cas où le fichier
             n'existe pas encore et retourne un état par défaut.

    @return  État JSON du système ou structure par défaut si fichier absent.
    """
    # Bloc de traitement avec gestion spécifique des exceptions
    try:
        # Ouverture du fichier d'état en mode lecture UTF-8
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            # Chargement des données d'état depuis le fichier JSON
            data = json.load(f)
        # Log conditionnel seulement si données significatives présentes
        if data.get('last_channel') is not None:
            # Affichage du canal et température de la dernière mesure
            print(f"[WEBUI] Données canal {data['last_channel']}: {data.get('last_temperature_c', 'N/A')}°C")
        # Retour des données d'état avec code HTTP 200 (succès)
        return jsonify(data), 200
    except FileNotFoundError:
        # Gestion spécifique du cas où le fichier d'état n'existe pas
        print(f"[WEBUI] Fichier état non trouvé: {STATE_PATH}")
        # Retour d'une structure d'état par défaut avec tous les champs
        return jsonify({
            "last_timestamp": None,
            "last_channel": None,
            "last_resistance_ohm": None,
            "last_temperature_c": None,
            "last_temperature_sim_c": None,
            "last_error": "state file not found",
            "channels": {}
        }), 200
    except Exception as e:
        # Gestion de toute autre erreur de lecture d'état
        print(f"[WEBUI] Erreur lecture état: {e}")
        # Retour d'erreur avec code HTTP 500 (erreur serveur)
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# API REST pour contrôle système
# ---------------------------------------------------------------------------

@app.route("/api/force-reload", methods=["POST"])
def force_reload():
    """
    @brief   Force le rechargement de la configuration au prochain cycle.
    @details Crée un fichier flag force_reload.flag avec horodatage
             pour déclencher le rechargement de configuration par
             le processus principal lors du prochain cycle de mesure.

    @return  Confirmation de demande ou message d'erreur avec code HTTP.
    """
    # Bloc de traitement avec gestion d'exceptions
    try:
        # Construction du chemin vers le fichier flag de rechargement
        flag_path = os.path.join(BASE_DIR, "state", "force_reload.flag")
        # Création du répertoire de destination si inexistant
        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        # Création du fichier flag avec horodatage ISO
        with open(flag_path, "w") as f:
            # Écriture de l'horodatage de la demande de rechargement
            f.write(datetime.now().isoformat())
        
        # Log de confirmation de demande de rechargement
        print(f"[WEBUI] Rechargement config demandé")
        # Retour de confirmation avec code HTTP 200 (succès)
        return jsonify({"status": "reload requested"}), 200
    except Exception as e:
        # Log de l'erreur rencontrée lors de la création du flag
        print(f"[WEBUI] Erreur demande rechargement: {e}")
        # Retour d'erreur avec code HTTP 500 (erreur serveur)
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Point d'entrée principal du serveur
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Affichage des chemins de configuration pour débogage
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"CONFIG_PATH: {CONFIG_PATH}")
    print(f"STATE_PATH: {STATE_PATH}")
    print(f"WEBUI_DIR: {WEBUI_DIR}")
    # Démarrage du serveur Flask sur adresse IP fixe et port 8080
    app.run(host="192.168.1.109", port=8080)