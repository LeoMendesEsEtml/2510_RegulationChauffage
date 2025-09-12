# -*- coding: utf-8 -*-
"""
soft/test_io/test_io_spi.py

CM5 bring-up:
- GPIO test (simple outputs) via GPIO chardev (/dev/gpiochipX), not sysfs
- ADG731 MUX bit-bang on MOSI/SCLK
- ADS124S0x ADC on SPI1 mode 1 (read ID register)

User constraints:
- Code in English, comments in French
- No ternary operators
- Explicit operations (no +=, -=, etc.)
"""

import time
from periphery import GPIO, SPI
from periphery.gpio import GPIOError


# =========================
# Hardware configuration
# =========================

# Liste des GPIO à tester en sortie simple
GPIO_PINS = [2, 3, 4, 9, 10, 11, 17, 18, 22, 23, 24, 25, 27]

# MUX ADG731 : SYNC par carte (actif bas), horloge et donnée en bit-bang
MUX_CS_PINS = [8, 7, 3, 2]   # MUX_CS_1..4 (GPIO8, GPIO7, GPIO3, GPIO2)
MUX_SCLK_PIN = 11            # SCLK bit-bang (GPIO11) ; si SPI0 actif, la ligne peut être occupée
MUX_MOSI_PIN = 10            # MOSI bit-bang (GPIO10) ; si SPI0 actif, la ligne peut être occupée
BITBANG_HALF_PERIOD_US = 2   # demi-période ~2 us -> ~250 kHz

# ADC ADS124S0x sur SPI1 CE0
ADC_SPI_DEV = "/dev/spidev1.0"
ADC_SPI_MODE = 1             # CPOL=0, CPHA=1
ADC_SPI_SPEED_HZ = 1000000   # 1 MHz

# Candidats gpiochip (RPi OS Bookworm / CM5)
GPIO_CHIP_CANDIDATES = [
    "/dev/gpiochip0",
    "/dev/gpiochip1",
    "/dev/gpiochip2",
    "/dev/gpiochip3",
    "/dev/gpiochip4",
    "/dev/gpiochip5",
    "/dev/gpiochip6",
    "/dev/gpiochip7",
    "/dev/gpiochip8",
    "/dev/gpiochip9",
]


# =========================
# GPIO chardev helpers
# =========================

class GpioLine:
    """
    Enveloppe simple d'une ligne GPIO ouverte via chardev.
    Ne passe pas d'argument 'initial' au constructeur periphery (non disponible selon versions).
    Régle l'état initial après ouverture si demandé.
    """
    def __init__(self, chip_path, line, direction, want_initial=None):
        self.gpio = GPIO(chip_path, line, direction)
        if want_initial is not None:
            # Mise à l'état initial explicitement après ouverture
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
    Essaie d'ouvrir la ligne 'line' sur /dev/gpiochipX.
    Régle l'état initial après ouverture si 'want_initial' est fourni.
    Retourne un objet GpioLine en cas de succès, sinon lève RuntimeError.
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
        self.cs_gpios = []
        i = 0
        while i < len(cs_pins):
            g = open_gpio_on_any_chip(cs_pins[i], "out", want_initial=True)  # SYNC inactif (haut)
            self.cs_gpios.append(g)
            i = i + 1

    def close(self):
        i = 0
        while i < len(self.cs_gpios):
            try:
                self.cs_gpios[i].write(True)
            except Exception:
                pass
            self.cs_gpios[i].close()
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
        print("Hint: if SPI0 is enabled, GPIO10/11 may be busy. Disable SPI0 or choose free pins for bit-bang.")
    finally:
        if mux is not None:
            mux.close()
    print("MUX test done.\n")


def test_spi_adc():
    print("=== ADC SPI test (ADS124S0x) ===")
    spi = None
    try:
        spi = SPI(ADC_SPI_DEV, ADC_SPI_MODE, ADC_SPI_SPEED_HZ)

        # Lecture registre 0x00 (ID) :
        # RREG | addr, count-1, dummy
        tx = [0x20 | 0x00, 0x00, 0x00]
        rx = spi.transfer(tx)

        print("ADC RREG ID raw:", rx)
        if len(rx) >= 3:
            print("ADC ID =", "0x%02X" % rx[2])
        else:
            print("Unexpected ADC response length:", len(rx))
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
