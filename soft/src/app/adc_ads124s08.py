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

# Définition des canaux selon le schéma
# Pour chaque canal :
# - IDAC injecte dans AINx_src qui est connecté à AINx_p sur la carte
# - RTD/fil entre AINx_p et AINx_n
# - La tension aux bornes de la sonde est AINx_p - AINx_n
CHANNELS = {
    1: {"idac_src": 0, "ainp_idx": 1, "ainn_idx": 2},    # IDAC->AIN0-[PCB]->AIN1-[RTD]->AIN2
    2: {"idac_src": 3, "ainp_idx": 4, "ainn_idx": 5},    # IDAC->AIN3-[PCB]->AIN4-[RTD]->AIN5
    3: {"idac_src": 6, "ainp_idx": 7, "ainn_idx": 8},    # IDAC->AIN6-[PCB]->AIN7-[RTD]->AIN8
    4: {"idac_src": 9, "ainp_idx": 10, "ainn_idx": 11}   # IDAC->AIN9-[PCB]->AIN10-[RTD]->AIN11
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

    def set_datarate_config(self, dr_nibble, filter_mode="normal"):
        """Configure le taux d'échantillonnage et le mode de filtrage.
        
        dr_nibble: Valeur de 0 à 15 pour le taux d'échantillonnage:
        - 0x00 = 2.5 SPS    (le plus lent, le plus stable)
        - 0x01 = 5 SPS
        - 0x02 = 10 SPS
        - 0x03 = 16.6 SPS
        - 0x04 = 20 SPS     (valeur par défaut)
        - 0x05 = 50 SPS
        - 0x06 = 60 SPS
        - 0x07 = 100 SPS
        - 0x08 = 400 SPS
        - 0x09 = 1200 SPS
        - 0x0A = 2400 SPS
        - 0x0B = 4800 SPS
        - 0x0C = 7200 SPS
        - 0x0D = 14400 SPS
        - 0x0E = 19200 SPS
        - 0x0F = 25600 SPS  (le plus rapide, le moins stable)
        
        filter_mode: 'normal' ou 'low-latency'
        - normal = meilleur filtrage, plus stable
        - low-latency = réponse plus rapide, moins stable
        """
        value = 0
        value = value | (1 << 5)           # MODE=1 single-shot
        if filter_mode == "low-latency":
            value = value | (1 << 4)       # FILTER=1 low-latency
        # sinon FILTER=0 normal mode (meilleur filtrage)
        value = value | (dr_nibble & 0x0F) # DR
        self._wreg(REG_DATARATE, [value])
        
        # Temps de stabilisation après changement de configuration
        time.sleep(0.010)  # 10ms de stabilisation

    def configure_channel(self, channel_index, pga_gain, idac_uA):
        """Configure un canal ADC selon la datasheet ADS124S08
        - INPMUX: sélectionne les entrées différentielles
        - PGA: configure le gain
        - IDACMUX: route le courant d'excitation
        - IDACMAG: définit l'amplitude du courant
        - REF: sélectionne la référence externe
        - SYS: configure le mode de conversion"""
        if channel_index not in CHANNELS:
            raise ValueError("Canal ADC inconnu: " + str(channel_index))
        ch = CHANNELS[channel_index]
        idac_src = ch["idac_src"]  # AINx pour source IDAC
        ainp = ch["ainp_idx"]      # AINx pour entrée positive
        ainn = ch["ainn_idx"]      # AINx pour entrée négative
        print(f"[ADC] Configuration canal {channel_index} gain={pga_gain} IDAC={idac_uA}µA")

        # PGA configuration
        # Bits[2:0] = Gain
        # Autres bits à 0 (pas de bypass, etc)
        gain_code = encode_gain(pga_gain)
        print(f"[ADC] PGA=0x{gain_code:02X} (Gain={pga_gain})")
        self._wreg(REG_PGA, [gain_code])

        # Configure le registre SYS
        # Bit 1 = 1 (Enable conversion start on SYNC falling edge)
        # Autres bits par défaut
        sys_val = 0x02
        print(f"[ADC] SYS=0x{sys_val:02X}")
        self._wreg(REG_SYS, [sys_val])

        # Configuration du taux d'échantillonnage et du filtrage
        # - DR=0x03 (16.6 SPS) pour plus de stabilité
        # - Mode normal (meilleur filtrage)
        self.set_datarate_config(0x03, "normal")

        # Configuration référence
        # Bit 5 = 0 (Internal ref off)
        # Bit 4 = 1 (REF0 selected)
        # Bits[3:0] = 0 (autres options désactivées)
        ref_val = 0x10
        print(f"[ADC] REF=0x{ref_val:02X} (REF0, ref interne OFF)")
        self._wreg(REG_REF, [ref_val])

        # Configure IDACMUX - Route le courant d'excitation
        # IDACMUX register: [7:4]=IDAC2MUX (OFF), [3:0]=IDAC1MUX
        # IDAC1 est routé vers la source de courant dédiée
        idacmux_val = (0x0F << 4) | (idac_src & 0x0F)  # IDAC1->AINx(src), IDAC2=OFF
        print(f"[ADC] IDACMUX=0x{idacmux_val:02X} (IDAC1->AIN{idac_src}, IDAC2=OFF)")
        self._wreg(REG_IDACMUX, [idacmux_val])

        # Configure INPMUX pour la mesure différentielle
        # INPMUX register: [7:4]=AINP, [3:0]=AINN
        # Connexion selon le schéma hardware:
        # - AINP = AINx(+) de la sonde
        # - AINN = AINx(-) de la sonde
        inpmux_val = ((ainp & 0x0F) << 4) | (ainn & 0x0F)
        print(f"[ADC] INPMUX=0x{inpmux_val:02X} (AIN{ainp}-AIN{ainn})")
        self._wreg(REG_INPMUX, [inpmux_val])

        # IDAC magnitude
        mag_code = encode_idac_uA(idac_uA)
        print("[ADC] IDACMAG=0x" + format(mag_code & 0x0F, "02X"))
        self._wreg(REG_IDACMAG, [mag_code & 0x0F])

        # Délai de stabilisation après config
        time.sleep(0.001)

        # Lecture et vérification des registres clés ADC
        reg_map = {
            "INPMUX": {"addr": REG_INPMUX, "desc": f"AIN{ainp}(+) et AIN{ainn}(-)"},
            "PGA": {"addr": REG_PGA, "desc": f"Gain={pga_gain}"},
            "DATARATE": {"addr": REG_DATARATE, "desc": "Single-shot, low-latency"},
            "REF": {"addr": REG_REF, "desc": "REF0 externe"},
            "IDACMUX": {"addr": REG_IDACMUX, "desc": f"IDAC1->AIN{idac_src}, IDAC2=OFF"},
            "IDACMAG": {"addr": REG_IDACMAG, "desc": f"{idac_uA}µA"},
            "SYS": {"addr": REG_SYS, "desc": "SYNC enabled"}
        }
        print("\n[ADC] Vérification configuration:")
        print("-" * 50)
        for name, info in reg_map.items():
            val = self._rreg(info["addr"], 1)[0]
            print(f"[ADC] {name:8} = 0x{val:02X} | {info['desc']}")
        print("-" * 50)

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

        print(f"[ADC DEBUG] Code brut: {code}")
        print(f"[ADC DEBUG] FS: {FS}")
        print(f"[ADC DEBUG] Rref: {rref_ohm} / Gain: {pga_gain}")

        if code < 0:
            code = -code
            print("[ADC DEBUG] Code négatif détecté, utilisation valeur absolue")

        # Circuit selon datasheet (Fig 2-1):
        # IDAC1 ---> AIN0 -[PCB]-> AIN1 --[RSENSE]--> AIN2
        #
        # Mesure ratiométrique :
        # VSENSE = IDAC * RSENSE
        # VREF = IDAC * RREF
        #
        # L'ADC mesure: code/FS = (VSENSE/gain)/(VREF/gain)
        # Le gain s'annule car il affecte les deux tensions!
        # 
        # code/FS = VSENSE/VREF = (IDAC*RSENSE)/(IDAC*RREF) = RSENSE/RREF
        # Donc : RSENSE = RREF * (code/FS)
        
        # Calcul du ratio par rapport à la pleine échelle
        ratio = float(code) / float(FS)
        print(f"[ADC DEBUG] Ratio mesure/FS: {ratio:.6f}")

        # Calcul ratiométrique simple (le gain s'annule !)
        r_sonde = float(rref_ohm) * ratio
        
        print(f"[ADC DEBUG] Équation: Rsense = {rref_ohm} * ({code}/{FS})")
        print(f"[ADC] Résistance mesurée: {r_sonde:.1f} ohms")
        return r_sonde
