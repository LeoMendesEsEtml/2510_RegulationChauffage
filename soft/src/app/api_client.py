# -*- coding: utf-8 -*-
# file: api_client.py
"""
Module pour interroger les APIs d'oblosolutions.ch:
- td25_param: récupère probe_type, n, k_m, temperature
- td25_forecast: récupère temperature prévue

Gère les erreurs de réseau et les données manquantes.
"""

import requests
import time
import json
from typing import Dict, Optional, Any

# Configuration des timeouts et retries
REQUEST_TIMEOUT = 10  # secondes
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconde

class ApiError(Exception):
    """Exception pour les erreurs d'API"""
    pass

class ApiClient:
    """Client pour interroger les APIs oblosolutions.ch"""
    
    API_PATH_PREFIX = ""  # Pas de préfixe, endpoints à la racine

    def __init__(self, mac_address: str):
        """
        Initialise le client API
        :param mac_address: Adresse MAC du dispositif (ex: "0030DEABCDEF")
        """
        self.mac_address = mac_address
    self.base_url = "https://dev.oblosolutions.ch"

    def get_parameters(self) -> Dict[str, Any]:
        """
        Récupère les paramètres depuis l'API td25_param
        :return: Dictionnaire contenant probe_type, n, k_m, temperature
        :raises ApiError: En cas d'erreur de récupération des données
        """
        url = f"{self.base_url}/td25_param"
        params = {"mac_address": self.mac_address}
        print(f"[API] GET {url} params={params}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                if response.status_code != 200:
                    raise ApiError(f"Erreur HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                # Vérification des champs requis
                required_fields = ["probe_type", "n", "k_m", "temperature"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    raise ApiError(f"Champs manquants dans la réponse: {missing_fields}")
                
                # Validation des types de données
                if not isinstance(data.get("probe_type"), str):
                    raise ApiError("probe_type doit être une chaîne de caractères")
                
                try:
                    float(data["n"])
                    float(data["k_m"])
                    float(data["temperature"])
                except (ValueError, TypeError):
                    raise ApiError("n, k_m et temperature doivent être des nombres")
                
                print(f"[API] Paramètres récupérés: {data}")
                return data
                
            except requests.exceptions.RequestException as e:
                print(f"[API] Tentative {attempt + 1}/{MAX_RETRIES} échouée: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise ApiError(f"Impossible de récupérer les paramètres après {MAX_RETRIES} tentatives: {e}")
            except json.JSONDecodeError as e:
                raise ApiError(f"Réponse JSON invalide: {e}")
    
    def get_forecast(self) -> Dict[str, Any]:
        """
        Récupère la température prévue depuis l'API td25_forecast
        :return: Dictionnaire contenant temperature prévue
        :raises ApiError: En cas d'erreur de récupération des données
        """
        url = f"{self.base_url}/td25_forecast"
        params = {"mac_address": self.mac_address}
        print(f"[API] GET {url} params={params}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                if response.status_code != 200:
                    raise ApiError(f"Erreur HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                # Vérification du champ requis
                if "temperature" not in data:
                    raise ApiError("Champ 'temperature' manquant dans la réponse prévisions")
                
                # Validation du type de données
                try:
                    float(data["temperature"])
                except (ValueError, TypeError):
                    raise ApiError("La température prévue doit être un nombre")
                
                print(f"[API] Prévisions récupérées: {data}")
                return data
                
            except requests.exceptions.RequestException as e:
                print(f"[API] Tentative {attempt + 1}/{MAX_RETRIES} échouée: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise ApiError(f"Impossible de récupérer les prévisions après {MAX_RETRIES} tentatives: {e}")
            except json.JSONDecodeError as e:
                raise ApiError(f"Réponse JSON invalide: {e}")

def validate_manual_input(probe_type: str, n: float, k_m: float, t_mes: float, t_prev: float) -> bool:
    """
    Valide les données saisies manuellement
    
    :param probe_type: Type de sonde
    :param n: Paramètre n
    :param k_m: Paramètre k_m
    :param t_mes: Température mesurée
    :param t_prev: Température prévue
    :return: True si toutes les données sont valides
    """
    # Vérification du type de sonde
    valid_probe_types = ["PT1000", "Ni1000_TK5000", "NTC_10k"]
    if probe_type not in valid_probe_types:
        print(f"[VALIDATION] Type de sonde invalide: {probe_type}")
        print(f"[VALIDATION] Types supportés: {valid_probe_types}")
        return False
    
    # Vérification des plages de valeurs
    if not (-1.0 <= n <= 1.0):
        print(f"[VALIDATION] Paramètre n hors plage [-1.0, 1.0]: {n}")
        return False
    
    if not (-10.0 <= k_m <= 10.0):
        print(f"[VALIDATION] Paramètre k_m hors plage [-10.0, 10.0]: {k_m}")
        return False
    
    if not (-50.0 <= t_mes <= 100.0):
        print(f"[VALIDATION] Température mesurée hors plage [-50°C, 100°C]: {t_mes}")
        return False
    
    if not (-50.0 <= t_prev <= 100.0):
        print(f"[VALIDATION] Température prévue hors plage [-50°C, 100°C]: {t_prev}")
        return False
    
    return True

def get_manual_input() -> Optional[Dict[str, Any]]:
    """
    Demande à l'utilisateur de saisir manuellement les données manquantes
    
    :return: Dictionnaire avec les données saisies ou None si annulation
    """
    print("\n=== Saisie manuelle des paramètres ===")
    
    try:
        # Type de sonde
        print("Types de sondes supportés: PT1000, Ni1000_TK5000, NTC_10k")
        probe_type = input("Type de sonde: ").strip()
        
        # Paramètres numériques
        n = float(input("Paramètre n (-1.0 à 1.0): "))
        k_m = float(input("Paramètre k_m (-10.0 à 10.0): "))
        t_mes = float(input("Température mesurée (°C): "))
        t_prev = float(input("Température prévue (°C): "))
        
        # Validation
        if not validate_manual_input(probe_type, n, k_m, t_mes, t_prev):
            return None
        
        return {
            "probe_type": probe_type,
            "n": n,
            "k_m": k_m,
            "temperature": t_mes,
            "forecast_temperature": t_prev
        }
        
    except (ValueError, KeyboardInterrupt):
        print("\n[INPUT] Saisie annulée ou données invalides")
        return None

def get_simulation_data(mac_address: str) -> Dict[str, Any]:
    """
    Récupère les données de simulation depuis les APIs ou par saisie manuelle
    
    :param mac_address: Adresse MAC du dispositif
    :return: Dictionnaire avec toutes les données nécessaires
    :raises ApiError: Si aucune donnée valide n'est obtenue
    """
    client = ApiClient(mac_address)
    
    try:
        # Tentative de récupération automatique
        print("[SIMULATION] Tentative de récupération automatique des données...")
        
        # Récupération des paramètres
        params = client.get_parameters()
        
        # Récupération des prévisions
        forecast = client.get_forecast()
        
        # Combinaison des données
        simulation_data = {
            "probe_type": params["probe_type"],
            "n": float(params["n"]),
            "k_m": float(params["k_m"]),
            "temperature": float(params["temperature"]),
            "forecast_temperature": float(forecast["temperature"])
        }
        
        print("[SIMULATION] Données récupérées automatiquement avec succès")
        return simulation_data
        
    except ApiError as e:
        print(f"[SIMULATION] Erreur API: {e}")
        print("[SIMULATION] Basculement vers saisie manuelle...")
        
        # Saisie manuelle en cas d'échec
        manual_data = get_manual_input()
        if manual_data is None:
            raise ApiError("Aucune donnée valide fournie (API et saisie manuelle échouées)")
        
        return manual_data

# Test du module (à des fins de développement)
if __name__ == "__main__":
    test_mac = "0030DEABCDEF"
    
    try:
        data = get_simulation_data(test_mac)
        print(f"\nDonnées finales: {data}")
    except ApiError as e:
        print(f"Erreur: {e}")