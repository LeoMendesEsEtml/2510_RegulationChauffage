# -*- coding: utf-8 -*-
"""
@file        resistance_mapping.py
@brief       Mapping des résistances TMUX par type de sonde de température.
@details     Ce module fournit les tables de correspondance entre les canaux
             0-31 du multiplexeur TMUX et les valeurs de résistance réelles
             pour différents types de sondes de température. Chaque type de
             sonde dispose d'un mapping spécifique avec 32 valeurs calibrées.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""


# ---------------------------------------------------------------------------
# Tables de mapping résistances par type de sonde
# ---------------------------------------------------------------------------

# Dictionnaire principal contenant les mappings de résistances pour chaque type de sonde
# Structure: {"Type_Sonde": {canal: resistance_ohms, ...}}
# Canaux 0-31 avec valeurs de résistance réelles calibrées [Ohms]
CHANNEL_MUX = {
    "De Dietrich AF60": {
        0: 2010, 1: 1900, 2: 1800, 3: 1700, 4: 1609, 5: 1518, 6: 1436, 7: 1354,
        8: 1279, 9: 1211, 10: 1143, 11: 1081, 12: 1019, 13: 963, 14: 912, 15: 861,
        16: 814, 17: 767, 18: 724, 19: 685, 20: 646, 21: 610, 22: 577, 23: 544,
        24: 514, 25: 484, 26: 457, 27: 430, 28: 406, 29: 382, 30: 360, 31: 340
    },
    "Siemens QAC32": {
        0: 653, 1: 650, 2: 647, 3: 643, 4: 640, 5: 637, 6: 633, 7: 630,
        8: 627, 9: 623, 10: 620, 11: 617, 12: 614, 13: 611, 14: 607, 15: 604,
        16: 601, 17: 597, 18: 594, 19: 591, 20: 588, 21: 584, 22: 581, 23: 578,
        24: 575, 25: 571, 26: 568, 27: 565, 28: 561, 29: 558, 30: 555, 31: 552
    },
    "PT1000": {
        0: 942, 1: 948, 2: 953, 3: 959, 4: 965, 5: 971, 6: 977, 7: 982,
        8: 989, 9: 994, 10: 1000, 11: 1006, 12: 1012, 13: 1018, 14: 1023, 15: 1029,
        16: 1035, 17: 1041, 18: 1047, 19: 1053, 20: 1059, 21: 1064, 22: 1070, 23: 1076,
        24: 1082, 25: 1088, 26: 1094, 27: 1099, 28: 1105, 29: 1111, 30: 1117, 31: 1123
    },
    "Ni1000 TK5000": {
        0: 935, 1: 941, 2: 947, 3: 954, 4: 960, 5: 967, 6: 973, 7: 980,
        8: 987, 9: 993, 10: 1000, 11: 1007, 12: 1014, 13: 1020, 14: 1027, 15: 1033,
        16: 1040, 17: 1047, 18: 1054, 19: 1061, 20: 1067, 21: 1074, 22: 1082, 23: 1089,
        24: 1095, 25: 1102, 26: 1110, 27: 1116, 28: 1123, 29: 1131, 30: 1138, 31: 1145
    },
    "NTC 1k 3528": {
        0: 5853, 1: 5423, 2: 5033, 3: 4673, 4: 4343, 5: 4043, 6: 3773, 7: 3503,
        8: 3283, 9: 3063, 10: 2863, 11: 2663, 12: 2483, 13: 2323, 14: 2193, 15: 2043,
        16: 1913, 17: 1803, 18: 1693, 19: 1583, 20: 1492, 21: 1401, 22: 1319, 23: 1244,
        24: 1169, 25: 1101, 26: 1039, 27: 983, 28: 927, 29: 876, 30: 825, 31: 782
    },
    "KTY81-210": {
        0: 1423, 1: 1445, 2: 1467, 3: 1487, 4: 1509, 5: 1531, 6: 1551, 7: 1573,
        8: 1595, 9: 1617, 10: 1637, 11: 1659, 12: 1681, 13: 1701, 14: 1723, 15: 1745,
        16: 1767, 17: 1787, 18: 1809, 19: 1831, 20: 1853, 21: 1873, 22: 1895, 23: 1917,
        24: 1937, 25: 1959, 26: 1981, 27: 2003, 28: 2023, 29: 2045, 30: 2067, 31: 2087
    },
    "NTC 2k 3390": {
        0: 11127, 1: 10307, 2: 9627, 3: 8947, 4: 8327, 5: 7767, 6: 7257, 7: 6787,
        8: 6317, 9: 5927, 10: 5537, 11: 5177, 12: 4847, 13: 4547, 14: 4277, 15: 4007,
        16: 3767, 17: 3527, 18: 3327, 19: 3127, 20: 2947, 21: 2767, 22: 2607, 23: 2477,
        24: 2327, 25: 2197, 26: 2077, 27: 1967, 28: 1857, 29: 1757, 30: 1666, 31: 1575
    },
    "NTC 2.2k 3528": {
        0: 12890, 1: 11980, 2: 11070, 3: 10320, 4: 9570, 5: 8890, 6: 8270, 7: 7710,
        8: 7200, 9: 6730, 10: 6260, 11: 5870, 12: 5480, 13: 5120, 14: 4790, 15: 4490,
        16: 4220, 17: 3950, 18: 3710, 19: 3490, 20: 3270, 21: 3090, 22: 2910, 23: 2730,
        24: 2570, 25: 2420, 26: 2290, 27: 2160, 28: 2040, 29: 1920, 30: 1820, 31: 1720
    },
    "NTC 10k 3977": {
        0: 72773, 1: 66573, 2: 61473, 3: 56373, 4: 52073, 5: 48173, 6: 44573, 7: 40973,
        8: 37973, 9: 35273, 10: 32573, 11: 30173, 12: 27973, 13: 25973, 14: 24173, 15: 22373,
        16: 20873, 17: 19373, 18: 18073, 19: 16873, 20: 15673, 21: 14673, 22: 13673, 23: 12763,
        24: 11943, 25: 11193, 26: 10443, 27: 9763, 28: 9143, 29: 8583, 30: 8073, 31: 7563
    }
}


# ---------------------------------------------------------------------------
# Fonctions d'accès aux mappings
# ---------------------------------------------------------------------------

def get_channel_mux_map(sensor_type: str) -> dict:
    """
    @brief   Retourne le mapping CHANNEL_MUX pour un type de sonde donné.
    @details Fonction d'accès qui extrait le dictionnaire de correspondance
             canal/résistance pour un type de sonde spécifique. Valide
             l'existence du type avant de retourner les données.

    @param sensor_type  Type de sonde demandé (doit exister dans CHANNEL_MUX).

    @return             Dictionnaire {canal: resistance} pour le type de sonde.

    @exception          KeyError si le type de sonde n'est pas supporté.
    """
    # Vérification de l'existence du type de sonde dans le mapping
    if sensor_type in CHANNEL_MUX:
        # Retour du dictionnaire de mapping pour ce type
        return CHANNEL_MUX[sensor_type]
    # Levée d'exception avec message explicite si type non supporté
    raise KeyError(f"Type de sonde non supporté: {sensor_type}")


def find_closest_channel(target_resistance: float, sensor_type: str) -> tuple:
    """
    @brief   Trouve le canal MUX le plus proche pour une résistance cible.
    @details Algorithme de recherche du canal TMUX offrant la résistance
             la plus proche de la valeur cible. Calcule l'erreur absolue
             et relative pour le meilleur canal trouvé.

    @param target_resistance  Valeur de résistance cible recherchée [Ohms].
    @param sensor_type        Type de sonde à utiliser pour la recherche.

    @return                   Tuple (canal, resistance_reelle, erreur_pourcent).
                              Retourne (None, None, None) si aucun canal trouvé.

    @exception                KeyError si le type de sonde n'existe pas.
    """
    # Récupération du mapping de résistances pour le type de sonde
    channel_map = get_channel_mux_map(sensor_type)
    
    # Initialisation des variables de recherche du meilleur canal
    best_channel = None
    # Erreur minimale initialisée à l'infini pour la comparaison
    best_error = float('inf')
    
    # Parcours de tous les canaux disponibles pour ce type de sonde
    for channel, resistance in channel_map.items():
        # Calcul de l'erreur absolue entre résistance cible et disponible
        error = abs(resistance - target_resistance)
        # Mise à jour si cette résistance est plus proche de la cible
        if error < best_error:
            # Sauvegarde de la nouvelle meilleure erreur
            best_error = error
            # Sauvegarde du canal correspondant
            best_channel = channel
    
    # Calcul des résultats si un canal a été trouvé
    if best_channel is not None:
        # Récupération de la résistance réelle du meilleur canal
        actual_resistance = channel_map[best_channel]
        # Calcul de l'erreur relative en pourcentage
        error_percent = abs(actual_resistance - target_resistance) / target_resistance * 100
        # Retour du triplet (canal, résistance, erreur%)
        return best_channel, actual_resistance, error_percent
    
    # Retour de valeurs nulles si aucun canal trouvé
    return None, None, None
