# -*- coding: utf-8 -*-
# file: resistance_simulation.py
"""
Module pour commander le MUX de simulation de résistance.
Permet d'appliquer une résistance simulée R_sim via le réseau de résistances.

Ce module gère:
- Calcul des commutateurs à activer pour obtenir la résistance désirée
- Commande du multiplexeur ADG731 pour la simulation
- Validation et vérification des valeurs appliquées
"""

import time
from typing import Optional, List, Dict, Tuple
from app.hw_mux_adg731 import Adg731MuxSpi

# Configuration des résistances disponibles (en ohms)
# Réseau de résistances simulées typique
RESISTANCE_NETWORK = {
    0: 1000,      # 1k ohm
    1: 2200,      # 2.2k ohm  
    2: 4700,      # 4.7k ohm
    3: 10000,     # 10k ohm
    4: 22000,     # 22k ohm
    5: 47000,     # 47k ohm
    6: 100000,    # 100k ohm
    7: 220000,    # 220k ohm
    8: 470000,    # 470k ohm
    9: 1000000,   # 1M ohm
    # Résistances parallèles pour valeurs intermédiaires
    10: 330,      # 330 ohm
    11: 680,      # 680 ohm
    12: 1500,     # 1.5k ohm
    13: 3300,     # 3.3k ohm
    14: 6800,     # 6.8k ohm
    15: 15000,    # 15k ohm
}

class ResistanceSimulationError(Exception):
    """Exception pour les erreurs de simulation de résistance"""
    pass

