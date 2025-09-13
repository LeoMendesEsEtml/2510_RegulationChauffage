# -*- coding: utf-8 -*-
# file: config_loader.py
"""
Charge un JSON minimal:
{
  "timeout_s": 180,
  "inter_measure_sleep_s": 0.1,
  "loop_sleep_s": 1.0,
  "channels": [
    { "channel": 1, "sensor": "Ni1000 TK5000" },
    ...
  ]
}
"""

import json
import os

def load_config(path):
    if os.path.exists(path) is False:
        raise FileNotFoundError("Config introuvable: " + str(path))
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
