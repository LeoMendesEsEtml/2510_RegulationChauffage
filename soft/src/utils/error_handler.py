# -*- coding: utf-8 -*-
"""
Gestionnaire d'erreurs centralisé.

Fournit:
- Des exceptions personnalisées
- Un gestionnaire d'erreurs global
- Des décorateurs pour la gestion des erreurs
- Des utilitaires de récupération d'erreur

Usage:
    from error_handler import handle_errors, retry_on_error
    
    @handle_errors
    def fonction_sensible():
        # code pouvant lever des exceptions
        
    @retry_on_error(max_attempts=3)
    def fonction_avec_retry():
        # code avec tentatives multiples
"""

import functools
import logging
import time
from typing import Type, Optional, Callable, Any, Union, Tuple
from utils.logging_config import setup_module_logger

# Configuration du logger
logger = setup_module_logger(__name__)

class SystemError(Exception):
    """Erreur système générique."""
    pass

class HardwareError(SystemError):
    """Erreur matérielle."""
    pass

class SensorError(HardwareError):
    """Erreur de capteur."""
    pass

class CommunicationError(HardwareError):
    """Erreur de communication."""
    pass

class ConfigurationError(SystemError):
    """Erreur de configuration."""
    pass

class ValidationError(SystemError):
    """Erreur de validation."""
    pass

def handle_errors(
    error_types: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR
) -> Callable:
    """
    Décorateur pour gérer les exceptions.
    
    Args:
        error_types: Types d'erreurs à gérer
        reraise: Si True, relève l'exception
        log_level: Niveau de log pour les erreurs
        
    Returns:
        Fonction décorée
    """
    if error_types is None:
        error_types = Exception
        
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                logger.log(
                    log_level,
                    f"Erreur dans {func.__name__}: {str(e)}",
                    exc_info=True
                )
                if reraise:
                    raise
            except Exception as e:
                logger.error(
                    f"Erreur inattendue dans {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator

def retry_on_error(
    max_attempts: int = 3,
    delay_s: float = 1.0,
    backoff_factor: float = 2.0,
    error_types: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None
) -> Callable:
    """
    Décorateur pour réessayer en cas d'erreur.
    
    Args:
        max_attempts: Nombre maximum de tentatives
        delay_s: Délai initial entre tentatives
        backoff_factor: Facteur de backoff pour le délai
        error_types: Types d'erreurs déclenchant retry
        
    Returns:
        Fonction décorée
    """
    if error_types is None:
        error_types = Exception
        
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error = None
            delay = delay_s
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except error_types as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Tentative {attempt + 1}/{max_attempts} "
                            f"échouée pour {func.__name__}: {str(e)}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"Échec après {max_attempts} tentatives "
                            f"pour {func.__name__}: {str(e)}"
                        )
            
            if last_error:
                raise last_error
                
        return wrapper
    return decorator

def safe_call(
    func: Callable,
    *args: Any,
    default: Any = None,
    log_errors: bool = True,
    **kwargs: Any
) -> Any:
    """
    Exécute une fonction de manière sécurisée.
    
    Args:
        func: Fonction à exécuter
        *args: Arguments positionnels
        default: Valeur par défaut si erreur
        log_errors: Si True, log les erreurs
        **kwargs: Arguments nommés
        
    Returns:
        Résultat ou valeur par défaut
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Erreur dans {func.__name__}: {str(e)}")
        return default

def cleanup_on_error(cleanup_func: Callable) -> Callable:
    """
    Décorateur exécutant une fonction de nettoyage en cas d'erreur.
    
    Args:
        cleanup_func: Fonction de nettoyage
        
    Returns:
        Fonction décorée
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.info(f"Exécution nettoyage après erreur dans {func.__name__}")
                cleanup_func()
                raise
        return wrapper
    return decorator
