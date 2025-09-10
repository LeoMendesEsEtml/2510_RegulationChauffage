"""
Gestionnaire de fautes pour le système de régulation.
Permet de tracer et gérer les erreurs système.
"""
from typing import Dict, List, Optional, Any
import time
import logging
from dataclasses import dataclass
from enum import IntEnum

class FaultCode(IntEnum):
    """Codes d'erreur du système"""
    NO_ERROR = 0
    SENSOR_ERROR = 1
    ADC_ERROR = 2
    COMMUNICATION_ERROR = 3
    CONFIGURATION_ERROR = 4
    REGULATION_ERROR = 5

@dataclass
class Fault:
    """Représente une erreur système"""
    code: FaultCode
    timestamp: float
    context: Dict[str, Any]
    description: str

class FaultManager:
    def __init__(self, max_history: int = 100):
        """
        Initialise le gestionnaire de fautes.
        
        Args:
            max_history: Nombre maximum d'erreurs à conserver
        """
        self._faults: List[Fault] = []
        self._max_history = max_history
        self.logger = logging.getLogger('faults')
        
    def report_fault(self, code: FaultCode, context: Dict[str, Any]) -> None:
        """
        Enregistre une nouvelle erreur.
        
        Args:
            code: Code d'erreur
            context: Contexte de l'erreur (variables, états, etc.)
        """
        fault = Fault(
            code=code,
            timestamp=time.time(),
            context=context.copy(),
            description=self._get_description(code)
        )
        
        self._faults.append(fault)
        if len(self._faults) > self._max_history:
            self._faults.pop(0)
            
        self.logger.error(f"Erreur {code.name}: {fault.description}")
        
    def get_last_fault(self) -> Optional[Fault]:
        """
        Retourne la dernière erreur enregistrée.
        
        Returns:
            Optional[Fault]: Dernière erreur ou None si pas d'erreur
        """
        return self._faults[-1] if self._faults else None
        
    def clear_faults(self) -> None:
        """Efface l'historique des erreurs."""
        self._faults.clear()
        
    def get_fault_history(self) -> List[Fault]:
        """
        Retourne l'historique des erreurs.
        
        Returns:
            List[Fault]: Liste des erreurs
        """
        return self._faults.copy()
        
    def _get_description(self, code: FaultCode) -> str:
        """Retourne une description pour un code d'erreur."""
        descriptions = {
            FaultCode.NO_ERROR: "Pas d'erreur",
            FaultCode.SENSOR_ERROR: "Erreur de capteur",
            FaultCode.ADC_ERROR: "Erreur de conversion analogique",
            FaultCode.COMMUNICATION_ERROR: "Erreur de communication",
            FaultCode.CONFIGURATION_ERROR: "Erreur de configuration",
            FaultCode.REGULATION_ERROR: "Erreur de régulation"
        }
        return descriptions.get(code, "Erreur inconnue")
