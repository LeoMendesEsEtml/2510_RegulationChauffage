"""
Gestionnaire de récupération après erreur.
Définit les stratégies de récupération pour différents types d'erreurs.
"""
from typing import Dict, Callable, Optional, Any
from enum import Enum, auto
from dataclasses import dataclass
import logging
from fault.fault_manager import FaultCode, Fault
from utils.logging_config import setup_module_logger

class RecoveryStrategy(Enum):
    """Stratégies de récupération disponibles"""
    RETRY = auto()          # Réessayer l'opération
    RESET = auto()          # Réinitialiser le composant
    FALLBACK = auto()       # Utiliser une valeur de repli
    DISABLE = auto()        # Désactiver le composant
    EMERGENCY = auto()      # Arrêt d'urgence

@dataclass
class RecoveryAction:
    """Action de récupération à effectuer"""
    strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay_s: float = 1.0
    fallback_value: Any = None

class RecoveryManager:
    def __init__(self):
        """Initialise le gestionnaire de récupération."""
        self.logger = setup_module_logger('recovery')
        self._recovery_map: Dict[FaultCode, RecoveryAction] = self._init_recovery_map()
        self._retry_counts: Dict[str, int] = {}
        self._recovery_handlers: Dict[RecoveryStrategy, Callable] = self._init_handlers()

    def _init_recovery_map(self) -> Dict[FaultCode, RecoveryAction]:
        """Initialise la table des stratégies de récupération."""
        return {
            FaultCode.SENSOR_ERROR: RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                retry_delay_s=2.0
            ),
            FaultCode.ADC_ERROR: RecoveryAction(
                strategy=RecoveryStrategy.RESET,
                max_retries=2,
                retry_delay_s=1.0
            ),
            FaultCode.COMMUNICATION_ERROR: RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                max_retries=5,
                retry_delay_s=0.5
            ),
            FaultCode.CONFIGURATION_ERROR: RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                fallback_value={}
            ),
            FaultCode.REGULATION_ERROR: RecoveryAction(
                strategy=RecoveryStrategy.EMERGENCY
            )
        }

    def _init_handlers(self) -> Dict[RecoveryStrategy, Callable]:
        """Initialise les handlers de récupération."""
        return {
            RecoveryStrategy.RETRY: self._handle_retry,
            RecoveryStrategy.RESET: self._handle_reset,
            RecoveryStrategy.FALLBACK: self._handle_fallback,
            RecoveryStrategy.DISABLE: self._handle_disable,
            RecoveryStrategy.EMERGENCY: self._handle_emergency
        }

    def handle_fault(self, fault: Fault, context: Dict[str, Any]) -> Optional[Any]:
        """
        Gère une erreur et tente une récupération.
        
        Args:
            fault: L'erreur à gérer
            context: Contexte de l'erreur
            
        Returns:
            Optional[Any]: Résultat de la récupération si applicable
        """
        action = self._recovery_map.get(fault.code)
        if not action:
            self.logger.warning(f"Pas de stratégie de récupération pour {fault.code}")
            return None

        handler = self._recovery_handlers.get(action.strategy)
        if not handler:
            self.logger.error(f"Handler non trouvé pour {action.strategy}")
            return None

        try:
            return handler(fault, action, context)
        except Exception as e:
            self.logger.error(f"Échec de la récupération: {e}")
            return None

    def _handle_retry(self, fault: Fault, action: RecoveryAction, 
                     context: Dict[str, Any]) -> Optional[Any]:
        """Gère la stratégie RETRY."""
        component = context.get('component', 'unknown')
        retry_key = f"{component}_{fault.code.name}"
        
        if self._retry_counts.get(retry_key, 0) >= action.max_retries:
            self.logger.error(f"Nombre maximum de tentatives atteint pour {component}")
            return None

        self._retry_counts[retry_key] = self._retry_counts.get(retry_key, 0) + 1
        self.logger.info(f"Tentative {self._retry_counts[retry_key]} pour {component}")
        
        # Exécute la fonction de retry si fournie
        retry_func = context.get('retry_func')
        if retry_func and callable(retry_func):
            return retry_func()
        return None

    def _handle_reset(self, fault: Fault, action: RecoveryAction, 
                     context: Dict[str, Any]) -> Optional[Any]:
        """Gère la stratégie RESET."""
        component = context.get('component', 'unknown')
        self.logger.info(f"Réinitialisation de {component}")
        
        reset_func = context.get('reset_func')
        if reset_func and callable(reset_func):
            return reset_func()
        return None

    def _handle_fallback(self, fault: Fault, action: RecoveryAction, 
                        context: Dict[str, Any]) -> Any:
        """Gère la stratégie FALLBACK."""
        self.logger.info(f"Utilisation valeur de repli: {action.fallback_value}")
        return action.fallback_value

    def _handle_disable(self, fault: Fault, action: RecoveryAction, 
                       context: Dict[str, Any]) -> None:
        """Gère la stratégie DISABLE."""
        component = context.get('component', 'unknown')
        self.logger.warning(f"Désactivation de {component}")
        
        disable_func = context.get('disable_func')
        if disable_func and callable(disable_func):
            disable_func()

    def _handle_emergency(self, fault: Fault, action: RecoveryAction, 
                         context: Dict[str, Any]) -> None:
        """Gère la stratégie EMERGENCY."""
        self.logger.critical("Arrêt d'urgence du système")
        
        emergency_func = context.get('emergency_func')
        if emergency_func and callable(emergency_func):
            emergency_func()

    def reset_retry_count(self, component: str, fault_code: FaultCode) -> None:
        """Réinitialise le compteur de tentatives pour un composant."""
        retry_key = f"{component}_{fault_code.name}"
        if retry_key in self._retry_counts:
            del self._retry_counts[retry_key]