class ResistanceSimulator:
    """Contrôleur pour la simulation de résistance via MUX"""
    
    def __init__(self, speed_hz: int = 100000):
        """
        Initialise le simulateur de résistance
        
        :param speed_hz: Vitesse SPI pour le MUX
        """
        self.mux = None
        self.speed_hz = speed_hz
        self.current_resistance = None
        self.active_channels = []
        
        try:
            self.mux = Adg731MuxSpi(speed_hz=speed_hz)
            print(f"[SIM_R] Simulateur de résistance initialisé (SPI: {speed_hz} Hz)")
        except Exception as e:
            print(f"[SIM_R] ❌ Erreur d'initialisation du MUX: {e}")
            raise ResistanceSimulationError(f"Impossible d'initialiser le MUX: {e}")
    
    def close(self):
        """Ferme les connexions du simulateur"""
        if self.mux:
            try:
                self.mux.close()
                print("[SIM_R] Simulateur fermé")
            except Exception as e:
                print(f"[SIM_R] Erreur lors de la fermeture: {e}")
    
    def calculate_parallel_resistance(self, resistances: List[float]) -> float:
        """
        Calcule la résistance équivalente de résistances en parallèle
        
        :param resistances: Liste des résistances en parallèle
        :return: Résistance équivalente
        """
        if not resistances:
            return float('inf')
        
        if len(resistances) == 1:
            return resistances[0]
        
        # Formule: 1/Req = 1/R1 + 1/R2 + ... + 1/Rn
        reciprocal_sum = sum(1.0 / r for r in resistances)
        return 1.0 / reciprocal_sum
    
    def find_best_resistance_combination(self, target_resistance: float, tolerance: float = 0.05) -> Optional[List[int]]:
        """
        Trouve la meilleure combinaison de résistances pour atteindre la valeur cible
        
        :param target_resistance: Résistance cible en ohms
        :param tolerance: Tolérance relative (0.05 = 5%)
        :return: Liste des canaux à activer ou None si impossible
        """
        best_combination = None
        best_error = float('inf')
        
        # Test de toutes les combinaisons possibles (force brute optimisée)
        max_channels = len(RESISTANCE_NETWORK)
        
        # Test des résistances individuelles d'abord
        for channel, resistance in RESISTANCE_NETWORK.items():
            error = abs(resistance - target_resistance) / target_resistance
            if error < best_error and error <= tolerance:
                best_error = error
                best_combination = [channel]
        
        # Test des combinaisons de 2 résistances en parallèle
        if best_error > tolerance:
            for i in range(max_channels):
                for j in range(i + 1, max_channels):
                    r1 = RESISTANCE_NETWORK[i]
                    r2 = RESISTANCE_NETWORK[j]
                    parallel_r = self.calculate_parallel_resistance([r1, r2])
                    
                    error = abs(parallel_r - target_resistance) / target_resistance
                    if error < best_error and error <= tolerance:
                        best_error = error
                        best_combination = [i, j]
        
        # Test des combinaisons de 3 résistances si nécessaire
        if best_error > tolerance:
            for i in range(max_channels):
                for j in range(i + 1, max_channels):
                    for k in range(j + 1, max_channels):
                        r1 = RESISTANCE_NETWORK[i]
                        r2 = RESISTANCE_NETWORK[j]
                        r3 = RESISTANCE_NETWORK[k]
                        parallel_r = self.calculate_parallel_resistance([r1, r2, r3])
                        
                        error = abs(parallel_r - target_resistance) / target_resistance
                        if error < best_error and error <= tolerance:
                            best_error = error
                            best_combination = [i, j, k]
        
        if best_combination:
            actual_resistance = self.get_combination_resistance(best_combination)
            error_percent = abs(actual_resistance - target_resistance) / target_resistance * 100
            print(f"[SIM_R] Combinaison trouvée: canaux {best_combination}")
            print(f"[SIM_R] Résistance réelle: {actual_resistance:.1f}Ω (cible: {target_resistance:.1f}Ω)")
            print(f"[SIM_R] Erreur: {error_percent:.1f}%")
        
        return best_combination
    
    def get_combination_resistance(self, channels: List[int]) -> float:
        """
        Calcule la résistance d'une combinaison de canaux
        
        :param channels: Liste des canaux actifs
        :return: Résistance équivalente
        """
        resistances = [RESISTANCE_NETWORK[ch] for ch in channels if ch in RESISTANCE_NETWORK]
        return self.calculate_parallel_resistance(resistances)
    
    def apply_resistance_simulation(self, target_resistance: float) -> bool:
        """
        Applique une résistance simulée via le MUX
        
        :param target_resistance: Résistance à simuler en ohms
        :return: True si succès, False sinon
        """
        print(f"\n[SIM_R] === APPLICATION RÉSISTANCE SIMULÉE ===")
        print(f"[SIM_R] Résistance cible: {target_resistance:.2f} Ω")
        
        if self.mux is None:
            print("[SIM_R] ❌ MUX non initialisé")
            return False
        
        # Validation de la plage de résistance
        min_resistance = min(RESISTANCE_NETWORK.values())
        max_resistance = max(RESISTANCE_NETWORK.values())
        
        if target_resistance < min_resistance * 0.1:  # Résistances parallèles peuvent aller plus bas
            print(f"[SIM_R] ❌ Résistance trop faible: {target_resistance:.1f}Ω < {min_resistance * 0.1:.1f}Ω")
            return False
        
        if target_resistance > max_resistance:
            print(f"[SIM_R] ❌ Résistance trop élevée: {target_resistance:.1f}Ω > {max_resistance:.1f}Ω")
            return False
        
        # Recherche de la meilleure combinaison
        combination = self.find_best_resistance_combination(target_resistance, tolerance=0.10)  # 10% de tolérance
        
        if combination is None:
            print(f"[SIM_R] ❌ Aucune combinaison trouvée pour {target_resistance:.1f}Ω")
            print(f"[SIM_R] Résistances disponibles: {sorted(RESISTANCE_NETWORK.values())}")
            return False
        
        # Désactivation de tous les canaux d'abord
        try:
            for board in range(4):  # 4 cartes MUX maximum
                for channel in range(32):  # 32 canaux par carte
                    try:
                        self.mux.set_channel(board, channel)  # Désactivation par défaut
                    except Exception:
                        pass  # Ignore les erreurs de cartes non présentes
            
            time.sleep(0.01)  # Délai de stabilisation
            
            # Activation des canaux sélectionnés
            for channel in combination:
                board_index = channel // 32  # Quelle carte MUX
                channel_addr = channel % 32   # Quelle adresse sur la carte
                
                print(f"[SIM_R] Activation canal {channel} (carte {board_index}, adresse {channel_addr})")
                self.mux.set_channel(board_index, channel_addr)
                time.sleep(0.001)  # Petit délai entre les commutations
            
            # Mémorisation de l'état actuel
            self.active_channels = combination.copy()
            self.current_resistance = self.get_combination_resistance(combination)
            
            print(f"[SIM_R] ✅ Résistance appliquée: {self.current_resistance:.2f}Ω")
            return True
            
        except Exception as e:
            print(f"[SIM_R] ❌ Erreur lors de l'application: {e}")
            return False
    
    def get_current_simulation(self) -> Dict[str, any]:
        """
        Retourne l'état actuel de la simulation
        
        :return: Dictionnaire avec les informations actuelles
        """
        return {
            "resistance": self.current_resistance,
            "active_channels": self.active_channels.copy() if self.active_channels else [],
            "network": RESISTANCE_NETWORK.copy()
        }
    
    def validate_resistance_applied(self, expected_resistance: float, tolerance: float = 0.10) -> bool:
        """
        Valide que la résistance appliquée correspond à l'attendu
        
        :param expected_resistance: Résistance attendue
        :param tolerance: Tolérance relative
        :return: True si la résistance est dans la tolérance
        """
        if self.current_resistance is None:
            print("[SIM_R] ❌ Aucune résistance actuellement appliquée")
            return False
        
        error = abs(self.current_resistance - expected_resistance) / expected_resistance
        
        if error <= tolerance:
            print(f"[SIM_R] ✅ Validation OK: {self.current_resistance:.2f}Ω (attendu: {expected_resistance:.2f}Ω, erreur: {error*100:.1f}%)")
            return True
        else:
            print(f"[SIM_R] ❌ Validation KO: {self.current_resistance:.2f}Ω (attendu: {expected_resistance:.2f}Ω, erreur: {error*100:.1f}%)")
            return False
    
    def reset_simulation(self):
        """Remet la simulation à zéro (désactive tous les canaux)"""
        print("[SIM_R] Remise à zéro de la simulation")
        
        if self.mux is None:
            return
        
        try:
            # Désactivation de tous les canaux
            for board in range(4):
                for channel in range(32):
                    try:
                        self.mux.set_channel(board, channel)
                    except Exception:
                        pass
            
            self.active_channels = []
            self.current_resistance = None
            print("[SIM_R] ✅ Simulation remise à zéro")
            
        except Exception as e:
            print(f"[SIM_R] ❌ Erreur lors de la remise à zéro: {e}")

