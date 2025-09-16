# -*- coding: utf-8 -*-
# file: temperature_conversion.py
"""
Module pour convertir une résistance mesurée en température via interpolation linéaire.
"""

from sensor_profiles import SENSOR_TABLES

import parse_sensor_data

# Load sensor data from CSV
sensor_data = parse_sensor_data.parse_sensor_data("sensor_resistance_reference.csv")

def resistance_to_temperature(resistance, table):
    """
    Convertit une résistance mesurée en température via interpolation linéaire.

    :param resistance: Résistance mesurée (en ohms).
    :param table: Liste de tuples (résistance, température).
    :return: Température interpolée (en °C).
    """
    for i in range(len(table) - 1):
        r1, t1 = table[i]
        r2, t2 = table[i + 1]
        if r1 <= resistance <= r2:
            # Interpolation linéaire
            temperature = t1 + (resistance - r1) / (r2 - r1) * (t2 - t1)
            return temperature
    # Si hors des limites de la table
    return None

def resistance_to_temperature_dynamic(resistance, sensor):
    """
    Convertit une résistance mesurée en température pour un capteur donné.

    :param resistance: Résistance mesurée (en ohms).
    :param sensor: Nom du capteur.
    :return: Température interpolée (en °C) ou None si hors limites.
    """
    # Vérifie si le capteur existe dans les données
    if sensor not in SENSOR_TABLES:
        raise ValueError(f"Capteur {sensor} non trouvé dans les données.")

    table = SENSOR_TABLES[sensor]
    for i in range(len(table) - 1):
        t1, r1 = table[i]
        t2, r2 = table[i + 1]
        if r1 <= resistance <= r2:
            # Interpolation linéaire
            temperature = t1 + (resistance - r1) / (r2 - r1) * (t2 - t1)
            return temperature
    # Si hors des limites de la table
    return None

# Table des résistances et températures pour la sonde Ni1000 TK5000
ni1000_table = [
    (935, -15.0), (941, -13.5), (947, -12.0), (954, -10.5), (961, -9.0),
    (967, -7.5), (973, -6.0), (980, -4.5), (987, -3.0), (993, -1.5),
    (1000, 0.0), (1007, 1.5), (1014, 3.0), (1020, 4.5), (1027, 6.0),
    (1033, 7.5), (1040, 9.0), (1047, 10.5), (1054, 12.0), (1061, 13.5),
    (1067, 15.0), (1074, 16.5), (1082, 18.0), (1089, 19.5), (1095, 21.0),
    (1102, 22.5), (1110, 24.0), (1116, 25.5), (1123, 27.0), (1131, 28.5),
    (1138, 30.0), (1145, 31.5)
]