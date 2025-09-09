# -*- coding: utf-8 -*-
"""
Module de régulation de température.

Ce module implémente:
1. Algorithme de régulation thermique
   - Calcul température simulée
   - Sélection résistance équivalente
   - Application loi de commande

2. Gestion des paramètres:
   - N: facteur de mélange (0..1)
   - kM: coefficient météo (-1..1) 
   - Tprevu: température prévue

3. Paramètres réseau résistif:
   - 32 points de 1k? à 50k?
   - Résolution ~0.1°C
   - Plage -20°C à +40°C

Auteur: LeoMendesEsEtml
Date: 2025
Licence: MIT
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import math
import logging
from utils.logging_config import setup_module_logger

# Configuration logging
logger = setup_module_logger(__name__)

@dataclass
class RegulationParams:
    """
    Paramètres de l'algorithme de régulation.
    
    Attributs:
        N: Facteur de mélange (0..1)
           0 = 100% mesure, 1 = 100% prévision
        kM: Coefficient météo (-1..1)
           Impact de la météo sur la prévision
        Tprevu: Température prévue (°C)
           Consigne de température
    """
    N: float           # Facteur mélange
    kM: float         # Coeff météo
    Tprevu: float     # T prévue
    
    def validate(self) -> None:
        """
        Valide les paramètres de régulation.
        
        Raises:
            ValueError: Si paramètres hors limites
        """
        if not 0 <= self.N <= 1:
            raise ValueError(f"N doit être entre 0 et 1: {self.N}")
        if not -1 <= self.kM <= 1:
            raise ValueError(f"kM doit être entre -1 et 1: {self.kM}")
        if not -50 <= self.Tprevu <= 50:
            raise ValueError(
                f"Tprevu doit être entre -50 et 50°C: {self.Tprevu}"
            )

class RegulationResult:
    """
    Résultat d'une itération de régulation.
    
    Attributs:
        slot: Index dans le réseau (0..31)
        step: Pas de résolution
        Tsim: Température simulée résultante
    """
    def __init__(
        self,
        slot: int,
        step: int,
        Tsim: float
    ):
        self.slot = slot
        self.step = step
        self.Tsim = Tsim
        
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire."""
        return {
            "slot": self.slot,
            "step": self.step,
            "Tsim": self.Tsim
        }

class Regulation:
    """
    Contrôleur de régulation thermique.
    
    Implémente l'algorithme de régulation avec:
    - Calcul température simulée
    - Sélection résistance équivalente
    - Gestion des transitions
    """
    
    def __init__(self):
        """Initialise le contrôleur."""
        # Table T -> index réseau (32 points)
        self._temp_table = [
            -20.0 + i * 2.0 for i in range(32)
        ]
        self._last_slot = 0
        
    def regulate(
        self,
        Tmes: float,
        N: float,
        kM: float,
        Tprevu: float
    ) -> RegulationResult:
        """
        Exécute une itération de régulation.
        
        Args:
            Tmes: Température mesurée (°C)
            N: Facteur de mélange (0..1)
            kM: Coefficient météo (-1..1)
            Tprevu: Température prévue (°C)
            
        Returns:
            RegulationResult avec:
            - slot: Index réseau sélectionné
            - step: Pas de résolution
            - Tsim: Température simulée
            
        Notes:
            La température simulée est calculée par:
            Tsim = (1-N)*Tmes + N*(Tprevu + kM*dT)
            avec dT = variation typique journalière
        """
        # Validation des paramètres
        params = RegulationParams(N, kM, Tprevu)
        params.validate()
        
        try:
            # 1. Calcul température simulée
            dT = 5.0  # Variation typique jour/nuit
            Tsim = (
                (1 - N) * Tmes +           # Composante mesure
                N * (Tprevu + kM * dT)     # Composante prévision
            )
            
            # 2. Sélection slot réseau résistif
            slot, step = self._find_network_slot(Tsim)
            
            # 3. Mise à jour et logging
            self._last_slot = slot
            logger.info(
                f"Régulation: Tmes={Tmes:.1f}°C, "
                f"Tsim={Tsim:.1f}°C -> slot {slot}"
            )
            
            return RegulationResult(slot, step, Tsim)
            
        except Exception as e:
            logger.error(f"Erreur régulation: {str(e)}")
            # En cas d'erreur, maintient dernier état
            return RegulationResult(
                self._last_slot, 1, Tmes
            )
            
    def _find_network_slot(
        self,
        temp: float
    ) -> Tuple[int, int]:
        """
        Trouve le slot réseau le plus proche.
        
        Args:
            temp: Température cible (°C)
            
        Returns:
            (slot, step) avec:
            - slot: Index dans le réseau (0..31)
            - step: Pas de résolution
        """
        # Limites de la table
        if temp <= self._temp_table[0]:
            return 0, 1
        if temp >= self._temp_table[-1]:
            return len(self._temp_table) - 1, 1
            
        # Recherche slot encadrant
        for i in range(len(self._temp_table) - 1):
            if (self._temp_table[i] <= temp <= 
                self._temp_table[i + 1]):
                # Interpole entre les slots
                alpha = (
                    (temp - self._temp_table[i]) /
                    (self._temp_table[i + 1] - 
                     self._temp_table[i])
                )
                return (
                    i if alpha < 0.5 else i + 1,
                    1
                )
                
        # Ne devrait jamais arriver
        return 0, 1

# Instance globale
CTRL = Regulation()
