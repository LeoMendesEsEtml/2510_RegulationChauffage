"""
Simulateur de capteurs de temperature pour tests et developpement.
"""
from math import exp
from typing import Optional, Dict
from random import gauss
from Metrology.sensor_profiles import SensorProfile

class SensorSimulator:
    def __init__(self, noise_std: float = 0.1):
        """
        Initialise le simulateur.
        
        Args:
            noise_std: Ecart-type du bruit gaussien ajoute
        """
        self.noise_std = noise_std
        self._cached_values: Dict[tuple, float] = {}

    def simulate(self, profile: SensorProfile, t_c: float) -> float:
        """
        Simule la resistance d'un capteur a une temperature donnee.
        
        Args:
            profile: Profil du capteur
            t_c: Temperature en C
            
        Returns:
            float: Resistance simulee en ohms avec bruit
        """
        # Utilise le cache pour eviter les calculs repetes
        cache_key = (id(profile), t_c)
        if cache_key in self._cached_values:
            base_value = self._cached_values[cache_key]
        else:
            # Calcul selon le type de capteur
            if profile.kind == "PTC":
                # R(T) = R0 * (1 + alpha*(T - T0))
                base_value = profile.r0_ohm * (1 + profile.alpha_per_c * (t_c - profile.t0_c))
            elif profile.kind == "NTC":
                # Steinhart-Hart inverse
                t_k = t_c + 273.15
                inv_t = 1.0 / t_k
                # Resolution approximative de l'equation S-H
                lnR = (inv_t - profile.A) / profile.B
                base_value = exp(lnR)
            else:
                raise ValueError(f"Type de capteur non supporte: {profile.kind}")
            
            self._cached_values[cache_key] = base_value
        
        # Ajoute du bruit gaussien
        noise = gauss(0, self.noise_std * base_value)
        return max(0.1, base_value + noise)  # Evite les valeurs negatives