# Fonction principale d'application de résistance
def apply_resistance_simulation(resistance_ohm: float) -> bool:
    """
    Fonction utilitaire pour appliquer une résistance simulée
    
    :param resistance_ohm: Résistance à appliquer en ohms
    :return: True si succès
    """
    simulator = None
    try:
        simulator = ResistanceSimulator()
        return simulator.apply_resistance_simulation(resistance_ohm)
    except Exception as e:
        print(f"[SIM_R] ❌ Erreur dans apply_resistance_simulation: {e}")
        return False
    finally:
        if simulator:
            simulator.close()

# Test du module (à des fins de développement)
if __name__ == "__main__":
    print("=== Test du simulateur de résistance ===")
    
    # Test des calculs de résistances parallèles
    sim = ResistanceSimulator()
    
    # Test 1: Résistance simple
    print("\nTest 1: Application de 1000Ω")
    success = sim.apply_resistance_simulation(1000.0)
    print(f"Résultat: {'Succès' if success else 'Échec'}")
    
    # Test 2: Résistance complexe nécessitant des parallèles
    print("\nTest 2: Application de 667Ω (parallèle de 1k et 2k)")
    success = sim.apply_resistance_simulation(667.0)
    print(f"Résultat: {'Succès' if success else 'Échec'}")
    
    # Test 3: Validation
    print("\nTest 3: Validation de la résistance appliquée")
    if sim.current_resistance:
        valid = sim.validate_resistance_applied(667.0, tolerance=0.15)
        print(f"Validation: {'OK' if valid else 'KO'}")
    
    # Nettoyage
    sim.reset_simulation()
    sim.close()