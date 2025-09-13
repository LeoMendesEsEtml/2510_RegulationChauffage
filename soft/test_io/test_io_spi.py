# -*- coding: utf-8 -*-

"""
soft/test_io/test_io_spi.py

Goal:
- Use SPI0 hardware for ADG731 MUX (CS on spidev0.0 and spidev0.1 today)
- Use SPI1 hardware for ADS124S0x ADC (spidev1.0, mode 1)

Precondition (config.txt):
    [all]
    dtparam=i2c_arm=on
    dtparam=spi=on
    dtoverlay=spi1-1cs
"""

import os
import time
import spidev
from periphery import GPIO

# =========================
# ADG731 (MUX) over SPI0
# =========================

def adg731_ctrl_byte(address, enable=True):
    # ADG731 control word (DB7..DB0): EN, CS, X, A3, A2, A1, A0, A4
    if not 0 <= address <= 31:
        raise ValueError("address out of range")
    en = 0 if enable else 1       # EN est actif bas : 0 = enable, 1 = tout OFF
    cs = 0                        # doit rester 0 pour écrire (bit de "bank" réservé aux variantes)
    
    # The MSB of address (bit 4) needs to go to LSB of ctrl byte
    a4 = (address >> 4) & 0x1     # Extract MSB (bit 4) of address
    
    # Extract lower 4 bits (A3-A0) of address
    a0_3 = address & 0xF          # Extract bits 3-0 of address
    
    # Build control byte with correct bit positions:
    # [7]   [6]  [5] [4] [3] [2] [1]  [0]
    # EN    CS   X   A3  A2  A1  A0   A4
    ctrl = ((en & 0x1) << 7) | ((cs & 0x1) << 6) | (0 << 5) | ((a0_3 & 0xF) << 1) | (a4 & 0x1)
    
    return ctrl


# =========================
# ADG731 (MUX) over SPI0
# =========================

import os
import spidev
import time

# =========================
# ADG731 (MUX) over SPI0
# =========================

def adg731_ctrl_byte(address, enable=True):
    """
    Construit l’octet de commande pour l’ADG731.

    Registre série 8 bits (DB7 -> DB0), d’après le datasheet :
      DB7 = EN (actif bas : 0 = enable, 1 = all OFF)
      DB6 = CS (laisser 0)
      DB5 = X  (laisser 0)
      DB4 = A4
      DB3 = A3
      DB2 = A2
      DB1 = A1
      DB0 = A0

    => Les 5 bits d’adresse A4..A0 occupent directement DB4..DB0.
    Données validées au front descendant de SCLK => SPI mode 1.
    """
    if not 0 <= address <= 31:
        raise ValueError("address out of range (0..31)")

    en = 0 if enable else 1
    ctrl = (en << 7) | (address & 0x1F)   # EN sur DB7, A4..A0 sur DB4..DB0
    return ctrl


class Adg731MuxSpi:
    """
    Board -> SPI0 CS mapping:
      0 -> /dev/spidev0.0
      1 -> /dev/spidev0.1
      2 -> /dev/spidev0.2  [requires overlay]
      3 -> /dev/spidev0.3  [requires overlay]

    Paramètres SPI (configurés une fois à l’ouverture) :
      - mode = 1  (CPOL=0, CPHA=1) données échantillonnées sur front descendant
      - bits_per_word = 8
      - lsbfirst = False (MSB d’abord)
      - cshigh   = False (CS actif bas)
      - no_cs    = False (utiliser CS matériel)
    """
    DEV = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev0.2", "/dev/spidev0.3"]

    def __init__(self, speed_hz=100000):
        self.speed = speed_hz
        self.handles = []
        for i in range(4):
            path = self.DEV[i]
            if os.path.exists(path):
                s = spidev.SpiDev()
                s.open(0, i)                 # bus 0, device i
                s.mode = 1                   # CPOL=0, CPHA=1
                s.max_speed_hz = self.speed
                s.bits_per_word = 8
                try: s.lsbfirst = False
                except Exception: pass
                try: s.cshigh = False
                except Exception: pass
                try: s.no_cs = False
                except Exception: pass
                try: s.threewire = False
                except Exception: pass
                self.handles.append(s)
            else:
                self.handles.append(None)

    def close(self):
        for h in self.handles:
            if h is not None:
                try: h.close()
                except Exception: pass

    def set_channel(self, board_index, address):
        """
        Envoie exactement 1 octet (8 fronts) sous CS bas, puis relâche CS.
        Ne touche pas aux paramètres SPI ici.
        """
        if not 0 <= board_index <= 3:
            raise ValueError("board_index out of range (0..3)")
        h = self.handles[board_index]
        if h is None:
            print("skip board", board_index, "(", self.DEV[board_index], "missing )")
            return
        ctrl = adg731_ctrl_byte(address, enable=True)
        # Optionnel: debug
        # print(f"ADG731: board={board_index}, chan={address}, ctrl=0x{ctrl:02X} ({ctrl:08b})")
        h.xfer2([ctrl])   # une seule trame
        return ctrl


def test_spi_mux_hw():
    mux = Adg731MuxSpi(100000)
    try:
        # Active le relais (GPIOCON 0xFF) via SPI1 (ADC)
        spi_relay = spidev.SpiDev()
        spi_relay.open(1, 0)
        spi_relay.mode = 1
        spi_relay.max_speed_hz = 100000
        spi_relay.bits_per_word = 8
        spi_relay.xfer2([0x64, 0x00, 0xFF])  # WREG 0x11, 1 byte, data=0xFF
        print("Relais activé (GPIOCON = 0xFF)")
        spi_relay.close()

        mux.set_channel(0, 0)
        print("MUX: board 0, channel min (0)")
        time.sleep(2)

        mux.set_channel(0, 31)
        print("MUX: board 0, channel max (31)")
        time.sleep(2)
    finally:
        mux.close()

