# -*- coding: utf-8 -*-
"""
hw_mux_adg731.py
ADG731 MUX driver over SPI0.
"""

import os
import spidev

def adg731_ctrl_byte(address, enable=True):
    if address < 0 or address > 31:
        raise ValueError("address out of range (0..31)")
    if enable is True:
        en = 0
    else:
        en = 1
    ctrl = (en << 7) | (address & 0x1F)
    return ctrl

class Adg731MuxSpi:
    DEV = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev0.2", "/dev/spidev0.3"]

    def __init__(self, speed_hz=100000):
        self.speed = speed_hz
        self.handles = []
        index = 0
        while index < 4:
            path = self.DEV[index]
            if os.path.exists(path) is True:
                s = spidev.SpiDev()
                s.open(0, index)
                s.mode = 1
                s.max_speed_hz = self.speed
                s.bits_per_word = 8
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
            else:
                self.handles.append(None)
            index = index + 1

    def close(self):
        for h in self.handles:
            if h is not None:
                try:
                    h.close()
                except Exception:
                    pass

    def set_channel(self, board_index, address):
        if board_index < 0 or board_index > 3:
            raise ValueError("board_index out of range (0..3)")
        h = self.handles[board_index]
        if h is None:
            print("ADG731: board", board_index, "non présent, ignoré")
            return None
        ctrl = adg731_ctrl_byte(address, True)
        h.xfer2([ctrl])
        return ctrl

    def set_output_channel(self, channel_index):
        # utilitaire simple si tu veux piloter par numéro de voie unique
        # ici: board 0, address = channel_index
        if channel_index < 0 or channel_index > 31:
            raise ValueError("channel_index out of range (0..31)")
        return self.set_channel(0, channel_index)
