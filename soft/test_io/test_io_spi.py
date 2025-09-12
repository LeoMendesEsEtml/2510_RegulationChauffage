# -*- coding: utf-8 -*-
"""
soft/test_io/test_io_spi.py

CM5 bring-up:
- GPIO test (simple outputs) via GPIO chardev (/dev/gpiochipX), not sysfs
- ADG731 MUX bit-bang on MOSI/SCLK with per-board SYNC pins
- ADS124S0x ADC on SPI1 mode 1 (read ID register with fallback)

User constraints:
- Code in English, comments in French
- No ternary operators
- Explicit operations (no +=, -=, etc.)
"""

import os
import time
from periphery import GPIO, SPI
from periphery.gpio import GPIOError


# =========================
# Hardware configuration
# =========================

# GPIO de test basique (éviter les lignes réservées par SPI/I2C/PWM quand overlays actifs)
# BCM18 est souvent SPI1_CE0: on l'exclut du test simple pour éviter un "busy".
GPIO_PINS = [2, 3, 4, 9, 10, 11, 17, 22, 23, 24, 25, 27]

# MUX ADG731 : SYNC par carte (actif bas), horloge et donnée en bit-bang
# Si SPI0 est actif, GPIO8 peut être occupé par CE0 et refuser l'ouverture en GPIO.
MUX_CS_PINS = [8, 7, 3, 2]      # BCM8, BCM7, BCM3, BCM2 (SYNC par carte)
MUX_SCLK_PIN = 11               # SCLK bit-bang (BCM11) ; si SPI0 actif, la ligne peut être occupée
MUX_MOSI_PIN = 10               # MOSI bit-bang (BCM10) ; si SPI0 actif, la ligne peut être occupée
BITBANG_HALF_PERIOD_US = 2      # demi-période ~2 us -> ~250 kHz

# ADC ADS124S0x sur SPI1 CE0
ADC_SPI_DEV = "/dev/spidev1.0"
ADC_SPI_MODE = 1                # CPOL=0, CPHA=1 (mode 1)
ADC_SPI_SPEED_HZ = 1000000      # 1 MHz

# Sur RPi OS Bookworm/CM5, les gpiochip existants peuvent varier ; filtre ceux qui existent réellement
GPIO_CHIP_CANDIDATES = ["/dev/gpiochip" + str(i) for i in range(0, 12) if os.path.exists("/dev/gpiochip" + str(i))]


# =========================
# GPIO chardev helpers
# =========================

class GpioLine:
    """
    Enveloppe simple d'une ligne GPIO ouverte via chardev.
    Régle l'état initial explicitement après ouverture si demandé.
    """
    def __init__(self, chip_path, line, direction, want_initial=None):
        self.gpio = GPIO(chip_path, line, direction)
        if want_initial is not None:
            self.gpio.write(want_initial)

    def write(self, value):
        self.gpio.write(value)

    def read(self):
        return self.gpio.read()

    def close(self):
        try:
            self.gpio.close()
        except Exception:
            pass


def open_gpio_on_any_chip(line, direction, want_initial=None):
    """
    Essaie d'ouvrir la ligne 'line' sur /dev/gpiochipX existants.
    Retourne un objet GpioLine ouvert ou lève RuntimeError avec la dernière cause pertinente.
    """
    last_err = None
    idx = 0
    while idx < len(GPIO_CHIP_CANDIDATES):
        chip = GPIO_CHIP_CANDIDATES[idx]
        try:
            g = GpioLine(chip, line, direction, want_initial)
            return g
        except GPIOError as e:
            last_err = e
        except OSError as e:
            last_err = e
        idx = idx + 1

    msg = "Cannot open GPIO line " + str(line) + " as " + direction + " on any gpiochip. Last error: " + str(last_err)
    raise RuntimeError(msg)


# =========================
# Minimal bit-bang SPI
# =========================

class BitBangSPI:
    """
    Bit-bang minimal pour générer SCLK et MOSI.
    Hypothèses timing :
      - CPOL = 0 (SCLK au repos à 0)
      - Donnée échantillonnée sur front montant (SCLK↑)
    """
    def __init__(self, sclk_pin, mosi_pin, half_period_us):
        self.sclk = open_gpio_on_any_chip(sclk_pin, "out", want_initial=False)
        self.mosi = open_gpio_on_any_chip(mosi_pin, "out", want_initial=False)
        self.thalf = float(half_period_us) / 1_000_000.0

    def close(self):
        try:
            self.sclk.write(False)
        except Exception:
            pass
        try:
            self.mosi.write(False)
        except Exception:
            pass
        self.sclk.close()
        self.mosi.close()

    def send_byte_msb_first(self, value):
        # Envoi MSB en premier, sans opérateurs abrégés
        bit_index = 7
        while bit_index >= 0:
            bit = (value >> bit_index) & 0x01
            if bit == 1:
                self.mosi.write(True)
            else:
                self.mosi.write(False)

            time.sleep(self.thalf)     # tsetup simple

            self.sclk.write(True)
            time.sleep(self.thalf)

            self.sclk.write(False)
            time.sleep(self.thalf)

            bit_index = bit_index - 1


# =========================
# ADG731 driver (bit-bang)
# =========================

