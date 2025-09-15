# -*- coding: utf-8 -*-
# file: sensor_profiles.py
"""
Profils capteurs extraits de 'Calcul ADC.xlsx' (Feuil1).
Clés:
- rref_ohm: Rref sélectionnée via TMUX1204 (A1 A0: 00=2.2k, 01=2.7k, 10=10k, 11=100k)
- idac_uA: courant IDAC
- pga_gain: gain PGA (1,2,4,8,16,32,64,128)

Sortie du système: résistance [Ohm] uniquement.
"""

SENSOR_PROFILES = {
    "De Dietrich AF60": {
        "rref_ohm": 2200,
        "idac_uA": 250,
        "pga_gain": 1
    },
    "Siemens QAC32": {
        "rref_ohm": 2700,
        "idac_uA": 250,
        "pga_gain": 4
    },
    "PT1000": {
        "rref_ohm": 10000,
        "idac_uA": 100,
        "pga_gain": 8
    },
    "Ni1000 TK5000": {
        "rref_ohm": 10000,
        "idac_uA": 100,
        "pga_gain": 4
    },
    "Ni1000 TK6180": {
        "rref_ohm": 10000,
        "idac_uA": 50,
        "pga_gain": 8
    },
    "NTC 1k 3528": {
        "rref_ohm": 10000,
        "idac_uA": 100,
        "pga_gain": 1
    },
    "KTY81-210": {
        "rref_ohm": 10000,
        "idac_uA": 100,
        "pga_gain": 4
    },
    "NTC 2k 3390": {
        "rref_ohm": 100000,
        "idac_uA": 10,
        "pga_gain": 8
    },
    "NTC 2.2k 3528": {
        "rref_ohm": 100000,
        "idac_uA": 10,
        "pga_gain": 4
    },
    "NTC 10k 3977": {
        "rref_ohm": 100000,
        "idac_uA": 10,
        "pga_gain": 1
    }
}

def get_profile(sensor_name):
    if sensor_name in SENSOR_PROFILES:
        return SENSOR_PROFILES[sensor_name]
    raise KeyError("Type de sonde inconnu: " + str(sensor_name))
