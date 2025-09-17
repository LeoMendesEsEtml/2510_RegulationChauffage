# -*- coding: utf-8 -*-
# file: temperature_simulation.py
"""
Module pour calculer la température simulée selon la formule:
T_sim = T_mes + ((T_prev - T_mes) * n * exp(k_m))

Inclut la validation des paramètres et la gestion des erreurs.
"""

import math
from typing import Optional

def calculate_simulated_temperature(t_mes: float, t_prev: float, n: float, k_m: float) -> Optional[float]:
    """
    Calcule la température simulée selon la formule donnée
    
    :param t_mes: Température mesurée (°C)
    :param t_prev: Température prévue (°C)  
    :param n: Paramètre n (facteur de pondération)
    :param k_m: Paramètre k_m (exposant)
    :return: Température simulée (°C) ou None si erreur
    """
    try:
        # Validation des paramètres d'entrée
        if not all(isinstance(param, (int, float)) for param in [t_mes, t_prev, n, k_m]):
            print("[CALC] Erreur: tous les paramètres doivent être des nombres")
            return None
        
        # Vérification des plages de valeurs raisonnables
        if not (-100.0 <= t_mes <= 200.0):
            print(f"[CALC] Attention: température mesurée hors plage normale: {t_mes}°C")
        
        if not (-100.0 <= t_prev <= 200.0):
            print(f"[CALC] Attention: température prévue hors plage normale: {t_prev}°C")
        
        # Limitation du paramètre k_m pour éviter l'overflow
        if abs(k_m) > 50:
            print(f"[CALC] Erreur: paramètre k_m trop élevé: {k_m}")
            return None
        
        # Calcul de exp(k_m) avec gestion de l'overflow
        try:
            exp_km = math.exp(k_m)
        except OverflowError:
            print(f"[CALC] Erreur: overflow lors du calcul de exp({k_m})")
            return None
        
        # Vérification que exp(k_m) est dans une plage raisonnable
        if exp_km > 1e10:
            print(f"[CALC] Erreur: exp(k_m) = {exp_km} trop élevé")
            return None
        
        # Calcul de la différence de température
        temp_diff = t_prev - t_mes
        
        # Calcul de la température simulée
        t_sim = t_mes + (temp_diff * n * exp_km)
        
        # Vérification du résultat
        if not math.isfinite(t_sim):
            print(f"[CALC] Erreur: résultat non fini: {t_sim}")
            return None
        
        # Limitation du résultat à une plage raisonnable
        if not (-200.0 <= t_sim <= 500.0):
            print(f"[CALC] Attention: température simulée hors plage raisonnable: {t_sim}°C")
        
        print(f"[CALC] Calcul réussi: T_sim = {t_mes} + (({t_prev} - {t_mes}) * {n} * exp({k_m})) = {t_sim:.2f}°C")
        return t_sim
        
    except Exception as e:
        print(f"[CALC] Erreur inattendue lors du calcul: {e}")
        return None

def validate_simulation_parameters(probe_type: str, n: float, k_m: float, t_mes: float, t_prev: float) -> bool:
    """
    Valide tous les paramètres de simulation
    
    :param probe_type: Type de sonde
    :param n: Paramètre n
    :param k_m: Paramètre k_m  
    :param t_mes: Température mesurée
    :param t_prev: Température prévue
    :return: True si tous les paramètres sont valides
    """
    print("[VALIDATION] Vérification des paramètres de simulation...")
    
    # Vérification du type de sonde
    valid_probe_types = ["PT1000", "Ni1000_TK5000", "NTC_10k", "Ni1000 TK5000", "NTC 10k 3977"]
    if probe_type not in valid_probe_types:
        print(f"[VALIDATION] Type de sonde non supporté: {probe_type}")
        print(f"[VALIDATION] Types supportés: {valid_probe_types}")
        return False
    else:
        print(f"[VALIDATION] Type de sonde valide: {probe_type}")
    
    # Vérification du paramètre n (facteur de pondération)
    if not (-2.0 <= n <= 2.0):
        print(f"[VALIDATION] Paramètre n hors plage [-2.0, 2.0]: {n}")
        return False
    else:
        print(f"[VALIDATION] Paramètre n valide: {n}")
    
    # Vérification du paramètre k_m (exposant)
    if not (-10.0 <= k_m <= 10.0):
        print(f"[VALIDATION] Paramètre k_m hors plage [-10.0, 10.0]: {k_m}")
        return False
    else:
        print(f"[VALIDATION] Paramètre k_m valide: {k_m}")
    
    # Vérification des températures
    if not (-50.0 <= t_mes <= 150.0):
        print(f"[VALIDATION] Température mesurée hors plage [-50°C, 150°C]: {t_mes}°C")
        return False
    else:
        print(f"[VALIDATION] Température mesurée valide: {t_mes}°C")
    
    if not (-50.0 <= t_prev <= 150.0):
        print(f"[VALIDATION] Température prévue hors plage [-50°C, 150°C]: {t_prev}°C")
        return False
    else:
        print(f"[VALIDATION] Température prévue valide: {t_prev}°C")
    
    # Vérification de la cohérence entre températures
    temp_diff = abs(t_prev - t_mes)
    if temp_diff > 50.0:
        print(f"[VALIDATION] Écart important entre températures: {temp_diff:.1f}°C")
        print(f"[VALIDATION] T_mes={t_mes}°C, T_prev={t_prev}°C")
        
        # Demander confirmation à l'utilisateur
        try:
            confirm = input("[VALIDATION] Continuer malgré l'écart important? (o/N): ").strip().lower()
            if confirm != 'o' and confirm != 'oui':
                print("[VALIDATION] Validation annulée par l'utilisateur")
                return False
        except KeyboardInterrupt:
            print("\n[VALIDATION] Validation interrompue")
            return False
    
    print("[VALIDATION] Tous les paramètres sont valides")
    return True