# =========================
# ADS124S0x (ADC) over SPI1
# =========================

def adc_read_id_once(spi):
    # RREG 0x00, 1 byte -> [0x20|0x00, 0x00] puis 1 octet clocké
    rx = spi.xfer2([0x20, 0x00, 0x00])
    if len(rx) >= 3:
        return rx[2]
    return None

def test_spi_adc():
    print("=== ADC SPI test (ADS124S0x @ SPI1) ===")
    spi = None
    try:
        if os.path.exists("/dev/spidev1.0") is False:
            print("FATAL: /dev/spidev1.0 missing. Enable dtoverlay=spi1-1cs.")
            return

        spi = spidev.SpiDev()
        spi.open(1, 0)            # SPI1 CE0 = GPIO18
        spi.mode = 1              # ADC requires mode 1 (CPOL=0, CPHA=1)
        spi.max_speed_hz = 100000
        spi.bits_per_word = 8

        print("ADC: lecture des registres clés en boucle (Ctrl+C pour arrêter)")
        try:
            while True:
                # ID (0x00)
                rx_id = spi.xfer2([0x20, 0x00, 0x00])
                # STATUS (0x01)
                rx_status = spi.xfer2([0x21, 0x00, 0x00])
                # DATARATE (0x04)
                rx_datarate = spi.xfer2([0x24, 0x00, 0x00])
                # REF (0x05)
                rx_ref = spi.xfer2([0x25, 0x00, 0x00])
                # IDACMUX (0x07)
                rx_idacmux = spi.xfer2([0x27, 0x00, 0x00])
                # FSCAL2 (0x0F)
                rx_fscal2 = spi.xfer2([0x2F, 0x00, 0x00])
                # GPIODAT (0x10)
                rx_gpiodat = spi.xfer2([0x30, 0x00, 0x00])
                # GPIOCON (0x11)
                rx_gpiocon = spi.xfer2([0x31, 0x00, 0x00])

                print(f"ADC ID        (0x00) = 0x{rx_id[2]:02X} (attendu ?)" if len(rx_id)>=3 else f"ADC ID: réponse invalide {rx_id}")
                print(f"ADC STATUS    (0x01) = 0x{rx_status[2]:02X} (bit7 FL_POR={bool(rx_status[2] & 0x80)})" if len(rx_status)>=3 else f"ADC STATUS: réponse invalide {rx_status}")
                print(f"ADC DATARATE  (0x04) = 0x{rx_datarate[2]:02X} (attendu 0x14)" if len(rx_datarate)>=3 else f"ADC DATARATE: réponse invalide {rx_datarate}")
                print(f"ADC REF       (0x05) = 0x{rx_ref[2]:02X} (attendu 0x10)" if len(rx_ref)>=3 else f"ADC REF: réponse invalide {rx_ref}")
                print(f"ADC IDACMUX   (0x07) = 0x{rx_idacmux[2]:02X} (attendu 0xFF)" if len(rx_idacmux)>=3 else f"ADC IDACMUX: réponse invalide {rx_idacmux}")
                print(f"ADC FSCAL2    (0x0F) = 0x{rx_fscal2[2]:02X} (attendu 0x40)" if len(rx_fscal2)>=3 else f"ADC FSCAL2: réponse invalide {rx_fscal2}")
                print(f"ADC GPIODAT   (0x10) = 0x{rx_gpiodat[2]:02X} (attendu 0x00)" if len(rx_gpiodat)>=3 else f"ADC GPIODAT: réponse invalide {rx_gpiodat}")
                print(f"ADC GPIOCON   (0x11) = 0x{rx_gpiocon[2]:02X} (attendu 0x00)" if len(rx_gpiocon)>=3 else f"ADC GPIOCON: réponse invalide {rx_gpiocon}")
                print("---")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Arrêt ADC demandé par l'utilisateur.")
        finally:
            spi.close()
    except Exception as e:
        print("ADC SPI error:", str(e))

# =========================
# Main
# =========================

def main():
    print("=== Activation du relais physique (CMD_RELAY, GPIO 17) et LED façade (GPIO 27) ===")
    cmd_relay = GPIO("/dev/gpiochip0", 17, "out")
    front_led = GPIO("/dev/gpiochip0", 27, "out")
    cmd_relay.write(True)
    front_led.write(True)
    print("Relais activé (GPIO 17), LED façade allumée (GPIO 27)")

    print("=== Test de tous les canaux MUX (0-31) ===")
    mux = Adg731MuxSpi(100000)
    try:
        for chan in range(32):
            expected_ctrl = adg731_ctrl_byte(chan, enable=True)
            print(f"CHAN {chan:02d} -> ctrl=0x{expected_ctrl:02X} ({expected_ctrl:08b})")
            mux.set_channel(0, chan)
            input("Entrée pour suivant...")
    except KeyboardInterrupt:
        print("Arrêt demandé par l'utilisateur.")
    finally:
        mux.close()
        front_led.write(False)
        cmd_relay.write(False)
        front_led.close()
        cmd_relay.close()
        print("LED façade éteinte, relais désactivé")

if __name__ == "__main__":
    main()
