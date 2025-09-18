#!/usr/bin/env python3
# file: webui_server.py
# One-page WebUI to read/write config.json and display last_state.json

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

# Adaptation pour Windows - chemins relatifs au script
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(BASE_DIR, "config_module", "sensors.json")
STATE_PATH = os.path.join(BASE_DIR, "state", "last_state.json")
WEBUI_DIR = os.path.join(BASE_DIR, "webui")

app = Flask(__name__, static_folder=WEBUI_DIR, static_url_path="")

@app.route("/", methods=["GET"])
def serve_index():
  return send_from_directory(WEBUI_DIR, "index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
  try:
    print(f"[WEBUI] Lecture configuration depuis {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
      data = json.load(f)
    print(f"[WEBUI] Configuration chargée: {len(data.get('channels', []))} canaux")
    return jsonify(data), 200
  except Exception as e:
    print(f"[WEBUI] Erreur lecture config: {e}")
    return jsonify({"error": str(e)}), 500

@app.route("/api/config", methods=["PUT"])
def put_config():
  try:
    payload = request.get_json(force=True, silent=False)
    print(f"[WEBUI] Sauvegarde configuration: {len(payload.get('channels', []))} canaux")
    
    # Affichage des changements principaux
    if 'mac_address' in payload:
      print(f"[WEBUI] MAC: {payload['mac_address']}")
    if 'auto_sequence' in payload:
      print(f"[WEBUI] Auto séquence: {payload['auto_sequence']}")
    
    enabled_channels = [ch for ch in payload.get('channels', []) if ch.get('enabled')]
    print(f"[WEBUI] Canaux activés: {[ch['channel'] for ch in enabled_channels]}")
    
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
      json.dump(payload, f, ensure_ascii=False, indent=2)
      f.flush()
      os.fsync(f.fileno())
    os.replace(tmp_path, CONFIG_PATH)
    
    print(f"[WEBUI] Configuration sauvegardée dans {CONFIG_PATH}")
    return jsonify({"status": "ok"}), 200
  except Exception as e:
    print(f"[WEBUI] Erreur sauvegarde config: {e}")
    return jsonify({"error": str(e)}), 400

@app.route("/api/last", methods=["GET"])
def get_last():
  try:
    with open(STATE_PATH, "r", encoding="utf-8") as f:
      data = json.load(f)
    # Log seulement si il y a des données intéressantes
    if data.get('last_channel') is not None:
      print(f"[WEBUI] Données canal {data['last_channel']}: {data.get('last_temperature_c', 'N/A')}°C")
    return jsonify(data), 200
  except FileNotFoundError:
    print(f"[WEBUI] Fichier état non trouvé: {STATE_PATH}")
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
    print(f"[WEBUI] Erreur lecture état: {e}")
    return jsonify({"error": str(e)}), 500

@app.route("/api/force-reload", methods=["POST"])
def force_reload():
  """Force le rechargement de la configuration au prochain cycle"""
  try:
    # Créer un fichier flag pour déclencher le rechargement
    flag_path = os.path.join(BASE_DIR, "state", "force_reload.flag")
    os.makedirs(os.path.dirname(flag_path), exist_ok=True)
    with open(flag_path, "w") as f:
      f.write(datetime.now().isoformat())
    
    print(f"[WEBUI] Rechargement config demandé")
    return jsonify({"status": "reload requested"}), 200
  except Exception as e:
    print(f"[WEBUI] Erreur demande rechargement: {e}")
    return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
  print(f"BASE_DIR: {BASE_DIR}")
  print(f"CONFIG_PATH: {CONFIG_PATH}")
  print(f"STATE_PATH: {STATE_PATH}")
  print(f"WEBUI_DIR: {WEBUI_DIR}")
  app.run(host="0.0.0.0", port=8080)