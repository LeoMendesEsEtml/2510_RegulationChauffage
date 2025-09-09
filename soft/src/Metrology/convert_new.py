# -*- coding: utf-8 -*-
"""
Module de conversion de mesures pour les capteurs de température.

Supporte deux types de capteurs:
1. PTC (Positive Temperature Coefficient):
   - PT1000: Platine, R(0°C) = 1000?, ? = 0.00385 ?/?/°C
   - Ni1000: Nickel, versions TK5000 et TK6180
   
2. NTC (Negative Temperature Coefficient):
   - Thermistances avec équation Steinhart-Hart
   - Profiles préconfigurés (AF60, QAC32, etc.)

Références:
- PT1000: IEC 60751 (précision classe B)
- Ni1000: DIN 43760
- NTC: Steinhart-Hart equation
"""

from math import log, exp
from typing import Literal, Union, Optional
from dataclasses import dataclass
from Metrology.sensor_profiles import SensorProfile
from Metrology.exceptions import ConfigError

def r_to_temp(profile: SensorProfile, r_ohm: float) -> float:
    """
    Convertit une résistance en température.
    
    Pour les PTC (PT1000, Ni1000):
    Utilise la linéarisation ? autour de 0°C:
    R(T) = R0 * (1 + ?*(T - T0))
    T = T0 + (R/R0 - 1)/?
    
    Pour les NTC:
    Utilise l'équation de Steinhart-Hart:
    1/T = A + B*ln(R) + C*(ln(R))³
    
    Args:
        profile: Profil du capteur avec coefficients
        r_ohm: Résistance mesurée en ohms
        
    Returns:
        float: Température en °C
        
    Raises:
        ValueError: Si la résistance est invalide
        ConfigError: Si le type de capteur est inconnu
    """
    # Validation
    if r_ohm <= 0:
        raise ValueError("La résistance doit être positive")
    if not profile:
        raise ConfigError("Profil de capteur manquant")

    # Conversion selon le type de capteur
    if profile.kind == "PTC":
        # Linéarisation ? pour PTC (PT1000, Ni1000)
        # Précis entre -15°C et +40°C
        return profile.t0_c + (r_ohm / profile.r0_ohm - 1.0) / profile.alpha_per_c
        
    elif profile.kind == "NTC":
        # Équation Steinhart-Hart pour NTC
        # 1/T = A + B*ln(R) + C*(ln(R))³
        lnR = log(r_ohm)
        invK = profile.A + profile.B * lnR + profile.C * (lnR ** 3)
        t_k = 1.0 / invK
        return t_k - 273.15  # Conversion K -> °C
        
    else:
        raise ConfigError(f"Type de capteur non supporté: {profile.kind}")

def temp_to_r(profile: SensorProfile, temp_c: float) -> float:
    """
    Convertit une température en résistance (fonction inverse).
    
    Utile pour:
    - Simulation de capteurs
    - Validation de mesures
    - Calcul de points de calibration
    
    Args:
        profile: Profil du capteur avec coefficients
        temp_c: Température en °C
        
    Returns:
        float: Résistance en ohms
        
    Raises:
        ConfigError: Si le type de capteur est inconnu
    """
    if profile.kind == "PTC":
        # R(T) = R0 * (1 + ?*(T - T0))
        return profile.r0_ohm * (1.0 + profile.alpha_per_c * (temp_c - profile.t0_c))
        
    elif profile.kind == "NTC":
        # Steinhart-Hart inverse
        t_k = temp_c + 273.15
        inv_t = 1.0 / t_k
        
        # Résolution approximative de l'équation cubique
        # On néglige le terme en ln(R)³ pour une première approximation
        lnR = (inv_t - profile.A) / profile.B
        # Une itération de Newton pour améliorer la précision
        for _ in range(3):
            f = profile.A + profile.B * lnR + profile.C * (lnR ** 3) - inv_t
            df = profile.B + 3 * profile.C * (lnR ** 2)
            lnR = lnR - f / df
            
        return exp(lnR)
        
    else:
        raise ConfigError(f"Type de capteur non supporté: {profile.kind}")

def validate_measurement(profile: SensorProfile, r_ohm: float, 
                       temp_min_c: float = -50, 
                       temp_max_c: float = 150) -> bool:
    """
    Vérifie si une mesure de résistance est plausible.
    
    Args:
        profile: Profil du capteur
        r_ohm: Résistance mesurée
        temp_min_c: Température minimale acceptable
        temp_max_c: Température maximale acceptable
        
    Returns:
        bool: True si la mesure est valide
    """
    try:
        # Conversion en température
        temp = r_to_temp(profile, r_ohm)
        # Vérification de la plage
        return temp_min_c <= temp <= temp_max_c
    except (ValueError, ConfigError):
        return False
