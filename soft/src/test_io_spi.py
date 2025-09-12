# -*- coding: utf-8 -*-
"""
Programme de mise en service complet pour CM5 :
- Test GPIO (configuration, lecture, écriture)
- Test SPI (communication avec MUX et ADC, lecture registre ID).
"""

import time
import spidev
import RPi.GPIO as GPIO

# Définition des broches CM5
GPIO_PINS = [2, 3, 4, 9, 10, 11, 17, 18, 22, 23, 24, 25, 27]
MUX_CS_PIN = 7
ADC_CS_PIN = 8

def test_gpio():
    print("=== Test GPIO ===")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # Test configuration et écriture
    for pin in GPIO_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.05)
        val = GPIO.input(pin)
        print(f"GPIO {pin} set HIGH, read: {val}")
        GPIO.output(pin, GPIO.LOW)
        val = GPIO.input(pin)
        print(f"GPIO {pin} set LOW, read: {val}")
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
