# -*- coding: utf-8 -*-
"""
Module de conversion résistance-température pour capteurs de température.

Ce module implémente:
1. Conversion R ? T pour capteurs PTC:
   - Linéarisation alpha autour du point de référence
   - Précision optimale entre -15°C et 40°C
   - Supporte PT1000, PT100, Ni1000, KTY81-210

2. Conversion R ? T pour thermistances NTC:
   - Équation Steinhart-Hart complète
   - Coefficients A, B, C calibrés
   - Grande précision sur toute la plage

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
    Convertit une résistance en température selon le profil capteur.
    
    Pour les PTC (ex: PT1000):
    - Utilise la linéarisation alpha : R(T) = R0*(1 + ?*(T-T0))
    - R0 : résistance à T0 (généralement 0°C ou 25°C)
    - ? : coefficient de température (/°C)
    - Précision ~0.1°C entre -15°C et 40°C
    
    Pour les NTC:
    - Utilise l'équation Steinhart-Hart : 1/T = A + B*ln(R) + C*ln(R)³
    - A, B, C : coefficients calibrés
    - T en Kelvin, conversion finale en °C
    - Précision ~0.05°C sur toute la plage
    
    Args:
        profile: Configuration du capteur avec:
            - kind: "PTC" ou "NTC"
            - Coefficients selon type (?, R0 ou A,B,C)
        r_ohm: Résistance mesurée en ohms
        
    Returns:
        float: Température en °C
        
    Raises:
        ConfigError: Type de capteur non supporté
        ValueError: Résistance ? 0 ou coefficients invalides
    
    Note:
        Les capteurs PTC supportés sont:
        - PT100/PT1000 (? = 0.00385 /°C)
        - Ni1000 (? = 0.00617 /°C)
        - KTY81-210 (? = 0.00772 /°C)
    """
    # Validation de la résistance
    if r_ohm <= 0:
        raise ValueError(
            f"La résistance doit être positive: {r_ohm} ?"
        )

    # Validation du profil
    if not profile:
        raise ConfigError("Profil capteur manquant")

    # Traitement selon type de capteur
    if profile.kind == "PTC":
        # Capteur PTC (coefficient positif)
        # Formule: R(T) = R0 * (1 + ?*(T - T0))
        # Résolution: T = T0 + (R/R0 - 1)/?
        
        # Validation des paramètres
        if not (profile.r0_ohm > 0 and profile.alpha_per_c > 0):
            raise ConfigError(
                f"Paramètres PTC invalides: R0={profile.r0_ohm}, "
                f"alpha={profile.alpha_per_c}"
            )
            
        # Calcul température
        t_c = profile.t0_c + (r_ohm / profile.r0_ohm - 1.0) / profile.alpha_per_c
        return t_c

    elif profile.kind == "NTC":
        # Thermistance NTC (coefficient négatif) 
        # Équation Steinhart-Hart:
        # 1/T(K) = A + B*ln(R) + C*(ln(R))³
        
        # Validation des coefficients
        if not all([profile.A, profile.B, profile.C]):
            raise ConfigError(
                f"Coefficients S-H manquants: A={profile.A}, "
                f"B={profile.B}, C={profile.C}"
            )
            
        # Calcul température
        try:
            lnR = log(r_ohm)                    # Logarithme naturel
            invK = (                            # Inverse des Kelvin
                profile.A +                     # Terme constant
                profile.B * lnR +              # Terme linéaire
                profile.C * (lnR ** 3)         # Terme cubique
            )
            t_k = 1.0 / invK                   # Température Kelvin
            return t_k - 273.15                # Conversion en °C
            
        except Exception as e:
            raise ValueError(
                f"Erreur calcul NTC: {str(e)}"
            )
    
    else:
        # Type de capteur non supporté
        raise ValueError(
            f"Type de capteur inconnu: {profile.kind}"
        )
