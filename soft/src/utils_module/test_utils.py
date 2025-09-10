# -*- coding: utf-8 -*-
"""
Utilitaires pour les tests.

Fournit:
- Des fonctions de test pour les capteurs
- Des generateurs de donnees de test
- Des outils de validation
"""

import numpy as np
from typing import List, Tuple, Optional, Union
from datetime import datetime
import logging
from utils_module.logging_config import setup_module_logger
from utils_module.error_handler import handle_errors, ValidationError

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
    Genere des donnees de temperature simulees.
    
    Args:
        start_temp: Temperature initiale (C)
        end_temp: Temperature finale (C)
        duration_s: Duree en secondes
        sample_rate_hz: Frequence d'echantillonnage
        noise_std: Ecart-type du bruit
        
    Returns:
        (timestamps, temperatures)
    """
    num_samples = int(duration_s * sample_rate_hz)
    
    # Vecteur temps
    t = np.linspace(0, duration_s, num_samples)
    
    # Rampe de temperature + bruit
    temp = np.linspace(start_temp, end_temp, num_samples)
    temp += np.random.normal(0, noise_std, num_samples)
    
    return t, temp

def validate_temperature(
    temp: float,
    min_temp: float = -50.0,
    max_temp: float = 150.0
) -> bool:
    """
    Valide une mesure de temperature.
    
    Args:
        temp: Temperature a valider
        min_temp: Temperature minimale
        max_temp: Temperature maximale
        
    Returns:
        True si valide
        
    Raises:
        ValidationError si invalide
    """
    if not isinstance(temp, (int, float)):
        raise ValidationError("Temperature doit etre un nombre")
        
    if not min_temp <= temp <= max_temp:
        raise ValidationError(
            f"Temperature {temp}C hors limites "
            f"[{min_temp}, {max_temp}]"
        )
    
    return True

def calculate_statistics(
    data: Union[List[float], np.ndarray]
) -> Tuple[float, float, float, float]:
    """
    Calcule les statistiques d'un ensemble de donnees.
    
    Args:
        data: Liste ou array de donnees
        
    Returns:
        (moyenne, ecart-type, min, max)
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
    Verifie la coherence des mesures d'un capteur.
    
    Args:
        values: Liste de mesures
        reference: Valeur de reference optionnelle
        max_deviation: Ecart maximal autorise
        
    Returns:
        True si coherent
        
    Raises:
        ValidationError si incoherent
    """
    if not values:
        raise ValidationError("Liste de mesures vide")
        
    mean = np.mean(values)
    std = np.std(values)
    
    # Verification ecart-type
    if std > max_deviation:
        raise ValidationError(
            f"Ecart-type trop important: {std:.2f} > {max_deviation}"
        )
        
    # Verification reference
    if reference is not None:
        if abs(mean - reference) > max_deviation:
            raise ValidationError(
                f"Ecart reference trop important: "
                f"|{mean:.2f} - {reference:.2f}| > {max_deviation}"
            )
            
    return True

def log_test_results(
    test_name: str,
    passed: bool,
    details: Optional[str] = None
) -> None:
    """
    Enregistre les resultats d'un test.
    
    Args:
        test_name: Nom du test
        passed: Resultat du test
        details: Details optionnels
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
        data: Donnees d'entree
        window_size: Taille de la fenetre
        
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
