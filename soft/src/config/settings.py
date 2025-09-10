# -*- coding: utf-8 -*-
"""
Configuration globale et constantes du systeme.
"""

from typing import Dict, Any
import json
from pathlib import Path
import logging
from utils.logging_config import setup_module_logger

# Logger
logger = setup_module_logger(__name__)

# Chemins
CONFIG_DIR = Path("config")
DATA_DIR = Path("data")
LOG_DIR = Path("logs")

# Parametres ADC
ADC_SETTINGS = {
    "spi_bus": 0,
    "spi_device": 0,
    "spi_speed_hz": 1_000_000,
    "vref": 2.5,  # Tension de reference en Volts
    "gain": 1,    # Gain par defaut
}

# Parametres MUX
MUX_SETTINGS = {
    "spi_bus": 0,
    "spi_device": 1,
    "channel_count": 32,
    "switch_delay_ms": 1
}

# Parametres de regulation
CONTROL_SETTINGS = {
    "sample_period_s": 1.0,    # Periode d'echantillonnage
    "filter_window": 5,        # Taille fenetre filtre
    "control_period_s": 5.0,   # Periode de regulation
    "deadband_c": 0.5,        # Bande morte en C
    "pid": {
        "kp": 1.0,  # Gain proportionnel
        "ki": 0.1,  # Gain integral
        "kd": 0.0   # Gain derive
    }
}

# Parametres capteurs
SENSOR_SETTINGS = {
    "ptc": {
        "r0": 1000.0,    # Resistance a 0C
        "a": 0.00385,    # Coefficient de temperature
        "min_temp": -50,
        "max_temp": 150
    },
    "ntc": {
        "r25": 10000.0,  # Resistance a 25C
        "beta": 3950,    # Coefficient beta
        "min_temp": -40,
        "max_temp": 125
    }
}

class Settings:
    """
    Gestionnaire de configuration.
    
    Charge/sauvegarde la configuration depuis/vers un fichier JSON.
    Permet la modification dynamique des parametres.
    """
    
    def __init__(self, config_file: str = "settings.json"):
        """
        Initialise les parametres avec les valeurs par defaut.
        
        Args:
            config_file: Nom du fichier de configuration
        """
        self.config_file = CONFIG_DIR / config_file
        
        # Valeurs par defaut
        self._settings = {
            "adc": ADC_SETTINGS,
            "mux": MUX_SETTINGS,
            "control": CONTROL_SETTINGS,
            "sensors": SENSOR_SETTINGS
        }
        
        # Charge la configuration si elle existe
        self.load()
        
    def load(self) -> None:
        """
        Charge la configuration depuis le fichier.
        Utilise les valeurs par defaut si le fichier n'existe pas.
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    # Mise a jour recursive
                    self._update_recursive(self._settings, loaded)
                logger.info(f"Configuration chargee: {self.config_file}")
        except Exception as e:
            logger.error(f"Erreur chargement config: {str(e)}")
            
    def save(self) -> None:
        """
        Sauvegarde la configuration dans le fichier.
        Cree les repertoires si necessaire.
        """
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._settings, f, indent=4)
            logger.info(f"Configuration sauvegardee: {self.config_file}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config: {str(e)}")
            
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Retourne une valeur de configuration.
        
        Args:
            section: Section de configuration
            key: Cle du parametre
            default: Valeur par defaut
            
        Returns:
            Valeur du parametre ou default
        """
        try:
            return self._settings[section][key]
        except KeyError:
            return default
            
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Modifie une valeur de configuration.
        
        Args:
            section: Section de configuration
            key: Cle du parametre
            value: Nouvelle valeur
        """
        if section not in self._settings:
            self._settings[section] = {}
        self._settings[section][key] = value
        
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Retourne une section complete.
        
        Args:
            section: Nom de la section
            
        Returns:
            Dictionnaire de la section
        """
        return self._settings.get(section, {})
        
    @staticmethod
    def _update_recursive(target: Dict, source: Dict) -> None:
        """
        Met a jour un dictionnaire de maniere recursive.
        
        Args:
            target: Dictionnaire cible
            source: Dictionnaire source
        """
        for key, value in source.items():
            if isinstance(value, dict):
                target.setdefault(key, {})
                Settings._update_recursive(target[key], value)
            else:
                target[key] = value

# Instance globale des parametres
settings = Settings()
