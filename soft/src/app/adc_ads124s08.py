# -*- coding: utf-8 -*-
# file: adc_ads124s08.py
"""
ADS124S08 minimal, SPI1.0, mode 1, mesure bloquante.

Séquence:
- Configurer INPMUX, PGA, DATARATE, REF, IDACMAG, IDACMUX selon canal et profil
- START (commande)
- Attendre DRDY ou timeout
- RDATA (24 bits)
- STOP
- Convertir en résistance ratiométrique: R = code/FS * (Rref / gain)
"""

import spidev
import time
from periphery import GPIO
from pins_cm5 import SPI1_BUS, SPI1_DEV0, SPI_ADC_SPEED_HZ, GPIO_CHIP_PATH, ADC_DRDY

# Registres
REG_ID        = 0x00
REG_STATUS    = 0x01
REG_INPMUX    = 0x02
REG_PGA       = 0x03
REG_DATARATE  = 0x04
REG_REF       = 0x05
REG_IDACMUX   = 0x07
REG_IDACMAG   = 0x0A

# Commandes
CMD_RESET  = 0x06
CMD_START  = 0x08
CMD_STOP   = 0x0A
CMD_RDATA  = 0x12

# Pleine échelle (24 bits bipolaire)
FS = (1 << 23) - 1

# Mapping canaux physiques
CHANNELS = {
    1: {"idac_src_idx": 0,  "ainp_idx": 1,  "ainn_idx": 2},
    2: {"idac_src_idx": 3,  "ainp_idx": 4,  "ainn_idx": 5},
    3: {"idac_src_idx": 6,  "ainp_idx": 7,  "ainn_idx": 8},
    4: {"idac_src_idx": 9,  "ainp_idx": 10, "ainn_idx": 11}
}

def encode_gain(pga_gain):
    if pga_gain == 1:
        return 0
    if pga_gain == 2:
        return 1
    if pga_gain == 4:
        return 2
    if pga_gain == 8:
        return 3
    if pga_gain == 16:
        return 4
    if pga_gain == 32:
        return 5
    if pga_gain == 64:
        return 6
    if pga_gain == 128:
        return 7
    raise ValueError("PGA gain invalide: " + str(pga_gain))

def encode_idac_uA(idac_uA):
    # Table typique TI
    if idac_uA == 10:
        return 1
    if idac_uA == 50:
        return 2
    if idac_uA == 100:
        return 3
    if idac_uA == 250:
        return 4
    if idac_uA == 500:
        return 5
    if idac_uA == 1000:
        return 6
    if idac_uA == 1500:
        return 7
    if idac_uA == 2000:
        return 8
    raise ValueError("IDAC µA non supporté: " + str(idac_uA))

def sign_extend_24(b0, b1, b2):
    raw = (b0 << 16) | (b1 << 8) | b2
    if (raw & 0x800000) != 0:
        value = raw | 0xFF000000
        value = value - (1 << 32)
        return value
    return raw

class Ads124s08:
    def __init__(self):
        # SPI
        self.spi = spidev.SpiDev()
        self.spi.open(SPI1_BUS, SPI1_DEV0)
        self.spi.mode = 1
        self.spi.max_speed_hz = SPI_ADC_SPEED_HZ
        self.spi.bits_per_word = 8
        # DRDY
        self.gpio_drdy = GPIO(GPIO_CHIP_PATH, ADC_DRDY, "in")

    def close(self):
        try:
            self.spi.close()
        except Exception:
            pass
        try:
            self.gpio_drdy.close()
        except Exception:
            pass

    def _rreg(self, addr, nbytes):
        cmd = 0x20 | (addr & 0x1F)
        count = nbytes - 1
        tx = [cmd, count]
        index = 0
        while index < nbytes:
            tx.append(0x00)
            index = index + 1
        rx = self.spi.xfer2(tx)
        data = rx[2:]
        return data

    def _wreg(self, addr, data_bytes):
        cmd = 0x40 | (addr & 0x1F)
        count = len(data_bytes) - 1
        tx = [cmd, count]
        tx = tx + list(data_bytes)
        self.spi.xfer2(tx)

    def wait_drdy(self, timeout_s):
        t0 = time.time()
        while True:
            val = self.gpio_drdy.read()
            if val is False:
                return True
            if time.time() - t0 > float(timeout_s):
                return False
            time.sleep(0.001)

    def configure_channel(self, channel_index, pga_gain, idac_uA):
        if channel_index not in CHANNELS:
            raise ValueError("Canal ADC inconnu: " + str(channel_index))
        ch = CHANNELS[channel_index]
        ainp = ch["ainp_idx"]
        ainn = ch["ainn_idx"]
        idac_src = ch["idac_src_idx"]

        # INPMUX
        inpmux_val = ((ainp & 0x0F) << 4) | (ainn & 0x0F)
        self._wreg(REG_INPMUX, [inpmux_val])

        # PGA
        gain_code = encode_gain(pga_gain)
        self._wreg(REG_PGA, [gain_code & 0x07])

        # DATARATE (0x14 vu dans tes lectures)
        self._wreg(REG_DATARATE, [0x14])

        # REF externe REFP0-REFN0 (0x10 vu dans tes lectures)
        self._wreg(REG_REF, [0x10])

        # IDAC magnitude
        mag_code = encode_idac_uA(idac_uA)
        self._wreg(REG_IDACMAG, [mag_code & 0x0F])

        # IDACMUX: IDAC1 -> idac_src ; IDAC2 -> off (0x0F)
        idac1_dest = idac_src & 0x0F
        idac2_dest = 0x0F
        idacmux_val = ((idac1_dest & 0x0F) << 4) | (idac2_dest & 0x0F)
        self._wreg(REG_IDACMUX, [idacmux_val])

    def start(self):
        self.spi.xfer2([CMD_START])

    def stop(self):
        self.spi.xfer2([CMD_STOP])

    def read_code24(self):
        rx = self.spi.xfer2([CMD_RDATA, 0x00, 0x00, 0x00])
        if len(rx) < 4:
            return None
        b0 = rx[1]
        b1 = rx[2]
        b2 = rx[3]
        value = sign_extend_24(b0, b1, b2)
        return value

    def measure_resistance(self, rref_ohm, pga_gain, timeout_s):
        # START
        self.start()

        ok = self.wait_drdy(timeout_s)
        if ok is False:
            self.stop()
            return None

        code = self.read_code24()
        self.stop()
        if code is None:
            return None

        if code < 0:
            code = -code

        ratio = float(code) / float(FS)
        r_div_gain = float(rref_ohm) / float(pga_gain)
        r_sonde = ratio * r_div_gain
        return r_sonde
