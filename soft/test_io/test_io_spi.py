# -*- coding: utf-8 -*-
"""
Programme de mise en service complet pour CM5 :
- Test GPIO (configuration, lecture, écriture)
- Test SPI (communication avec MUX et ADC, lecture registre ID).
"""


import time
from periphery import GPIO, SPI

# Pinout défini
GPIO_PINS = [2, 3, 4, 9, 10, 11, 17, 18, 22, 23, 24, 25, 27]
MUX_CS_PINS = [8, 7, 3, 2]  # MUX_CS_1 à MUX_CS_4
ADC_CS_PIN = 18

def test_gpio():
    print("=== Test GPIO ===")
    # Test configuration et écriture
    for pin in GPIO_PINS:
        gpio = GPIO(pin, "out")
        gpio.write(True)
        time.sleep(0.05)
        val = gpio.read()
        print(f"GPIO {pin} set HIGH, read: {val}")
        gpio.write(False)
        val = gpio.read()
        print(f"GPIO {pin} set LOW, read: {val}")
        gpio.close()
    print("GPIO test terminé.\n")

def test_spi_mux():
    print("=== Test SPI MUX ===")
    spi = SPI("/dev/spidev0.0", 0, 1000000)
    for idx, cs_pin in enumerate(MUX_CS_PINS, 1):
        cs_gpio = GPIO(cs_pin, "out")
        cs_gpio.write(False)  # Chip select active
        try:
            for channel in range(4):  # Teste les 4 premiers canaux
                cmd = [channel]
                resp = spi.transfer(cmd)
                print(f"MUX_CS_{idx} (GPIO {cs_pin}) channel {channel} response: {resp}")
        except Exception as e:
            print(f"Erreur SPI MUX_CS_{idx}: {e}")
        finally:
            cs_gpio.write(True)  # Chip select inactive
            cs_gpio.close()
    spi.close()
    print("SPI MUX test terminé.\n")

def test_spi_adc():
    print("=== Test SPI ADC ===")
    spi = SPI("/dev/spidev1.0", 0, 1000000)
    cs_gpio = GPIO(ADC_CS_PIN, "out")
    cs_gpio.write(False)  # Chip select active
    try:
        cmd = [0x20, 0x00, 0x00]  # RREG, adresse 0x00, 1 byte à lire
        resp = spi.transfer(cmd)
        print(f"ADC_CS (GPIO {ADC_CS_PIN}) ID register response: {resp}")
    except Exception as e:
        print(f"Erreur SPI ADC_CS: {e}")
    finally:
        cs_gpio.write(True)  # Chip select inactive
        cs_gpio.close()
        spi.close()
    print("SPI ADC test terminé.\n")

def main():
    test_gpio()
    test_spi_mux()
    test_spi_adc()

if __name__ == "__main__":
    main()
