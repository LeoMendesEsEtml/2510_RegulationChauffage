# -*- coding: utf-8 -*-
"""
@file        api_client.py
@brief       Client API pour les services oblosolutions.ch.
@details     Ce module fournit un client HTTP pour interroger les APIs
             td25_param et td25_forecast. Il gère les timeouts, les retries
             automatiques et les erreurs de réseau. Inclut des fonctions
             utilitaires pour récupérer les données de simulation et envoyer
             les mesures de température.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations

# Client HTTP pour les requêtes REST
import requests
# Fonctions temporelles (délais, sleep)
import time
# Sérialisation/désérialisation JSON
import json
# Types pour l'annotation de code
from typing import Dict, Optional, Any

# ---------------------------------------------------------------------------
# Constantes du module
# ---------------------------------------------------------------------------

# Délai d'attente pour les requêtes HTTP [s]
REQUEST_TIMEOUT = 10
# Nombre maximum de tentatives en cas d'échec
MAX_RETRIES = 3
# Délai entre les tentatives [s]
RETRY_DELAY = 1

# ---------------------------------------------------------------------------
# Classes d'exception
# ---------------------------------------------------------------------------

class ApiError(Exception):
    """
    @brief   Exception pour les erreurs d'API.
    @details Exception personnalisée levée en cas d'erreur lors des
             communications avec les APIs oblosolutions.ch.
    """
    pass

# ---------------------------------------------------------------------------
# Classes principales
# ---------------------------------------------------------------------------

class ApiClient:
    """
    @brief   Client pour interroger les APIs oblosolutions.ch.
    @details Fournit des méthodes pour récupérer les paramètres de simulation,
             les prévisions météo et envoyer les mesures de température.
             Gère automatiquement les retries et les timeouts.
    """
    
    # Pas de préfixe, endpoints à la racine
    API_PATH_PREFIX = ""

    def __init__(self, mac_address: str):
        """
        @brief   Initialise le client API.
        @details Configure l'adresse MAC du dispositif et l'URL de base
                 pour les communications avec les services oblosolutions.ch.

        @param   mac_address Adresse MAC du dispositif (ex: "0030DEABCDEF").
        """
        # Stockage de l'adresse MAC du dispositif
        self.mac_address = mac_address
        # URL de base pour tous les appels API
        self.base_url = "https://dev.oblosolutions.ch"

    def get_parameters(self) -> Dict[str, Any]:
        """
        @brief   Récupère les paramètres depuis l'API td25_param.
        @details Effectue une requête GET vers l'endpoint td25_param avec
                 l'adresse MAC comme paramètre. Parse la réponse JSON et
                 extrait les champs probe_type, n, k_m et temperature.
                 Inclut un système de retry automatique en cas d'échec.

        @return  Dictionnaire contenant probe_type, n, k_m, temperature.

        @exception ApiError En cas d'erreur de récupération des données.
        """
        # Construction de l'URL pour l'endpoint des paramètres
        url = f"{self.base_url}/td25_param"
        # Paramètres de la requête GET
        params = {"mac_address": self.mac_address}
        # Affichage de la requête pour le debug
        print(f"[API] GET {url} params={params}")
        
        # Boucle de retry en cas d'échec
        for attempt in range(MAX_RETRIES):
            try:
                # Exécution de la requête GET avec timeout
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                # Vérification du code de statut HTTP
                if response.status_code != 200:
                    # Lever une exception en cas d'erreur HTTP
                    raise ApiError(f"Erreur HTTP {response.status_code}: {response.text}")
                
                # Parsing de la réponse JSON
                data = response.json()
                # Vérification de la présence du champ 'param'
                if "param" not in data or not data["param"]:
                    raise ApiError("Champ 'param' manquant ou vide")
                # Extraction du premier élément des paramètres
                entry = data["param"][0]
                # Extraction des champs individuels
                probe_type = entry.get("probe_type")
                n = entry.get("n")
                k_m = entry.get("k_m")
                temperature = entry.get("temperature")
                # Vérification que tous les champs requis sont présents
                if None in (probe_type, n, k_m, temperature):
                    raise ApiError("Un ou plusieurs champs requis sont manquants dans la réponse API")
                # Affichage des paramètres récupérés
                print(f"[API] Paramètres récupérés: {entry}")
                # Retour du dictionnaire formaté
                return {
                    "probe_type": probe_type,
                    "n": n,
                    "k_m": k_m,
                    "temperature": temperature
                }
                
            except requests.exceptions.RequestException as e:
                # Gestion des erreurs de réseau
                print(f"[API] Tentative {attempt + 1}/{MAX_RETRIES} échouée: {e}")
                # Attente avant retry si ce n'est pas la dernière tentative
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    # Lever une exception après épuisement des tentatives
                    raise ApiError(f"Impossible de récupérer les paramètres après {MAX_RETRIES} tentatives: {e}")
            except json.JSONDecodeError as e:
                # Gestion des erreurs de parsing JSON
                raise ApiError(f"Réponse JSON invalide: {e}")
    
    def get_forecast(self) -> Dict[str, Any]:
        """
        @brief   Récupère la température prévue depuis l'API td25_forecast.
        @details Effectue une requête GET vers l'endpoint td25_forecast avec
                 l'adresse MAC comme paramètre. Parse la réponse JSON et
                 extrait la température de prévision météorologique.
                 Inclut un système de retry automatique en cas d'échec.

        @return  Dictionnaire contenant la temperature prévue.

        @exception ApiError En cas d'erreur de récupération des données.
        """
        # Construction de l'URL pour l'endpoint des prévisions
        url = f"{self.base_url}/td25_forecast"
        # Paramètres de la requête GET
        params = {"mac_address": self.mac_address}
        # Affichage de la requête pour le debug
        print(f"[API] GET {url} params={params}")
        
        # Boucle de retry en cas d'échec
        for attempt in range(MAX_RETRIES):
            try:
                # Exécution de la requête GET avec timeout
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                
                # Vérification du code de statut HTTP
                if response.status_code != 200:
                    # Lever une exception en cas d'erreur HTTP
                    raise ApiError(f"Erreur HTTP {response.status_code}: {response.text}")
                
                # Parsing de la réponse JSON
                data = response.json()
                # Vérification de la présence du champ 'forecast'
                if "forecast" not in data or not data["forecast"]:
                    raise ApiError("Champ 'forecast' manquant ou vide")
                # Extraction du premier élément des prévisions
                forecast = data["forecast"][0]
                # Extraction de la température de prévision
                temperature_forecast = forecast["temperature"]
                # Affichage des prévisions récupérées
                print(f"[API] Prévisions récupérées: {forecast}")
                # Retour du dictionnaire avec la température
                return {"temperature": temperature_forecast}
                
            except requests.exceptions.RequestException as e:
                # Gestion des erreurs de réseau
                print(f"[API] Tentative {attempt + 1}/{MAX_RETRIES} échouée: {e}")
                # Attente avant retry si ce n'est pas la dernière tentative
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    # Lever une exception après épuisement des tentatives
                    raise ApiError(f"Impossible de récupérer les prévisions après {MAX_RETRIES} tentatives: {e}")
            except json.JSONDecodeError as e:
                # Gestion des erreurs de parsing JSON
                raise ApiError(f"Réponse JSON invalide: {e}")

    def post_measured_temperature(self, temperature: float, channel: int = None) -> bool:
        """
        @brief   Envoie la température mesurée vers l'API td25_param.
        @details Effectue une requête POST vers l'endpoint td25_param avec
                 la température mesurée et optionnellement le numéro de canal.
                 Tous les paramètres sont envoyés dans l'URL comme paramètres
                 de requête. Inclut un système de retry automatique.

        @param   temperature Température mesurée en °C.
        @param   channel     Canal de mesure (optionnel).

        @return  True si succès, False sinon.
        """
        # Construction de l'URL pour l'endpoint des paramètres
        url = f"{self.base_url}/td25_param"
        
        # Préparation des paramètres URL (comme dans l'exemple fourni)
        # Paramètres de base pour l'envoi
        params = {
            "mac_address": self.mac_address,
            "measured_temp": temperature
        }
        
        # Ajout du canal si spécifié
        if channel is not None:
            params["channel"] = channel
            
        # Affichage de la requête pour le debug
        print(f"[API] POST {url} params={params}")
        
        # Boucle de retry en cas d'échec
        for attempt in range(MAX_RETRIES):
            try:
                # Exécution de la requête POST avec paramètres en URL
                response = requests.post(
                    url, 
                    # Tout en paramètres URL
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Vérification du succès de la requête
                if response.status_code in [200, 201]:
                    print(f"[API] Température envoyée avec succès: {temperature}°C")
                    return True
                else:
                    # Affichage de l'erreur HTTP
                    print(f"[API] Erreur HTTP {response.status_code}: {response.text}")
                    # Retry si ce n'est pas la dernière tentative
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        return False
                        
            except requests.exceptions.RequestException as e:
                # Gestion des erreurs de réseau
                print(f"[API] Tentative {attempt + 1}/{MAX_RETRIES} d'envoi échouée: {e}")
                # Attente avant retry si ce n'est pas la dernière tentative
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"[API] Impossible d'envoyer la température après {MAX_RETRIES} tentatives")
                    return False
        
        return False

# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def get_simulation_data(mac_address: str) -> Dict[str, Any]:
    """
    @brief   Récupère les données de simulation depuis les APIs.
    @details Combine les appels vers td25_param et td25_forecast pour
             récupérer tous les paramètres nécessaires à la simulation
             de température. Utilise le client ApiClient pour gérer
             les retries et les erreurs automatiquement.

    @param   mac_address Adresse MAC du dispositif.

    @return  Dictionnaire avec toutes les données nécessaires pour la simulation.

    @exception ApiError Si aucune donnée valide n'est obtenue.
    """
    # Création d'une instance du client API
    client = ApiClient(mac_address)
    
    # Récupération automatique
    print("[SIMULATION] Tentative de récupération automatique des données...")
    
    # Récupération des paramètres
    params = client.get_parameters()
    
    # Récupération des prévisions
    forecast = client.get_forecast()
    
    # Combinaison des données
    # Création du dictionnaire de données de simulation
    simulation_data = {
        "probe_type": params["probe_type"],
        "n": float(params["n"]),
        "k_m": float(params["k_m"]),
        "temperature": float(params["temperature"]),
        "forecast_temperature": float(forecast["temperature"])
    }
    
    # Confirmation du succès de la récupération
    print("[SIMULATION] Données récupérées automatiquement avec succès")
    return simulation_data

def send_temperature_measurement(mac_address: str, temperature: float, channel: int = None) -> bool:
    """
    @brief   Envoie une mesure de température vers l'API.
    @details Fonction utilitaire qui crée un client ApiClient et utilise
             la méthode post_measured_temperature pour envoyer la température
             mesurée. Gère les exceptions et retourne un booléen simple.

    @param   mac_address Adresse MAC du dispositif.
    @param   temperature Température mesurée en °C.
    @param   channel     Canal de mesure (optionnel).

    @return  True si succès, False sinon.
    """
    # Création d'une instance du client API
    client = ApiClient(mac_address)
    
    try:
        # Tentative d'envoi de la température
        return client.post_measured_temperature(temperature, channel)
    except Exception as e:
        # Gestion des erreurs générales
        print(f"[API] Erreur lors de l'envoi de la température: {e}")
        return False

# ---------------------------------------------------------------------------
# Point d'entrée pour les tests
# ---------------------------------------------------------------------------

# Test du module (à des fins de développement)
if __name__ == "__main__":
    # Adresse MAC de test
    test_mac = "0030DEABCDEF"
    
    try:
        # Tentative de récupération des données de simulation
        data = get_simulation_data(test_mac)
        # Affichage des données récupérées
        print(f"\nDonnées finales: {data}")
    except ApiError as e:
        # Gestion des erreurs spécifiques à l'API
        print(f"Erreur: {e}")