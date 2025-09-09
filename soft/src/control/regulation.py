# -*- coding: utf-8 -*-
"""
Module de r�gulation de temp�rature.

Ce module impl�mente:
1. Algorithme de r�gulation thermique
   - Calcul temp�rature simul�e
   - S�lection r�sistance �quivalente
   - Application loi de commande

2. Gestion des param�tres:
   - N: facteur de m�lange (0..1)
   - kM: coefficient m�t�o (-1..1) 
   - Tprevu: temp�rature pr�vue

3. Param�tres r�seau r�sistif:
   - 32 points de 1k? � 50k?
   - R�solution ~0.1�C
   - Plage -20�C � +40�C

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
    Param�tres de l'algorithme de r�gulation.
    
    Attributs:
        N: Facteur de m�lange (0..1)
           0 = 100% mesure, 1 = 100% pr�vision
        kM: Coefficient m�t�o (-1..1)
           Impact de la m�t�o sur la pr�vision
        Tprevu: Temp�rature pr�vue (�C)
           Consigne de temp�rature
    """
    N: float           # Facteur melange
    kM: float         # Coeff meteo
    Tprevu: float     # T prevue
    
    def validate(self) -> None:
        """
        Valide les param�tres de r�gulation.
        
        Raises:
            ValueError: Si param�tres hors limites
        """
        if not 0 <= self.N <= 1:
            raise ValueError(f"N doit �tre entre 0 et 1: {self.N}")
        if not -1 <= self.kM <= 1:
            raise ValueError(f"kM doit �tre entre -1 et 1: {self.kM}")
        if not -50 <= self.Tprevu <= 50:
            raise ValueError(
                f"Tprevu doit �tre entre -50 et 50�C: {self.Tprevu}"
            )

class RegulationResult:
    """
    R�sultat d'une it�ration de r�gulation.
    
    Attributs:
        slot: Index dans le r�seau (0..31)
        step: Pas de r�solution
        Tsim: Temp�rature simul�e r�sultante
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
    Contr�leur de r�gulation thermique.
    
    Impl�mente l'algorithme de r�gulation avec:
    - Calcul temp�rature simul�e
    - S�lection r�sistance �quivalente
    - Gestion des transitions
    """
    
    def __init__(self):
        """Initialise le contr�leur."""
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
        Ex�cute une it�ration de r�gulation.
        
        Args:
            Tmes: Temp�rature mesur�e (�C)
            N: Facteur de m�lange (0..1)
            kM: Coefficient m�t�o (-1..1)
            Tprevu: Temp�rature pr�vue (�C)
            
        Returns:
            RegulationResult avec:
            - slot: Index r�seau s�lectionn�
            - step: Pas de r�solution
            - Tsim: Temp�rature simul�e
            
        Notes:
            La temp�rature simul�e est calcul�e par:
            Tsim = (1-N)*Tmes + N*(Tprevu + kM*dT)
            avec dT = variation typique journali�re
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
                f"R�gulation: Tmes={Tmes:.1f}�C, "
                f"Tsim={Tsim:.1f}�C -> slot {slot}"
            )
            
            return RegulationResult(slot, step, Tsim)
            
        except Exception as e:
            logger.error(f"Erreur r�gulation: {str(e)}")
            # En cas d'erreur, maintient dernier etat
            return RegulationResult(
                self._last_slot, 1, Tmes
            )
            
    def _find_network_slot(
        self,
        temp: float
    ) -> Tuple[int, int]:
        """
        Trouve le slot r�seau le plus proche.
        
        Args:
            temp: Temp�rature cible (�C)
            
        Returns:
            (slot, step) avec:
            - slot: Index dans le r�seau (0..31)
            - step: Pas de r�solution
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
