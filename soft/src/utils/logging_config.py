"""
Configuration du système de logging.
Fournit une configuration centralisée et cohérente des logs.
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime

class LogManager:
    def __init__(self):
        self._initialized = False
        self.root_logger = logging.getLogger()
        self.formatters = {
            'default': logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ),
            'detailed': logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
            )
        }

    def setup_logging(self, 
                     log_file: str = "regulation.log",
                     level: str = "INFO",
                     max_size_mb: int = 10,
                     backup_count: int = 5,
                     console: bool = True) -> None:
        """
        Configure le système de logging.
        
        Args:
            log_file: Chemin du fichier de log
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_size_mb: Taille maximale du fichier en MB
            backup_count: Nombre de fichiers de backup à conserver
            console: Si True, ajoute aussi les logs dans la console
        """
        if self._initialized:
            return

        # Configure le logger racine
        self.root_logger.setLevel(getattr(logging, level.upper()))

        # Crée le dossier des logs si nécessaire
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Handler fichier rotatif
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(self.formatters['detailed'])
        self.root_logger.addHandler(file_handler)

        # Handler console si demandé
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self.formatters['default'])
            self.root_logger.addHandler(console_handler)

        # Capture les exceptions non gérées
        logging.captureWarnings(True)

        self._initialized = True
        self.root_logger.info("Système de logging initialisé")

    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtient un logger nommé avec la configuration standard.
        
        Args:
            name: Nom du logger
            
        Returns:
            logging.Logger: Logger configuré
        """
        return logging.getLogger(name)

    def add_file_handler(self, name: str, file_path: str, 
                        level: str = "INFO") -> None:
        """
        Ajoute un handler de fichier spécifique pour un logger.
        
        Args:
            name: Nom du logger
            file_path: Chemin du fichier de log
            level: Niveau de log pour ce handler
        """
        logger = logging.getLogger(name)
        handler = logging.FileHandler(file_path)
        handler.setLevel(getattr(logging, level.upper()))
        handler.setFormatter(self.formatters['detailed'])
        logger.addHandler(handler)

    def set_level(self, name: str, level: str) -> None:
        """
        Change le niveau de log d'un logger.
        
        Args:
            name: Nom du logger
            level: Nouveau niveau (DEBUG, INFO, etc.)
        """
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))

# Instance globale du gestionnaire de logs
log_manager = LogManager()

def setup_module_logger(module_name: str) -> logging.Logger:
    """
    Configure un logger pour un module.
    
    Args:
        module_name: Nom du module
        
    Returns:
        logging.Logger: Logger configuré
    """
    return log_manager.get_logger(module_name)
