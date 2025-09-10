# -*- coding: utf-8 -*-
"""
Module de regulation de temperature.

Ce module implemente:
1. Algorithme de regulation thermique
   - Calcul temperature simulee
   - Selection resistance equivalente
   - Application loi de commande

2. Gestion des parametres:
   - N: facteur de melange (0..1)
   - kM: coefficient meteo (-1..1) 
   - Tprevu: temperature prevue

3. Parametres reseau resistif:
   - 32 points de 1kOhm a 50kOhm
   - Resolution ~0.1C
   - Plage -20C a +40C

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
    Parametres de l'algorithme de regulation.
    
    Attributs:
        N: Facteur de melange (0..1)
           0 = 100% mesure, 1 = 100% prevision
        kM: Coefficient meteo (-1..1)
           Impact de la meteo sur la prevision
        Tprevu: Temperature prevue (C)
           Consigne de temperature
    """
    N: float           # Facteur melange
    kM: float         # Coeff meteo
    Tprevu: float     # T prevue
    
    def validate(self) -> None:
        """
        Valide les parametres de regulation.
        
        Raises:
            ValueError: Si parametres hors limites
        """
        if not 0 <= self.N <= 1:
            raise ValueError(f"N doit etre entre 0 et 1: {self.N}")
        if not -1 <= self.kM <= 1:
            raise ValueError(f"kM doit etre entre -1 et 1: {self.kM}")
        if not -50 <= self.Tprevu <= 50:
            raise ValueError(
                f"Tprevu doit etre entre -50 et 50C: {self.Tprevu}"
            )

class RegulationResult:
    """
    Resultat d'une iteration de regulation.
    
    Attributs:
        slot: Index dans le reseau (0..31)
        step: Pas de resolution
        Tsim: Temperature simulee resultante
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
    Controleur de regulation thermique.
    
    Implemente l'algorithme de regulation avec:
    - Calcul temperature simulee
    - Selection resistance equivalente
    - Gestion des transitions
    """
    
    def __init__(self):
        """Initialise le controleur."""
    # Table T -> index reseau (32 points)
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
        Execute une iteration de regulation.
        
        Args:
            Tmes: Temperature mesuree (C)
            N: Facteur de melange (0..1)
            kM: Coefficient meteo (-1..1)
            Tprevu: Temperature prevue (C)
            
        Returns:
            RegulationResult avec:
            - slot: Index reseau selectionne
            - step: Pas de resolution
            - Tsim: Temperature simulee
            
        Notes:
            La temperature simulee est calculee par:
            Tsim = (1-N)*Tmes + N*(Tprevu + kM*dT)
            avec dT = variation typique journaliere
        """
    # Validation des parametres
        params = RegulationParams(N, kM, Tprevu)
        params.validate()
        
        try:
            # 1. Calcul temperature simulee
            dT = 5.0  # Variation typique jour/nuit
            Tsim = (
                (1 - N) * Tmes +           # Composante mesure
                N * (Tprevu + kM * dT)     # Composante prevision
            )
            
            # 2. Selection slot reseau resistif
            slot, step = self._find_network_slot(Tsim)
            
            # 3. Mise a jour et logging
            self._last_slot = slot
            logger.info(
                f"Regulation: Tmes={Tmes:.1f}C, "
                f"Tsim={Tsim:.1f}C -> slot {slot}"
            )
            
            return RegulationResult(slot, step, Tsim)
            
        except Exception as e:
            logger.error(f"Erreur regulation: {str(e)}")
            # En cas d'erreur, maintient dernier etat
            return RegulationResult(
                self._last_slot, 1, Tmes
            )
            
    def _find_network_slot(
        self,
        temp: float
    ) -> Tuple[int, int]:
        """
        Trouve le slot reseau le plus proche.
        
        Args:
            temp: Temperature cible (C)
            
        Returns:
            (slot, step) avec:
            - slot: Index dans le reseau (0..31)
            - step: Pas de resolution
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
