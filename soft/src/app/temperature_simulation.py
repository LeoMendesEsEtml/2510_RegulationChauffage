# -*- coding: utf-8 -*-
"""
@file        temperature_simulation.py
@brief       Module de calcul de température simulée selon formule prédictive.
@details     Ce module implémente la formule de simulation de température:
             T_sim = T_mes + ((T_prev - T_mes) * n * exp(k_m))
             Inclut la validation complète des paramètres, la gestion
             des erreurs numériques et l'exécution de simulations complètes.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

# Import des modules système standard
import math
# Import des annotations de type pour la documentation
from typing import Optional


# ---------------------------------------------------------------------------
# Fonctions de calcul principal
# ---------------------------------------------------------------------------

def calculate_simulated_temperature(t_mes: float, t_prev: float, n: float, k_m: float) -> Optional[float]:
    """
    @brief   Calcule la température simulée selon la formule prédictive.
    @details Implémente la formule T_sim = T_mes + ((T_prev - T_mes) * n * exp(k_m))
             avec validation complète des paramètres et gestion des erreurs
             numériques (overflow, underflow, valeurs infinies).

    @param t_mes   Température mesurée [°C].
    @param t_prev  Température prévue [°C].
    @param n       Paramètre de pondération [-∞, +∞].
    @param k_m     Paramètre exposant pour fonction exponentielle [-∞, +∞].

    @return        Température simulée [°C] ou None en cas d'erreur.

    @exception     OverflowError si exp(k_m) dépasse les limites numériques.
    @warning       Limitation automatique des paramètres extrêmes.
    """
    try:
        # Validation du type des paramètres d'entrée
        if not all(isinstance(param, (int, float)) for param in [t_mes, t_prev, n, k_m]):
            # Affichage d'erreur si types incorrects
            print("[CALC] Erreur: tous les paramètres doivent être des nombres")
            return None
        
        # Vérification des plages de températures raisonnables pour mesure
        if not (-100.0 <= t_mes <= 200.0):
            # Avertissement pour température mesurée hors plage normale
            print(f"[CALC] Attention: température mesurée hors plage normale: {t_mes}°C")
        
        # Vérification des plages de températures raisonnables pour prévision
        if not (-100.0 <= t_prev <= 200.0):
            # Avertissement pour température prévue hors plage normale
            print(f"[CALC] Attention: température prévue hors plage normale: {t_prev}°C")
        
        # Limitation du paramètre k_m pour éviter l'overflow exponentiel
        if abs(k_m) > 50:
            # Erreur critique si k_m trop élevé
            print(f"[CALC] Erreur: paramètre k_m trop élevé: {k_m}")
            return None
        
        # Calcul de l'exponentielle avec gestion des cas d'overflow
        try:
            # Application de la fonction exponentielle
            exp_km = math.exp(k_m)
        except OverflowError:
            # Gestion de l'overflow lors du calcul exponentiel
            print(f"[CALC] Erreur: overflow lors du calcul de exp({k_m})")
            return None
        
        # Vérification que l'exponentielle reste dans une plage numérique raisonnable
        if exp_km > 1e10:
            # Limitation de la valeur exponentielle pour éviter instabilité
            print(f"[CALC] Erreur: exp(k_m) = {exp_km} trop élevé")
            return None
        
        # Calcul de la différence entre température prévue et mesurée
        temp_diff = t_prev - t_mes
        
        # Application de la formule complète de simulation
        t_sim = t_mes + (temp_diff * n * exp_km)
        
        # Vérification que le résultat est un nombre fini valide
        if not math.isfinite(t_sim):
            # Erreur si résultat infini ou NaN
            print(f"[CALC] Erreur: résultat non fini: {t_sim}")
            return None
        
        # Limitation du résultat dans une plage physiquement raisonnable
        if not (-200.0 <= t_sim <= 500.0):
            # Avertissement pour température simulée hors plage physique
            print(f"[CALC] Attention: température simulée hors plage raisonnable: {t_sim}°C")
        
        # Affichage de confirmation avec détail du calcul effectué
        print(f"[CALC] Calcul réussi: T_sim = {t_mes} + (({t_prev} - {t_mes}) * {n} * exp({k_m})) = {t_sim:.2f}°C")
        # Retour de la température simulée calculée
        return t_sim
        
    except Exception as e:
        # Gestion d'exception générale pour erreurs inattendues
        print(f"[CALC] Erreur inattendue lors du calcul: {e}")
        return None

def validate_simulation_parameters(probe_type: str, n: float, k_m: float, t_mes: float, t_prev: float) -> bool:
    """
    @brief   Valide tous les paramètres de simulation avant exécution.
    @details Fonction de validation complète qui vérifie la cohérence
             et les plages de tous les paramètres d'entrée. Inclut
             la vérification interactive pour les écarts importants.

    @param probe_type  Type de sonde à utiliser pour la simulation.
    @param n          Paramètre de pondération de la simulation.
    @param k_m        Paramètre exposant de la fonction exponentielle.
    @param t_mes      Température mesurée à valider [°C].
    @param t_prev     Température prévue à valider [°C].

    @return           True si tous les paramètres sont valides.

    @warning          Demande confirmation utilisateur pour écarts importants.
    """
    # Affichage du début de la procédure de validation
    print("[VALIDATION] Vérification des paramètres de simulation...")
    
    # Liste des types de sondes supportés par le système
    valid_probe_types = ["PT1000", "Ni1000_TK5000", "NTC_10k", "Ni1000 TK5000", "NTC 10k 3977"]
    # Vérification que le type de sonde est dans la liste supportée
    if probe_type not in valid_probe_types:
        # Affichage d'erreur avec liste des types supportés
        print(f"[VALIDATION] Type de sonde non supporté: {probe_type}")
        print(f"[VALIDATION] Types supportés: {valid_probe_types}")
        return False
    else:
        # Confirmation que le type de sonde est valide
        print(f"[VALIDATION] Type de sonde valide: {probe_type}")
    
    # Vérification du paramètre n dans sa plage de fonctionnement recommandée
    if not (-2.0 <= n <= 2.0):
        # Erreur si paramètre n hors plage acceptable
        print(f"[VALIDATION] Paramètre n hors plage [-2.0, 2.0]: {n}")
        return False
    else:
        # Confirmation de validité du paramètre n
        print(f"[VALIDATION] Paramètre n valide: {n}")
    
    # Vérification du paramètre k_m dans sa plage de sécurité numérique
    if not (-10.0 <= k_m <= 10.0):
        # Erreur si k_m risque de causer overflow exponentiel
        print(f"[VALIDATION] Paramètre k_m hors plage [-10.0, 10.0]: {k_m}")
        return False
    else:
        # Confirmation de validité du paramètre k_m
        print(f"[VALIDATION] Paramètre k_m valide: {k_m}")
    
    # Vérification de la température mesurée dans plage physique normale
    if not (-50.0 <= t_mes <= 150.0):
        # Erreur si température mesurée hors plage d'application
        print(f"[VALIDATION] Température mesurée hors plage [-50°C, 150°C]: {t_mes}°C")
        return False
    else:
        # Confirmation de validité de la température mesurée
        print(f"[VALIDATION] Température mesurée valide: {t_mes}°C")
    
    # Vérification de la température prévue dans plage physique normale
    if not (-50.0 <= t_prev <= 150.0):
        # Erreur si température prévue hors plage d'application
        print(f"[VALIDATION] Température prévue hors plage [-50°C, 150°C]: {t_prev}°C")
        return False
    else:
        # Confirmation de validité de la température prévue
        print(f"[VALIDATION] Température prévue valide: {t_prev}°C")
    
    # Calcul de l'écart absolu entre températures pour vérification cohérence
    temp_diff = abs(t_prev - t_mes)
    # Vérification si l'écart entre températures est anormalement important
    if temp_diff > 50.0:
        # Avertissement pour écart important entre températures
        print(f"[VALIDATION] Écart important entre températures: {temp_diff:.1f}°C")
        print(f"[VALIDATION] T_mes={t_mes}°C, T_prev={t_prev}°C")
        
        # Procédure de demande de confirmation utilisateur pour écart important
        try:
            # Demande de confirmation interactive
            confirm = input("[VALIDATION] Continuer malgré l'écart important? (o/N): ").strip().lower()
            # Vérification de la réponse utilisateur
            if confirm != 'o' and confirm != 'oui':
                # Annulation si utilisateur refuse de continuer
                print("[VALIDATION] Validation annulée par l'utilisateur")
                return False
        except KeyboardInterrupt:
            # Gestion de l'interruption par Ctrl+C
            print("\n[VALIDATION] Validation interrompue")
            return False
    
    # Confirmation finale que tous les paramètres sont validés
    print("[VALIDATION] Tous les paramètres sont valides")
    return True

def run_temperature_simulation(simulation_data: dict) -> Optional[float]:
    """
    @brief   Exécute une simulation complète de température avec dictionnaire.
    @details Fonction principale d'orchestration qui extrait les paramètres
             d'un dictionnaire, valide tous les paramètres et execute la
             simulation complète avec gestion d'erreur robuste.

    @param simulation_data  Dictionnaire contenant tous les paramètres requis:
                           - probe_type: Type de sonde (str)
                           - n: Paramètre de pondération (float)
                           - k_m: Paramètre exposant (float)
                           - temperature: Température mesurée (float)
                           - forecast_temperature: Température prévue (float)

    @return                Température simulée [°C] ou None si erreur.

    @warning               Retourne None pour toute erreur de validation ou calcul.
    """
    # Affichage d'en-tête de la simulation avec séparateur visuel
    print("\n=== SIMULATION DE TEMPÉRATURE ===")
    
    # Bloc de traitement avec gestion complète des exceptions
    try:
        # Extraction sécurisée de tous les paramètres du dictionnaire
        probe_type = simulation_data["probe_type"]
        n = float(simulation_data["n"])
        k_m = float(simulation_data["k_m"])
        t_mes = float(simulation_data["temperature"])
        t_prev = float(simulation_data["forecast_temperature"])
        
        # Affichage formaté de tous les paramètres extraits
        print(f"[SIM] Paramètres d'entrée:")
        print(f"[SIM]   Type de sonde: {probe_type}")
        print(f"[SIM]   Paramètre n: {n}")
        print(f"[SIM]   Paramètre k_m: {k_m}")
        print(f"[SIM]   Température mesurée: {t_mes}°C")
        print(f"[SIM]   Température prévue: {t_prev}°C")
        
        # Étape de validation complète des paramètres extraits
        if not validate_simulation_parameters(probe_type, n, k_m, t_mes, t_prev):
            # Arrêt immédiat si validation échoue
            print("[SIM] Échec de la validation des paramètres")
            return None
        
        # Calcul de la température simulée avec paramètres validés
        t_sim = calculate_simulated_temperature(t_mes, t_prev, n, k_m)
        
        # Vérification que le calcul a réussi
        if t_sim is None:
            # Gestion du cas d'échec de calcul
            print("[SIM] Échec du calcul de la température simulée")
            return None
        
        # Section d'affichage des résultats avec formatage soigné
        print(f"\n[SIM] RÉSULTAT:")
        print(f"[SIM] Température simulée: {t_sim:.2f}°C")
        
        # Analyse comparative automatique du résultat obtenu
        ecart_mesure = abs(t_sim - t_mes)
        ecart_prevision = abs(t_sim - t_prev)
        
        # Classification intelligente du résultat selon les écarts
        if ecart_mesure < 0.1:
            # Résultat très proche de la mesure actuelle
            print(f"[SIM] Simulation proche de la mesure (écart: {ecart_mesure:.3f}°C)")
        elif ecart_prevision < ecart_mesure:
            # Résultat tend vers la prévision plutôt que la mesure
            print(f"[SIM] Simulation tend vers la prévision")
        else:
            # Résultat tend vers la mesure plutôt que la prévision
            print(f"[SIM] Simulation tend vers la mesure")
        
        # Retour du résultat calculé et validé
        return t_sim
        
    except KeyError as e:
        # Gestion des paramètres manquants dans le dictionnaire
        print(f"[SIM] Paramètre manquant: {e}")
        return None
    except (ValueError, TypeError) as e:
        # Gestion des erreurs de conversion de type
        print(f"[SIM] Erreur de conversion de type: {e}")
        return None
    except Exception as e:
        # Capture de toute autre exception non prévue
        print(f"[SIM] Erreur inattendue: {e}")
        return None

