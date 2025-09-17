# -*- coding: utf-8 -*-
# fichier : adc_ads124s08.py
"""
ADS124S08 — SPI1.0 mode 1 — mesure bloquante avec DRDY.

Séquence:
- Reset + délai + purge POR
- INPMUX, PGA, REF, IDACMAG, IDACMUX
- DATARATE: single-shot + low-latency (DR=0x04 par défaut)
- START par commande
- Attente DRDY bas, RDATA 24 bits, STOP
- R = |code|/FS * (Rref / gain) * (I1 / (I1 + I2))  # Équation détaillée ratiométrique mise à jour
"""

import spidev  # Bibliothèque pour la communication SPI
import time  # Module pour la gestion du temps
from periphery import GPIO  # Bibliothèque pour la gestion des GPIO
from pins_cm5 import SPI1_BUS, SPI1_DEV0, SPI_ADC_SPEED_HZ, GPIO_CHIP_PATH, ADC_DRDY  # Importation des constantes matérielles
from app.temperature_conversion import resistance_to_temperature_dynamic  # Conversion résistance -> température
from app.sensor_profiles import SENSOR_TABLES  # Tables de conversion des capteurs

# Définition des registres ADC
REG_ID        = 0x00  # Registre ID
REG_STATUS    = 0x01  # Registre STATUS
REG_INPMUX    = 0x02  # Registre INPMUX (multiplexeur d'entrée)
REG_PGA       = 0x03  # Registre PGA (amplificateur programmable)
REG_DATARATE  = 0x04  # Registre DATARATE (taux d'échantillonnage)
REG_REF       = 0x05  # Registre REF (configuration de la référence)
REG_IDACMUX   = 0x07  # Registre IDACMUX (multiplexeur IDAC)
REG_SYS       = 0x09  # Registre SYS (configuration système)
REG_IDACMAG   = 0x06  # Registre IDACMAG (magnitude IDAC)

# Définition des commandes ADC
CMD_RESET  = 0x06  # Commande RESET
CMD_START  = 0x08  # Commande START
CMD_STOP   = 0x0A  # Commande STOP
CMD_RDATA  = 0x12  # Commande RDATA (lecture des données)

# Pleine échelle 24 bits signé
FS = (1 << 23) - 1  # Valeur maximale pour un code 24 bits signé

# Mapping des canaux physiques ADC
CHANNELS = {
    1: {"ainp_idx": 1,  "ainn_idx": 2},  # Canal 1
    2: {"ainp_idx": 4,  "ainn_idx": 5},  # Canal 2
    3: {"ainp_idx": 7,  "ainn_idx": 8},  # Canal 3
    4: {"ainp_idx": 10, "ainn_idx": 11}  # Canal 4
}


def encode_gain(pga_gain):
    """Encode le gain PGA en code binaire."""
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
    """Encode la magnitude IDAC en code binaire."""
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
    """Étend le signe d'un code 24 bits."""
    raw = (b0 << 16) | (b1 << 8) | b2
    if (raw & 0x800000) != 0:
        value = raw | 0xFF000000
        value = value - (1 << 32)
        return value
    return raw

