import RPi.GPIO as GPIO

# Constantes pour utiliser la même API que dans le reste du code
BCM = GPIO.BCM
OUT = GPIO.OUT
IN = GPIO.IN
HIGH = GPIO.HIGH
LOW = GPIO.LOW
PUD_UP = GPIO.PUD_UP
PUD_DOWN = GPIO.PUD_DOWN

# Initialisation
def setmode(mode):
    GPIO.setmode(mode)

def setwarnings(flag):
    GPIO.setwarnings(flag)

def setup(pin, direction, initial=None, pull_up_down=None):
    if initial is not None and pull_up_down is not None:
        GPIO.setup(pin, direction, initial=initial, pull_up_down=pull_up_down)
    elif initial is not None:
        GPIO.setup(pin, direction, initial=initial)
    elif pull_up_down is not None:
        GPIO.setup(pin, direction, pull_up_down=pull_up_down)
    else:
        GPIO.setup(pin, direction)

def output(pin, value):
    GPIO.output(pin, value)

def input(pin):
    return GPIO.input(pin)

def cleanup(pin=None):
    if pin is None:
        GPIO.cleanup()
    else:
        GPIO.cleanup(pin)
