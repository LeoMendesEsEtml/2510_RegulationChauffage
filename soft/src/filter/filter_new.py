# -*- coding: utf-8 -*-
"""
Module de filtrage numérique pour le traitement des mesures.

Implémente plusieurs types de filtres:
1. Moyenne mobile (lissage simple)
2. Moyenne exponentielle (EMA, réponse rapide)
3. Filtre médian (suppression des outliers)
4. Détection des valeurs aberrantes

Ces filtres sont utilisés pour:
- Réduire le bruit des mesures
- Éliminer les valeurs aberrantes
- Améliorer la stabilité de la régulation
"""

from typing import List, Tuple, Optional
from statistics import median, mean, stdev
from collections import deque
from dataclasses import dataclass

@dataclass
class FilterConfig:
    """Configuration des paramètres de filtrage"""
    window_size: int = 5      # Taille de la fenêtre glissante
    alpha_ema: float = 0.2    # Coefficient EMA (0..1)
    outlier_thresh: float = 3.0  # Seuils en écarts-types

class Filter:
    """
    Classe de filtrage des mesures.
    Maintient l'état des filtres entre les appels.
    """
    
    def __init__(self, config: Optional[FilterConfig] = None):
        """
        Initialise les filtres avec leur configuration.
        
        Args:
            config: Configuration des filtres
        """
        self.config = config or FilterConfig()
        self._ma_buffer = deque(maxlen=self.config.window_size)
        self._last_ema: Optional[float] = None

    def moving_average(self, values: List[float], 
                      window: Optional[int] = None) -> List[float]:
        """
        Applique un filtre de moyenne mobile.
        
        Calcule la moyenne sur une fenêtre glissante:
        y[n] = (x[n] + x[n-1] + ... + x[n-window+1]) / window
        
        Args:
            values: Liste des valeurs à filtrer
            window: Taille de la fenêtre (optionnel)
            
        Returns:
            Liste des valeurs filtrées
            
        Raises:
            ValueError: Si la fenêtre est invalide
        """
        # Validation
        win = window or self.config.window_size
        if win < 1:
            raise ValueError("Taille de fenêtre invalide")
        if not values:
            return []
            
        # Initialisation du buffer
        buffer = deque(maxlen=win)
        result = []
        
        # Calcul de la moyenne glissante
        for x in values:
            buffer.append(x)
            result.append(sum(buffer) / len(buffer))
            
        return result

    def ema(self, values: List[float], 
            alpha: Optional[float] = None) -> List[float]:
        """
        Applique un filtre de moyenne mobile exponentielle.
        
        Formule: y[n] = ?*x[n] + (1-?)*y[n-1]
        ? contrôle la "mémoire" du filtre:
        - ? proche de 1: réponse rapide
        - ? proche de 0: lissage important
        
        Args:
            values: Liste des valeurs à filtrer
            alpha: Coefficient de lissage (0..1)
            
        Returns:
            Liste des valeurs filtrées
            
        Raises:
            ValueError: Si alpha est invalide
        """
        # Validation
        a = alpha or self.config.alpha_ema
        if not 0 <= a <= 1:
            raise ValueError("Alpha doit être entre 0 et 1")
        if not values:
            return []
            
        # Initialisation
        if self._last_ema is None:
            self._last_ema = values[0]
            
        result = []
        ema = self._last_ema
        
        # Calcul EMA
        for x in values:
            ema = a * x + (1 - a) * ema
            result.append(ema)
            
        self._last_ema = ema
        return result

    def median(self, values: List[float], 
               window: Optional[int] = None) -> List[float]:
        """
        Applique un filtre médian.
        
        Efficace pour supprimer les pics isolés.
        Préserve les transitions franches.
        
        Args:
            values: Liste des valeurs à filtrer
            window: Taille de la fenêtre (optionnel)
            
        Returns:
            Liste des valeurs filtrées
            
        Raises:
            ValueError: Si la fenêtre est invalide
        """
        # Validation
        win = window or self.config.window_size
        if win < 1 or win % 2 == 0:
            raise ValueError("Taille de fenêtre invalide")
        if not values:
            return []
            
        # Padding des bords
        pad = win // 2
        padded = [values[0]] * pad + values + [values[-1]] * pad
        result = []
        
        # Calcul de la médiane glissante
        for i in range(len(values)):
            window = padded[i:i + win]
            result.append(median(window))
            
        return result

    def detect_outliers(self, values: List[float], 
                       threshold: Optional[float] = None) -> List[bool]:
        """
        Détecte les valeurs aberrantes par écart-type.
        
        Une valeur est considérée aberrante si elle s'écarte
        de plus de N écarts-types de la moyenne.
        
        Args:
            values: Liste des valeurs à analyser
            threshold: Seuil en nombre d'écarts-types
            
        Returns:
            Liste de booléens (True = outlier)
        """
        if not values:
            return []
            
        # Calcul des statistiques
        avg = mean(values)
        std = stdev(values) if len(values) > 1 else 0
        thresh = threshold or self.config.outlier_thresh
        
        # Détection des outliers
        return [abs(x - avg) > thresh * std for x in values]

    def filter_outliers(self, values: List[float], 
                       replacement: str = "previous") -> List[float]:
        """
        Filtre les valeurs aberrantes.
        
        Args:
            values: Liste des valeurs à filtrer
            replacement: Méthode de remplacement:
                        "previous": Dernière valeur valide
                        "median": Médiane locale
                        "interpolate": Interpolation linéaire
            
        Returns:
            Liste des valeurs filtrées
        """
        if not values:
            return []
            
        # Détection des outliers
        is_outlier = self.detect_outliers(values)
        result = values.copy()
        
        # Remplacement selon la méthode choisie
        if replacement == "previous":
            last_valid = values[0]
            for i in range(len(values)):
                if is_outlier[i]:
                    result[i] = last_valid
                else:
                    last_valid = values[i]
                    
        elif replacement == "median":
            for i in range(len(values)):
                if is_outlier[i]:
                    # Utilise une fenêtre locale pour la médiane
                    start = max(0, i - self.config.window_size)
                    end = min(len(values), i + self.config.window_size + 1)
                    window = [v for j, v in enumerate(values[start:end])
                            if not is_outlier[j + start]]
                    result[i] = median(window) if window else values[i]
                    
        elif replacement == "interpolate":
            i = 0
            while i < len(values):
                if is_outlier[i]:
                    # Trouve la prochaine valeur valide
                    next_valid = i + 1
                    while (next_valid < len(values) and 
                           is_outlier[next_valid]):
                        next_valid += 1
                    
                    # Interpolation linéaire
                    if next_valid < len(values):
                        start_val = result[i - 1]
                        end_val = values[next_valid]
                        step = (end_val - start_val) / (next_valid - i + 1)
                        for j in range(i, next_valid):
                            result[j] = start_val + step * (j - i + 1)
                    i = next_valid
                else:
                    i += 1
                    
        return result
