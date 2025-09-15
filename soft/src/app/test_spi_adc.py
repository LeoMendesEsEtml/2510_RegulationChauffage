# -*- coding: utf-8 -*-
# file: test_spi_adc.py

import time
import os

def test_spi_adc():
    print("=== ADC SPI test (ADS124S0x @ SPI1) ===")
    spi = None
    try:
        spi_path = "/dev/spidev1.0"
        if not os.path.exists(spi_path):
            print("FATAL: " + spi_path + " missing. Vérifiez la configuration SPI.")
            return

        import spidev
        spi = spidev.SpiDev()
        spi.open(1, 0)            # SPI1 CE0
        spi.mode = 1              # Mode 1 (CPOL=0, CPHA=1)
        spi.max_speed_hz = 100000
        spi.bits_per_word = 8

        print("ADC: lecture des registres clés en boucle (Ctrl+C pour arrêter)")
        try:
            while True:
                rx_id = spi.xfer2([0x20, 0x00, 0x00])
                rx_status = spi.xfer2([0x21, 0x00, 0x00])
                rx_datarate = spi.xfer2([0x24, 0x00, 0x00])
                rx_ref = spi.xfer2([0x25, 0x00, 0x00])
                rx_idacmux = spi.xfer2([0x27, 0x00, 0x00])
                rx_fscal2 = spi.xfer2([0x2F, 0x00, 0x00])
                rx_gpiodat = spi.xfer2([0x30, 0x00, 0x00])
                rx_gpiocon = spi.xfer2([0x31, 0x00, 0x00])

                if len(rx_id) >= 3:
                    print("ADC ID        0x00 = 0x" + format(rx_id[2], "02X"))
                else:
                    print("ADC ID: réponse invalide " + str(rx_id))

                if len(rx_status) >= 3:
                    bit7 = (rx_status[2] & 0x80) != 0
                    print("ADC STATUS    0x01 = 0x" + format(rx_status[2], "02X") + "  FL_POR=" + str(bit7))
                else:
                    print("ADC STATUS: réponse invalide " + str(rx_status))

                if len(rx_datarate) >= 3:
                    print("ADC DATARATE  0x04 = 0x" + format(rx_datarate[2], "02X"))
                else:
                    print("ADC DATARATE: réponse invalide " + str(rx_datarate))

                if len(rx_ref) >= 3:
                    print("ADC REF       0x05 = 0x" + format(rx_ref[2], "02X"))
                else:
                    print("ADC REF: réponse invalide " + str(rx_ref))

                if len(rx_idacmux) >= 3:
                    print("ADC IDACMUX   0x07 = 0x" + format(rx_idacmux[2], "02X"))
                else:
                    print("ADC IDACMUX: réponse invalide " + str(rx_idacmux))

                if len(rx_fscal2) >= 3:
                    print("ADC FSCAL2    0x0F = 0x" + format(rx_fscal2[2], "02X"))
                else:
                    print("ADC FSCAL2: réponse invalide " + str(rx_fscal2))

                if len(rx_gpiodat) >= 3:
                    print("ADC GPIODAT   0x10 = 0x" + format(rx_gpiodat[2], "02X"))
                else:
                    print("ADC GPIODAT: réponse invalide " + str(rx_gpiodat))

                if len(rx_gpiocon) >= 3:
                    print("ADC GPIOCON   0x11 = 0x" + format(rx_gpiocon[2], "02X"))
                else:
                    print("ADC GPIOCON: réponse invalide " + str(rx_gpiocon))

                print("---")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Arrêt ADC demandé par l'utilisateur.")
        finally:
            try:
                spi.close()
            except Exception:
                pass
    except Exception as e:
        print("ADC SPI error: " + str(e))
