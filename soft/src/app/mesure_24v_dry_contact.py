#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mesure I/O 24V - Contacts secs
Test simple des entrées/sorties 24V pour validation des contacts secs
"""

import time
from periphery import GPIO
from pins_cm5 import GPIO_CHIP_PATH

# Pins I/O 24V
CM_24V_OUT_1 = 13    # Sortie 24V canal 1
CM_24V_SENSE_1 = 14  # Sense 24V canal 1
CM_24V_OUT_2 = 15    # Sortie 24V canal 2
CM_24V_SENSE_2 = 16  # Sense 24V canal 2

# Variables globales résultat
io_24v_ch1_ok = 0  # 0=ouvert, 1=fermé
io_24v_ch2_ok = 0  # 0=ouvert, 1=fermé

def test_24v_dry_contact():
    """
    Test des contacts secs I/O 24V
    
    Met à jour les variables globales io_24v_ch1_ok et io_24v_ch2_ok
    Affiche le résultat pour chaque canal
    
    Returns:
        tuple: (ch1_state, ch2_state) - 0=ouvert, 1=fermé
    """
    global io_24v_ch1_ok, io_24v_ch2_ok
    
    print("\n[TEST-24V] === Test contacts secs I/O 24V ===")
    
    try:
        # Configuration GPIO
        out1 = GPIO(GPIO_CHIP_PATH, CM_24V_OUT_1, "out")
        out2 = GPIO(GPIO_CHIP_PATH, CM_24V_OUT_2, "out") 
        sense1 = GPIO(GPIO_CHIP_PATH, CM_24V_SENSE_1, "in")
        sense2 = GPIO(GPIO_CHIP_PATH, CM_24V_SENSE_2, "in")
        
        # Test Canal 1
        out1.write(False)  # Mise au repos
        time.sleep(0.01)
        out1.write(True)   # Activation
        time.sleep(0.02)   # Stabilisation
        state1 = sense1.read()
        out1.write(False)  # Désactivation
        
        if state1:
            print("[TEST-24V] Canal 1: fermé")
            io_24v_ch1_ok = 1
        else:
            print("[TEST-24V] Canal 1: ouvert")
            io_24v_ch1_ok = 0
        
        # Test Canal 2
        out2.write(False)  # Mise au repos
        time.sleep(0.01)
        out2.write(True)   # Activation
        time.sleep(0.02)   # Stabilisation
        state2 = sense2.read()
        out2.write(False)  # Désactivation
        
        if state2:
            print("[TEST-24V] Canal 2: fermé")
            io_24v_ch2_ok = 1
        else:
            print("[TEST-24V] Canal 2: ouvert")
            io_24v_ch2_ok = 0
        
        # Nettoyage
        out1.close()
        out2.close()
        sense1.close()
        sense2.close()
        
        print(f"[TEST-24V] Résultat: CH1={io_24v_ch1_ok}, CH2={io_24v_ch2_ok}")
        
        return (io_24v_ch1_ok, io_24v_ch2_ok)
        
    except Exception as e:
        print(f"[TEST-24V] Erreur: {e}")
        io_24v_ch1_ok = 0
        io_24v_ch2_ok = 0
        return (0, 0)

def get_dry_contact_status():
    """
    Retourne l'état actuel des contacts secs
    
    Returns:
        dict: {"ch1": 0|1, "ch2": 0|1}
    """
    return {
        "ch1": io_24v_ch1_ok,
        "ch2": io_24v_ch2_ok
    }