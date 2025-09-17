#!/usr/bin/env python3
# file: webui_server.py
# One-page WebUI to read/write config.json and display last_state.json

import os
import json
from flask import Flask, request, jsonify, send_from_directory

# Adaptation pour Windows - chemins relatifs au script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config_module", "sensors.json")
STATE_PATH = os.path.join(BASE_DIR, "state", "last_state.json")
WEBUI_DIR = os.path.join(BASE_DIR, "webui")

app = Flask(__name__, static_folder=None)

@app.route("/", methods=["GET"])
def serve_index():
  return send_from_directory(WEBUI_DIR, "index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
  try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
      data = json.load(f)
    return jsonify(data), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500

@app.route("/api/config", methods=["PUT"])
def put_config():
  try:
    payload = request.get_json(force=True, silent=False)
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
      json.dump(payload, f, ensure_ascii=False, indent=2)
      f.flush()
      os.fsync(f.fileno())
    os.replace(tmp_path, CONFIG_PATH)
    return jsonify({"status": "ok"}), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 400

@app.route("/api/last", methods=["GET"])
def get_last():
  try:
    with open(STATE_PATH, "r", encoding="utf-8") as f:
      data = json.load(f)
    return jsonify(data), 200
  except FileNotFoundError:
    return jsonify({
      "timestamp": None,
      "channel": None,
      "resistance_ohm": None,
      "temperature_c": None,
      "temperature_sim_c": None,
      "error": "state file not found"
    }), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
  print(f"BASE_DIR: {BASE_DIR}")
  print(f"CONFIG_PATH: {CONFIG_PATH}")
  print(f"STATE_PATH: {STATE_PATH}")
  print(f"WEBUI_DIR: {WEBUI_DIR}")
  app.run(host="0.0.0.0", port=8080)