def run_temperature_simulation(simulation_data: dict) -> Optional[float]:
    """
    Exécute une simulation complète de température
    
    :param simulation_data: Dictionnaire contenant tous les paramètres
    :return: Température simulée ou None si erreur
    """
    print("\n=== SIMULATION DE TEMPÉRATURE ===")
    
    try:
        # Extraction des paramètres
        probe_type = simulation_data["probe_type"]
        n = float(simulation_data["n"])
        k_m = float(simulation_data["k_m"])
        t_mes = float(simulation_data["temperature"])
        t_prev = float(simulation_data["forecast_temperature"])
        
        print(f"[SIM] Paramètres d'entrée:")
        print(f"[SIM]   Type de sonde: {probe_type}")
        print(f"[SIM]   Paramètre n: {n}")
        print(f"[SIM]   Paramètre k_m: {k_m}")
        print(f"[SIM]   Température mesurée: {t_mes}°C")
        print(f"[SIM]   Température prévue: {t_prev}°C")
        
        # Validation des paramètres
        if not validate_simulation_parameters(probe_type, n, k_m, t_mes, t_prev):
            print("[SIM] Échec de la validation des paramètres")
            return None
        
        # Calcul de la température simulée
        t_sim = calculate_simulated_temperature(t_mes, t_prev, n, k_m)
        
        if t_sim is None:
            print("[SIM] Échec du calcul de la température simulée")
            return None
        
        # Affichage du résultat
        print(f"\n[SIM] RÉSULTAT:")
        print(f"[SIM] Température simulée: {t_sim:.2f}°C")
        
        # Analyse du résultat
        if abs(t_sim - t_mes) < 0.1:
            print(f"[SIM] Simulation proche de la mesure (écart: {abs(t_sim - t_mes):.3f}°C)")
        elif abs(t_sim - t_prev) < abs(t_sim - t_mes):
            print(f"[SIM] Simulation tend vers la prévision")
        else:
            print(f"[SIM] Simulation tend vers la mesure")
        
        return t_sim
        
    except KeyError as e:
        print(f"[SIM] Paramètre manquant: {e}")
        return None
    except (ValueError, TypeError) as e:
        print(f"[SIM] Erreur de conversion de type: {e}")
        return None
    except Exception as e:
        print(f"[SIM] Erreur inattendue: {e}")
        return None

# Test du module (à des fins de développement)
if __name__ == "__main__":
    # Test des calculs
    print("=== Tests du module de simulation ===")
    
    # Test 1: Calcul normal
    print("\nTest 1: Calcul normal")
    result = calculate_simulated_temperature(20.0, 25.0, 0.5, 0.1)
    print(f"Résultat: {result}")
    
    # Test 2: Paramètres extrêmes
    print("\nTest 2: Paramètres extrêmes")
    result = calculate_simulated_temperature(0.0, 100.0, 1.0, 5.0)
    print(f"Résultat: {result}")
    
    # Test 3: Simulation complète
    print("\nTest 3: Simulation complète")
    test_data = {
        "probe_type": "PT1000",
        "n": 0.3,
        "k_m": 0.5,
        "temperature": 22.5,
        "forecast_temperature": 28.0
    }
    result = run_temperature_simulation(test_data)
    print(f"Résultat final: {result}")