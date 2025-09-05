# 2510_RegulationChauffage

## Description
Solution matérielle et logicielle basée sur Raspberry Pi Compute Module 5 pour remplacer un automate de chaudière.  
Le système lit des sondes réelles, calcule une température « simulée » à partir des prévisions météo, et applique une résistance équivalente à la chaudière (réseau commandé). Connexion à l’API Oblo en HTTP (GET/POST) et publication des **mesures** & de l’**état** vers un Cloud, conformément au CdC.

## Fonctionnalités (réf. CdC v02)
- Récupération des paramètres et prévisions via **API HTTP** (Oblo, GET/POST).
- Lecture d’une sonde de température extérieure (capteur **résistif**), conversion en **°C**.
- Génération d’une **sonde simulée** via réseau de résistances (pilotage **ADG731**).
- **Publication** des mesures et de l’état de l’appareil vers le **Cloud**.
- Cadence périodique **5 minutes**, journalisation en **JSON lines**.
- Gestion de **1 à 4** canaux actifs, contact sec prioritaire, relais bypass et LED d’état.

## Matériel principal
- **Compute Module 5 (CM5)**
- **ADS124S0x** (ADC delta-sigma, **SPI1**, DRDY/START en GPIO)
- **TMUX1204** (sélection **Rref** A0/A1)
- **ADG731** (**SPI0**) vers réseau de **résistances simulées**
- **Entrée contact sec**, **relais bypass**, **LED** frontale

## Logiciel principal
- **Python 3.11**
- **spidev**, **RPi.GPIO** (SPI/GPIO), **requests** (HTTP), **PyYAML** (config)
- Boucle périodique **5 min**, **logs JSON** rotatifs
- Service **systemd** en option

## Flux opératoire (périodique)
1. Lire **contact sec** (prioritaire).  
2. Pour chaque **canal actif (1..4)** : **sélection Rref** → **configurer ADC** → **single-shot** → **code 24 bits** → **Tmes**.  
3. Interroger **API Oblo** (**N, kM, Tprevu**) → **Tsim / slot / step** → **programmer ADG731**.  
4. **Publier** mesures + état vers **Cloud** ; **log** des événements.  
5. En faute : **relais OFF**, **LED 2 Hz**, **log "fault"**.

---

## Checklist routage & CEM (hardware)
- **Découplage** proche de chaque IC.
- **Retour de masse** propre autour de l’ADC.
- **SPI** longueurs maîtrisées, isolement des pistes bruyantes.
- **Réseau résistif** : tolérances & **TCR** documentés.
- **Testpoints** : DRDY, SCLK, MOSI, MISO, CS, A0, A1, **rails d’alim**.

## Dépendances logicielles
- RPi.GPIO  
- spidev  
- requests  
- PyYAML

---

## I/O CM5 – mappage & configuration SPI

### Résumé SPI
- **SPI0 → ADG731** (sortie réseau résistif) : **SCLK**, **MOSI** (pas de MISO).  
- **SPI1 → ADS124S0x** (métrologie) : **SCLK**, **MOSI**, **MISO**, **CS**.  
  Signaux **DRDY**, **START_SYNC**, **A0**, **A1** en **GPIO**.

### Table I/O
| Signal (nouveau nom) | GPIO | Patte CM5 | N° fonction | Fonction SoC        |
|----------------------|:----:|:---------:|:-----------:|---------------------|
| MUX CS 4             |  2   |    58     |     A0      | SPI0_CSn[3]         |
| MUX CS 3             |  3   |    56     |     A0      | SPI0_CSn[2]         |
| MUX CS 2             |  7   |    37     |     A0      | SPI0_CSn[1]         |
| MUX CS 1             |  8   |    39     |     A0      | SPI0_CSn[0]         |
| MUX MOSI             | 10   |    44     |     A0      | SPI0_SIO[0]         |
| MUX SCLK             | 11   |    38     |     A0      | SPI0_SCLK           |
| CM 24V OUT 1         | 12   |    31     |     A6      | PIO[12]             |
| CM 24V SENSE 1       | 13   |     8     |     A6      | PIO[13]             |
| CM 24V OUT 2         | 14   |     5     |     A6      | PIO[14]             |
| CM 24V SENSE 2       | 15   |    29     |     A6      | PIO[15]             |
| CMD RELAY            | 16   |    20     |     A6      | PIO[16]             |
| CS ADC               | 17   |    50     |     A0      | SPI1_CSn[0]         |
| SPI MISO ADC         | 18   |    49     |     A0      | SPI1_SIO[1]         |
| SPI MOSI ADC         | 19   |    26     |     A0      | SPI1_SIO[0]         |
| SPI SCLK ADC         | 20   |    25     |     A0      | SPI1_SCLK           |
| ADC DRDY             | 21   |    46     |     A6      | PIO[21]             |
| ADC START SYNC       | 22   |    47     |     A6      | PIO[22]             |
| ADC A0               | 23   |    45     |     A6      | PIO[23]             |
| ADC A1               | 24   |    41     |     A6      | PIO[24]             |
| FRONT LED            | 26   |    24     |     A6      | PIO[26]             |
---

## Références internes
- **Cahier des charges** : exigences API/Cloud, E/S, contraintes  
- **Schémas & notes hardware** : câblage, protections, valeurs  
- **Rapport & annexes techniques** : détails d’implémentation
