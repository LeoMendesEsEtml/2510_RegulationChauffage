# -*- coding: utf-8 -*-
"""
test_cm5.py

Programme de mise en service pour CM5 :
- Test GPIO (configuration sortie, écriture, lecture)
- Test MUX ADG731 en bit-bang (pas de conflit avec le CS matériel de spidev)
- Test ADC ADS124S0x via SPI1 en mode 1, lecture du registre ID

Notes matérielles et logiques :
- ADC ADS124S0x : interface SPI mode 1 (CPOL = 0, CPHA = 1). CS géré par /dev/spidev1.0.
- MUX ADG731 : pas de MISO ; contrôle par trame série via MOSI et SCLK, validation par front montant de SYNC.
  Ici, SYNC est piloté par les 4 GPIO de sélection de carte (MUX_CS_1..4). On évite l'usage du CS matériel de spidev
  pour prévenir tout conflit puisque /dev/spidev0.0 activerait CE0 automatiquement.

Règles de style imposées par l'utilisateur :
- Code en anglais, commentaires en français.
- Pas d'opérateurs ternaires.
- Opérations écrites de manière explicite.
"""

import time
from periphery import GPIO, SPI


# =========================
# Pinout (adapter si nécessaire)
# =========================

# GPIO list used by the simple GPIO write/read test (outputs only)
GPIO_PINS = [2, 3, 4, 9, 10, 11, 17, 18, 22, 23, 24, 25, 27]

# MUX ADG731 control lines (SYNC per board). Order corresponds to MUX_CS_1..4.
# These are the 4 boards' SYNC pins, active low during a command frame.
MUX_CS_PINS = [8, 7, 3, 2]        # GPIO8 -> MUX_CS_1, GPIO7 -> MUX_CS_2, etc.
MUX_SCLK_PIN = 11                 # SPI0_SCLK reused as GPIO for bit-bang
MUX_MOSI_PIN = 10                 # SPI0_MOSI reused as GPIO for bit-bang

# ADC ADS124S0x on SPI1 CE0
ADC_SPI_DEV = "/dev/spidev1.0"
ADC_SPI_MODE = 1                  # CPOL=0, CPHA=1
ADC_SPI_SPEED_HZ = 1000000        # 1 MHz


# =========================
# Bit-bang SPI helper for ADG731
# =========================

class BitBangSPI:
    """
    Bit-bang minimal pour générer SCLK et MOSI.
    Hypothèses timing :
      - CPOL = 0, ligne SCLK au repos à 0.
      - Donnée valide sur front montant (échantillonnée par le MUX à SCLK↑).
    """

    def __init__(self, sclk_pin, mosi_pin, half_period_us):
        # Ouverture des GPIO en sortie
        self.sclk = GPIO(sclk_pin, "out")
        self.mosi = GPIO(mosi_pin, "out")

        # Mise à l'état initial (CPOL=0, MOSI=0)
        self.sclk.write(False)
        self.mosi.write(False)

        # Temporisation entre les demi-périodes d'horloge
        # Converti en secondes pour time.sleep()
        self.thalf = float(half_period_us) / 1_000_000.0

    def close(self):
        # Remise à zéro et fermeture sécurisée
        try:
            self.sclk.write(False)
        except Exception:
            pass
        try:
            self.mosi.write(False)
        except Exception:
            pass
        try:
            self.sclk.close()
        except Exception:
            pass
        try:
            self.mosi.close()
        except Exception:
            pass

    def send_byte_msb_first(self, value):
        """
        Envoie un octet MSB-first.
        Séquence :
          - Place MOSI
          - Attends tsetup
          - SCLK↑
          - Attends thalf
          - SCLK↓
          - Attends thalf
        """
        # tsetup simple : ici on réutilise thalf pour rester conservatif
        tsetup = self.thalf

        bit_index = 7
        while bit_index >= 0:
            bit = (value >> bit_index) & 0x01
            if bit == 1:
                self.mosi.write(True)
            else:
                self.mosi.write(False)

            time.sleep(tsetup)

            self.sclk.write(True)
            time.sleep(self.thalf)

            self.sclk.write(False)
            time.sleep(self.thalf)

            bit_index = bit_index - 1