class Ads124s08:
    def __init__(self):
        # Initialisation SPI
        self.spi = spidev.SpiDev()
        self.spi.open(SPI1_BUS, SPI1_DEV0)
        self.spi.mode = 1  # Mode SPI 1.0
        self.spi.max_speed_hz = SPI_ADC_SPEED_HZ  # Vitesse SPI
        self.spi.bits_per_word = 8  # Taille des mots SPI

        # Initialisation GPIO pour DRDY
        self.gpio_drdy = GPIO(GPIO_CHIP_PATH, ADC_DRDY, "in")

        # Réinitialisation ADC
        self.spi.xfer2([CMD_RESET])
        time.sleep(0.002)  # Délai après RESET

        # Purge des flags STATUS
        self._wreg(REG_STATUS, [0x00])

        # Lecture du registre ID pour vérification
        adc_id = self.read_id()
        if adc_id is None:
            print("[ADC] Erreur: aucune réponse sur le registre ID (0x00)")
        else:
            print("[ADC] ID (0x00) = 0x" + format(adc_id, "02X"))

    def read_id(self):
        """Lit le registre ID de l'ADC."""
        rx = self.spi.xfer2([0x20, 0x00, 0x00])  # RREG 0x00, 1 byte
        if len(rx) >= 3:
            return rx[2]
        return None

    def close(self):
        """Ferme les interfaces SPI et GPIO."""
        try:
            self.spi.close()
        except Exception:
            pass
        try:
            self.gpio_drdy.close()
        except Exception:
            pass

    def _rreg(self, addr, nbytes):
        """Lit un registre ADC."""
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
        """Écrit dans un registre ADC."""
        cmd = 0x40 | (addr & 0x1F)
        count = len(data_bytes) - 1
        tx = [cmd, count]
        tx = tx + list(data_bytes)
        self.spi.xfer2(tx)

    def _sclk_nudge(self):
        """Envoie un coup de pouce sur SCLK pour synchroniser."""
        _ = self._rreg(REG_STATUS, 1)
        time.sleep(0.0001)

    def _ensure_drdy_high(self, timeout_ms):
        """Assure que DRDY est à l'état HIGH."""
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
        """Configure le mode single-shot low-latency."""
        value = 0
        value = value | (1 << 5)           # MODE=1 single-shot
        value = value | (1 << 4)           # FILTER=1 low-latency
        value = value | (dr_nibble & 0x0F) # DR
        self._wreg(REG_DATARATE, [value])

    def configure_channel(self, channel_index, pga_gain, idac_uA):
        """
        Configure un canal ADC.

        :param channel_index: Index du canal (1-4).
        :param pga_gain: Gain PGA.
        :param idac_uA: Courant IDAC en microamperes.
        """
        if channel_index not in CHANNELS:
            raise ValueError("Canal ADC inconnu: " + str(channel_index))
        ch = CHANNELS[channel_index]
        ainp = ch["ainp_idx"]
        ainn = ch["ainn_idx"]
        print("[ADC] Configuration canal " + str(channel_index) + " gain=" + str(pga_gain) + " IDAC=" + str(idac_uA) + "uA")

        # INPMUX
        inpmux_val = ((ainp & 0x0F) << 4) | (ainn & 0x0F)
        print("[ADC] INPMUX=0x" + format(inpmux_val, "02X"))
        self._wreg(REG_INPMUX, [inpmux_val])

        # PGA avec activation
        gain_code = encode_gain(pga_gain)              # 0..7
        pga_val = 0
        pga_val = pga_val | (1 << 3)                   # PGA_EN = 01b
        pga_val = pga_val | (gain_code & 0x07)         # GAIN = xxx
        print("[ADC] PGA=0x" + format(pga_val, "02X"))
        self._wreg(REG_PGA, [pga_val])
        val = self._rreg(REG_PGA, 1)
        print("[ADC DEBUG] PGA readback: 0x" + format(val[0], "02X"))

        # Mode single-shot low-latency, DR=0x04
        self.set_single_shot_lowlatency(0x04)

        # REF externe REFP0-REFN0 avec REF interne activée
        print("[ADC] REF=0x12")  # REFSEL=00 (REFP0/REFN0), REFCON=10 (ref interne ON)
        self._wreg(REG_REF, [0x12])
        time.sleep(0.006)  # Attente pour stabilisation de la référence interne
        val = self._rreg(REG_REF, 1)
        print("[ADC DEBUG] REF readback: 0x" + format(val[0], "02X"))

        # IDAC magnitude
        mag_code = encode_idac_uA(idac_uA)
        print("[ADC] IDACMAG=0x" + format(mag_code & 0x0F, "02X"))
        self._wreg(REG_IDACMAG, [mag_code & 0x0F])
        val = self._rreg(REG_IDACMAG, 1)
        print("[ADC DEBUG] IDACMAG readback: 0x" + format(val[0], "02X"))

        # IDACMUX dynamique: IDAC1 vers AIN0/3/6/9, IDAC2 déconnecté
        idac1_route = 0 + (channel_index - 1) * 3      # 0, 3, 6, 9
        if idac1_route < 0:
            idac1_route = 0
        if idac1_route > 15:
            idac1_route = 15
        idac2_route = 0x0F                             # disconnect
        idacmux_val = ((idac2_route & 0x0F) << 4) | (idac1_route & 0x0F)
        print("[ADC] IDACMUX=0x" + format(idacmux_val, "02X"))
        self._wreg(REG_IDACMUX, [idacmux_val])
        val = self._rreg(REG_IDACMUX, 1)
        print("[ADC DEBUG] IDACMUX readback: 0x" + format(val[0], "02X"))

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
        """Démarre une conversion ADC."""
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
        """Arrête une conversion ADC."""
        self.spi.xfer2([CMD_STOP])

    def read_code24(self):
        """Lit un code de données 24 bits."""
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
        """
        Mesure la résistance en utilisant l'ADC.

        :param rref_ohm: Résistance de référence (en ohms).
        :param pga_gain: Gain PGA.
        :param timeout_s: Timeout pour la mesure.
        :return: Résistance mesurée (en ohms) ou None en cas d'erreur.
        """
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

        ratio = float(code) / float(FS)
        r_sonde = ratio * (float(rref_ohm) / float(pga_gain))

        print(f"[ADC] Résistance mesurée: {r_sonde:.1f} ohms")
        return r_sonde

    def measure_temperature(self, sensor_name, rref_ohm, pga_gain, timeout_s):
        """
        Mesure la température en utilisant la résistance mesurée.

        :param sensor_name: Nom du capteur.
        :param rref_ohm: Résistance de référence (en ohms).
        :param pga_gain: Gain PGA.
        :param timeout_s: Timeout pour la mesure.
        :return: Température mesurée (en °C) ou None si saturation.
        """
        resistance = self.measure_resistance(rref_ohm, pga_gain, timeout_s)
        if resistance is None:
            print("[ADC] Erreur: Résistance non mesurée ou saturation détectée.")
            return None

        if sensor_name not in SENSOR_TABLES:
            print(f"[ADC] Erreur: Table de conversion introuvable pour le capteur {sensor_name}.")
            return None

        temperature = resistance_to_temperature_dynamic(resistance, sensor_name)
        if temperature is None:
            print("[ADC] Erreur: Température non calculable (hors plage de la table).")
            return None

        print(f"[ADC] Température mesurée: {temperature:.2f} °C")
        return temperature

    def read_gain(self):
        """Lit le registre de gain PGA."""
        val = self._rreg(REG_PGA, 1)
        print(f"[ADC DEBUG] PGA Gain Register: 0x{val[0]:02X}")
        return val[0]

    def read_ref(self):
        """Lit le registre de configuration de la référence."""
        val = self._rreg(REG_REF, 1)
        print(f"[ADC DEBUG] Reference Register: 0x{val[0]:02X}")
        return val[0]

    def read_inpmux(self):
        """Lit le registre de configuration du multiplexeur d'entrée."""
        val = self._rreg(REG_INPMUX, 1)
        print(f"[ADC DEBUG] INPMUX Register: 0x{val[0]:02X}")
        return val[0]
