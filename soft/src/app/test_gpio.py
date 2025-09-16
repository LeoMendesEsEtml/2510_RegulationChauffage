# -*- coding: utf-8 -*-
# Programme de test des GPIO individuels
from periphery import GPIO
from pins_cm5 import GPIO_CHIP_PATH, FRONT_LED, CMD_RELAY, ADC_DRDY
import time

def test_gpio(gpio_num, name, direction="out"):
    print(f"\nTest du GPIO {gpio_num} ({name}):")
    try:
        gpio = GPIO(GPIO_CHIP_PATH, gpio_num, direction)
        print("- Ouverture OK")
        
        if direction == "out":
            print("- Test écriture HIGH")
            gpio.write(True)
            time.sleep(1)
            print("- Test écriture LOW")
            gpio.write(False)
        else:
            val = gpio.read()
            print(f"- Valeur lue: {val}")
            
        gpio.close()
        print("- Fermeture OK")
        return True
    except Exception as e:
        print(f"ERREUR: {str(e)}")
        return False

if __name__ == "__main__":
    print("Test des GPIO:")
    test_gpio(FRONT_LED, "LED façade")
    test_gpio(CMD_RELAY, "Relai commande")
    test_gpio(ADC_DRDY, "ADC DRDY", "in")