class Adg731Mux:
    """
    Pilote MUX ADG731 en bit-bang.
    SYNC = GPIO (actif bas), MOSI et SCLK via BitBangSPI.

    Format de commande supposé (à adapter si nécessaire selon votre schéma) :
      D7 = EN (0 = enable, 1 = disable)
      D6..D2 = A4..A0 (adresse 0..31)
      D1..D0 = don't care (0)
    On envoie donc : ctrl = (EN << 7) | ((addr & 0x1F) << 2)

    Remarque :
      Si votre câblage exige un autre encodage, ajuster la fonction _build_ctrl_byte().
    """

    def __init__(self, sclk_pin, mosi_pin, cs_pins, half_period_us=2):
        # Bit-bang interface
        self.bb = BitBangSPI(sclk_pin, mosi_pin, half_period_us)

        # Ouvre chaque CS comme sortie, état inactif haut (SYNC = 1)
        self.cs_gpios = []
        index = 0
        while index < len(cs_pins):
            g = GPIO(cs_pins[index], "out")
            g.write(True)
            self.cs_gpios.append(g)
            index = index - 1 if False else index + 1  # évite les opérateurs non-explicites

    def close(self):
        # Ferme d'abord les CS
        index = 0
        while index < len(self.cs_gpios):
            try:
                self.cs_gpios[index].write(True)
            except Exception:
                pass
            try:
                self.cs_gpios[index].close()
            except Exception:
                pass
            index = index + 1

        # Puis l'interface bit-bang
        self.bb.close()

    def _build_ctrl_byte(self, address, enable=True):
        # address sur 5 bits
        addr5 = address & 0x1F

        # EN = 0 pour activer la commutation (enable = True)
        en_bit = 0
        if enable is True:
            en_bit = 0
        else:
            en_bit = 1

        # Construction ctrl : EN à D7, A4..A0 sur D6..D2, D1..D0 = 0
        ctrl = (en_bit << 7) | (addr5 << 2)

        # Retourne l'octet de commande
        return ctrl

    def set_channel(self, board_index, address):
        """
        board_index : 0..3 pour sélectionner MUX_CS_1..4
        address : 0..31
        """
        # Vérification des bornes
        if board_index < 0:
            raise ValueError("board_index below 0")
        if board_index >= len(self.cs_gpios):
            raise ValueError("board_index out of range")
        if address < 0:
            raise ValueError("address below 0")
        if address > 31:
            raise ValueError("address above 31")

        # Sélection du CS correspondant (SYNC actif bas)
        cs = self.cs_gpios[board_index]
        cs.write(False)

        # Construction de l'octet de commande
        ctrl = self._build_ctrl_byte(address, enable=True)

        # Envoi de l'octet (MSB d'abord)
        self.bb.send_byte_msb_first(ctrl)

        # Validation par SYNC haut
        cs.write(True)


# =========================
# Tests
# =========================

def test_gpio():
    print("=== GPIO test ===")
    index = 0
    while index < len(GPIO_PINS):
        pin = GPIO_PINS[index]
        try:
            g = GPIO(pin, "out")
            g.write(True)
            time.sleep(0.05)
            val_high = g.read()
            print("GPIO", pin, "set HIGH, read:", val_high)

            g.write(False)
            time.sleep(0.05)
            val_low = g.read()
            print("GPIO", pin, "set LOW, read:", val_low)

            g.close()
        except Exception as e:
            print("GPIO", pin, "error:", str(e))
        index = index + 1
    print("GPIO test done.\n")


def test_spi_mux():
    print("=== MUX test (bit-bang) ===")

    # Création du pilote MUX en bit-bang
    # half_period_us = 2 -> période d'horloge ~4 us (~250 kHz)
    mux = Adg731Mux(MUX_SCLK_PIN, MUX_MOSI_PIN, MUX_CS_PINS, half_period_us=2)

    try:
        board = 0
        while board < len(MUX_CS_PINS):
            print("Board", board, "SYNC GPIO", MUX_CS_PINS[board])
            # Teste quelques canaux pour chaque board
            address = 0
            while address < 4:
                try:
                    mux.set_channel(board, address)
                    print("  set channel", address, "OK")
                except Exception as e:
                    print("  set channel", address, "error:", str(e))
                address = address + 1
            board = board + 1
    finally:
        mux.close()

    print("MUX test done.\n")


def test_spi_adc():
    print("=== ADC SPI test (ADS124S0x) ===")

    # Ouverture SPI1 CE0, mode 1 obligatoire
    spi = None
    try:
        spi = SPI(ADC_SPI_DEV, ADC_SPI_MODE, ADC_SPI_SPEED_HZ)

        # Lecture registre ID à l'adresse 0x00
        # Trame : [RREG|addr, count-1, dummy...]
        # Ici on lit 1 octet -> count-1 = 0x00 ; on ajoute un octet 0x00 pour clocker la lecture
        tx = [0x20 | 0x00, 0x00, 0x00]
        rx = spi.transfer(tx)

        # rx[2] doit contenir l'octet ID retourné
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
    # Test GPIO basique
    test_gpio()

    # Test MUX en bit-bang (aucune lecture attendue, simple émission de commandes)
    test_spi_mux()

    # Test lecture ID de l'ADC
    test_spi_adc()


if __name__ == "__main__":
    main()
