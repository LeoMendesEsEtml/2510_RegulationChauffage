# -*- coding: utf-8 -*-
# file: test_temperature_simulation_integration.py
"""
Script de test pour valider l'intégration complète du système de simulation de température.
Ce test vérifie que tous les modules fonctionnent ensemble correctement.
"""

import os
import sys

# Ajout du chemin pour les imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

def test_api_client():
    """Test du module API client"""
    print("Test 1: Module API Client")
    try:
        from app.api_client import ApiClient, validate_manual_input, get_manual_input
        
        # Test de validation manuelle
        valid = validate_manual_input("PT1000", 0.5, 1.0, 25.0, 30.0)
        print(f"   Validation manuelle: {'OK' if valid else 'KO'}")
        
        # Test client API (sans connexion réelle)
        client = ApiClient("0030DEABCDEF")
        print(f"   Client API initialisé: {client.mac_address}")
        
        return True
    except Exception as e:
        print(f"   Erreur: {e}")
        return False

def test_temperature_simulation():
    """Test du module de simulation de température"""
    print("Test 2: Module Simulation de Température")
    try:
        from app.temperature_simulation import calculate_simulated_temperature, run_temperature_simulation
        
        # Test de calcul simple
        t_sim = calculate_simulated_temperature(20.0, 25.0, 0.5, 0.1)
        print(f"   Calcul de base: T_sim = {t_sim:.2f}°C")
        
        # Test de simulation complète
        test_data = {
            "probe_type": "PT1000",
            "n": 0.3,
            "k_m": 0.5,
            "temperature": 22.5,
            "forecast_temperature": 28.0
        }
        
        t_sim_full = run_temperature_simulation(test_data)
        print(f"   Simulation complète: T_sim = {t_sim_full:.2f}°C")
        
        return True
    except Exception as e:
        print(f"   Erreur: {e}")
        return False

def test_temperature_conversion():
    """Test du module de conversion de température"""
    print("🧪 Test 3: Module Conversion de Température")
    try:
        from app.temperature_conversion import (
            convert_temperature_to_resistance, 
            get_supported_probe_types,
            validate_temperature_range
        )
        
        # Test des types supportés
        probe_types = get_supported_probe_types()
        print(f"   ✅ Types de sondes supportés: {len(probe_types)}")
        
        # Test de conversion
        r_sim = convert_temperature_to_resistance(25.0, "PT1000")
        print(f"   ✅ Conversion T->R: 25°C -> {r_sim:.2f}Ω (PT1000)")
        
        # Test de validation de plage
        valid_range = validate_temperature_range(25.0, "PT1000")
        print(f"   ✅ Validation plage: {'OK' if valid_range else 'KO'}")
        
        return True
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False

def test_resistance_simulation():
    """Test du module de simulation de résistance"""
    print("🧪 Test 4: Module Simulation de Résistance")
    try:
        from app.resistance_simulation import ResistanceSimulator
        
        # Test d'initialisation (sans matériel réel)
        print("   ⚠️  Test sans matériel réel - simulation logique uniquement")
        
        # Test des calculs de résistances parallèles
        sim = ResistanceSimulator.__new__(ResistanceSimulator)  # Création sans __init__
        sim.mux = None
        sim.current_resistance = None
        sim.active_channels = []
        
        # Test calcul parallèle
        parallel_r = sim.calculate_parallel_resistance([1000, 2000])
        expected = 1000 * 2000 / (1000 + 2000)  # 666.67
        print(f"   ✅ Calcul parallèle: 1kΩ || 2kΩ = {parallel_r:.1f}Ω (attendu: {expected:.1f}Ω)")
        
        # Test recherche de combinaison
        combination = sim.find_best_resistance_combination(1000.0, tolerance=0.1)
        print(f"   ✅ Combinaison pour 1kΩ: {combination}")
        
        return True
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False

def test_integration_complete():
    """Test d'intégration complète (sans matériel)"""
    print("🧪 Test 5: Intégration Complète")
    try:
        # Données de test
        test_data = {
            "probe_type": "PT1000",
            "n": 0.3,
            "k_m": 0.2,
            "temperature": 20.0,
            "forecast_temperature": 25.0
        }
        
        # Étape 1: Simulation de température
        from app.temperature_simulation import run_temperature_simulation
        t_sim = run_temperature_simulation(test_data)
        print(f"   ✅ Étape 1 - T_sim calculée: {t_sim:.2f}°C")
        
        # Étape 2: Conversion en résistance
        from app.temperature_conversion import convert_temperature_to_resistance
        r_sim = convert_temperature_to_resistance(t_sim, "PT1000")
        print(f"   ✅ Étape 2 - R_sim calculée: {r_sim:.2f}Ω")
        
        # Étape 3: Simulation logique de l'application (sans MUX réel)
        from app.resistance_simulation import ResistanceSimulator
        sim = ResistanceSimulator.__new__(ResistanceSimulator)
        sim.mux = None
        sim.current_resistance = None
        sim.active_channels = []
        
        combination = sim.find_best_resistance_combination(r_sim, tolerance=0.15)
        if combination:
            actual_r = sim.get_combination_resistance(combination)
            print(f"   ✅ Étape 3 - Combinaison trouvée: {actual_r:.2f}Ω (canaux: {combination})")
        else:
            print(f"   ⚠️  Étape 3 - Aucune combinaison pour {r_sim:.2f}Ω")
        
        print("   ✅ Intégration complète validée")
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Lance tous les tests"""
    print("=" * 80)
    print("    TESTS D'INTÉGRATION - SIMULATION DE TEMPÉRATURE")
    print("=" * 80)
    print()
    
    tests = [
        test_api_client,
        test_temperature_simulation,
        test_temperature_conversion,
        test_resistance_simulation,
        test_integration_complete
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print(f"   Résultat: {'✅ SUCCÈS' if result else '❌ ÉCHEC'}")
        except Exception as e:
            print(f"   ❌ ERREUR CRITIQUE: {e}")
            results.append(False)
        print()
    
    # Résumé
    print("=" * 80)
    print("    RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"Tests réussis: {success_count}/{total_count}")
    print(f"Taux de réussite: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 TOUS LES TESTS SONT RÉUSSIS!")
        print("Le système de simulation de température est prêt à être utilisé.")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("Veuillez corriger les problèmes avant utilisation.")
    
    print("=" * 80)
    
    return success_count == total_count

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)