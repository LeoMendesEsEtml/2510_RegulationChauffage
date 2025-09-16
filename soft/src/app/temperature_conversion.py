# -*- coding: utf-8 -*-
# file: temperature_conversion.py
"""
Module pour convertir une résistance mesurée en température via interpolation linéaire.
"""

from app.sensor_profiles import SENSOR_TABLES

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