# -*- coding: utf-8 -*-
"""
Programme de mise en service complet pour CM5 :
- Test GPIO (configuration, lecture, écriture)
- Test SPI (communication avec MUX et ADC, lecture registre ID).
"""


import time
import spidev
# Utilisation du mockio pour GPIO
from mockio import MOCK_PINS, get_pin_info

class MockGPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    IN = 'IN'
    LOW = 0
    HIGH = 1
    _pin_states = {}

    @staticmethod
    def setmode(mode):
        print(f"MockGPIO: setmode({mode})")

    @staticmethod
    def setwarnings(flag):
        print(f"MockGPIO: setwarnings({flag})")

    @staticmethod
    def setup(pin, mode, initial=None):
        MockGPIO._pin_states[pin] = initial if initial is not None else MockGPIO.LOW
        print(f"MockGPIO: setup(pin={pin}, mode={mode}, initial={initial})")

    @staticmethod
    def output(pin, value):
        MockGPIO._pin_states[pin] = value
        print(f"MockGPIO: output(pin={pin}, value={value})")

    @staticmethod
    def input(pin):
        val = MockGPIO._pin_states.get(pin, MockGPIO.LOW)
        print(f"MockGPIO: input(pin={pin}) -> {val}")
        return val

    @staticmethod
    def cleanup():
        MockGPIO._pin_states.clear()
        print("MockGPIO: cleanup()")

GPIO = MockGPIO

def test_gpio():
    print("=== Test GPIO ===")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # Test configuration et écriture
    for pin in GPIO_PINS:
        pin_info = get_pin_info(f"GPIO_{pin}")
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)
        val = GPIO.input(pin)
        print(f"GPIO {pin} set HIGH, read: {val} | info: {pin_info}")
        GPIO.output(pin, GPIO.LOW)
        val = GPIO.input(pin)
        print(f"GPIO {pin} set LOW, read: {val} | info: {pin_info}")
    GPIO.cleanup()
    print("GPIO test terminé.\n")

def test_spi(bus=0, device=0, cs_pin=None, test_name="SPI"):
    import logging
    print(f"=== Test {test_name} ===")
    logger = logging.getLogger("SPI-Test")
    spi = spidev.SpiDev()
    try:
        spi.open(bus, device)
        spi.max_speed_hz = 1000000
        spi.mode = 0b01
        spi.bits_per_word = 8
        if test_name == "ADC":
            cmd = [0x20, 0x00]
            resp = spi.xfer2(cmd + [0x00])
            logger.info(f"ADC ID register response: {resp}")
        elif test_name == "MUX":
            cmd = [0x01]
            resp = spi.xfer2(cmd)
            logger.info(f"MUX SPI response: {resp}")
        else:
            resp = spi.xfer2([0xAA, 0x55])
            logger.info(f"SPI generic response: {resp}")
        if cs_pin is not None:
            GPIO.output(cs_pin, GPIO.HIGH)
    except Exception as e:
        logger.error(f"Erreur SPI {test_name}: {e}")
    finally:
        if cs_pin is not None:
            GPIO.output(cs_pin, GPIO.HIGH)
        spi.close()
    print(f"{test_name} test terminé.\n")

def main():
    test_gpio()
    test_spi(bus=0, device=0, cs_pin=MUX_CS_PIN, test_name="MUX")
    test_spi(bus=1, device=0, cs_pin=ADC_CS_PIN, test_name="ADC")

if __name__ == "__main__":
    main()
