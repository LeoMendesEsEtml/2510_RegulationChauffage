# -*- coding: utf-8 -*-
# fichier : temperature_conversion.py
"""
Module pour convertir une résistance mesurée en température via interpolation linéaire
et pour convertir une température en résistance (pour la simulation).
"""

from app.sensor_profiles import SENSOR_TABLES  # Importation des tables de capteurs depuis le module sensor_profiles

def resistance_to_temperature(resistance, table):
    """
    Convertit une résistance mesurée en température via interpolation linéaire.

    :param resistance: Résistance mesurée (en ohms).
    :param table: Liste de tuples (résistance, température).
    :return: Température interpolée (en °C).
    """
    for i in range(len(table) - 1):  # Parcourt les paires de points dans la table
        r1, t1 = table[i]  # Récupère la résistance et la température du premier point
        r2, t2 = table[i + 1]  # Récupère la résistance et la température du second point
        if r1 <= resistance <= r2:  # Vérifie si la résistance mesurée est entre les deux points
            # Interpolation linéaire
            temperature = t1 + (resistance - r1) / (r2 - r1) * (t2 - t1)  # Calcule la température interpolée
            return temperature  # Retourne la température interpolée
    # Si hors des limites de la table
    r_min, t_min = table[0]  # Récupère la résistance et la température minimales
    r_max, t_max = table[-1]  # Récupère la résistance et la température maximales
    if resistance < r_min:  # Si la résistance est inférieure à la résistance minimale
        return t_min  # Retourne la température minimale
    if resistance > r_max:  # Si la résistance est supérieure à la résistance maximale
        return t_max  # Retourne la température maximale
    return None  # Retourne None si aucune condition n'est remplie

def resistance_to_temperature_dynamic(resistance, sensor):
    """
    Convertit une résistance mesurée en température pour un capteur donné.

    :param resistance: Résistance mesurée (en ohms).
    :param sensor: Nom du capteur.
    :return: Température interpolée (en °C) ou None si hors limites.
    """
    # Vérifie si le capteur existe dans les données
    if sensor not in SENSOR_TABLES:  # Vérifie si le capteur est présent dans les tables de capteurs
        raise ValueError(f"Capteur {sensor} non trouvé dans les données.")  # Lève une erreur si le capteur est introuvable

    table = SENSOR_TABLES[sensor]  # Récupère la table associée au capteur
    for i in range(len(table) - 1):  # Parcourt les paires de points dans la table
        t1, r1 = table[i]  # Récupère la température et la résistance du premier point
        t2, r2 = table[i + 1]  # Récupère la température et la résistance du second point
        if r1 <= resistance <= r2:  # Vérifie si la résistance mesurée est entre les deux points
            # Interpolation linéaire
            temperature = t1 + (resistance - r1) / (r2 - r1) * (t2 - t1)  # Calcule la température interpolée
            return temperature  # Retourne la température interpolée
    # min/max
    t_min, r_min = table[0]  # Récupère la température et la résistance minimales
    t_max, r_max = table[-1]  # Récupère la température et la résistance maximales
    if resistance < r_min:  # Si la résistance est inférieure à la résistance minimale
        return t_min  # Retourne la température minimale
    if resistance > r_max:  # Si la résistance est supérieure à la résistance maximale
        return t_max  # Retourne la température maximale
    return None  # Retourne None si aucune condition n'est remplie

def temperature_to_resistance_dynamic(temperature, sensor):
    """
    Convertit une température en résistance pour un capteur donné (conversion inverse).
    Utilisé pour la simulation de résistance.

    :param temperature: Température en °C.
    :param sensor: Nom du capteur.
    :return: Résistance interpolée (en ohms) ou None si hors limites.
    """
    # Vérifie si le capteur existe dans les données
    if sensor not in SENSOR_TABLES:
        raise ValueError(f"Capteur {sensor} non trouvé dans les données.")

    table = SENSOR_TABLES[sensor]  # Récupère la table associée au capteur
    
    # Parcourt les paires de points dans la table
    for i in range(len(table) - 1):
        t1, r1 = table[i]  # Récupère la température et la résistance du premier point
        t2, r2 = table[i + 1]  # Récupère la température et la résistance du second point
        
        # Vérifie si la température est entre les deux points
        if t1 <= temperature <= t2:
            # Interpolation linéaire inverse (température -> résistance)
            resistance = r1 + (temperature - t1) / (t2 - t1) * (r2 - r1)
            return resistance
    
    # Gestion des limites de la table
    t_min, r_min = table[0]  # Récupère la température et la résistance minimales
    t_max, r_max = table[-1]  # Récupère la température et la résistance maximales
    
    if temperature < t_min:  # Si la température est inférieure à la température minimale
        return r_min  # Retourne la résistance minimale
    if temperature > t_max:  # Si la température est supérieure à la température maximale
        return r_max  # Retourne la résistance maximale
    
    return None  # Retourne None si aucune condition n'est remplie

