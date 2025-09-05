# Gestion des entrées/sorties pour CM5 régulation chauffage
# Utilise RPi.GPIO ou une bibliothèque compatible (adapter si besoin !)

try:
    import RPi.GPIO as GPIO
except ImportError:
    # Mock GPIO for dev/test
    from unittest import mock
    GPIO = mock.MagicMock()

# Table des signaux et leur GPIO BCM
SIGNALS = {
    "MUX_CS_4": 2,
    "MUX_CS_3": 3,
    "MUX_CS_2": 7,
    "MUX_CS_1": 8,
    "MUX_MOSI": 10,
    "MUX_SCLK": 11,
    "CM_24V_OUT_1": 12,
    "CM_24V_SENSE_1": 13,
    "CM_24V_OUT_2": 14,
    "CM_24V_SENSE_2": 15,
    "CMD_RELAY": 16,
    "CS_ADC": 17,
    "SPI_MISO_ADC": 18,
    "SPI_MOSI_ADC": 19,
    "SPI_SCLK_ADC": 20,
    "ADC_DRDY": 21,
    "ADC_START_SYNC": 22,
    "ADC_A0": 23,
    "ADC_A1": 24,
    "FRONT_LED": 26,
}

# Directions par défaut (à ajuster selon usage réel)
DEFAULT_OUTPUTS = [
    "MUX_CS_4", "MUX_CS_3", "MUX_CS_2", "MUX_CS_1",
    "MUX_MOSI", "MUX_SCLK",
    "CM_24V_OUT_1", "CM_24V_OUT_2",
    "CMD_RELAY",
    "CS_ADC", "SPI_MOSI_ADC", "SPI_SCLK_ADC",
    "ADC_START_SYNC", "ADC_A0", "ADC_A1",
    "FRONT_LED"
]
DEFAULT_INPUTS = [
    "CM_24V_SENSE_1", "CM_24V_SENSE_2",
    "SPI_MISO_ADC", "ADC_DRDY"
]

def setup():
    GPIO.setmode(GPIO.BCM)
    # Sorties
    for name in DEFAULT_OUTPUTS:
        GPIO.setup(SIGNALS[name], GPIO.OUT)
    # Entrées
    for name in DEFAULT_INPUTS:
        GPIO.setup(SIGNALS[name], GPIO.IN)

def set_signal(name, value):
    """Met à jour un signal sortie"""
    GPIO.output(SIGNALS[name], value)

def get_signal(name):
    """Lit un signal entrée (ou sortie si besoin)"""
    return GPIO.input(SIGNALS[name])

def toggle_signal(name):
    """Inverse la sortie (utile pour test, LED, etc)"""
    current = get_signal(name)
    set_signal(name, not current)

def cleanup():
    GPIO.cleanup()

# Exemple d'utilisation
if __name__ == "__main__":
    setup()
    set_signal("FRONT_LED", True)      # Allume la LED
    set_signal("CMD_RELAY", True)      # Active le relais
    print("ADC DRDY =", get_signal("ADC_DRDY"))
    cleanup()


