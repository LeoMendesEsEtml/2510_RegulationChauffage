# -*- coding: utf-8 -*-
#!/usr/bin/env python3
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

# =========================
# ADG731 (MUX) over SPI0
# =========================

def adg731_ctrl_byte(address, enable=True):
    # D7=EN(0=enable), D6..D2=A4..A0, D1..D0=0
    if address < 0:
        raise ValueError("address below 0")
    if address > 31:
        raise ValueError("address above 31")
    en_bit = 0
    if enable is not True:
        en_bit = 1
    ctrl = (en_bit << 7) | ((address & 0x1F) << 2)
    return ctrl

class Adg731MuxSpi:
    """
    Map boards to SPI0 chip-selects:
      board 0 -> /dev/spidev0.0  (CS=GPIO8)
      board 1 -> /dev/spidev0.1  (CS=GPIO7)
      board 2 -> /dev/spidev0.2  (CS=GPIO3)  [requires overlay to exist]
      board 3 -> /dev/spidev0.3  (CS=GPIO2)  [requires overlay to exist]
    """
    DEV = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev0.2", "/dev/spidev0.3"]

    def __init__(self, speed_hz=1000000):
        self.speed = speed_hz
        self.handles = []
        i = 0
        while i < 4:
            path = self.DEV[i]
            if os.path.exists(path):
                s = spidev.SpiDev()
                # bus=0, device=i
                s.open(0, i)
                # ADG731 accepte mode 0 ou 1; on reste en mode 1 (CPOL=0, CPHA=1)
                s.mode = 1
                s.max_speed_hz = self.speed
                s.bits_per_word = 8
                self.handles.append(s)
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
        if board_index < 0:
            raise ValueError("board_index below 0")
        if board_index > 3:
            raise ValueError("board_index above 3")
        h = self.handles[board_index]
        if h is None:
            print("skip board", board_index, "(", self.DEV[board_index], "missing )")
            return
        ctrl = adg731_ctrl_byte(address, enable=True)
        print(f"SPI MUX: board={board_index}, address={address}, ctrl=0x{ctrl:02X}")
        print(f"Appel xfer2 sur {self.DEV[board_index]} avec [{ctrl}]")
        # Une seule trame: CS actif bas pendant xfer2, latch à CS↑
        h.xfer2([ctrl])

def test_spi_mux_hw():
    print("=== MUX test (SPI0 hardware) ===")
    mux = Adg731MuxSpi(100000)
    try:
        b = 0
        while b < 4:
            print("Board", b, "->", Adg731MuxSpi.DEV[b])
            a = 0
            while a < 4:
                try:
                    mux.set_channel(b, a)
                    print("  set channel", a, "OK")
                except Exception as e:
                    print("  set channel", a, "error:", str(e))
                a = a + 1
            b = b + 1
    finally:
        mux.close()
    print("MUX test done.\n")

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

        time.sleep(0.003)         # POR ~2.2ms
        spi.xfer2([0x06])         # RESET
        time.sleep(0.002)         # wait td(RSSC)

        # Envoi d'une commande simple que l'ADC peut comprendre : lecture du registre ID (RREG 0x00, 1 byte)
        rx = spi.xfer2([0x20, 0x00, 0x00])
        if len(rx) >= 3:
            print(f"ADC ID = 0x{rx[2]:02X}")
        else:
            print("ADC ID: réponse invalide", rx)

        # Lecture du registre STATUS (RREG 0x01, 1 byte)
        rx2 = spi.xfer2([0x21, 0x00, 0x00])
        if len(rx2) >= 3:
            print(f"ADC STATUS = 0x{rx2[2]:02X}")
        else:
            print("ADC STATUS: réponse invalide", rx2)

    except Exception as e:
        print("ADC SPI error:", str(e))
    finally:
        if spi is not None:
            try:
                spi.close()
            except Exception:
                pass
    print("ADC SPI test done.\n")

# =========================
# Main
# =========================

def main():
    print("=== Boucle infinie de tests SPI (Ctrl+C pour arrêter) ===")
    try:
        while True:
            test_spi_mux_hw()
            test_spi_adc()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt demandé par l'utilisateur.")

if __name__ == "__main__":
    main()