class Adg731Mux:
    """
    Pilote MUX ADG731 en bit-bang.
    SYNC = GPIO par carte (actif bas). MOSI/SCLK via BitBangSPI.

    Format de commande adopté :
      D7 = EN (0 = enable, 1 = disable)
      D6..D2 = A4..A0 (adresse 0..31)
      D1..D0 = 0
      ctrl = (EN << 7) | ((addr & 0x1F) << 2)
    """
    def __init__(self, sclk_pin, mosi_pin, cs_pins, half_period_us=2):
        self.bb = BitBangSPI(sclk_pin, mosi_pin, half_period_us)
        self.cs_gpios = []        # liste d'objets GpioLine ou None si indisponible
        self.cs_state = []        # True = opened, False = skipped
        i = 0
        while i < len(cs_pins):
            pin = cs_pins[i]
            try:
                g = open_gpio_on_any_chip(pin, "out", want_initial=True)  # SYNC inactif (haut)
                self.cs_gpios.append(g)
                self.cs_state.append(True)
            except Exception as e:
                print("MUX SYNC GPIO", pin, "unavailable:", str(e))
                self.cs_gpios.append(None)
                self.cs_state.append(False)
            i = i + 1

    def close(self):
        i = 0
        while i < len(self.cs_gpios):
            g = self.cs_gpios[i]
            if g is not None:
                try:
                    g.write(True)
                except Exception:
                    pass
                g.close()
            i = i + 1
        self.bb.close()

    def _build_ctrl_byte(self, address, enable=True):
        if address < 0:
            raise ValueError("address below 0")
        if address > 31:
            raise ValueError("address above 31")

        addr5 = address & 0x1F

        en_bit = 0
        if enable is True:
            en_bit = 0
        else:
            en_bit = 1

        ctrl = (en_bit << 7) | (addr5 << 2)
        return ctrl

    def set_channel(self, board_index, address):
        if board_index < 0:
            raise ValueError("board_index below 0")
        if board_index >= len(self.cs_gpios):
            raise ValueError("board_index out of range")
        if self.cs_state[board_index] is False:
            print("  skip board", board_index, ": SYNC GPIO not available")
            return

        cs = self.cs_gpios[board_index]

        # SYNC bas
        cs.write(False)

        # Trame 8 bits
        ctrl = self._build_ctrl_byte(address, enable=True)
        self.bb.send_byte_msb_first(ctrl)

        # Validation SYNC haut
        cs.write(True)


# =========================
# Tests
# =========================

def test_gpio():
    print("=== GPIO test ===")
    i = 0
    while i < len(GPIO_PINS):
        pin = GPIO_PINS[i]
        try:
            g = open_gpio_on_any_chip(pin, "out", want_initial=False)
            g.write(True)
            time.sleep(0.02)
            val_high = g.read()
            print("GPIO", pin, "set HIGH, read:", val_high)
            g.write(False)
            time.sleep(0.02)
            val_low = g.read()
            print("GPIO", pin, "set LOW, read:", val_low)
            g.close()
        except Exception as e:
            print("GPIO", pin, "error:", str(e))
        i = i + 1
    print("GPIO test done.\n")


def test_spi_mux():
    print("=== MUX test (bit-bang) ===")
    mux = None
    try:
        mux = Adg731Mux(MUX_SCLK_PIN, MUX_MOSI_PIN, MUX_CS_PINS, half_period_us=BITBANG_HALF_PERIOD_US)

        b = 0
        while b < len(MUX_CS_PINS):
            print("Board", b, "SYNC GPIO", MUX_CS_PINS[b])
            a = 0
            while a < 4:
                try:
                    mux.set_channel(b, a)
                    print("  set channel", a, "OK")
                except Exception as e:
                    print("  set channel", a, "error:", str(e))
                a = a + 1
            b = b + 1
    except Exception as e:
        print("MUX bit-bang init error:", str(e))
        print("Hint: if SPI0 is enabled, GPIO8 and GPIO10/11 may be busy. Disable SPI0 or choose free pins for bit-bang.")
    finally:
        if mux is not None:
            mux.close()
    print("MUX test done.\n")


def adc_read_id_once(spi):
    # Lecture registre 0x00 (ID) :
    # RREG | addr, count-1, dummy
    tx = [0x20 | 0x00, 0x00, 0x00]
    rx = spi.transfer(tx)
    if len(rx) >= 3:
        return rx[2]
    return None


def test_spi_adc():
    print("=== ADC SPI test (ADS124S0x) ===")
    spi = None
    try:
        # Ouvre SPI1, CE0, mode 1, 1 MHz
        spi = SPI("/dev/spidev1.0", 1, 1000000)

        # Attendre la fin du POR interne (~2.2 ms) si démarrage à froid
        time.sleep(0.003)  # 3 ms de marge ; datasheet: ~2.2 ms

        # RESET digital (0x06), puis attendre td(RSSC) ≈ 4096·tCLK ≈ ~1 ms
        spi.transfer([0x06])
        time.sleep(0.002)  # 2 ms de marge

        # Lecture ID (registre 0x00), 1 octet :
        # [RREG|0x00, 0x00] puis 1 octet clocké
        tx = [0x20 | 0x00, 0x00, 0x00]
        rx = spi.transfer(tx)
        if len(rx) >= 3:
            print("ADC RREG ID raw:", rx, " ID=0x%02X" % rx[2])
        else:
            print("Unexpected ADC response length:", len(rx))

        # Optionnel : lire aussi STATUS (0x01) pour vérifier FL_POR/RDY
        tx2 = [0x20 | 0x01, 0x00, 0x00]
        rx2 = spi.transfer(tx2)
        if len(rx2) >= 3:
            print("ADC STATUS(0x01) =", "0x%02X" % rx2[2])
        else:
            print("Unexpected STATUS response length:", len(rx2))

    except Exception as e:
        print("ADC SPI error:", str(e))
    finally:
        if spi is not None:
            try:
                spi.close()
            except Exception:
                pass
    print("ADC SPI test done.\n")



def main():
    test_gpio()
    test_spi_mux()
    test_spi_adc()


if __name__ == "__main__":
    main()
