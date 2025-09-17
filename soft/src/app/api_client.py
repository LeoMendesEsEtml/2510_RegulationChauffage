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
                if "param" not in data or not data["param"]:
                    raise ApiError("Champ 'param' manquant ou vide")
                entry = data["param"][0]
                probe_type = entry.get("probe_type")
                n = entry.get("n")
                k_m = entry.get("k_m")
                temperature = entry.get("temperature")
                if None in (probe_type, n, k_m, temperature):
                    raise ApiError("Un ou plusieurs champs requis sont manquants dans la réponse API")
                print(f"[API] Paramètres récupérés: {entry}")
                return {
                    "probe_type": probe_type,
                    "n": n,
                    "k_m": k_m,
                    "temperature": temperature
                }
                
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
                if "forecast" not in data or not data["forecast"]:
                    raise ApiError("Champ 'forecast' manquant ou vide")
                forecast = data["forecast"][0]
                temperature_forecast = forecast["temperature"]
                print(f"[API] Prévisions récupérées: {forecast}")
                return {"temperature": temperature_forecast}
                
            except requests.exceptions.RequestException as e:
                print(f"[API] Tentative {attempt + 1}/{MAX_RETRIES} échouée: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise ApiError(f"Impossible de récupérer les prévisions après {MAX_RETRIES} tentatives: {e}")
            except json.JSONDecodeError as e:
                raise ApiError(f"Réponse JSON invalide: {e}")

    def post_measured_temperature(self, temperature: float, channel: int = None) -> bool:
        """
        Envoie la température mesurée vers l'API td25_param
        :param temperature: Température mesurée en °C
        :param channel: Canal de mesure (optionnel)
        :return: True si succès, False sinon
        """
        url = f"{self.base_url}/td25_param"
        
        # Préparation des paramètres URL (comme dans l'exemple fourni)
        params = {
            "mac_address": self.mac_address,
            "measured_temp": temperature
        }
        
        if channel is not None:
            params["channel"] = channel
            
        print(f"[API] POST {url} params={params}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    url, 
                    params=params,  # Tout en paramètres URL
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code in [200, 201]:
                    print(f"[API] Température envoyée avec succès: {temperature}°C")
                    return True
                else:
                    print(f"[API] Erreur HTTP {response.status_code}: {response.text}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        return False
                        
            except requests.exceptions.RequestException as e:
                print(f"[API] Tentative {attempt + 1}/{MAX_RETRIES} d'envoi échouée: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"[API] Impossible d'envoyer la température après {MAX_RETRIES} tentatives")
                    return False
        
        return False

def get_simulation_data(mac_address: str) -> Dict[str, Any]:
    """
    Récupère les données de simulation depuis les APIs
    
    :param mac_address: Adresse MAC du dispositif
    :return: Dictionnaire avec toutes les données nécessaires
    :raises ApiError: Si aucune donnée valide n'est obtenue
    """
    client = ApiClient(mac_address)
    
    # Récupération automatique
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

def send_temperature_measurement(mac_address: str, temperature: float, channel: int = None) -> bool:
    """
    Envoie une mesure de température vers l'API
    
    :param mac_address: Adresse MAC du dispositif
    :param temperature: Température mesurée en °C
    :param channel: Canal de mesure (optionnel)
    :return: True si succès, False sinon
    """
    client = ApiClient(mac_address)
    
    try:
        return client.post_measured_temperature(temperature, channel)
    except Exception as e:
        print(f"[API] Erreur lors de l'envoi de la température: {e}")
        return False

# Test du module (à des fins de développement)
if __name__ == "__main__":
    test_mac = "0030DEABCDEF"
    
    try:
        data = get_simulation_data(test_mac)
        print(f"\nDonnées finales: {data}")
    except ApiError as e:
        print(f"Erreur: {e}")