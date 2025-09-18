# -*- coding: utf-8 -*-
"""
@file        front_led_management.py
@brief       Gestionnaire de LED frontale avec patterns d'erreur.
@details     Ce module fournit une classe pour gérer les clignotements et états
             de la LED frontale avec différents patterns d'erreur. Supporte
             les modes continus, les clignotements d'erreur et la gestion
             thread-safe des patterns LED.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations

# Gestion multithread pour les patterns asynchrones
import threading
# Fonctions temporelles pour les délais et temporisations
import time
# Abstraction GPIO (bibliothèque periphery)
from periphery import GPIO

# ---------------------------------------------------------------------------
# Classes principales
# ---------------------------------------------------------------------------

class LedErrorIndicator:
    """
    @brief   Gestionnaire de LED avec patterns d'erreur.
    @details Classe pour contrôler une LED frontale avec différents patterns
             de clignotement selon les états du système. Supporte les modes
             normal, standby, séquence en cours et divers patterns d'erreur
             avec clignotements codifiés.
    """
    
    # Définition des patterns d'erreur (temps de base pour clignotement)
    # 200ms ON/OFF pour un clignotement plus rapide [s]
    BASE_BLINK_TIME = 0.2
    # Cycle de 10 secondes [s]
    CYCLE_TIME = 10.0
    
    # Dictionnaire des patterns disponibles
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
        """
        @brief   Initialise le gestionnaire LED.
        @details Configure l'interface GPIO pour la LED, initialise les variables
                 de thread et les mécanismes de synchronisation thread-safe.

        @param   gpio_chip_path Chemin vers le périphérique GPIO.
        @param   led_pin        Numéro de pin de la LED.
        """
        # Initialisation de l'interface GPIO pour la LED
        self.led = GPIO(gpio_chip_path, led_pin, "out")
        # Pattern actuel (par défaut normal)
        self.current_pattern = 'normal'
        # Thread pour le pattern en cours
        self.pattern_thread = None
        # Événement pour arrêter le pattern
        self.pattern_stop = threading.Event()
        # Verrou pour la synchronisation thread-safe
        self.led_lock = threading.Lock()
        
    def set_pattern(self, pattern_name):
        """
        @brief   Change le pattern de clignotement.
        @details Arrête le pattern précédent et démarre le nouveau selon
                 le nom fourni. Gère les modes continus, clignotements
                 d'erreur et états fixes de manière thread-safe.

        @param   pattern_name Nom du pattern à activer.
        """
        # Vérification de l'existence du pattern
        if pattern_name not in self.ERROR_PATTERNS:
            print(f"[LED] Pattern inconnu: {pattern_name}")
            return
        
        # Ne rien faire si c'est déjà le pattern actuel
        if self.current_pattern == pattern_name:
            return
            
        # Section critique thread-safe
        with self.led_lock:
            # Arrêt du pattern précédent
            # Vérification de l'existence et de l'activité du thread
            if self.pattern_thread and self.pattern_thread.is_alive():
                # Demande d'arrêt du thread
                self.pattern_stop.set()
                # Attente de la fin du thread avec timeout
                self.pattern_thread.join(timeout=1)
            
            # Démarrage du nouveau pattern
            # Stockage du nouveau pattern courant
            self.current_pattern = pattern_name
            # Remise à zéro de l'événement d'arrêt
            self.pattern_stop.clear()
            
            # Récupération de la valeur du pattern
            pattern_value = self.ERROR_PATTERNS[pattern_name]
            
            # Gestion des différents types de patterns
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
                # Création du thread pour clignotement continu
                self.pattern_thread = threading.Thread(target=self._continuous_blink, daemon=True)
                # Démarrage du thread
                self.pattern_thread.start()
                print(f"[LED] Pattern activé: {pattern_name} (clignotement continu)")
            elif isinstance(pattern_value, int):
                # Pattern d'erreur avec X clignotements
                # Création du thread pour pattern d'erreur
                self.pattern_thread = threading.Thread(target=self._error_pattern, args=(pattern_value,), daemon=True)
                # Démarrage du thread
                self.pattern_thread.start()
                print(f"[LED] Pattern activé: {pattern_name} ({pattern_value} clignotement(s) sur 10s)")
    
    def _continuous_blink(self):
        """
        @brief   Clignotement continu pendant séquence.
        @details Méthode privée exécutée dans un thread séparé pour gérer
                 le clignotement continu de la LED. Alterne entre ON/OFF
                 avec le temps de base défini jusqu'à réception d'un signal d'arrêt.
        """
        # Boucle de clignotement jusqu'à demande d'arrêt
        while not self.pattern_stop.is_set():
            try:
                # Allumage de la LED
                self.led.write(True)
                # Attente avec vérification d'arrêt
                if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                    break
                # Extinction de la LED
                self.led.write(False)
                # Attente avec vérification d'arrêt
                if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                    break
            except Exception as e:
                # Gestion des erreurs de clignotement
                print(f"[LED] Erreur clignotement continu: {e}")
                break
    
    def _error_pattern(self, blink_count):
        """
        @brief   Pattern d'erreur avec nombre de clignotements défini.
        @details Méthode privée pour gérer les patterns d'erreur. Effectue
                 un nombre spécifique de clignotements puis attend jusqu'à
                 compléter un cycle de 10 secondes avant de répéter.

        @param   blink_count Nombre de clignotements à effectuer par cycle.
        """
        # Boucle de pattern d'erreur jusqu'à demande d'arrêt
        while not self.pattern_stop.is_set():
            try:
                # Phase clignotements
                # Boucle pour le nombre de clignotements demandé
                for i in range(blink_count):
                    # Vérification d'arrêt
                    if self.pattern_stop.is_set():
                        break
                    # ON
                    # Allumage de la LED
                    self.led.write(True)
                    # Attente avec vérification d'arrêt
                    if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                        break
                    # OFF
                    # Extinction de la LED
                    self.led.write(False)
                    # Attente avec vérification d'arrêt
                    if self.pattern_stop.wait(self.BASE_BLINK_TIME):
                        break
                
                # Vérification d'arrêt avant la phase d'attente
                if self.pattern_stop.is_set():
                    break
                
                # Phase d'attente (9 temps vides pour compléter les 10 secondes)
                # Temps utilisé pour clignotements : blink_count * (0.5 + 0.5) = blink_count secondes
                # Temps restant : 10 - blink_count secondes
                # Calcul du temps restant pour compléter le cycle
                remaining_time = self.CYCLE_TIME - (blink_count * 2 * self.BASE_BLINK_TIME)
                # Attente seulement si du temps reste
                if remaining_time > 0:
                    # LED éteinte pendant l'attente
                    self.led.write(False)
                    # Attente du temps restant avec vérification d'arrêt
                    if self.pattern_stop.wait(remaining_time):
                        break
                        
            except Exception as e:
                # Gestion des erreurs de pattern d'erreur
                print(f"[LED] Erreur pattern d'erreur: {e}")
                break
    
    def set_solid(self, state):
        """
        @brief   LED fixe ON ou OFF.
        @details Force la LED dans un état fixe (allumée ou éteinte) en
                 arrêtant tout pattern en cours. Utilisé pour des états
                 temporaires ou des tests.

        @param   state État demandé (True=ON, False=OFF).
        """
        # Section critique thread-safe
        with self.led_lock:
            # Arrêt du thread de pattern si actif
            if self.pattern_thread and self.pattern_thread.is_alive():
                # Demande d'arrêt du thread
                self.pattern_stop.set()
                # Attente de la fin du thread avec timeout
                self.pattern_thread.join(timeout=1)
            try:
                # Application de l'état demandé
                self.led.write(state)
                # Affichage de confirmation
                print(f"[LED] État fixe: {'ON' if state else 'OFF'}")
            except Exception as e:
                # Gestion des erreurs d'écriture GPIO
                print(f"[LED] Erreur état fixe: {e}")
    
    def close(self):
        """
        @brief   Ferme proprement la LED.
        @details Arrête tous les threads en cours, éteint la LED et ferme
                 l'interface GPIO. À appeler avant la fin du programme pour
                 un nettoyage propre des ressources.
        """
        # Section critique thread-safe
        with self.led_lock:
            # Arrêt du thread de pattern si actif
            if self.pattern_thread and self.pattern_thread.is_alive():
                # Demande d'arrêt du thread
                self.pattern_stop.set()
                # Attente de la fin du thread avec timeout
                self.pattern_thread.join(timeout=1)
            try:
                # Extinction de la LED
                self.led.write(False)
                # Fermeture de l'interface GPIO
                self.led.close()
                # Confirmation de fermeture
                print("[LED] LED fermée")
            except Exception as e:
                # Gestion des erreurs de fermeture
                print(f"[LED] Erreur fermeture: {e}")


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def create_led_indicator(gpio_chip_path, led_pin):
    """
    @brief   Factory function pour créer une instance LedErrorIndicator.
    @details Fonction utilitaire qui encapsule la création et l'initialisation
             d'un gestionnaire LED. Gère les erreurs d'initialisation et
             configure automatiquement le pattern normal par défaut.

    @param   gpio_chip_path Chemin vers le périphérique GPIO.
    @param   led_pin        Numéro de pin de la LED.

    @return  Instance de LedErrorIndicator si succès, None sinon.
    """
    try:
        # Création de l'instance du gestionnaire LED
        led_indicator = LedErrorIndicator(gpio_chip_path, led_pin)
        # LED allumée par défaut
        led_indicator.set_pattern('normal')
        # Confirmation de l'initialisation
        print("[LED] Gestionnaire LED initialisé avec succès")
        return led_indicator
    except Exception as e:
        # Gestion des erreurs d'initialisation
        print(f"[LED] Erreur lors de l'initialisation: {e}")
        return None