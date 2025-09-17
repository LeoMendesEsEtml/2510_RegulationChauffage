# -*- coding: utf-8 -*-
# file: main_temperature_simulation.py
"""
Programme principal pour la simulation de température selon le cahier des charges:

1. Interroge les APIs oblosolutions.ch pour récupérer les paramètres
2. Calcule T_sim = T_mes + ((T_prev - T_mes) * n * exp(Km))
3. Convertit T_sim en R_sim selon le type de sonde
4. Commande le MUX pour appliquer R_sim
5. Confirme les valeurs appliquées à l'utilisateur

MAC Address: 0030DEABCDEF (comme spécifié dans le prompt)
"""

import os
import sys
import time

# Ajout du chemin pour les imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# Imports des modules développés
from app.api_client import get_simulation_data, ApiError
from app.temperature_simulation import run_temperature_simulation
from app.temperature_conversion import convert_temperature_to_resistance, get_supported_probe_types
from app.resistance_simulation import ResistanceSimulator, ResistanceSimulationError

# Configuration
MAC_ADDRESS = "0030DEABCDEF"

def display_banner():
    """Affiche la bannière du programme"""
    print("=" * 80)
    print("    SYSTÈME DE SIMULATION DE TEMPÉRATURE")
    print("    Calcul et application de la température simulée")
    print("=" * 80)
    print(f"MAC Address: {MAC_ADDRESS}")
    print(f"Heure de démarrage: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def display_parameters(data):
    """Affiche les paramètres récupérés"""
    print("📋 PARAMÈTRES RÉCUPÉRÉS:")
    print(f"   Type de sonde: {data['probe_type']}")
    print(f"   Paramètre n: {data['n']}")
    print(f"   Paramètre k_m: {data['k_m']}")
    print(f"   Température mesurée: {data['temperature']:.2f}°C")
    print(f"   Température prévue: {data['forecast_temperature']:.2f}°C")
    print()

def confirm_parameters(data):
    """Demande confirmation des paramètres à l'utilisateur"""
    print("⚠️  CONFIRMATION DES PARAMÈTRES")
    display_parameters(data)
    
    try:
        confirm = input("Les paramètres sont-ils corrects? (o/N): ").strip().lower()
        return confirm in ['o', 'oui', 'y', 'yes']
    except KeyboardInterrupt:
        print("\nOpération annulée par l'utilisateur")
        return False

def display_simulation_result(t_sim, r_sim, probe_type):
    """Affiche les résultats de la simulation"""
    print("🎯 RÉSULTATS DE LA SIMULATION:")
    print(f"   Température simulée (T_sim): {t_sim:.2f}°C")
    print(f"   Résistance simulée (R_sim): {r_sim:.2f}Ω")
    print(f"   Type de sonde: {probe_type}")
    print()

def confirm_application():
    """Demande confirmation avant application de la résistance"""
    try:
        confirm = input("🤖 Appliquer la résistance simulée sur le MUX? (o/N): ").strip().lower()
        return confirm in ['o', 'oui', 'y', 'yes']
    except KeyboardInterrupt:
        print("\nApplication annulée par l'utilisateur")
        return False

def display_final_confirmation(t_sim, r_sim, success):
    """Affiche la confirmation finale"""
    print("✅ CONFIRMATION FINALE:")
    if success:
        print(f"   ✅ Température simulée: {t_sim:.2f}°C")
        print(f"   ✅ Résistance simulée appliquée: {r_sim:.2f}Ω")
        print("   ✅ MUX configuré avec succès")
        print("\n🎉 SIMULATION TERMINÉE AVEC SUCCÈS!")
    else:
        print(f"   ❌ Température simulée: {t_sim:.2f}°C")
        print(f"   ❌ Échec de l'application de la résistance: {r_sim:.2f}Ω")
        print("   ❌ Problème avec la configuration du MUX")
        print("\n⚠️  SIMULATION TERMINÉE AVEC ERREURS!")
    print()

def handle_missing_data():
    """Gère le cas où les données API sont manquantes"""
    print("⚠️  DONNÉES MANQUANTES OU INVALIDES")
    print("Les informations récupérées depuis l'API sont incomplètes.")
    print("Veuillez:")
    print("1. Vérifier la connexion réseau")
    print("2. Contrôler les APIs oblosolutions.ch")
    print("3. Ou entrer les valeurs manuellement")
    print()

def main():
    """Fonction principale du programme de simulation"""
    display_banner()
    
    # Variables de simulation
    simulator = None
    simulation_successful = False
    
    try:
        # Étape 1: Récupération des paramètres depuis l'API
        print("🌐 ÉTAPE 1: Récupération des paramètres depuis l'API")
        print("-" * 50)
        
        try:
            simulation_data = get_simulation_data(MAC_ADDRESS)
            display_parameters(simulation_data)
            
            # Confirmation des paramètres
            if not confirm_parameters(simulation_data):
                print("❌ Paramètres non confirmés. Arrêt du programme.")
                return
                
        except ApiError as e:
            print(f"❌ Erreur API: {e}")
            handle_missing_data()
            return
        
        # Étape 2: Calcul de la température simulée
        print("🧮 ÉTAPE 2: Calcul de la température simulée")
        print("-" * 50)
        
        t_sim = run_temperature_simulation(simulation_data)
        if t_sim is None:
            print("❌ Impossible de calculer la température simulée")
            return
        
        # Étape 3: Conversion température -> résistance
        print("🔄 ÉTAPE 3: Conversion température vers résistance")
        print("-" * 50)
        
        probe_type = simulation_data["probe_type"]
        r_sim = convert_temperature_to_resistance(t_sim, probe_type)
        
        if r_sim is None:
            print(f"❌ Impossible de convertir {t_sim:.2f}°C en résistance pour {probe_type}")
            print(f"Types de sondes supportés: {get_supported_probe_types()}")
            return
        
        # Affichage des résultats
        display_simulation_result(t_sim, r_sim, probe_type)
        
        # Étape 4: Application via MUX (avec confirmation)
        print("🤖 ÉTAPE 4: Application de la résistance simulée")
        print("-" * 50)
        
        if not confirm_application():
            print("❌ Application annulée par l'utilisateur")
            return
        
        # Initialisation et utilisation du simulateur
        try:
            simulator = ResistanceSimulator()
            print("✅ Simulateur de résistance initialisé")
            
            # Application de la résistance
            success = simulator.apply_resistance_simulation(r_sim)
            
            if success:
                # Validation de l'application
                validation_ok = simulator.validate_resistance_applied(r_sim, tolerance=0.15)
                simulation_successful = success and validation_ok
            else:
                simulation_successful = False
                
        except ResistanceSimulationError as e:
            print(f"❌ Erreur du simulateur: {e}")
            simulation_successful = False
        
        # Étape 5: Confirmation finale
        print("📋 ÉTAPE 5: Confirmation finale")
        print("-" * 50)
        display_final_confirmation(t_sim, r_sim, simulation_successful)
        
        # Maintien de la simulation si succès
        if simulation_successful:
            try:
                print("⏳ Maintien de la simulation active...")
                print("Appuyez sur Ctrl+C pour arrêter la simulation")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Arrêt de la simulation demandé")
        
    except KeyboardInterrupt:
        print("\n🛑 Programme interrompu par l'utilisateur")
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Nettoyage final
        if simulator:
            print("🧹 Nettoyage du simulateur...")
            try:
                simulator.reset_simulation()
                simulator.close()
                print("✅ Simulateur fermé proprement")
            except Exception as e:
                print(f"⚠️  Erreur lors du nettoyage: {e}")
        
        print("\n" + "=" * 80)
        print("    FIN DU PROGRAMME DE SIMULATION")
        print("=" * 80)

def run_test_simulation():
    """Lance une simulation de test avec des données fictives"""
    print("🧪 MODE TEST: Simulation avec données fictives")
    print("-" * 50)
    
    test_data = {
        "probe_type": "PT1000",
        "n": 0.3,
        "k_m": 0.5,
        "temperature": 22.5,
        "forecast_temperature": 28.0
    }
    
    # Calcul de test
    t_sim = run_temperature_simulation(test_data)
    if t_sim:
        r_sim = convert_temperature_to_resistance(t_sim, "PT1000")
        if r_sim:
            print(f"🧪 Test réussi: T_sim={t_sim:.2f}°C, R_sim={r_sim:.2f}Ω")
        else:
            print("❌ Échec de conversion température->résistance")
    else:
        print("❌ Échec du calcul de simulation")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulateur de température")
    parser.add_argument("--test", action="store_true", help="Lance une simulation de test")
    
    args = parser.parse_args()
    
    if args.test:
        run_test_simulation()
    else:
        main()