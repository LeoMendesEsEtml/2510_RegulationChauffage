"""
Gestionnaire de LED frontale avec patterns d'erreur
Module pour la gestion des clignotements et états de la LED frontale
"""

import threading
import time
from periphery import GPIO


class LedErrorIndicator:
    """Gestionnaire de LED avec patterns d'erreur"""
    
    # Définition des patterns d'erreur (temps de base pour clignotement)
    BASE_BLINK_TIME = 0.5  # 500ms ON/OFF pour un clignotement
    CYCLE_TIME = 10.0      # Cycle de 10 secondes
    
    ERROR_PATTERNS = {
        # LED normalement allumée en continu
        'normal': 'solid_on',
        
        # LED éteinte (standby)
        'standby': 'solid_off',
        
        # Clignotement continu pendant séquence de mesure
        'sequence_running': 'continuous_blink',
        
        # Patterns d'erreur : X clignotements sur 10 secondes puis répétition
        'no_internet': 1,        # 1 clignotement = Pas de connexion Internet
        'api_failed': 2,         # 2 clignotements = Erreur API (connexion ou réponse)
        'measure_failed': 3,     # 3 clignotements = Erreur de mesure ADC/résistance
        'critical_error': 4,     # 4 clignotements = Erreur critique système
        'config_error': 5        # 5 clignotements = Erreur de configuration
    }
    
    def __init__(self, gpio_chip_path, led_pin):
        """Initialise le gestionnaire LED"""
        self.led = GPIO(gpio_chip_path, led_pin, "out")
        self.current_pattern = 'normal'
        self.pattern_thread = None
        self.pattern_stop = threading.Event()
        self.led_lock = threading.Lock()
        
    def set_pattern(self, pattern_name):
        """Change le pattern de clignotement"""
        if pattern_name not in self.ERROR_PATTERNS:
            print(f"[LED] Pattern inconnu: {pattern_name}")
            return
        
        # Ne rien faire si c'est déjà le pattern actuel
        if self.current_pattern == pattern_name:
            return
            
        with self.led_lock:
            # Arrêt du pattern précédent
            if self.pattern_thread and self.pattern_thread.is_alive():
                self.pattern_stop.set()
                self.pattern_thread.join(timeout=1)
            
            # Démarrage du nouveau pattern
            self.current_pattern = pattern_name
            self.pattern_stop.clear()
            
            pattern_value = self.ERROR_PATTERNS[pattern_name]
            
            if pattern_value == 'solid_on':
                # LED allumée en continu
                self.led.write(True)
                print(f"[LED] Pattern activé: {pattern_name} (LED allumée)")
            elif pattern_value == 'solid_off':
                # LED éteinte en continu
                self.led.write(False)
                print(f"[LED] Pattern activé: {pattern_name} (LED éteinte)")
            elif pattern_value == 'continuous_blink':
                # Clignotement continu
                self.pattern_thread = threading.Thread(target=self._continuous_blink, daemon=True)
                self.pattern_thread.start()
                print(f"[LED] Pattern activé: {pattern_name} (clignotement continu)")
            elif isinstance(pattern_value, int):
                # Pattern d'erreur avec X clignotements
                self.pattern_thread = threading.Thread(target=self._error_pattern, args=(pattern_value,), daemon=True)
                self.pattern_thread.start()
                print(f"[LED] Pattern activé: {pattern_name} ({pattern_value} clignotement(s) sur 10s)")
    
    def _continuous_blink(self):
        """Clignotement continu pendant séquence"""
        while not self.pattern_stop.is_set():
            try:
                self.led.write(True)
                if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                    break
                self.led.write(False)
                if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                    break
            except Exception as e:
                print(f"[LED] Erreur clignotement continu: {e}")
                break
    
    def _error_pattern(self, blink_count):
        """Pattern d'erreur : X clignotements sur 10 secondes puis répétition"""
        while not self.pattern_stop.is_set():
            try:
                # Phase clignotements
                for i in range(blink_count):
                    if self.pattern_stop.is_set():
                        break
                    # ON
                    self.led.write(True)
                    if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                        break
                    # OFF
                    self.led.write(False)
                    if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                        break
                
                if self.pattern_stop.is_set():
                    break
                
                # Phase d'attente (9 temps vides pour compléter les 10 secondes)
                # Temps utilisé pour clignotements : blink_count * (0.5 + 0.5) = blink_count secondes
                # Temps restant : 10 - blink_count secondes
                remaining_time = self.CYCLE_TIME - (blink_count * 2 * self.BASE_BLINK_TIME)
                if remaining_time > 0:
                    self.led.write(False)  # LED éteinte pendant l'attente
                    if self.pattern_stop.wait(remaining_time):
                        break
                        
            except Exception as e:
                print(f"[LED] Erreur pattern d'erreur: {e}")
                break
    
    def set_solid(self, state):
        """LED fixe ON ou OFF"""
        with self.led_lock:
            if self.pattern_thread and self.pattern_thread.is_alive():
                self.pattern_stop.set()
                self.pattern_thread.join(timeout=1)
            try:
                self.led.write(state)
                print(f"[LED] État fixe: {'ON' if state else 'OFF'}")
            except Exception as e:
                print(f"[LED] Erreur état fixe: {e}")
    
    def close(self):
        """Ferme proprement la LED"""
        with self.led_lock:
            if self.pattern_thread and self.pattern_thread.is_alive():
                self.pattern_stop.set()
                self.pattern_thread.join(timeout=1)
            try:
                self.led.write(False)
                self.led.close()
                print("[LED] LED fermée")
            except Exception as e:
                print(f"[LED] Erreur fermeture: {e}")


def create_led_indicator(gpio_chip_path, led_pin):
    """Factory function pour créer une instance LedErrorIndicator"""
    try:
        led_indicator = LedErrorIndicator(gpio_chip_path, led_pin)
        led_indicator.set_pattern('normal')  # LED allumée par défaut
        print("[LED] Gestionnaire LED initialisé avec succès")
        return led_indicator
    except Exception as e:
        print(f"[LED] Erreur lors de l'initialisation: {e}")
        return None