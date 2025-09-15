# -*- coding: utf-8 -*-
# file: adc_ads124s08.py
"""
ADS124S08 — SPI1.0 mode 1 — mesure bloquante avec DRDY.

Séquence:
- Reset + délai + purge POR
- INPMUX, PGA, REF, IDACMAG, IDACMUX
- DATARATE: single-shot + low-latency (DR=0x04 par défaut)
- START par commande
- Attente DRDY bas, RDATA 24 bits, STOP
- R = |code|/FS * (Rref / gain) * (I1 / (I1 + I2))  # Updated to detailed ratiometric equation
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
REG_SYS       = 0x09
REG_IDACMAG   = 0x0A

# Commandes
CMD_RESET  = 0x06
CMD_START  = 0x08
CMD_STOP   = 0x0A
CMD_RDATA  = 0x12

# Pleine échelle 24 bits signé
FS = (1 << 23) - 1

# Mapping canaux physiques
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

        # DRDY (entrée, actif bas)
        self.gpio_drdy = GPIO(GPIO_CHIP_PATH, ADC_DRDY, "in")

        # Reset + attente >= 4096*tCLK
        self.spi.xfer2([CMD_RESET])
        time.sleep(0.002)

        # Purge flags (STATUS=0x00)
        self._wreg(REG_STATUS, [0x00])

        # Lecture ID pour sanity-check
        adc_id = self.read_id()
        if adc_id is None:
            print("[ADC] Erreur: aucune réponse sur le registre ID (0x00)")
        else:
            print("[ADC] ID (0x00) = 0x" + format(adc_id, "02X"))

    def read_id(self):
        rx = self.spi.xfer2([0x20, 0x00, 0x00])  # RREG 0x00, 1 byte
        if len(rx) >= 3:
            return rx[2]
        return None

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

    def _sclk_nudge(self):
        _ = self._rreg(REG_STATUS, 1)
        time.sleep(0.0001)

    def _ensure_drdy_high(self, timeout_ms):
        t0 = time.time()
        kicked = False
        while True:
            val = self.gpio_drdy.read()
            if val is True:
                return True
            if kicked is False:
                self._sclk_nudge()
                kicked = True
            if time.time() - t0 > float(timeout_ms) / 1000.0:
                return False
            time.sleep(0.001)

    def wait_drdy_falling_edge(self, timeout_s):
        """
        Attend un front descendant sur DRDY (HIGH -> LOW) avec timeout.
        Retourne True si front observé, False sinon.
        """
        t0 = time.time()
        prev = self.gpio_drdy.read()
        while True:
            val = self.gpio_drdy.read()
            if prev is True and val is False:
                print("[ADC] Front descendant DRDY détecté")
                return True
            prev = val
            if time.time() - t0 > float(timeout_s):
                print("[ADC] Timeout DRDY front descendant !")
                return False
            time.sleep(0.001)

    def set_single_shot_lowlatency(self, dr_nibble):
        value = 0
        value = value | (1 << 5)           # MODE=1 single-shot
        value = value | (1 << 4)           # FILTER=1 low-latency
        value = value | (dr_nibble & 0x0F) # DR
        self._wreg(REG_DATARATE, [value])

    def configure_channel(self, channel_index, pga_gain, idac_uA):
        if channel_index not in CHANNELS:
            raise ValueError("Canal ADC inconnu: " + str(channel_index))
        ch = CHANNELS[channel_index]
        ainp = ch["ainp_idx"]
        ainn = ch["ainn_idx"]
        idac_src = ch["idac_src_idx"]
        print("[ADC] Configuration canal " + str(channel_index) + " gain=" + str(pga_gain) + " IDAC=" + str(idac_uA) + "uA")

        # INPMUX
        inpmux_val = ((ainp & 0x0F) << 4) | (ainn & 0x0F)
        print("[ADC] INPMUX=0x" + format(inpmux_val, "02X"))
        self._wreg(REG_INPMUX, [inpmux_val])

        # PGA
        gain_code = encode_gain(pga_gain)
        print("[ADC] PGA=0x" + format(gain_code & 0x07, "02X"))
        self._wreg(REG_PGA, [gain_code & 0x07])

        # Mode single-shot low-latency, DR=0x04
        self.set_single_shot_lowlatency(0x04)

        # REF externe REFP0-REFN0
        print("[ADC] REF=0x10")
        self._wreg(REG_REF, [0x10])

        # IDAC magnitude
        mag_code = encode_idac_uA(idac_uA)
        print("[ADC] IDACMAG=0x" + format(mag_code & 0x0F, "02X"))
        self._wreg(REG_IDACMAG, [mag_code & 0x0F])

        # IDAC settings: I2MUX in bits 7:4, I1MUX in bits 3:0
        # En 2-fils low-side ref: un seul IDAC sur la borne + mesurée (AINP)
        # IDAC1 -> AINP ; IDAC2 -> OFF
        # Bits 7:4 = I2MUX (IDAC2), bits 3:0 = I1MUX (IDAC1)
        # Ratiométrique robuste: IDAC1 -> AINP, IDAC2 -> AINN (nœud Rref+)
        i1mux = ainp & 0x0F         # ex. CH1: AIN1
        i2mux = ainn & 0x0F         # ex. CH1: AIN2
        idacmux_val = ((i2mux & 0x0F) << 4) | (i1mux & 0x0F)
        print("[ADC] IDACMUX=0x" + format(idacmux_val, "02X"))
        self._wreg(REG_IDACMUX, [idacmux_val])

        # Délai de stabilisation après config
        time.sleep(0.001)

        # Lecture des registres clés ADC pour debug
        reg_map = {
            "INPMUX": REG_INPMUX,
            "PGA": REG_PGA,
            "DATARATE": REG_DATARATE,
            "REF": REG_REF,
            "IDACMAG": REG_IDACMAG,
            "IDACMUX": REG_IDACMUX
        }
        for name, addr in reg_map.items():
            val = self._rreg(addr, 1)
            print(f"[ADC] {name} (0x{addr:02X}) = 0x{val[0]:02X}")

    def start(self):
        # Kick SCLK pour relâcher DRDY à HIGH
        t0 = time.time()
        while self.gpio_drdy.read() is not True:
            self._rreg(REG_STATUS, 1)
            time.sleep(0.001)
            if time.time() - t0 > 1.0:
                print("[ADC] Timeout: DRDY n'est pas remonté HIGH avant START !")
                break
        # START conversion
        self.spi.xfer2([CMD_START])

    def stop(self):
        self.spi.xfer2([CMD_STOP])

    def read_code24(self):
        rx = self.spi.xfer2([CMD_RDATA, 0x00, 0x00, 0x00])
        if len(rx) < 4:
            print("[ADC] Erreur: réponse SPI trop courte " + str(rx))
            return None
        b0 = rx[1]
        b1 = rx[2]
        b2 = rx[3]
        value = sign_extend_24(b0, b1, b2)
        return value

    def measure_resistance(self, rref_ohm, pga_gain, timeout_s):
        print("[ADC] Mesure résistance: rref=" + str(rref_ohm) + " gain=" + str(pga_gain) + " timeout=" + str(timeout_s))

        self.start()

        ok = self.wait_drdy_falling_edge(timeout_s)
        if ok is False:
            self.stop()
            print("[ADC] Erreur: DRDY non détecté, mesure annulée")
            return None

        code = self.read_code24()
        self.stop()
        if code is None:
            print("[ADC] Erreur: code ADC non lu")
            return None

        if code < 0:
            code = -code

        # Calcul unique de la résistance
        ratio = float(code) / float(FS)
        r_sonde = ratio * (float(rref_ohm) / float(pga_gain)) * (idac1 / (idac1 + idac2))  # Updated to detailed ratiometric equation
        
        print(f"[ADC] Résistance mesurée: {r_sonde:.1f} ohms")
        
        return r_sonde