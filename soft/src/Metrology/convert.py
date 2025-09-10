# -*- coding: utf-8 -*-
"""
Module de conversion resistance-temperature pour capteurs de temperature.

Ce module implemente:
1. Conversion R -> T pour capteurs PTC:
   - Linearisation alpha autour du point de reference
   - Precision optimale entre -15C et 40C
   - Supporte PT1000, PT100, Ni1000, KTY81-210

2. Conversion R -> T pour thermistances NTC:
   - Equation Steinhart-Hart complete
   - Coefficients A, B, C calibres
   - Grande precision sur toute la plage

Auteur: LeoMendesEsEtml
Date: 2025
Licence: MIT
"""

from math import log
from typing import Union
from Metrology.sensor_profiles import SensorProfile
from Metrology.exceptions import ConfigError

def r_to_temp(profile: SensorProfile, r_ohm: float) -> float:
    """
    Convertit une resistance en temperature selon le profil capteur.
    
    Pour les PTC (ex: PT1000):
    - Utilise la linearisation alpha : R(T) = R0*(1 + alpha*(T-T0))
    - R0 : resistance a T0 (generalement 0C ou 25C)
    - alpha : coefficient de temperature (/C)
    - Precision ~0.1C entre -15C et 40C
    
    Pour les NTC:
    - Utilise l'equation Steinhart-Hart : 1/T = A + B*ln(R) + C*ln(R)^3
    - A, B, C : coefficients calibres
    - T en Kelvin, conversion finale en C
    - Precision ~0.05C sur toute la plage
    
    Args:
        profile: Configuration du capteur avec:
            - kind: "PTC" ou "NTC"
            - Coefficients selon type (alpha, R0 ou A,B,C)
        r_ohm: Resistance mesuree en ohms
        
    Returns:
        float: Temperature en C
        
    Raises:
        ConfigError: Type de capteur non supporte
        ValueError: Resistance <= 0 ou coefficients invalides
    
    Note:
        Les capteurs PTC supportes sont:
        - PT100/PT1000 (alpha = 0.00385 /C)
        - Ni1000 (alpha = 0.00617 /C)
        - KTY81-210 (alpha = 0.00772 /C)
    """
    # Validation de la resistance
    if r_ohm <= 0:
        raise ValueError(
            f"La resistance doit etre positive: {r_ohm} ohms"
        )

    # Validation du profil
    if not profile:
        raise ConfigError("Profil capteur manquant")

    # Traitement selon type de capteur
    if profile.kind == "PTC":
        # Capteur PTC (coefficient positif)
        # Formule: R(T) = R0 * (1 + alpha*(T - T0))
        # Resolution: T = T0 + (R/R0 - 1)/alpha
        
        # Validation des parametres
        if not (profile.r0_ohm > 0 and profile.alpha_per_c > 0):
            raise ConfigError(
                f"Parametres PTC invalides: R0={profile.r0_ohm}, "
                f"alpha={profile.alpha_per_c}"
            )
            
        # Calcul temperature
        t_c = profile.t0_c + (r_ohm / profile.r0_ohm - 1.0) / profile.alpha_per_c
        return t_c

    elif profile.kind == "NTC":
        # Thermistance NTC (coefficient negatif) 
        # Equation Steinhart-Hart:
        # 1/T(K) = A + B*ln(R) + C*(ln(R))^3
        
        # Validation des coefficients
        if not all([profile.A, profile.B, profile.C]):
            raise ConfigError(
                f"Coefficients S-H manquants: A={profile.A}, "
                f"B={profile.B}, C={profile.C}"
            )
            
        # Calcul temperature
        try:
            lnR = log(r_ohm)                    # Logarithme naturel
            invK = (                            # Inverse des Kelvin
                profile.A +                     # Terme constant
                profile.B * lnR +              # Terme lineaire
                profile.C * (lnR ** 3)         # Terme cubique
            )
            t_k = 1.0 / invK                   # Temperature Kelvin
            return t_k - 273.15                # Conversion en C
            
        except Exception as e:
            raise ValueError(
                f"Erreur calcul NTC: {str(e)}"
            )
    
    else:
        # Type de capteur non supporte
        raise ValueError(
            f"Type de capteur inconnu: {profile.kind}"
        )
