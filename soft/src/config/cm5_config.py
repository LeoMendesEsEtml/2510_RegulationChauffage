"""
Configuration materielle du CM5
- Configuration des canaux ADC
- Configuration SPI (MUX et ADC)
- Configuration GPIO
"""
import spidev
import logging
from typing import Dict, List
from config.pins_cm5 import PINS
from hw.gpio_cm5 import GPIO

logger = logging.getLogger(__name__)

# Configuration SPI pour chaque peripherique
SPI_CONFIG = {
    "mux": {
        "bus": 0,
        "device": 0,
        "max_hz": 100_000,
        "mode": 0,
        "bits": 8
    },
    "adc": {
        "bus": 1,
        "device": 0,
        "max_hz": 100_000,
        "mode": 1,
        "bits": 8
    }
}

# Configuration des canaux ADC (pins physiques)
ADC_CHANNELS = [
    {"name": "CH1", "idac_pin": "AIN0",  "adc_pos": "AIN1",  "adc_neg": "AIN2"},
    {"name": "CH2", "idac_pin": "AIN3",  "adc_pos": "AIN4",  "adc_neg": "AIN5"},
    {"name": "CH3", "idac_pin": "AIN6",  "adc_pos": "AIN7",  "adc_neg": "AIN8"},
    {"name": "CH4", "idac_pin": "AIN9",  "adc_pos": "AIN10", "adc_neg": "AIN11"},
]

def _validate_channel_config(channels: List[Dict]) -> None:
    """Valide la configuration des canaux ADC"""
    pins_used = set()
    for ch in channels:
    # Verifie que tous les champs requis sont presents
        required_fields = {"name", "idac_pin", "adc_pos", "adc_neg"}
        missing = required_fields - set(ch.keys())
        if missing:
            raise ValueError(f"Champs manquants pour le canal {ch.get('name', '?')}: {missing}")

    # Verifie que les pins ne sont pas dupliquees
        current_pins = {ch["idac_pin"], ch["adc_pos"], ch["adc_neg"]}
        duplicates = current_pins & pins_used
        if duplicates:
            raise ValueError(f"Pins dupliqu�es dans le canal {ch['name']}: {duplicates}")
        pins_used.update(current_pins)

def _open_spi(config: Dict) -> spidev.SpiDev:
    """Initialise et configure une interface SPI"""
    try:
        spi = spidev.SpiDev()
        spi.open(config["bus"], config["device"])
        spi.max_speed_hz = config["max_hz"]
        spi.mode = config["mode"]
        spi.bits_per_word = config["bits"]
        return spi
    except Exception as e:
        logger.error(f"Erreur configuration SPI: {str(e)}")
        raise

def _setup_gpio() -> None:
    """Configure les broches GPIO"""
    try:
        GPIO.setmode(GPIO.BCM)

    # Broches de controle ADC
        for k in ["CS_ADC", "ADC_START_SYNC", "ADC_A0", "ADC_A1"]:
            GPIO.setup(PINS[k], GPIO.OUT, initial=GPIO.HIGH)

    # DRDY avec pull-up
        GPIO.setup(PINS["ADC_DRDY"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Chip-selects du multiplexeur
        for cs in PINS["mux_cs_list"]:
            GPIO.setup(cs, GPIO.OUT, initial=GPIO.HIGH)

    except Exception as e:
        logger.error(f"Erreur configuration GPIO: {str(e)}")
        raise

def build_hw() -> Dict:
    """
    Initialise le mat�riel (SPI et GPIO)
    Returns:
        Dict contenant les objets SPI et les broches configur�es
    """
    try:
    # Validation de la configuration
        _validate_channel_config(ADC_CHANNELS)

    # Configuration GPIO
        _setup_gpio()

    # Configuration SPI
        spi_mux = _open_spi(SPI_CONFIG["mux"])
        spi_adc = _open_spi(SPI_CONFIG["adc"])

        logger.info("Initialisation mat�rielle r�ussie")
        return {
            "spi_mux": spi_mux,
            "spi_adc": spi_adc,
            "pins": PINS,
        }

    except Exception as e:
        logger.error(f"Erreur initialisation mat�rielle: {str(e)}")
    # Nettoyage en cas d'erreur
        GPIO.cleanup()
        raise
