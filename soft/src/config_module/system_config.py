"""
Configuration globale du systeme de regulation.
Ce module centralise toutes les configurations et assure leur coherence.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import json
import logging
from pathlib import Path
from Metrology_module.exceptions import ConfigError

@dataclass
class ADCConfig:
    """Configuration de l'ADC"""
    spi_speed_hz: int = 1_000_000
    spi_mode: int = 1
    reference_mode: str = "ratiometric_REFP0_REFN0"
    data_rate_sps: float = 20.0
    chop_mode: bool = True

@dataclass
class SensorConfig:
    """Configuration d'un capteur"""
    name: str
    type: str  # "PT1000", "NTC_10k", etc.
    adc_channel: int
    mux_card: int
    mux_channel: int
    filter_window: int = 5
    enabled: bool = True

@dataclass
class RegulationConfig:
    """Configuration de la regulation"""
    sample_interval_s: float = 1.0
    control_interval_s: float = 10.0
    min_temp_c: float = 5.0
    max_temp_c: float = 35.0
    default_setpoint_c: float = 20.0

@dataclass
class LoggingConfig:
    """Configuration du logging"""
    level: str = "INFO"
    file_path: str = "regulation.log"
    max_size_mb: int = 10
    backup_count: int = 5

class SystemConfig:
    def __init__(self, config_path: str = "config.json"):
        """
        Initialise la configuration systeme.
        
        Args:
            config_path: Chemin vers le fichier de configuration JSON
        """
        self.config_path = Path(config_path)
        self.adc = ADCConfig()
        self.sensors: Dict[str, SensorConfig] = {}
        self.regulation = RegulationConfig()
        self.logging = LoggingConfig()
        self.logger = logging.getLogger('config')
        
        # Etat du systeme
        self._is_initialized = False
        self._last_error: Optional[str] = None

    def load(self) -> bool:
        """
        Charge la configuration depuis le fichier JSON.
        
        Returns:
            bool: True si le chargement reussit
        """
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Fichier de configuration non trouve: {self.config_path}")
                self._save_default_config()
                return True

            with open(self.config_path, 'r') as f:
                data = json.load(f)

            # Charge la configuration ADC
            adc_data = data.get('adc', {})
            self.adc = ADCConfig(**adc_data)

            # Charge la configuration des capteurs
            sensors_data = data.get('sensors', {})
            self.sensors.clear()
            for sensor_name, sensor_data in sensors_data.items():
                self.sensors[sensor_name] = SensorConfig(name=sensor_name, **sensor_data)

            # Charge la configuration de regulation
            reg_data = data.get('regulation', {})
            self.regulation = RegulationConfig(**reg_data)

            # Charge la configuration de logging
            log_data = data.get('logging', {})
            self.logging = LoggingConfig(**log_data)

            self._is_initialized = True
            self._last_error = None
            return True

        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Erreur de chargement de la configuration: {e}")
            return False

    def save(self) -> bool:
        """
        Sauvegarde la configuration dans le fichier JSON.
        
        Returns:
            bool: True si la sauvegarde reussit
        """
        try:
            config_data = {
                'adc': {
                    'spi_speed_hz': self.adc.spi_speed_hz,
                    'spi_mode': self.adc.spi_mode,
                    'reference_mode': self.adc.reference_mode,
                    'data_rate_sps': self.adc.data_rate_sps,
                    'chop_mode': self.adc.chop_mode
                },
                'sensors': {
                    name: {
                        'type': sensor.type,
                        'adc_channel': sensor.adc_channel,
                        'mux_card': sensor.mux_card,
                        'mux_channel': sensor.mux_channel,
                        'filter_window': sensor.filter_window,
                        'enabled': sensor.enabled
                    }
                    for name, sensor in self.sensors.items()
                },
                'regulation': {
                    'sample_interval_s': self.regulation.sample_interval_s,
                    'control_interval_s': self.regulation.control_interval_s,
                    'min_temp_c': self.regulation.min_temp_c,
                    'max_temp_c': self.regulation.max_temp_c,
                    'default_setpoint_c': self.regulation.default_setpoint_c
                },
                'logging': {
                    'level': self.logging.level,
                    'file_path': self.logging.file_path,
                    'max_size_mb': self.logging.max_size_mb,
                    'backup_count': self.logging.backup_count
                }
            }

            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            return True

        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Erreur de sauvegarde de la configuration: {e}")
            return False

    def validate(self) -> List[str]:
        """
        Valide la configuration actuelle.
        
        Returns:
            List[str]: Liste des erreurs trouvees (vide si tout est OK)
        """
        errors = []

        # Validation ADC
        if not 100_000 <= self.adc.spi_speed_hz <= 50_000_000:
            errors.append(f"Vitesse SPI invalide: {self.adc.spi_speed_hz} Hz")
        if self.adc.spi_mode not in [0, 1, 2, 3]:
            errors.append(f"Mode SPI invalide: {self.adc.spi_mode}")

        # Validation capteurs
        for name, sensor in self.sensors.items():
            if sensor.adc_channel < 0 or sensor.adc_channel > 7:
                errors.append(f"Canal ADC invalide pour {name}: {sensor.adc_channel}")
            if sensor.mux_channel < 0 or sensor.mux_channel > 31:
                errors.append(f"Canal MUX invalide pour {name}: {sensor.mux_channel}")
            if sensor.filter_window < 1 or sensor.filter_window > 50:
                errors.append(f"Fenetre de filtrage invalide pour {name}: {sensor.filter_window}")

        # Validation regulation
        if self.regulation.sample_interval_s <= 0:
            errors.append(f"Intervalle d'echantillonnage invalide: {self.regulation.sample_interval_s}")
        if self.regulation.control_interval_s <= 0:
            errors.append(f"Intervalle de controle invalide: {self.regulation.control_interval_s}")
        if self.regulation.min_temp_c >= self.regulation.max_temp_c:
            errors.append(f"Plage de temperature invalide: {self.regulation.min_temp_c}..{self.regulation.max_temp_c}")

        return errors

    def _save_default_config(self) -> None:
        """Sauvegarde une configuration par defaut."""
        self.save()
        self.logger.info("Configuration par defaut creee")

    @property
    def last_error(self) -> Optional[str]:
        """Retourne la derniere erreur survenue."""
        return self._last_error
