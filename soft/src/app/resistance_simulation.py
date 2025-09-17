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
from app.resistance_mapping import get_channel_mux_map, find_closest_channel

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
            print(f"[SIM_R] ERREUR d'initialisation du MUX: {e}")
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
    
    def apply_resistance_simulation(self, target_resistance: float, measurement_channel: int, sensor_type: str = "Ni1000 TK5000") -> bool:
        """
        Applique une résistance simulée via le MUX sur le canal de mesure spécifique
        
        :param target_resistance: Résistance à simuler en ohms
        :param measurement_channel: Canal sur lequel la mesure a été faite (pour info seulement)
        :param sensor_type: Type de sonde pour sélectionner la bonne carte MUX
        :return: True si succès, False sinon
        """
        print(f"\n[SIM_R] === APPLICATION RÉSISTANCE SIMULÉE ===")
        print(f"[SIM_R] Résistance cible: {target_resistance:.2f} Ω")
        print(f"[SIM_R] Canal de mesure: {measurement_channel}")
        print(f"[SIM_R] Type de sonde: {sensor_type}")
        
        if self.mux is None:
            print("[SIM_R] ERREUR MUX non initialisé")
            return False
        
        # Trouve le canal MUX le plus proche en utilisant le mapping dynamique
        try:
            channel, actual_resistance, error_percent = find_closest_channel(target_resistance, sensor_type)
            
            if channel is None:
                print(f"[SIM_R] ERREUR Aucun canal MUX trouvé pour {target_resistance:.1f}Ω")
                return False
            
            print(f"[SIM_R] Canal MUX trouvé: {channel}")
            print(f"[SIM_R] Résistance MUX: {actual_resistance}Ω (cible: {target_resistance:.1f}Ω)")
            print(f"[SIM_R] Erreur: {error_percent:.1f}%")
            
        except KeyError as e:
            print(f"[SIM_R] ERREUR {e}")
            return False
        
        try:
            # Application sur le MUX (toujours carte 0)
            board_index = 0  
            print(f"[SIM_R] Application MUX canal {channel} (carte {board_index})")
            self.mux.set_channel(board_index, channel)
            
            # Mémorisation de l'état actuel
            self.active_channels = [channel]
            self.current_resistance = actual_resistance
            
            print(f"[SIM_R] SUCCES Résistance appliquée: {actual_resistance}Ω sur canal MUX {channel}")
            return True
            
        except Exception as e:
            print(f"[SIM_R] ERREUR lors de l'application: {e}")
            return False
    
    def get_current_simulation(self) -> Dict[str, any]:
        """
        Retourne l'état actuel de la simulation
        
        :return: Dictionnaire avec les informations actuelles
        """
        return {
            "resistance": self.current_resistance,
            "active_channels": self.active_channels.copy() if self.active_channels else [],
            "mux_available": True
        }
    
    def validate_resistance_applied(self, expected_resistance: float, tolerance: float = 0.10) -> bool:
        """
        Valide que la résistance appliquée correspond à l'attendu
        
        :param expected_resistance: Résistance attendue
        :param tolerance: Tolérance relative
        :return: True si la résistance est dans la tolérance
        """
        if self.current_resistance is None:
            print("[SIM_R] ERREUR Aucune résistance actuellement appliquée")
            return False
        
        error = abs(self.current_resistance - expected_resistance) / expected_resistance
        
        if error <= tolerance:
            print(f"[SIM_R] VALIDATION OK: {self.current_resistance:.2f}Ω (attendu: {expected_resistance:.2f}Ω, erreur: {error*100:.1f}%)")
            return True
        else:
            print(f"[SIM_R] VALIDATION KO: {self.current_resistance:.2f}Ω (attendu: {expected_resistance:.2f}Ω, erreur: {error*100:.1f}%)")
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
            print("[SIM_R] SUCCES Simulation remise à zéro")
            
        except Exception as e:
            print(f"[SIM_R] ERREUR lors de la remise à zéro: {e}")

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
        print(f"[SIM_R] ERREUR dans apply_resistance_simulation: {e}")
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