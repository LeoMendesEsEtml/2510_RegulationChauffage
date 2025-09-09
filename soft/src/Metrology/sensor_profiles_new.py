# -*- coding: utf-8 -*-
"""
Base de données des profils de capteurs de température.

Ce module définit:
1. Les profils des capteurs supportés:
   - PTC: PT100/1000, Ni1000, KTY81
   - NTC: Thermistances diverses
   
2. Les paramètres ADC associés:
   - Gain
   - Courant d'excitation
   - Fréquence d'échantillonnage
   - Mode de référence

3. Utilitaires de calibration:
   - Calcul des coefficients à partir de points
   - Validation des paramètres

Chaque profil contient:
- Type de capteur (PTC/NTC)
- Paramètres de conversion R?T
- Configuration ADC optimale
- Résistance de référence

Auteur: LeoMendesEsEtml
Date: 2025
Licence: MIT
"""

from dataclasses import dataclass
from math import exp, log
from typing import Dict, Tuple

# Base de données des paramètres ADC par profil
ADC_PARAMS_DB: Dict[str, Dict[str, float]] = {
    # AF60 (sonde extérieure)
    "AF60": {
        "ref_bank": 2,    # Banque ref 2.5V
        "idac_uA": 100,   # Excitation 100µA
        "gain": 4,        # Gain PGA = 4
        "data_rate_sps": 20  # 20 SPS (rejet 50/60Hz)
    },
    
    # PT1000 (classe A)
    "PT1000": {
        "ref_bank": 2,    # Banque ref 2.5V
        "idac_uA": 100,   # Excitation 100µA 
        "gain": 8,        # Gain PGA = 8
        "data_rate_sps": 20  # 20 SPS
    },
    
    # Ni1000 (TK5000/TK6180)
    "NI1000_TK5000": {
        "ref_bank": 2,
        "idac_uA": 100,
        "gain": 8,
        "data_rate_sps": 20
    },
    "NI1000_TK6180": {
        "ref_bank": 2, 
        "idac_uA": 100,
        "gain": 8,
        "data_rate_sps": 20
    },
    
    # Thermistances NTC
    "NTC_1k_3528": {
        "ref_bank": 2,     # 2.5V ref
        "idac_uA": 100,    # 100µA (R faible)
        "gain": 1,         # Gain unitaire
        "data_rate_sps": 20
    },
    "NTC_10k_3977": {
        "ref_bank": 3,    # 5V ref  
        "idac_uA": 10,    # 10µA (R élevée)
        "gain": 1,        # Gain unitaire
        "data_rate_sps": 20
    },
    
    # KTY81-210 (PTC silicium)
    "KTY81_210": {
        "ref_bank": 2,
        "idac_uA": 100,
        "gain": 4,
        "data_rate_sps": 20
    }
}

@dataclass
class SensorProfile:
    """
    Profil complet d'un capteur de température.
    
    Attributs:
        name: Identifiant unique du profil
        kind: Type de capteur ("PTC" ou "NTC") 
        r0_ohm: Résistance de référence (?)
        t0_c: Température de référence (°C)
        alpha_per_c: Coefficient ? pour PTC (/°C)
        A, B, C: Coefficients Steinhart-Hart pour NTC
        rref_nom: Résistance référence du réseau
    """
    name: str          # Identifiant
    kind: str          # "PTC" ou "NTC"
    r0_ohm: float      # R à t0_c
    t0_c: float        # T référence
    alpha_per_c: float = 0.0  # PTC: ?
    A: float = 0.0     # NTC: coeff A
    B: float = 0.0     # NTC: coeff B  
    C: float = 0.0     # NTC: coeff C
    rref_nom: float = 10_000  # Rref réseau

def _ptc_from_two_points(
    t1_c: float,
    r1_ohm: float, 
    t2_c: float,
    r2_ohm: float
) -> Tuple[float, float]:
    """
    Calcule R0 et ? d'un PTC à partir de 2 points.
    
    Utilise le modèle linéaire:
    R(T) = R0 * (1 + ?*(T - T0))
    
    Args:
        t1_c, t2_c: Températures en °C
        r1_ohm, r2_ohm: Résistances en ?
        
    Returns:
        (r0_ohm, alpha_per_c)
    """
    # Calcul de la pente
    slope = (r2_ohm - r1_ohm) / (t2_c - t1_c)
    
    # R0 à 0°C par extrapolation
    r0 = r1_ohm - slope * t1_c
    
    # Coefficient ? = pente/R0
    alpha = slope / r0
    
    return r0, alpha

def _ntc_sh_from_two_points(
    t1_c: float,
    r1_ohm: float,
    t2_c: float,
    r2_ohm: float
) -> Tuple[float, float, float, float]:
    """
    Calcule les coefficients Steinhart-Hart d'une NTC.
    
    Utilise le modèle réduit (C=0):
    1/T = A + B*ln(R)
    
    Args:
        t1_c, t2_c: Températures en °C
        r1_ohm, r2_ohm: Résistances en ?
        
    Returns:
        (A, B, C=0, R25) avec:
        - A, B: Coefficients S-H
        - C = 0 (modèle réduit)
        - R25: R à 25°C (valeur nominale)
    """
    # Conversion en Kelvin
    t1_k = t1_c + 273.15
    t2_k = t2_c + 273.15
    
    # Calcul coefficient B
    B = (1.0/t1_k - 1.0/t2_k) / (log(r1_ohm) - log(r2_ohm))
    
    # Calcul coefficient A
    A = 1.0/t1_k - B * log(r1_ohm)
    
    # Calcul R25 (valeur nominale)
    t0_k = 25.0 + 273.15
    ln_r25 = (1.0/t0_k - A) / B
    r25 = exp(ln_r25)
    
    return A, B, 0.0, r25

# Base de données des profils
SENSOR_DB = {
    # PT1000 classe A (? = 0.00385)
    "PT1000": SensorProfile(
        name="PT1000",
        kind="PTC",
        r0_ohm=1000.0,
        t0_c=0.0,
        alpha_per_c=0.00385
    ),
    
    # Ni1000 (? = 0.00618)
    "NI1000_TK5000": SensorProfile(
        name="NI1000_TK5000", 
        kind="PTC",
        r0_ohm=1000.0,
        t0_c=0.0,
        alpha_per_c=0.00500
    ),
    
    # NTC 10k ?=3977
    "NTC_10k_3977": SensorProfile(
        name="NTC_10k_3977",
        kind="NTC",
        r0_ohm=10000.0,  # R25
        t0_c=25.0,
        A=1.129241e-3,
        B=2.341077e-4,
        C=8.775468e-8
    ),
    
    # Autres profils...
}
