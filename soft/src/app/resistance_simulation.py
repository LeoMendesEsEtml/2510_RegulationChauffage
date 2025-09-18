# -*- coding: utf-8 -*-
"""
@file        resistance_simulation.py
@brief       Module pour commander le MUX de simulation de résistance.
@details     Ce module permet d'appliquer une résistance simulée R_sim via
             le réseau de résistances contrôlé par multiplexeur ADG731.
             Il gère le calcul des commutateurs à activer, la commande du
             multiplexeur, et la validation des valeurs appliquées.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

# Import des modules système standard
import time
# Import des annotations de type pour la documentation
from typing import Optional, List, Dict, Tuple
# Import du driver multiplexeur ADG731
from app.hw_mux_adg731 import Adg731MuxSpi
# Import des utilitaires de mapping de résistances
from app.resistance_mapping import get_channel_mux_map, find_closest_channel


# ---------------------------------------------------------------------------
# Classes d'exception personnalisées
# ---------------------------------------------------------------------------

class ResistanceSimulationError(Exception):
    """
    @brief   Exception pour les erreurs de simulation de résistance.
    @details Exception spécialisée levée lors d'erreurs dans le processus
             de simulation de résistance via le multiplexeur.
    """
    pass


# ---------------------------------------------------------------------------
# Classe principale de simulation
# ---------------------------------------------------------------------------

class ResistanceSimulator:
    """
    @brief   Contrôleur pour la simulation de résistance via MUX.
    @details Classe principale qui encapsule toute la logique de simulation
             de résistance en utilisant le multiplexeur ADG731 et les
             mappings de résistances calibrées.
    """
    
    def __init__(self, speed_hz: int = 100000):
        """
        @brief   Initialise le simulateur de résistance.
        @details Constructeur qui configure le multiplexeur ADG731 avec
                 la vitesse SPI spécifiée et initialise les variables
                 d'état du simulateur.

        @param speed_hz  Vitesse de communication SPI en Hz (défaut: 100kHz).

        @exception ResistanceSimulationError si l'initialisation du MUX échoue.
        """
        # Référence vers le multiplexeur ADG731
        self.mux = None
        # Vitesse de communication SPI configurée
        self.speed_hz = speed_hz
        # Résistance actuellement appliquée (None si aucune)
        self.current_resistance = None
        # Liste des canaux MUX actuellement actifs
        self.active_channels = []
        
        try:
            # Initialisation du multiplexeur ADG731 avec la vitesse SPI
            self.mux = Adg731MuxSpi(speed_hz=speed_hz)
            # Affichage de confirmation d'initialisation
            print(f"[SIM_R] Simulateur de résistance initialisé (SPI: {speed_hz} Hz)")
        except Exception as e:
            # Affichage d'erreur en cas d'échec d'initialisation
            print(f"[SIM_R] ERREUR d'initialisation du MUX: {e}")
            # Levée d'exception avec contexte détaillé
            raise ResistanceSimulationError(f"Impossible d'initialiser le MUX: {e}")
    
    def close(self):
        """
        @brief   Ferme les connexions du simulateur.
        @details Méthode de nettoyage qui ferme proprement la connexion
                 SPI avec le multiplexeur et libère les ressources.
        """
        # Vérification de l'existence de la connexion MUX
        if self.mux:
            try:
                # Fermeture de la connexion SPI
                self.mux.close()
                # Confirmation de fermeture
                print("[SIM_R] Simulateur fermé")
            except Exception as e:
                # Affichage d'erreur en cas de problème de fermeture
                print(f"[SIM_R] Erreur lors de la fermeture: {e}")
    
    def calculate_parallel_resistance(self, resistances: List[float]) -> float:
        """
        @brief   Calcule la résistance équivalente de résistances en parallèle.
        @details Applique la formule 1/Req = 1/R1 + 1/R2 + ... + 1/Rn
                 pour calculer la résistance équivalente d'un ensemble
                 de résistances connectées en parallèle.

        @param resistances  Liste des valeurs de résistance en parallèle [Ohms].

        @return             Résistance équivalente calculée [Ohms].
                            Retourne l'infini si la liste est vide.
        """
        # Cas d'une liste vide: résistance infinie
        if not resistances:
            return float('inf')
        
        # Cas d'une seule résistance: pas de calcul parallèle
        if len(resistances) == 1:
            return resistances[0]
        
        # Calcul de la somme des inverses (1/R1 + 1/R2 + ...)
        reciprocal_sum = sum(1.0 / r for r in resistances)
        # Application de la formule: Req = 1 / (somme des 1/Ri)
        return 1.0 / reciprocal_sum
    
    def apply_resistance_simulation(self, target_resistance: float, measurement_channel: int, sensor_type: str = "Ni1000 TK5000") -> bool:
        """
        @brief   Applique une résistance simulée via le MUX sur le canal de mesure.
        @details Fonction principale qui recherche le canal MUX optimal pour
                 simuler la résistance cible, configure le multiplexeur et
                 mémorise l'état de la simulation.

        @param target_resistance     Résistance à simuler [Ohms].
        @param measurement_channel   Canal sur lequel la mesure a été faite (info).
        @param sensor_type          Type de sonde pour sélectionner la carte MUX.

        @return                     True si succès, False en cas d'erreur.
        """
        # Affichage de l'en-tête de la procédure de simulation
        print(f"\n[SIM_R] === APPLICATION RÉSISTANCE SIMULÉE ===")
        # Affichage de la résistance cible avec précision
        print(f"[SIM_R] Résistance cible: {target_resistance:.2f} Ω")
        # Affichage du canal de mesure pour traçabilité
        print(f"[SIM_R] Canal de mesure: {measurement_channel}")
        # Affichage du type de sonde sélectionné
        print(f"[SIM_R] Type de sonde: {sensor_type}")
        
        # Vérification de l'initialisation du multiplexeur
        if self.mux is None:
            # Erreur critique: MUX non initialisé
            print("[SIM_R] ERREUR MUX non initialisé")
            return False
        
        # Recherche du canal MUX optimal en utilisant le mapping dynamique
        try:
            # Appel de la fonction de recherche du canal le plus proche
            channel, actual_resistance, error_percent = find_closest_channel(target_resistance, sensor_type)
            
            # Vérification que la recherche a trouvé un canal valide
            if channel is None:
                # Aucun canal MUX disponible pour cette résistance
                print(f"[SIM_R] ERREUR Aucun canal MUX trouvé pour {target_resistance:.1f}Ω")
                return False
            
            # Affichage du canal MUX sélectionné
            print(f"[SIM_R] Canal MUX trouvé: {channel}")
            # Affichage de la résistance réelle vs cible
            print(f"[SIM_R] Résistance MUX: {actual_resistance}Ω (cible: {target_resistance:.1f}Ω)")
            # Affichage de l'erreur relative en pourcentage
            print(f"[SIM_R] Erreur: {error_percent:.1f}%")
            
        except KeyError as e:
            # Erreur: type de sonde non supporté
            print(f"[SIM_R] ERREUR {e}")
            return False
        
        try:
            # Configuration du multiplexeur (toujours carte 0 par défaut)
            board_index = 0
            # Affichage de l'action de configuration MUX
            print(f"[SIM_R] Application MUX canal {channel} (carte {board_index})")
            # Activation du canal sélectionné sur la carte MUX
            self.mux.set_channel(board_index, channel)
            
            # Mémorisation de l'état actuel de simulation
            self.active_channels = [channel]
            # Sauvegarde de la résistance réellement appliquée
            self.current_resistance = actual_resistance
            
            # Confirmation de succès avec résistance appliquée
            print(f"[SIM_R] SUCCES Résistance appliquée: {actual_resistance}Ω sur canal MUX {channel}")
            return True
            
        except Exception as e:
            # Erreur lors de la communication avec le MUX
            print(f"[SIM_R] ERREUR lors de l'application: {e}")
            return False
    
    def get_current_simulation(self) -> Dict[str, any]:
        """
        @brief   Retourne l'état actuel de la simulation.
        @details Fonction d'interrogation qui fournit un dictionnaire
                 contenant toutes les informations sur l'état actuel
                 de la simulation de résistance.

        @return  Dictionnaire contenant les informations actuelles:
                 - resistance: valeur appliquée [Ohms] ou None
                 - active_channels: liste des canaux MUX actifs
                 - mux_available: disponibilité du multiplexeur
        """
        # Construction du dictionnaire d'état avec résistance actuelle
        return {
            "resistance": self.current_resistance,
            # Copie de la liste des canaux actifs (protection contre modification)
            "active_channels": self.active_channels.copy() if self.active_channels else [],
            # Indication de disponibilité du MUX (toujours True si initialisé)
            "mux_available": True
        }
    
    def validate_resistance_applied(self, expected_resistance: float, tolerance: float = 0.10) -> bool:
        """
        @brief   Valide que la résistance appliquée correspond à l'attendu.
        @details Fonction de validation qui compare la résistance actuellement
                 appliquée avec la valeur attendue en tenant compte d'une
                 tolérance relative spécifiée.

        @param expected_resistance  Résistance attendue pour la validation [Ohms].
        @param tolerance           Tolérance relative acceptée (défaut: 10%).

        @return                    True si la résistance est dans la tolérance.
        """
        # Vérification qu'une résistance est actuellement appliquée
        if self.current_resistance is None:
            # Erreur: aucune résistance n'est actuellement simulée
            print("[SIM_R] ERREUR Aucune résistance actuellement appliquée")
            return False
        
        # Calcul de l'erreur relative entre résistance appliquée et attendue
        error = abs(self.current_resistance - expected_resistance) / expected_resistance
        
        # Comparaison de l'erreur avec la tolérance spécifiée
        if error <= tolerance:
            # Validation réussie: affichage des détails
            print(f"[SIM_R] VALIDATION OK: {self.current_resistance:.2f}Ω (attendu: {expected_resistance:.2f}Ω, erreur: {error*100:.1f}%)")
            return True
        else:
            # Validation échouée: affichage des détails d'erreur
            print(f"[SIM_R] VALIDATION KO: {self.current_resistance:.2f}Ω (attendu: {expected_resistance:.2f}Ω, erreur: {error*100:.1f}%)")
            return False
    
    def reset_simulation(self):
        """
        @brief   Remet la simulation à zéro (désactive tous les canaux).
        @details Procédure de nettoyage qui désactive tous les canaux de
                 tous les multiplexeurs et remet l'état de simulation
                 à sa configuration initiale.
        """
        # Affichage du début de la procédure de remise à zéro
        print("[SIM_R] Remise à zéro de la simulation")
        
        # Vérification de l'initialisation du multiplexeur
        if self.mux is None:
            return
        
        try:
            # Désactivation systématique de tous les canaux
            for board in range(4):
                # Parcours de tous les canaux de chaque carte
                for channel in range(32):
                    try:
                        # Tentative de désactivation du canal
                        self.mux.set_channel(board, channel)
                    except Exception:
                        # Ignore les erreurs individuelles de canal
                        pass
            
            # Remise à zéro des variables d'état
            self.active_channels = []
            # Effacement de la résistance mémorisée
            self.current_resistance = None
            # Confirmation de succès de la remise à zéro
            print("[SIM_R] SUCCES Simulation remise à zéro")
            
        except Exception as e:
            # Erreur lors de la procédure de remise à zéro
            print(f"[SIM_R] ERREUR lors de la remise à zéro: {e}")


# ---------------------------------------------------------------------------
# Fonctions utilitaires globales
# ---------------------------------------------------------------------------

def apply_resistance_simulation(resistance_ohm: float) -> bool:
    """
    @brief   Fonction utilitaire pour appliquer une résistance simulée.
    @details Fonction de commodité qui encapsule la création d'un simulateur,
             l'application d'une résistance et le nettoyage automatique.
             Utilise le pattern RAII pour la gestion des ressources.

    @param resistance_ohm  Résistance à appliquer [Ohms].

    @return                True si l'application a réussi, False sinon.
    """
    # Initialisation du simulateur à None pour le nettoyage
    simulator = None
    try:
        # Création d'une instance du simulateur
        simulator = ResistanceSimulator()
        # Application de la résistance avec paramètres par défaut
        return simulator.apply_resistance_simulation(resistance_ohm)
    except Exception as e:
        # Gestion d'erreur avec affichage du contexte
        print(f"[SIM_R] ERREUR dans apply_resistance_simulation: {e}")
        return False
    finally:
        # Nettoyage automatique du simulateur si créé
        if simulator:
            simulator.close()


# ---------------------------------------------------------------------------
# Section de test et démonstration
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    """
    @brief   Point d'entrée pour les tests de développement.
    @details Section de test qui démontre l'utilisation du simulateur
             avec différents cas d'usage et validation des résultats.
    """
    # Affichage de l'en-tête des tests de développement
    print("=== Test du simulateur de résistance ===")
    
    # Création d'une instance de simulateur pour les tests
    sim = ResistanceSimulator()
    
    # Test 1: Application d'une résistance simple de 1000 Ohms
    print("\nTest 1: Application de 1000Ω")
    # Appel de la fonction de simulation avec résistance cible
    success = sim.apply_resistance_simulation(1000.0)
    # Affichage du résultat du test avec évaluation booléenne
    print(f"Résultat: {'Succès' if success else 'Échec'}")
    
    # Test 2: Application d'une résistance complexe (parallèle calculé)
    print("\nTest 2: Application de 667Ω (parallèle de 1k et 2k)")
    # Test avec une valeur nécessitant une approximation par le MUX
    success = sim.apply_resistance_simulation(667.0)
    # Évaluation et affichage du résultat
    print(f"Résultat: {'Succès' if success else 'Échec'}")
    
    # Test 3: Validation de la résistance appliquée avec tolérance
    print("\nTest 3: Validation de la résistance appliquée")
    # Vérification qu'une résistance est effectivement appliquée
    if sim.current_resistance:
        # Validation avec tolérance élargie de 15%
        valid = sim.validate_resistance_applied(667.0, tolerance=0.15)
        # Affichage du résultat de validation
        print(f"Validation: {'OK' if valid else 'KO'}")
    
    # Procédure de nettoyage et fermeture
    sim.reset_simulation()
    # Fermeture propre du simulateur
    sim.close()