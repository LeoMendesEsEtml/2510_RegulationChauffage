import time
import os

def test_spi_adc():
    print("=== ADC SPI test (ADS124S0x @ SPI1) ===")
    spi = None
    try:
        # Adapter le chemin SPI pour Windows ou Linux
        spi_path = "/dev/spidev1.0"
        if not os.path.exists(spi_path):
            print(f"FATAL: {spi_path} missing. Vérifiez la configuration SPI.")
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

        # Test lecture ID ADC
        adc_id = self.read_id()
        if adc_id is None:
            print("[ADC] Erreur: aucune réponse sur le registre ID (0x00)")
        else:
            print(f"[ADC] ID (0x00) = 0x{adc_id:02X}")

    def read_id(self):
        # Lecture du registre ID (0x00), 1 octet
        rx = self.spi.xfer2([0x20, 0x00, 0x00])
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
