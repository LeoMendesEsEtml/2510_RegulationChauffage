# 2510_RegulationChauffage

## Description
Solution matérielle et logicielle basée sur Raspberry Pi Compute Module 5 pour remplacer un automate de chaudière.  
Le système lit des sondes réelles, calcule une température « simulée » à partir des prévisions météo, et applique une résistance équivalente à la chaudière via un réseau de résistances commandé. Connexion à l'API Oblo en HTTP (GET/POST) et publication des **mesures** & de l'**état** vers un Cloud, conformément au CdC.

**Documentation complète disponible sur : [leomendesesetml.github.io/2510_RegulationChauffage.github.io](https://leomendesesetml.github.io/2510_RegulationChauffage.github.io/index.html)**

## Fonctionnalités (réf. CdC v02)
- Récupération des paramètres et prévisions via **API HTTP** (Oblo, GET/POST).
- Lecture d'une sonde de température extérieure (capteur **résistif**), conversion en **°C**.
- Génération d'une **sonde simulée** via réseau de résistances (pilotage **ADG731**).
- **Publication** des mesures et de l'état de l'appareil vers le **Cloud**.
- Cadence périodique **5 minutes**, journalisation en **JSON lines**.
- Gestion de **1 à 4** canaux actifs, contact sec prioritaire, relais bypass et LED d'état.

## Architecture système

### Matériel principal
- **Compute Module 5 (CM5)** - Processeur principal
- **ADS124S08** - ADC delta-sigma, communication **SPI1**, signaux DRDY/START en GPIO
- **TMUX1204** - Multiplexeur sélection **Rref** (A0/A1)
- **ADG731** - Multiplexeur **SPI0** vers réseau de **résistances simulées**
- **Entrée contact sec**, **relais bypass**, **LED** frontale

### Logiciel principal
- **Python 3.11+** avec architecture modulaire
- **spidev**, **periphery** (SPI/GPIO), **requests** (HTTP), **flask** (WebUI)
- Interface web intégrée pour configuration et monitoring
- Service **systemd** et logs JSON rotatifs
- Simulation et validation complète des mesures

## Flux opératoire (cycle 5 min)

### Séquence de mesure
1. **Contacts secs** - Lecture état prioritaire via mesure_24v_dry_contact.py
2. **Pour chaque canal actif (1-4)** :
   - Sélection **Rref** via TMUX1204
   - Configuration **ADC** via ADS124S08
   - **Mesure single-shot** → code 24 bits → **Tmes**
   - Conversion résistance/température

### Simulation et application
3. **API Oblo** - Récupération paramètres (**N, kM, Tprevu**)
4. **Calcul Tsim** - Formule prédictive temperature_simulation.py
5. **Application MUX** - Résistance simulée via ADG731
6. **Sauvegarde** - État système dans last_state.json

### Gestion d'erreurs
- **LED frontale** - Patterns d'erreur (1Hz normal, 2Hz faute)
- **Relais bypass** - Sécurité en cas de défaut
- **Logs JSON** - Traçabilité complète des événements

## Interface utilisateur et contrôle

### Interface web intégrée
- **URL locale** : `http://192.168.1.109:8080`
- **Configuration** : Types capteurs, timeouts, intervalles
- **Monitoring** : Données temps réel, historique des mesures
- **API REST** : `/api/config`, `/api/state`

### Types de capteurs supportés
- **De Dietrich AF60**, **Siemens QAC32**
- **PT1000**, **Ni1000 TK5000/TK6180**
- **NTC 1k/2k/2.2k/10k** (diverses courbes)
- **KTY81-210**

## Installation et déploiement

### Installation système
```bash
# Dépendances système
sudo apt update
sudo apt install python3-pip python3-venv

# Dépendances Python
pip3 install spidev periphery requests flask

# Configuration SPI
sudo raspi-config  # Activer SPI0 et SPI1
```

### Lancement du système
```bash
# Mode automatique avec cycles 5 minutes
python3 /home/oblo/proj/2510_RegulationChauffage_soft/soft/src/app/main.py

# Mode manuel avec interface web
python3 /home/oblo/proj/2510_RegulationChauffage_soft/soft/src/app/main.py --webui

# Mode manuel sans cycles automatiques
python3 /home/oblo/proj/2510_RegulationChauffage_soft/soft/src/app/main.py --manual

# Exécution unique (test)
python3 /home/oblo/proj/2510_RegulationChauffage_soft/soft/src/app/main.py --once
```

### Service systemd (production)
```bash
# Installation service automatique
sudo cp 2510-regulation.service /etc/systemd/system/
sudo systemctl enable 2510-regulation
sudo systemctl start 2510-regulation

# Vérification statut
sudo systemctl status 2510-regulation
```

## API et connectivité

### API oblosolutions.ch
- **Endpoint paramètres** : `GET /td25_param?mac_address=XXX`
- **Endpoint prévisions** : `GET /td25_forecast?mac_address=XXX`
- **Envoi mesures** : `POST /td25_param` avec données température

### Données JSON échangées
```json
{
  "probe_type": "Ni1000 TK5000",
  "n": 0.8,
  "k_m": -0.1,
  "temperature": 18.5,
  "forecast_temperature": 15.2,
  "timestamp": "2025-09-18T14:30:00Z"
}
```

### Configuration réseau
- **Interface** : eth0 (192.168.1.109)
- **Port web** : 8080
- **Timeout API** : 10 secondes
- **Retry** : 3 tentatives

## Mappage matériel CM5

### Configuration SPI
- **SPI0** → **ADG731** (réseau résistif) : SCLK, MOSI, CS[0..3]
- **SPI1** → **ADS124S08** (métrologie) : SCLK, MOSI, MISO, CS

### Table GPIO principale
| Signal               | GPIO | Fonction                    | Description               |
|----------------------|:----:|-----------------------------|---------------------------|
| **MUX CS 1-4**       | 2,3,7,8 | Sélection carte ADG731   | Adressage résistances     |
| **MUX MOSI/SCLK**    | 10,11 | Communication SPI0         | Commande multiplexeur     |
| **CM 24V OUT/SENSE** | 12-15 | Contacts secs              | Entrées prioritaires      |
| **ADC SPI1**         | 17-20 | Communication ADC          | Mesures température       |
| **ADC DRDY/START**   | 21,22 | Signaux contrôle ADC       | Synchronisation mesures   |
| **ADC A0/A1**        | 23,24 | Sélection canal/Rref       | Multiplexage entrées      |
| **FRONT LED**        | 26    | Indicateur état            | Status visuel système     |
| **CMD RELAY**        | 16    | Relais bypass              | Sécurité défaillance      |

## Validation et diagnostics

### Tests système
- **Communication ADC** : Vérification SPI et conversion
- **Simulation résistance** : Validation calculs et MUX
- **API connectivity** : Test endpoints oblosolutions.ch
- **Temperature accuracy** : Calibration capteurs

### Monitoring système
- **État système** : last_state.json (dernières mesures)
- **Patterns LED** : 
  - 1Hz : Fonctionnement normal
  - 2Hz : Erreur système
  - Fixe : Mode manuel
- **Interface web** : Dashboard temps réel
- **Logs JSON** : Historique complet des événements

### Sécurité et robustesse
- **Gestion d'exceptions** : Toutes les communications
- **Validation paramètres** : Avant simulation résistance
- **Timeouts configurables** : API et communications série
- **État de repli** : Relais bypass en cas d'erreur critique
- **Watchdog logiciel** : Redémarrage automatique

## Conformité hardware

### Checklist CEM
- **Découplage** : Condensateurs proche de chaque IC
- **Plans de masse** : Retour propre autour ADC
- **Routage SPI** : Longueurs égalisées, impédance contrôlée
- **Réseau résistif** : Tolérances 0.1%, TCR < 25ppm/°C
- **Testpoints** : Tous signaux critiques accessibles

### Points de mesure
- **Signaux SPI** : DRDY, SCLK, MOSI, MISO, CS
- **Alimentations** : 3.3V, 5V, 24V
- **Références** : Rref, AVDD, AVSS
- **GPIO** : A0, A1, contrôles multiplexeurs

---

## Références et documentation

- **Documentation technique complète** : [leomendesesetml.github.io/2510_RegulationChauffage.github.io](https://leomendesesetml.github.io/2510_RegulationChauffage.github.io/index.html)
- **Cahier des charges** : Exigences fonctionnelles et techniques
- **Schémas électroniques** : Plans de câblage et BOM
- **API Documentation** : Spécifications oblosolutions.ch
- **Code source** : Modules Python avec documentation inline

## Informations projet

**Auteur** : Léo Mendes - ETML ES  
**Projet** : 2510_RegulationsChauffage  
**Mandant** : Oblo Solutions  
**Version** : 1.0.0  
**Chemin système** : `/home/oblo/proj/2510_RegulationChauffage_soft/soft/src/`  
**Copyright** : 2025
