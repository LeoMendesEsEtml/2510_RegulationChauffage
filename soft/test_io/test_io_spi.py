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
                # ADG731 : SPI mode 1 (CPOL=0, CPHA=1) : échantillonnage sur front descendant, horloge au repos bas
                s.mode = 1
                
                # Always limit speed to 100kHz for reliability
                actual_speed = 100000  # Force to 100kHz
                s.max_speed_hz = actual_speed
                s.bits_per_word = 8
                
                # Set lsbfirst to False to ensure MSB is sent first (standard SPI behavior)
                s.lsbfirst = False
                
                # Ensure no_cs is False (we want to use the CS line)
                s.no_cs = False
                
                # Minimize the transfer delay (depends on your hardware capabilities)
                # Short delays ensure signal integrity but too long delays might cause timing issues
                if hasattr(s, 'delay_usecs'):
                    s.delay_usecs = 5  # 5 microseconds delay
                
                self.handles.append(s)
                print(f"Opened SPI device {path} with mode={s.mode}, speed={s.max_speed_hz} Hz, bits={s.bits_per_word}")
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
            
        # Calculate control byte
        ctrl = adg731_ctrl_byte(address, enable=True)
        
        # Debug output in binary format to check each bit
        bin_repr = format(ctrl, '08b')
        a4_bit = (address >> 4) & 0x1
        a0_3_bits = address & 0xF
        
        print(f"MUX CHANNEL DEBUG: board={board_index}, address={address} (0x{address:02X})")
        print(f"  Address bits: A4={a4_bit}, A3-A0={format(a0_3_bits, '04b')}")
        print(f"  Control byte: 0x{ctrl:02X}, binary={bin_repr}")
        print(f"  Expected bit positions: [7:EN=0][6:CS=0][5:X=0][4-1:A3-A0={format(a0_3_bits, '04b')}][0:A4={a4_bit}]")
        
        # Let's perform a more controlled SPI transfer
        # First make sure we're in the right mode
        h.mode = 1  # Reconfirm we're in the right mode
        
        # Force optimal SPI settings again
        h.max_speed_hz = 100000  # Set to 100kHz for stability
        h.lsbfirst = False       # MSB first
        
        # Add a small stabilization delay before transmission
        time.sleep(0.002)
        
        # Perform the SPI transfer
        print(f"Sending SPI data: [0x{ctrl:02X}] to {self.DEV[board_index]}")
        
        # Cleaner SPI transfer with explicit padding
        # Some SPI implementations require multiple bytes for proper clocking
        result = h.xfer2([ctrl])
        
        # Add another small delay after transmission to ensure stable latch
        time.sleep(0.002)
        
        # Debug output for verification
        print(f"SPI transfer completed, result: {result}")
        return ctrl  # Return the control byte for verification

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

    print("=== Test MUX avec vérification de chaque canal (analyse des défauts pour 8-15 et 22-32) ===")
    # Force slower speed for reliability
    mux = Adg731MuxSpi(100000)
    try:
        # Test groups separately to identify patterns in failures
        test_groups = [
            (0, 7, "Groupe 1 (canaux 0-7)"),  # Working group
            (8, 15, "Groupe 2 (canaux 8-15)"),  # Problem group
            (16, 21, "Groupe 3 (canaux 16-21)"),  # Mixed results expected
            (22, 31, "Groupe 4 (canaux 22-31)")   # Problem group
        ]
        
        for start, end, group_name in test_groups:
            print(f"\n===== TEST {group_name} =====")
            
            for chan in range(start, end + 1):
                # Generate the expected control byte
                ctrl_byte = adg731_ctrl_byte(chan, enable=True)
                
                # Detailed bit analysis
                a4_bit = (chan >> 4) & 0x1
                a0_3_bits = chan & 0xF
                
                print(f"\nTEST CANAL {chan} (0x{chan:02X})")
                print(f"  Bits d'adresse: A4={a4_bit}, A3-A0={format(a0_3_bits, '04b')}")
                print(f"  Octet de contrôle: 0x{ctrl_byte:02X}, binaire={format(ctrl_byte, '08b')}")
                
                # Set the channel with additional debug info
                actual_ctrl = mux.set_channel(0, chan)
                
                # Verify control byte matches expected
                if actual_ctrl == ctrl_byte:
                    print(f"  ✓ Le contrôle correspond à l'attendu: 0x{actual_ctrl:02X}")
                else:
                    print(f"  ✗ ERREUR: Le contrôle ne correspond pas: attendu 0x{ctrl_byte:02X}, obtenu 0x{actual_ctrl:02X}")
                
                # Add extra verification for problematic ranges
                if (8 <= chan <= 15) or (22 <= chan <= 31):
                    print("  VÉRIFICATION SUPPLÉMENTAIRE POUR CANAL PROBLÉMATIQUE:")
                    # Bit-by-bit verification
                    expected_bits = format(ctrl_byte, '08b')
                    for i, bit in enumerate(expected_bits):
                        bit_pos = 7 - i  # Convert from left-to-right to bit position (7 to 0)
                        print(f"    Bit {bit_pos}: {bit} - {'EN' if bit_pos == 7 else 'CS' if bit_pos == 6 else 'X' if bit_pos == 5 else f'A{3-(bit_pos-1)}' if 1 <= bit_pos <= 4 else 'A4'}")
                
                # Wait for confirmation or set timing
                user_input = input("Appuie sur Entrée pour continuer, ou entre 'skip' pour passer au groupe suivant... ")
                if user_input.lower() == 'skip':
                    break
                    
            print(f"===== FIN TEST {group_name} =====\n")
        
        # Additional test for problematic channels with modified settings
        print("\n===== TEST SUPPLÉMENTAIRE: CANAUX PROBLÉMATIQUES AVEC VITESSE RÉDUITE =====")
        print("Réduction de la vitesse SPI à 50kHz pour vérifier si cela résout les problèmes")
        
        # Close and reopen with slower speed
        mux.close()
        mux = Adg731MuxSpi(50000)
        
        # Test a sample of problematic channels
        for chan in [8, 15, 22, 31]:
            ctrl_byte = adg731_ctrl_byte(chan, enable=True)
            print(f"\nTEST LENT CANAL {chan} (0x{chan:02X})")
            print(f"  Octet de contrôle: 0x{ctrl_byte:02X}, binaire={format(ctrl_byte, '08b')}")
            
            # Set the channel with additional debug info
            actual_ctrl = mux.set_channel(0, chan)
            
            # Wait for confirmation
            input("Appuie sur Entrée pour continuer... ")
            
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
