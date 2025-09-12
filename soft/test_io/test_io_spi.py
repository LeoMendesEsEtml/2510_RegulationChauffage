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
    """
    Calculate control byte for ADG731 mux.
    
    ADG731 control byte layout (DB7..DB0):
    [7] EN: Enable bit (active low: 0=enable, 1=disable all switches)
    [6] CS: Chip select (must be 0 to write)
    [5] X: Unused bit (set to 0)
    [4] A3: Address bit 3
    [3] A2: Address bit 2
    [2] A1: Address bit 1
    [1] A0: Address bit 0
    [0] A4: Address bit 4 (MSB of address - in LSB position)
    
    The unusual bit order (A4 in position 0) requires special attention
    for addresses 16-31 (where A4=1).
    """
    if not 0 <= address <= 31:
        raise ValueError(f"address {address} out of range (0-31)")
    
    # Calculate individual bits
    en = 0 if enable else 1     # EN is active low: 0=enable, 1=disable all
    cs = 0                      # Must be 0 to write
    x = 0                       # Unused bit
    
    # Split address bits
    a4 = (address >> 4) & 0x1   # Extract A4 (bit 4) - goes to position 0
    a0_3 = address & 0xF        # Extract A0-A3 (bits 0-3)
    
    # Extract individual address bits from a0_3
    a3 = (a0_3 >> 3) & 0x1      # A3 - goes to position 4
    a2 = (a0_3 >> 2) & 0x1      # A2 - goes to position 3
    a1 = (a0_3 >> 1) & 0x1      # A1 - goes to position 2
    a0 = a0_3 & 0x1             # A0 - goes to position 1
    
    # Assemble control byte bit by bit to ensure correct positioning
    ctrl = (en << 7) | (cs << 6) | (x << 5) | (a3 << 4) | (a2 << 3) | (a1 << 2) | (a0 << 1) | a4
    
    # Double-check bit positions for addresses that use A4 (16-31)
    if address >= 16:
        # Verify that A4 bit is set in the control byte
        if (ctrl & 0x01) != 1:
            print(f"WARNING: A4 bit not correctly set for address {address}")
    
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
                # CRITICAL: ADG731 requires SPI mode 0 (CPOL=0, CPHA=0)
                # Clock idles low, data sampled on rising edge
                s.mode = 0
                
                # Reduce speed for better reliability
                actual_speed = 50000  # Force to 50kHz for stability
                s.max_speed_hz = actual_speed
                s.bits_per_word = 8
                
                # Set lsbfirst to False to ensure MSB is sent first (standard SPI behavior)
                s.lsbfirst = False
                
                # Ensure no_cs is False (we want to use the CS line)
                s.no_cs = False
                
                # Add significant delay to ensure stable CS transitions
                if hasattr(s, 'delay_usecs'):
                    s.delay_usecs = 100  # 100 microseconds delay
                
                # Add loop delay for settling time
                s.loop_delay = 10  # Microseconds between repeated transfers
                
                self.handles.append(s)
                print(f"Opened SPI device {path} with mode={s.mode}, speed={s.max_speed_hz} Hz, bits={s.bits_per_word}, delay={s.delay_usecs if hasattr(s, 'delay_usecs') else 'default'} µs")
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
        
        # Reconfirm critical SPI settings before each transfer
        h.mode = 0  # CRITICAL: Using mode 0 (CPOL=0, CPHA=0)
        h.max_speed_hz = 50000  # 50kHz for stability
        h.lsbfirst = False  # MSB first
        
        # Add stabilization delay before transmission
        time.sleep(0.005)  # 5ms pre-transmission delay
        
        # Use a properly formatted command sequence with padding
        # Some hardware requires extra padding bytes for proper clock generation
        command = [ctrl]
        
        # Add a pre-command delay to ensure CS line stability
        if hasattr(h, 'delay_usecs'):
            original_delay = h.delay_usecs
            h.delay_usecs = 100  # Temporarily increase to 100µs
        
        print(f"Sending SPI data: {[hex(x) for x in command]} to {self.DEV[board_index]}")
        
        # Execute SPI transfer with padding - using xfer2 which keeps CS active throughout
        # Use multiple identical bytes to ensure proper clocking for problematic channels
        if address >= 8:  # For problematic channels (8+)
            # Send the command twice to ensure proper clocking
            result = h.xfer2([ctrl, ctrl])
            print(f"SPI transfer completed, sent duplicated command: {[hex(x) for x in [ctrl, ctrl]]}, result: {[hex(x) for x in result]}")
        else:
            # Standard single-byte transfer for working channels
            result = h.xfer2([ctrl])
            print(f"SPI transfer completed, result: {[hex(x) for x in result]}")
        
        # Restore original delay if changed
        if hasattr(h, 'delay_usecs'):
            h.delay_usecs = original_delay
        
        # Add post-transmission delay to ensure data latches properly
        time.sleep(0.005)  # 5ms post-transmission delay
        
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

    print("\n=== TEST MUX avec SPI MODE 0 et VITESSE RÉDUITE ===")
    # Force very slow speed and correct mode for reliability
    mux = Adg731MuxSpi(50000)  # 50kHz
    try:
        print("\n=== VÉRIFICATION DE TOUS LES CANAUX INDIVIDUELLEMENT ===")
        
        # Test channels one by one for detailed analysis
        for chan in range(32):  # Test all 32 channels (0-31)
            ctrl_byte = adg731_ctrl_byte(chan, enable=True)
            
            # Detailed bit analysis
            a4_bit = (chan >> 4) & 0x1
            a0_3_bits = chan & 0xF
            
            print(f"\n=== TEST CANAL {chan} (0x{chan:02X}) ===")
            print(f"Adresse binaire: {format(chan, '05b')} (A4={a4_bit}, A3-A0={format(a0_3_bits, '04b')})")
            print(f"Octet de contrôle: 0x{ctrl_byte:02X}, binaire={format(ctrl_byte, '08b')}")
            
            # Perform detailed bit-by-bit verification
            print("Vérification bit par bit du mot de contrôle:")
            bit_names = ["A4", "A0", "A1", "A2", "A3", "X", "CS", "EN"]
            expected_values = [
                a4_bit,                     # A4 (bit 0)
                chan & 0x1,                 # A0 (bit 1)
                (chan >> 1) & 0x1,          # A1 (bit 2)
                (chan >> 2) & 0x1,          # A2 (bit 3)
                (chan >> 3) & 0x1,          # A3 (bit 4)
                0,                          # X (bit 5)
                0,                          # CS (bit 6)
                0 if True else 1            # EN (bit 7)
            ]
            
            for i in range(8):
                bit_pos = i
                bit_val = (ctrl_byte >> i) & 0x1
                print(f"  Bit {bit_pos}: {bit_val} [{bit_names[i]}] (attendu: {expected_values[i]})")
            
            # Set the channel
            print("\nEnvoi de la commande SPI...")
            actual_ctrl = mux.set_channel(0, chan)
            
            # Verify control byte matches expected
            if actual_ctrl == ctrl_byte:
                print(f"✓ Contrôle OK: 0x{actual_ctrl:02X}")
            else:
                print(f"✗ ERREUR: Contrôle attendu 0x{ctrl_byte:02X}, obtenu 0x{actual_ctrl:02X}")
            
            # Add prompt for oscilloscope analysis
            if chan in [0, 7, 8, 15, 16, 22, 31]:  # Key channels to check
                input(f"\n>>> CANAL {chan}: Vérifiez l'oscilloscope et appuyez sur Entrée pour continuer...")
            else:
                time.sleep(0.5)  # Brief pause between channels
            
            print(f"=== FIN TEST CANAL {chan} ===")
        
        # Additional test for problematic channels with slower speed
        print("\n=== TEST SUPPLÉMENTAIRE: CANAUX PROBLÉMATIQUES ===")
        
        # Test specific problematic channels more carefully
        problem_channels = [8, 15, 22, 31]
        for chan in problem_channels:
            print(f"\n>>> TEST APPROFONDI CANAL {chan} <<<")
            
            # Set channel and wait for analysis
            ctrl_byte = mux.set_channel(0, chan)
            
            # Add detailed oscilloscope checking prompt
            input(f"Vérifiez l'oscilloscope pour le canal {chan} (ctrl=0x{ctrl_byte:02X}) et appuyez sur Entrée...")
            
            # Try sending the command again with different timing
            print(f"Nouvel essai avec timing modifié pour canal {chan}...")
            time.sleep(0.01)  # Longer pre-delay
            ctrl_byte = mux.set_channel(0, chan)
            time.sleep(0.01)  # Longer post-delay
            
            input("Vérifiez l'oscilloscope après le second essai et appuyez sur Entrée...")
            
        print("\n=== TEST DE BALAYAGE RAPIDE ===")
        # Test rapid scanning of all channels
        for _ in range(3):  # Do 3 sweeps
            print("\nBalayage de tous les canaux...")
            for chan in range(32):
                mux.set_channel(0, chan)
                time.sleep(0.1)  # Brief pause between channels
            print("Balayage terminé")
            
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
