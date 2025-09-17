# Système de Simulation de Température

Ce système implémente le calcul et l'application de la température simulée selon le cahier des charges spécifié.

## Vue d'ensemble

Le système effectue les étapes suivantes :

1. **Récupération des paramètres** depuis les APIs oblosolutions.ch
2. **Calcul de la température simulée** : `T_sim = T_mes + ((T_prev - T_mes) * n * exp(k_m))`
3. **Conversion en résistance simulée** selon le type de sonde
4. **Application via MUX** pour simuler la résistance
5. **Confirmation** des valeurs appliquées à l'utilisateur

## Architecture

### Modules développés

- **`api_client.py`** : Client pour interroger les APIs oblosolutions.ch
- **`temperature_simulation.py`** : Calcul de la température simulée avec validation
- **`temperature_conversion.py`** : Conversion température ↔ résistance (étendu)
- **`resistance_simulation.py`** : Commande du MUX pour simulation de résistance
- **`main_temperature_simulation.py`** : Orchestrateur principal
- **`test_temperature_simulation_integration.py`** : Tests d'intégration

### APIs utilisées

- **td25_param** : `https://oblosolutions.ch/td25_param?mac_address=0030DEABCDEF`
  - Retourne : `probe_type`, `n`, `k_m`, `temperature`
- **td25_forecast** : `https://oblosolutions.ch/td25_forecast?mac_address=0030DEABCDEF`
  - Retourne : `temperature` (prévue)

## Utilisation

### Mode principal : Simulation de température

```bash
# Lancement de la simulation complète
python main.py --simulation
```

### Mode test : Validation des modules

```bash
# Tests d'intégration
python main.py --test-simulation
```

### Mode normal : Mesures ADC (original)

```bash
# Mode de mesure original
python main.py
```

### Aide

```bash
# Affichage de l'aide détaillée
python main.py --info
```

## Workflow de simulation

### 1. Récupération des paramètres

```
🌐 ÉTAPE 1: Récupération des paramètres depuis l'API
- Interrogation de td25_param et td25_forecast
- Validation des données reçues
- Fallback vers saisie manuelle si échec API
```

### 2. Calcul de la température simulée

```
🧮 ÉTAPE 2: Calcul de la température simulée
- Application de la formule : T_sim = T_mes + ((T_prev - T_mes) * n * exp(k_m))
- Validation des paramètres d'entrée
- Gestion des cas limites (overflow, valeurs aberrantes)
```

### 3. Conversion en résistance

```
🔄 ÉTAPE 3: Conversion température vers résistance
- Utilisation des tables de conversion par type de sonde
- Interpolation linéaire inverse
- Support : PT1000, Ni1000_TK5000, NTC_10k, etc.
```

### 4. Application via MUX

```
🤖 ÉTAPE 4: Application de la résistance simulée
- Calcul de la combinaison optimale de résistances
- Commande du multiplexeur ADG731
- Validation de l'application
```

### 5. Confirmation finale

```
📋 ÉTAPE 5: Confirmation finale
- Affichage des valeurs appliquées
- Validation de la précision
- Maintien de la simulation active
```

## Types de sondes supportés

- **PT1000** : Sonde platine 1000Ω
- **Ni1000 TK5000** : Sonde nickel 1000Ω
- **NTC 10k 3977** : Thermistance NTC 10kΩ
- **De Dietrich AF60** : Sonde spécifique
- **Siemens QAC32** : Sonde spécifique
- Et autres selon les tables de conversion

## Configuration réseau de résistances

Le système utilise un réseau de résistances simulées via MUX :

```python
RESISTANCE_NETWORK = {
    0: 1000,      # 1k ohm
    1: 2200,      # 2.2k ohm  
    2: 4700,      # 4.7k ohm
    3: 10000,     # 10k ohm
    4: 22000,     # 22k ohm
    5: 47000,     # 47k ohm
    6: 100000,    # 100k ohm
    # ... plus résistances parallèles
}
```

## Gestion des erreurs

### Erreurs API
- Timeout de connexion (10s)
- Retries automatiques (3 tentatives)
- Fallback vers saisie manuelle

### Erreurs de calcul
- Validation des plages de valeurs
- Gestion de l'overflow mathématique
- Vérification de cohérence

### Erreurs matérielles
- Test de présence du MUX
- Validation des commutations
- Reset automatique en cas d'erreur

## Validation et tests

### Tests unitaires

```bash
# Test d'un module spécifique
python -m app.temperature_simulation
python -m app.resistance_simulation
```

### Tests d'intégration

```bash
# Tests complets sans matériel
python app/test_temperature_simulation_integration.py
```

### Mode simulation test

```bash
# Simulation avec données fictives
python app/main_temperature_simulation.py --test
```

## Dépendances

### Modules Python requis
- `requests` : Communication HTTP avec APIs
- `spidev` : Communication SPI avec MUX
- `periphery` : Gestion GPIO (existant)
- `math` : Calculs mathématiques

### Matériel requis
- Multiplexeur ADG731 sur SPI0
- Réseau de résistances simulées
- GPIO pour contrôle CS

## Configuration

### MAC Address
```python
MAC_ADDRESS = "0030DEABCDEF"  # Configuré selon cahier des charges
```

### URLs API
```python
base_url = "https://oblosolutions.ch"
# td25_param et td25_forecast
```

### Timeouts et retries
```python
REQUEST_TIMEOUT = 10  # secondes
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconde
```

## Exemples d'utilisation

### Simulation complète automatique

```bash
$ python main.py --simulation

=== SYSTÈME DE SIMULATION DE TEMPÉRATURE ===
MAC Address: 0030DEABCDEF

🌐 ÉTAPE 1: Récupération des paramètres depuis l'API
[API] Paramètres récupérés: {"probe_type": "PT1000", "n": 0.3, ...}

🧮 ÉTAPE 2: Calcul de la température simulée
[SIM] Température simulée: 24.52°C

🔄 ÉTAPE 3: Conversion température vers résistance
[CONV] Conversion réussie: 24.52°C -> 1094.8 ohms

🤖 ÉTAPE 4: Application de la résistance simulée
[SIM_R] Résistance appliquée: 1094.2Ω

✅ SIMULATION TERMINÉE AVEC SUCCÈS!
```

### Simulation avec saisie manuelle

```bash
$ python main.py --simulation

[API] Erreur de connexion, basculement vers saisie manuelle...

=== Saisie manuelle des paramètres ===
Type de sonde: PT1000
Paramètre n: 0.3
Paramètre k_m: 0.5
Température mesurée (°C): 22.5
Température prévue (°C): 28.0

[SIM] Température simulée: 23.32°C
...
```

## Troubleshooting

### Problèmes courants

1. **Erreur API** : Vérifier connexion réseau et URLs
2. **Type de sonde non supporté** : Vérifier la liste des types disponibles
3. **Résistance non simulable** : Ajuster le réseau de résistances
4. **MUX non détecté** : Vérifier connexions SPI et GPIO

### Logs de débogage

Le système fournit des logs détaillés pour chaque étape :
- `[API]` : Communications réseau
- `[SIM]` : Calculs de simulation
- `[CONV]` : Conversions de température
- `[SIM_R]` : Simulation de résistance

### Mode debug

Pour activer plus de logs, modifier les modules directement ou utiliser le mode test.

## Contact et support

Ce système a été développé selon le cahier des charges spécifié pour le projet 2510_RegulationChauffage.

Version : 1.0
Date : Septembre 2024