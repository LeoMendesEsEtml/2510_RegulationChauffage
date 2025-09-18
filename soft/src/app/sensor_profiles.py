# -*- coding: utf-8 -*-
"""
@file        sensor_profiles.py
@brief       Profils capteurs extraits de 'Calcul ADC.xlsx' (Feuil1).
@details     Ce module contient les profils de configuration pour différents
             types de capteurs de température avec leurs paramètres ADC
             optimisés (Rref, IDAC, PGA) et leurs tables de conversion
             température/résistance. Les données proviennent des calculs
             d'optimisation du fichier Excel de référence.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""


# ---------------------------------------------------------------------------
# Profils de configuration ADC par capteur
# ---------------------------------------------------------------------------

# Dictionnaire principal contenant les profils de configuration pour chaque capteur
# Structure: paramètres optimisés pour l'acquisition ADC
# - rref_ohm: Résistance de référence sélectionnée via TMUX1204 (A1 A0: 00=2.2k, 01=2.7k, 10=10k, 11=100k)
# - idac_uA: Courant IDAC en microampères pour l'excitation du capteur
# - pga_gain: Gain PGA programmable (1,2,4,8,16,32,64,128)
# Sortie du système: résistance [Ohm] uniquement
SENSOR_PROFILES = {
    # Profil pour le capteur De Dietrich AF60 (sonde industrielle)
    "De Dietrich AF60": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 2200,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 250,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 1
    },
    # Profil pour le capteur Siemens QAC32 (sonde qualité d'air)
    "Siemens QAC32": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 2700,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 250,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 4
    },
    # Profil pour le capteur PT1000 (sonde platine de précision)
    "PT1000": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 10000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 100,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 8
    },
    # Profil pour le capteur Ni1000 TK5000 (sonde nickel coefficient standard)
    "Ni1000 TK5000": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 10000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 100,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 8
    },
    # Profil pour le capteur Ni1000 TK6180 (sonde nickel coefficient élevé)
    "Ni1000 TK6180": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 10000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 50,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 8
    },
    # Profil pour le capteur NTC 1k 3528 (thermistance 1kOhm)
    "NTC 1k 3528": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 10000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 100,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 1
    },
    # Profil pour le capteur KTY81-210 (capteur silicium)
    "KTY81-210": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 10000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 100,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 4
    },
    # Profil pour le capteur NTC 2k 3390 (thermistance 2kOhm haute précision)
    "NTC 2k 3390": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 100000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 10,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 8
    },
    # Profil pour le capteur NTC 2.2k 3528 (thermistance 2.2kOhm)
    "NTC 2.2k 3528": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 100000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 10,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 4
    },
    # Profil pour le capteur NTC 10k 3977 (thermistance 10kOhm haute résolution)
    "NTC 10k 3977": {
        # Résistance de référence optimale pour ce type de capteur [Ohms]
        "rref_ohm": 100000,
        # Courant d'excitation IDAC configuré [microampères]
        "idac_uA": 10,
        # Gain d'amplification programmable sélectionné
        "pga_gain": 1
    }
}


# ---------------------------------------------------------------------------
# Tables de conversion température/résistance
# ---------------------------------------------------------------------------

# Dictionnaire contenant les tables de correspondance température [°C] / résistance [Ohms]
# Structure: liste de tuples (température, résistance) pour interpolation linéaire
# Données calibrées issues des fiches techniques des capteurs
SENSOR_TABLES = {
    # Table de conversion température/résistance pour capteur De Dietrich AF60
    # Points de calibration (température_°C, résistance_Ohms) - sonde industrielle
    "De Dietrich AF60": [
        (-15.0, 2010), (-13.5, 1900), (-12.0, 1800), (-10.5, 1700), (-9.0, 1609),
        (-7.5, 1518), (-6.0, 1436), (-4.5, 1354), (-3.0, 1279), (-1.5, 1211),
        (0.0, 1143), (1.5, 1081), (3.0, 1019), (4.5, 963), (6.0, 912),
        (7.5, 861), (9.0, 814), (10.5, 767), (12.0, 724), (13.5, 685),
        (15.0, 646), (16.5, 610), (18.0, 577), (19.5, 544), (21.0, 514),
        (22.5, 484), (24.0, 457), (25.5, 430), (27.0, 406), (28.5, 382),
        (30.0, 360), (31.5, 340), (32.0, 334), (32.5, 328), (33.0, 322),
        (33.5, 316), (34.0, 311), (34.5, 305), (35.0, 300), (35.5, 295),
        (36.0, 290), (36.5, 284), (37.0, 279), (37.5, 275), (38.0, 270),
        (38.5, 265), (39.0, 260), (39.5, 256), (40.0, 251.37)
    ],
    # Table de conversion température/résistance pour capteur Ni1000 TK6180
    # Points de calibration (température_°C, résistance_Ohms) - sonde nickel haute sensibilité
    "Ni1000 TK6180": [
        (-15.0, 919), (-13.5, 927), (-12.0, 935), (-10.5, 943), (-9.0, 951),
        (-7.5, 959), (-6.0, 968), (-4.5, 976), (-3.0, 984), (-1.5, 992),
        (0.0, 1000), (1.5, 1009), (3.0, 1017), (4.5, 1025), (6.0, 1033),
        (7.5, 1041), (9.0, 1050), (10.5, 1059), (12.0, 1067), (13.5, 1075),
        (15.0, 1084), (16.5, 1092), (18.0, 1101), (19.5, 1110), (21.0, 1118),
        (22.5, 1127), (24.0, 1135), (25.5, 1144), (27.0, 1153), (28.5, 1162),
        (30.0, 1171), (32.0, 1182), (33.0, 1188), (34.0, 1194.21), (35.0, 1200),
        (36.0, 1206), (37.0, 1212), (38.0, 1218), (39.0, 1224), (40.0, 1230.7)
    ],
    # Table de conversion température/résistance pour capteur Ni1000 TK5000
    # Points de calibration (température_°C, résistance_Ohms) - sonde nickel standard
    "Ni1000 TK5000": [
        (-15.0, 935), (-13.5, 941), (-12.0, 947), (-10.5, 954), (-9.0, 960),
        (-7.5, 967), (-6.0, 973), (-4.5, 980), (-3.0, 987), (-1.5, 993),
        (0.0, 1000), (1.5, 1007), (3.0, 1014), (4.5, 1020), (6.0, 1027),
        (7.5, 1033), (9.0, 1040), (10.5, 1047), (12.0, 1054), (13.5, 1061),
        (15.0, 1067), (16.5, 1074), (18.0, 1082), (19.5, 1089), (21.0, 1095),
        (22.5, 1102), (24.0, 1110), (25.5, 1116), (27.0, 1123), (28.5, 1131),
        (30.0, 1138), (31.5, 1145), (32.0, 1147), (33.0, 1152), (34.0, 1157),
        (35.0, 1162), (36.0, 1166), (37.0, 1171), (38.0, 1176), (39.0, 1181),
        (40.0, 1185.71)
    ],
    # Table de conversion température/résistance pour capteur PT1000
    # Points de calibration (température_°C, résistance_Ohms) - sonde platine de précision
    "PT1000": [
        (-15.0, 942), (-13.5, 948), (-12.0, 953), (-10.5, 959), (-9.0, 965),
        (-7.5, 971), (-6.0, 977), (-4.5, 982), (-3.0, 989), (-1.5, 994),
        (0.0, 1000), (1.5, 1006), (3.0, 1012), (4.5, 1018), (6.0, 1023),
        (7.5, 1029), (9.0, 1035), (10.5, 1041), (12.0, 1047), (13.5, 1053),
        (15.0, 1059), (16.5, 1064), (18.0, 1070), (19.5, 1076), (21.0, 1082),
        (22.5, 1088), (24.0, 1094), (25.5, 1099), (27.0, 1105), (28.5, 1111),
        (30.0, 1117), (31.5, 1123), (32.0, 1124), (32.5, 1126), (33.0, 1128),
        (33.5, 1130), (34.0, 1132), (34.5, 1134), (35.0, 1136), (35.5, 1138),
        (36.0, 1140), (36.5, 1142), (37.0, 1144), (37.5, 1146), (38.0, 1148),
        (38.5, 1150), (39.0, 1152), (39.5, 1153), (40.0, 1155.5)
    ],
    # Table de conversion température/résistance pour capteur Siemens QAC32
    # Points de calibration (température_°C, résistance_Ohms) - sonde qualité d'air
    "Siemens QAC32": [
        (-15.0, 653), (-13.5, 650), (-12.0, 647), (-10.5, 643), (-9.0, 640),
        (-7.5, 637), (-6.0, 633), (-4.5, 630), (-3.0, 627), (-1.5, 623),
        (0.0, 620), (1.5, 617), (3.0, 614), (4.5, 611), (6.0, 607),
        (7.5, 604), (9.0, 601), (10.5, 597), (12.0, 594), (13.5, 591),
        (15.0, 588), (16.5, 584), (18.0, 581), (19.5, 578), (21.0, 575),
        (22.5, 571), (24.0, 568), (25.5, 565), (27.0, 561), (28.5, 558),
        (30.0, 555), (31.5, 552), (40.0, 525)
    ],
    # Table de conversion température/résistance pour capteur NTC 1k 3528
    # Points de calibration (température_°C, résistance_Ohms) - thermistance 1kΩ
    "NTC 1k 3528": [
        (-15.0, 5855), (-13.5, 5431), (-12.0, 5041), (-10.5, 4683), (-9.0, 4353),
        (-7.5, 4050), (-6.0, 3771), (-4.5, 3513), (-3.0, 3276), (-1.5, 3057),
        (0.0, 2854), (1.5, 2667), (3.0, 2493), (4.5, 2333), (6.0, 2184),
        (7.5, 2046), (9.0, 1918), (10.5, 1799), (12.0, 1689), (13.5, 1586),
        (15.0, 1491), (16.5, 1402), (18.0, 1319), (19.5, 1242), (21.0, 1170),
        (22.5, 1102), (24.0, 1040), (25.5, 981), (27.0, 926), (28.5, 875),
        (30.0, 827), (31.5, 782), (32.0, 767), (32.5, 753), (33.0, 739),
        (33.5, 726), (34.0, 713), (34.5, 700), (35.0, 687), (35.5, 675),
        (36.0, 663), (36.5, 651), (37.0, 639), (37.5, 628), (38.0, 617),
        (38.5, 606), (39.0, 595), (39.5, 585), (40.0, 574.6)
    ],
    # Table de conversion température/résistance pour capteur KTY81-210
    # Points de calibration (température_°C, résistance_Ohms) - capteur silicium
    "KTY81-210": [
        (-15.0, 1423), (-13.5, 1445), (-12.0, 1466), (-10.5, 1488), (-9.0, 1509),
        (-7.5, 1531), (-6.0, 1552), (-4.5, 1573), (-3.0, 1595), (-1.5, 1616),
        (0.0, 1638), (1.5, 1659), (3.0, 1681), (4.5, 1702), (6.0, 1723),
        (7.5, 1745), (9.0, 1766), (10.5, 1788), (12.0, 1809), (13.5, 1831),
        (15.0, 1852), (16.5, 1873), (18.0, 1895), (19.5, 1916), (21.0, 1938),
        (22.5, 1959), (24.0, 1981), (25.5, 2002), (27.0, 2023), (28.5, 2045),
        (30.0, 2066), (31.5, 2088), (40.0, 2245)
    ],
    # Table de conversion température/résistance pour capteur NTC 2k 3390
    # Points de calibration (température_°C, résistance_Ohms) - thermistance 2kΩ haute précision
    "NTC 2k 3390": [
        (-15.0, 11124), (-13.5, 10340), (-12.0, 9618), (-10.5, 8954), (-9.0, 8341),
        (-7.5, 7777), (-6.0, 7255), (-4.5, 6774), (-3.0, 6329), (-1.5, 5917),
        (0.0, 5536), (1.5, 5183), (3.0, 4855), (4.5, 4551), (6.0, 4269),
        (7.5, 4007), (9.0, 3764), (10.5, 3537), (12.0, 3326), (13.5, 3130),
        (15.0, 2947), (16.5, 2776), (18.0, 2616), (19.5, 2468), (21.0, 2328),
        (22.5, 2198), (24.0, 2077), (25.5, 1963), (27.0, 1856), (28.5, 1756),
        (30.0, 1663), (31.5, 1575), (32.0, 1546), (32.5, 1519), (33.0, 1492),
        (33.5, 1466), (34.0, 1440), (34.5, 1415), (35.0, 1390), (35.5, 1365),
        (36.0, 1342), (36.5, 1318), (37.0, 1296), (37.5, 1273), (38.0, 1251),
        (38.5, 1230), (39.0, 1209), (39.5, 1188), (40.0, 1168.05)
    ],
    # Table de conversion température/résistance pour capteur NTC 2.2k 3528
    # Points de calibration (température_°C, résistance_Ohms) - thermistance 2.2kΩ
    "NTC 2.2k 3528": [
        (-15.0, 12881), (-13.5, 11947), (-12.0, 11089), (-10.5, 10301), (-9.0, 9576),
        (-7.5, 8909), (-6.0, 8295), (-4.5, 7729), (-3.0, 7206), (-1.5, 6724),
        (0.0, 6278), (1.5, 5866), (3.0, 5485), (4.5, 5132), (6.0, 4804),
        (7.5, 4501), (9.0, 4220), (10.5, 3958), (12.0, 3715), (13.5, 3489),
        (15.0, 3279), (16.5, 3084), (18.0, 2901), (19.5, 2732), (21.0, 2573),
        (22.5, 2425), (24.0, 2287), (25.5, 2158), (27.0, 2037), (28.5, 1924),
        (30.0, 1819), (31.5, 1720), (32.0, 1600), (32.5, 1569), (33.0, 1538),
        (33.5, 1508), (34.0, 1479), (34.5, 1450), (35.0, 1422), (35.5, 1395),
        (36.0, 1368), (36.5, 1342), (37.0, 1316), (37.5, 1291), (38.0, 1266),
        (38.5, 1242), (39.0, 1219), (39.5, 1196), (40.0, 1173)
    ],
    # Table de conversion température/résistance pour capteur NTC 10k 3977
    # Points de calibration (température_°C, résistance_Ohms) - thermistance 10kΩ haute résolution
    "NTC 10k 3977": [
        (-15.0, 72502), (-13.5, 66690), (-12.0, 61394), (-10.5, 56563), (-9.0, 52153),
        (-7.5, 48123), (-6.0, 44439), (-4.5, 41068), (-3.0, 37980), (-1.5, 35151),
        (0.0, 32555), (1.5, 30173), (3.0, 27985), (4.5, 25973), (6.0, 24122),
        (7.5, 22419), (9.0, 20850), (10.5, 19403), (12.0, 18068), (13.5, 16836),
        (15.0, 15698), (16.5, 14646), (18.0, 13673), (19.5, 12773), (21.0, 11939),
        (22.5, 11166), (24.0, 10449), (25.5, 9784), (27.0, 9166), (28.5, 8593),
        (30.0, 8059), (31.5, 7563), (32.0, 7330), (32.5, 7183), (33.0, 7037),
        (33.5, 6895), (34.0, 6754), (34.5, 6620), (35.0, 6487), (35.5, 6358),
        (36.0, 6231), (36.5, 6108), (37.0, 5987), (37.5, 5869), (38.0, 5754),
        (38.5, 5642), (39.0, 5532), (39.5, 5424), (40.0, 5320)
    ],
}


# ---------------------------------------------------------------------------
# Fonctions d'accès aux profils
# ---------------------------------------------------------------------------

def get_profile(sensor_name):
    """
    @brief   Récupère le profil de configuration ADC pour un capteur donné.
    @details Fonction d'accès qui retourne le dictionnaire de configuration
             contenant les paramètres optimisés (Rref, IDAC, PGA) pour
             un type de capteur spécifique.

    @param sensor_name  Nom du type de capteur recherché.

    @return             Dictionnaire contenant les paramètres de configuration:
                        - rref_ohm: résistance de référence [Ohms]
                        - idac_uA: courant d'excitation [microampères]  
                        - pga_gain: gain programmable [1-128]

    @exception          KeyError si le type de capteur n'est pas reconnu.
    """
    # Vérification de l'existence du capteur dans les profils
    if sensor_name in SENSOR_PROFILES:
        # Retour du profil de configuration pour ce capteur
        return SENSOR_PROFILES[sensor_name]
    # Levée d'exception avec message explicite pour capteur inconnu
    raise KeyError("Type de sonde inconnu: " + str(sensor_name))