def convert_temperature_to_resistance(temperature, probe_type):
    """
    Fonction de conversion principale pour la simulation de résistance.
    Supporte différents types de sondes avec leurs caractéristiques spécifiques.
    
    :param temperature: Température simulée en °C
    :param probe_type: Type de sonde ("PT1000", "Ni1000_TK5000", "NTC_10k", etc.)
    :return: Résistance simulée en ohms
    """
    print(f"[CONV] Conversion T->R: {temperature:.2f}°C -> ? ohms (sonde: {probe_type})")
    
    # Normalisation du nom de la sonde pour compatibilité
    probe_mapping = {
        "PT1000": "PT1000",
        "Ni1000_TK5000": "Ni1000 TK5000",
        "Ni1000_TK5000": "Ni1000 TK5000",
        "NTC_10k": "NTC 10k 3977",
        "NTC_10k_3977": "NTC 10k 3977",
        "NTC 10k": "NTC 10k 3977"
    }
    
    # Recherche du nom correct de la sonde
    normalized_probe = probe_mapping.get(probe_type, probe_type)
    
    try:
        resistance = temperature_to_resistance_dynamic(temperature, normalized_probe)
        
        if resistance is None:
            print(f"[CONV] Température {temperature:.2f}°C hors plage pour {normalized_probe}")
            return None
        
        print(f"[CONV] Conversion réussie: {temperature:.2f}°C -> {resistance:.2f} ohms")
        return resistance
        
    except ValueError as e:
        print(f"[CONV] Erreur de conversion: {e}")
        
        # Tentative avec d'autres variantes de noms
        alternative_names = [
            "PT1000",
            "Ni1000 TK5000", 
            "Ni1000 TK6180",
            "NTC 10k 3977",
            "NTC 1k 3528",
            "De Dietrich AF60",
            "Siemens QAC32"
        ]
        
        for alt_name in alternative_names:
            if probe_type.lower().replace("_", " ") in alt_name.lower():
                try:
                    resistance = temperature_to_resistance_dynamic(temperature, alt_name)
                    if resistance is not None:
                        print(f"[CONV] Conversion avec nom alternatif '{alt_name}': {temperature:.2f}°C -> {resistance:.2f} ohms")
                        return resistance
                except ValueError:
                    continue
        
        print(f"[CONV] Aucune sonde compatible trouvée pour '{probe_type}'")
        print(f"[CONV] Sondes disponibles: {list(SENSOR_TABLES.keys())}")
        return None

def get_supported_probe_types():
    """
    Retourne la liste des types de sondes supportés.
    
    :return: Liste des noms de sondes disponibles
    """
    return list(SENSOR_TABLES.keys())

def validate_temperature_range(temperature, probe_type):
    """
    Valide si une température est dans la plage supportée par une sonde.
    
    :param temperature: Température à valider (°C)
    :param probe_type: Type de sonde
    :return: True si la température est dans la plage supportée
    """
    try:
        # Normalisation du nom de la sonde
        probe_mapping = {
            "PT1000": "PT1000",
            "Ni1000_TK5000": "Ni1000 TK5000",
            "NTC_10k": "NTC 10k 3977"
        }
        normalized_probe = probe_mapping.get(probe_type, probe_type)
        
        if normalized_probe not in SENSOR_TABLES:
            return False
        
        table = SENSOR_TABLES[normalized_probe]
        t_min, _ = table[0]
        t_max, _ = table[-1]
        
        return t_min <= temperature <= t_max
        
    except (KeyError, IndexError):
        return False