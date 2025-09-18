# -*- coding: utf-8 -*-
"""
@file        temperature_conversion.py
@brief       Module de conversion résistance/température via interpolation linéaire.
@details     Ce module fournit les fonctions de conversion bidirectionnelle
             entre résistance mesurée et température pour différents types
             de capteurs. Utilise l'interpolation linéaire sur les tables
             de calibration et supporte la conversion inverse pour la
             simulation de résistance.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

# Import des tables de capteurs depuis le module de profils
from app.sensor_profiles import SENSOR_TABLES


# ---------------------------------------------------------------------------
# Fonctions de conversion de base
# ---------------------------------------------------------------------------

def resistance_to_temperature(resistance, table):
    """
    @brief   Convertit une résistance mesurée en température via interpolation linéaire.
    @details Algorithme d'interpolation linéaire qui recherche l'intervalle
             contenant la résistance mesurée et calcule la température
             correspondante. Gère les cas limites hors plage de mesure.

    @param resistance  Résistance mesurée [Ohms].
    @param table      Liste de tuples (résistance, température) pour interpolation.

    @return           Température interpolée [°C], ou valeurs limites si hors plage.
    """
    # Parcours des paires de points consécutifs dans la table de conversion
    for i in range(len(table) - 1):
        # Extraction des coordonnées du premier point de l'intervalle
        r1, t1 = table[i]
        # Extraction des coordonnées du second point de l'intervalle
        r2, t2 = table[i + 1]
        # Vérification si la résistance mesurée est dans l'intervalle courant
        if r1 <= resistance <= r2:
            # Application de la formule d'interpolation linéaire
            temperature = t1 + (resistance - r1) / (r2 - r1) * (t2 - t1)
            # Retour de la température interpolée
            return temperature
    
    # Gestion des cas hors limites de la table de conversion
    r_min, t_min = table[0]
    # Extraction des valeurs maximales de la table
    r_max, t_max = table[-1]
    # Retour de la température minimale si résistance trop faible
    if resistance < r_min:
        return t_min
    # Retour de la température maximale si résistance trop élevée
    if resistance > r_max:
        return t_max
    # Retour de None si aucune condition n'est satisfaite (cas d'erreur)
    return None

def resistance_to_temperature_dynamic(resistance, sensor):
    """
    @brief   Convertit une résistance mesurée en température pour un capteur donné.
    @details Fonction dynamique qui sélectionne automatiquement la table de
             conversion appropriée selon le type de capteur spécifié.
             Effectue la validation du capteur avant conversion.

    @param resistance  Résistance mesurée [Ohms].
    @param sensor     Nom du type de capteur à utiliser.

    @return           Température interpolée [°C] ou None si hors limites.

    @exception        ValueError si le capteur n'est pas reconnu.
    """
    # Vérification de l'existence du capteur dans les tables disponibles
    if sensor not in SENSOR_TABLES:
        # Levée d'exception avec message explicite si capteur introuvable
        raise ValueError(f"Capteur {sensor} non trouvé dans les données.")

    # Récupération de la table de conversion spécifique au capteur
    table = SENSOR_TABLES[sensor]
    # Parcours des paires de points consécutifs dans la table
    for i in range(len(table) - 1):
        # Extraction température et résistance du premier point (format inversé)
        t1, r1 = table[i]
        # Extraction température et résistance du second point
        t2, r2 = table[i + 1]
        # Vérification si la résistance mesurée est dans l'intervalle
        if r1 <= resistance <= r2:
            # Application de l'interpolation linéaire pour calculer la température
            temperature = t1 + (resistance - r1) / (r2 - r1) * (t2 - t1)
            # Retour de la température calculée
            return temperature
    
    # Gestion des valeurs minimales et maximales de la table
    t_min, r_min = table[0]
    # Extraction des valeurs maximales
    t_max, r_max = table[-1]
    # Retour de la température minimale si résistance trop faible
    if resistance < r_min:
        return t_min
    # Retour de la température maximale si résistance trop élevée
    if resistance > r_max:
        return t_max
    # Retour de None si aucune condition n'est remplie
    return None

def temperature_to_resistance_dynamic(temperature, sensor):
    """
    @brief   Convertit une température en résistance pour un capteur donné (conversion inverse).
    @details Fonction de conversion inverse utilisée pour la simulation de résistance.
             Effectue l'interpolation linéaire sur l'axe température pour obtenir
             la résistance correspondante selon le type de capteur.

    @param temperature  Température d'entrée [°C].
    @param sensor      Nom du type de capteur à utiliser.

    @return            Résistance interpolée [Ohms] ou None si hors limites.

    @exception         ValueError si le capteur n'est pas reconnu.
    """
    # Vérification de l'existence du capteur dans les tables de conversion
    if sensor not in SENSOR_TABLES:
        # Levée d'exception avec message d'erreur explicite
        raise ValueError(f"Capteur {sensor} non trouvé dans les données.")

    # Récupération de la table de conversion pour le capteur spécifié
    table = SENSOR_TABLES[sensor]
    
    # Parcours des paires de points consécutifs pour la recherche d'intervalle
    for i in range(len(table) - 1):
        # Extraction des coordonnées du premier point (température, résistance)
        t1, r1 = table[i]
        # Extraction des coordonnées du second point
        t2, r2 = table[i + 1]
        
        # Vérification si la température est contenue dans l'intervalle courant
        if t1 <= temperature <= t2:
            # Application de l'interpolation linéaire inverse (température -> résistance)
            resistance = r1 + (temperature - t1) / (t2 - t1) * (r2 - r1)
            # Retour de la résistance calculée
            return resistance
    
    # Gestion des cas hors limites de la table de conversion
    t_min, r_min = table[0]
    # Extraction des valeurs maximales de température et résistance
    t_max, r_max = table[-1]
    
    # Retour de la résistance minimale si température trop basse
    if temperature < t_min:
        return r_min
    # Retour de la résistance maximale si température trop élevée
    if temperature > t_max:
        return r_max
    
    # Retour de None si aucune condition n'est satisfaite
    return None

def convert_temperature_to_resistance(temperature, probe_type):
    """
    @brief   Fonction de conversion principale pour la simulation de résistance.
    @details Fonction de haut niveau qui supporte différents types de sondes
             avec leurs caractéristiques spécifiques. Inclut la normalisation
             des noms de sondes et la gestion des variantes de nomenclature.

    @param temperature  Température simulée [°C].
    @param probe_type  Type de sonde (formats multiples supportés).

    @return            Résistance simulée [Ohms] ou None si échec.
    """
    # Affichage d'information sur la conversion en cours
    print(f"[CONV] Conversion T->R: {temperature:.2f}°C -> ? ohms (sonde: {probe_type})")
    
    # Dictionnaire de normalisation des noms de sondes pour compatibilité
    probe_mapping = {
        "PT1000": "PT1000",
        "Ni1000_TK5000": "Ni1000 TK5000",
        "Ni1000_TK5000": "Ni1000 TK5000",
        "NTC_10k": "NTC 10k 3977",
        "NTC_10k_3977": "NTC 10k 3977",
        "NTC 10k": "NTC 10k 3977"
    }
    
    # Recherche du nom normalisé de la sonde dans le mapping
    normalized_probe = probe_mapping.get(probe_type, probe_type)
    
    try:
        # Tentative de conversion avec le nom normalisé
        resistance = temperature_to_resistance_dynamic(temperature, normalized_probe)
        
        # Vérification de la validité du résultat de conversion
        if resistance is None:
            # Affichage d'information si température hors plage supportée
            print(f"[CONV] Température {temperature:.2f}°C hors plage pour {normalized_probe}")
            return None
        
        # Affichage de confirmation de conversion réussie
        print(f"[CONV] Conversion réussie: {temperature:.2f}°C -> {resistance:.2f} ohms")
        # Retour de la résistance calculée
        return resistance
        
    except ValueError as e:
        # Affichage d'erreur lors de la conversion principale
        print(f"[CONV] Erreur de conversion: {e}")
        
        # Liste des noms alternatifs pour tentatives de récupération
        alternative_names = [
            "PT1000",
            "Ni1000 TK5000", 
            "Ni1000 TK6180",
            "NTC 10k 3977",
            "NTC 1k 3528",
            "De Dietrich AF60",
            "Siemens QAC32"
        ]
        
        # Tentative de correspondance avec les noms alternatifs
        for alt_name in alternative_names:
            # Comparaison de noms avec normalisation (minuscules, espaces)
            if probe_type.lower().replace("_", " ") in alt_name.lower():
                try:
                    # Tentative de conversion avec le nom alternatif
                    resistance = temperature_to_resistance_dynamic(temperature, alt_name)
                    # Vérification de la validité du résultat
                    if resistance is not None:
                        # Affichage de succès avec nom alternatif utilisé
                        print(f"[CONV] Conversion avec nom alternatif '{alt_name}': {temperature:.2f}°C -> {resistance:.2f} ohms")
                        return resistance
                except ValueError:
                    # Continuation de la boucle si échec avec ce nom alternatif
                    continue
        
        # Affichage d'erreur si aucune sonde compatible trouvée
        print(f"[CONV] Aucune sonde compatible trouvée pour '{probe_type}'")
        # Affichage de la liste des sondes disponibles pour assistance
        print(f"[CONV] Sondes disponibles: {list(SENSOR_TABLES.keys())}")
        return None

# ---------------------------------------------------------------------------
# Fonctions utilitaires et validation
# ---------------------------------------------------------------------------

def get_supported_probe_types():
    """
    @brief   Retourne la liste des types de sondes supportés.
    @details Fonction utilitaire qui extrait la liste complète des noms
             de capteurs disponibles dans les tables de conversion.

    @return  Liste des noms de capteurs disponibles pour conversion.
    """
    # Retour direct des clés du dictionnaire des tables de capteurs
    return list(SENSOR_TABLES.keys())

def validate_temperature_range(temperature, probe_type):
    """
    @brief   Valide si une température est dans la plage supportée par une sonde.
    @details Fonction de validation qui vérifie si une température donnée
             est compatible avec la plage de fonctionnement d'un type de
             capteur spécifique selon sa table de calibration.

    @param temperature  Température à valider [°C].
    @param probe_type  Type de sonde à vérifier.

    @return            True si la température est dans la plage supportée.
    """
    try:
        # Dictionnaire de normalisation des noms pour la validation
        probe_mapping = {
            "PT1000": "PT1000",
            "Ni1000_TK5000": "Ni1000 TK5000",
            "NTC_10k": "NTC 10k 3977"
        }
        # Application de la normalisation du nom de sonde
        normalized_probe = probe_mapping.get(probe_type, probe_type)
        
        # Vérification de l'existence de la sonde dans les tables
        if normalized_probe not in SENSOR_TABLES:
            return False
        
        # Récupération de la table de conversion pour la sonde
        table = SENSOR_TABLES[normalized_probe]
        # Extraction de la température minimale de la table
        t_min, _ = table[0]
        # Extraction de la température maximale de la table
        t_max, _ = table[-1]
        
        # Vérification si la température est dans la plage [t_min, t_max]
        return t_min <= temperature <= t_max
        
    except (KeyError, IndexError):
        # Retour de False en cas d'erreur d'accès aux données
        return False