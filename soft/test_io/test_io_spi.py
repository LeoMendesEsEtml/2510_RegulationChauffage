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

def adg731_ctrl_byte(address, enable=True):
    """
    Construit l’octet de commande pour l’ADG731.

    Format exact du registre à décalage (DB7 -> DB0), d’après le datasheet ADG731 :
      DB7 = EN    (bit d’activation, actif bas : 0 = enable, 1 = all OFF)
      DB6 = CS    (laisser à 0 pour écriture normale)
      DB5 = X     (non utilisé, mettre 0)
      DB4 = A3
      DB3 = A2
      DB2 = A1
      DB1 = A0
      DB0 = A4    (MSB d’adresse au LSB du mot)

    Remarque : l’ordre "A4 au LSB" est volontaire et spécifique à l’ADG731.
    L’octet est échantillonné sur le front descendant de SCLK (SPI mode 1).
    """

    if address < 0 or address > 31:
        raise ValueError("address out of range (0..31)")

    en = 0 if enable else 1
    a0 = (address >> 0) & 0x1
    a1 = (address >> 1) & 0x1
    a2 = (address >> 2) & 0x1
    a3 = (address >> 3) & 0x1
    a4 = (address >> 4) & 0x1

    ctrl = 0
    ctrl = ctrl | (en << 7)   # DB7
    ctrl = ctrl | (0  << 6)   # DB6 = CS (0)
    ctrl = ctrl | (0  << 5)   # DB5 = X  (0)
    ctrl = ctrl | (a3 << 4)   # DB4
    ctrl = ctrl | (a2 << 3)   # DB3
    ctrl = ctrl | (a1 << 2)   # DB2
    ctrl = ctrl | (a0 << 1)   # DB1
    ctrl = ctrl | (a4 << 0)   # DB0

    return ctrl


class Adg731MuxSpi:
    """
    Mapping cartes -> chip-selects SPI0 :
      board 0 -> /dev/spidev0.0  (CS=GPIO8)
      board 1 -> /dev/spidev0.1  (CS=GPIO7)
      board 2 -> /dev/spidev0.2  (CS=GPIO3)  [overlay requis]
      board 3 -> /dev/spidev0.3  (CS=GPIO2)  [overlay requis]

    Paramètres SPI du MUX (à l’ouverture une seule fois) :
      - mode = 1  (CPOL=0, CPHA=1)  données valides sur front descendant
      - bits_per_word = 8
      - lsbfirst = False            MSB d’abord
      - cshigh   = False            CS actif bas
      - no_cs    = False            on utilise le CS matériel
      - vitesse  = fixée à l’ouverture; ne pas la réécrire pendant les transferts
    """

    DEV = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev0.2", "/dev/spidev0.3"]

    def __init__(self, speed_hz=100000):
        self.speed = speed_hz
        self.handles = []
        i = 0
        while i < 4:
            path = self.DEV[i]
            if os.path.exists(path):
                s = spidev.SpiDev()
                s.open(0, i)                 # bus 0, device i
                s.mode = 1                   # CPOL=0, CPHA=1 (ADG731 = falling edge)
                s.max_speed_hz = self.speed  # ex. 100 kHz pour debug; peut monter ensuite
                s.bits_per_word = 8

                # sécurité : certains kernels n’exposent pas ces propriétés -> try/except
                try:
                    s.lsbfirst = False
                except Exception:
                    pass
                try:
                    s.cshigh = False
                except Exception:
                    pass
                try:
                    s.no_cs = False
                except Exception:
                    pass
                try:
                    s.threewire = False
                except Exception:
                    pass

                self.handles.append(s)
                # print(f"SPI0 device {path} ouvert : mode={s.mode}, f={s.max_speed_hz} Hz, 8 bits")
            else:
                self.handles.append(None)
            i = i + 1

    def close(self):
        i = 0
        while i < 4:
            h = self.handles[i]
            if h is not None:
                try:
                    h.close()
                except Exception:
                    pass
            i = i + 1

    def set_channel(self, board_index, address):
        """
        Envoie exactement 1 octet (8 fronts d’horloge) avec CS bas,
        puis relâche CS. Ne change pas le mode ni la vitesse ici.
        """
        if board_index < 0:
            raise ValueError("board_index below 0")
        if board_index > 3:
            raise ValueError("board_index above 3")

        h = self.handles[board_index]
        if h is None:
            print("skip board", board_index, "(", self.DEV[board_index], "missing )")
            return

        ctrl = adg731_ctrl_byte(address, enable=True)

        # debug optionnel
        # print(f"ADG731: board={board_index}, chan={address}, ctrl=0x{ctrl:02X} ({ctrl:08b})")

        # Une seule trame : latch interne après le 8e front descendant
        h.xfer2([ctrl])

        return ctrl


def test_spi_mux_hw():
    mux = Adg731MuxSpi(100000)
    try:
        # Active le relais (GPIOCON 0xFF) via SPI1
        spi_relay = spidev.SpiDev()
        spi_relay.open(1, 0)
        spi_relay.mode = 1
        spi_relay.max_speed_hz = 100000
        spi_relay.bits_per_word = 8
        spi_relay.xfer2([0x64, 0x00, 0xFF])  # WREG 0x11, 1 byte, data=0xFF
        print("Relais activé (GPIOCON = 0xFF)")
        spi_relay.close()

        # Place le MUX au min (canal 0)
        mux.set_channel(0, 0)
        print("MUX: board 0, channel min (0)")
        time.sleep(2)

        # Place le MUX au max (canal 31)
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
    cmd_relay.write(True)  # Active le relais
    front_led.write(True)  # Allume la LED façade
    print("Relais activé (GPIO 17), LED façade allumée (GPIO 27)")

    print("=== Test de tous les canaux MUX (0-31) avec vérification du bit 7 ===")
    # Reduce speed to improve stability
    mux = Adg731MuxSpi(100000)
    try:
        # Test systematic all channels to verify bit 7 behavior
        for chan in range(32):
            # Generate control byte manually for comparison
            expected_ctrl = adg731_ctrl_byte(chan, enable=True)
            expected_binary = format(expected_ctrl, '08b')
            print(f"Testing channel {chan} - Expected control: 0x{expected_ctrl:02X}, binary: {expected_binary}")
            
            # Set the channel
            mux.set_channel(0, chan)
            
            # Explicit check for bit 7 (enable bit)
            if expected_ctrl & 0x80 == 0:
                print(f"Channel {chan}: Bit 7 is correctly set to 0 (enabled)")
            else:
                print(f"Channel {chan}: WARNING - Bit 7 is set to 1 (disabled)")
            
            # Wait for confirmation from user
            input("Appuie sur Entrée pour passer au canal suivant...")
    except KeyboardInterrupt:
        print("Arrêt demandé par l'utilisateur.")
    finally:
        mux.close()
        front_led.write(False)  # Éteint la LED façade
        cmd_relay.write(False)  # Désactive le relais
        front_led.close()
        cmd_relay.close()
        print("LED façade éteinte, relais désactivé")

if __name__ == "__main__":
    main()
