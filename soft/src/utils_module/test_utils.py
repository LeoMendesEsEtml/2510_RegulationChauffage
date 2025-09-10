# -*- coding: utf-8 -*-
"""
Utilitaires pour les tests.

Fournit:
- Des fonctions de test pour les capteurs
- Des générateurs de données de test
- Des outils de validation
"""

import numpy as np
from typing import List, Tuple, Optional, Union
from datetime import datetime
import logging
from utils.logging_config import setup_module_logger
from utils.error_handler import handle_errors, ValidationError

# Logger
logger = setup_module_logger(__name__)

def generate_temperature_data(
    start_temp: float,
    end_temp: float,
    duration_s: float,
    sample_rate_hz: float,
    noise_std: float = 0.1
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Génère des données de température simulées.
    
    Args:
        start_temp: Température initiale (°C)
        end_temp: Température finale (°C)
        duration_s: Durée en secondes
        sample_rate_hz: Fréquence d'échantillonnage
        noise_std: Écart-type du bruit
        
    Returns:
        (timestamps, temperatures)
    """
    num_samples = int(duration_s * sample_rate_hz)
    
    # Vecteur temps
    t = np.linspace(0, duration_s, num_samples)
    
    # Rampe de température + bruit
    temp = np.linspace(start_temp, end_temp, num_samples)
    temp += np.random.normal(0, noise_std, num_samples)
    
    return t, temp

def validate_temperature(
    temp: float,
    min_temp: float = -50.0,
    max_temp: float = 150.0
) -> bool:
    """
    Valide une mesure de température.
    
    Args:
        temp: Température à valider
        min_temp: Température minimale
        max_temp: Température maximale
        
    Returns:
        True si valide
        
    Raises:
        ValidationError si invalide
    """
    if not isinstance(temp, (int, float)):
        raise ValidationError("Température doit être un nombre")
        
    if not min_temp <= temp <= max_temp:
        raise ValidationError(
            f"Température {temp}°C hors limites "
            f"[{min_temp}, {max_temp}]"
        )
    
    return True

def calculate_statistics(
    data: Union[List[float], np.ndarray]
) -> Tuple[float, float, float, float]:
    """
    Calcule les statistiques d'un ensemble de données.
    
    Args:
        data: Liste ou array de données
        
    Returns:
        (moyenne, écart-type, min, max)
    """
    data = np.array(data)
    return (
        float(np.mean(data)),
        float(np.std(data)),
        float(np.min(data)),
        float(np.max(data))
    )

@handle_errors
def check_sensor_consistency(
    values: List[float],
    reference: Optional[float] = None,
    max_deviation: float = 2.0
) -> bool:
    """
    Vérifie la cohérence des mesures d'un capteur.
    
    Args:
        values: Liste de mesures
        reference: Valeur de référence optionnelle
        max_deviation: Écart maximal autorisé
        
    Returns:
        True si cohérent
        
    Raises:
        ValidationError si incohérent
    """
    if not values:
        raise ValidationError("Liste de mesures vide")
        
    mean = np.mean(values)
    std = np.std(values)
    
    # Vérification écart-type
    if std > max_deviation:
        raise ValidationError(
            f"Écart-type trop important: {std:.2f} > {max_deviation}"
        )
        
    # Vérification référence
    if reference is not None:
        if abs(mean - reference) > max_deviation:
            raise ValidationError(
                f"Écart référence trop important: "
                f"|{mean:.2f} - {reference:.2f}| > {max_deviation}"
            )
            
    return True

def log_test_results(
    test_name: str,
    passed: bool,
    details: Optional[str] = None
) -> None:
    """
    Enregistre les résultats d'un test.
    
    Args:
        test_name: Nom du test
        passed: Résultat du test
        details: Détails optionnels
    """
    status = "PASS" if passed else "FAIL"
    message = f"Test {test_name}: {status}"
    if details:
        message += f" - {details}"
        
    level = logging.INFO if passed else logging.ERROR
    logger.log(level, message)

def timestamp() -> float:
    """
    Retourne un timestamp en secondes.
    
    Returns:
        Timestamp en secondes
    """
    return datetime.now().timestamp()

def moving_average(
    data: List[float],
    window_size: int = 5
) -> List[float]:
    """
    Calcule la moyenne mobile.
    
    Args:
        data: Données d'entrée
        window_size: Taille de la fenêtre
        
    Returns:
        Liste des moyennes
    """
    if not data:
        return []
        
    result = []
    for i in range(len(data)):
        start = max(0, i - window_size + 1)
        window = data[start:i + 1]
        result.append(sum(window) / len(window))
        
    return result
