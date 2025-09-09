# Test LM70 SPI - Guide d'utilisation

Ce répertoire contient plusieurs scripts pour tester la communication SPI avec un capteur de température LM70.

## Structure des fichiers

- `app/main.py` : Application principale (contient une fonction `test_lm70_spi()`)
- `app/test_lm70_compatible.py` : Script autonome qui fonctionne sur PC et Raspberry Pi
- `test_lm70_standalone.py` : Script autonome pour Raspberry Pi uniquement
- `mock_imports.py` : Module qui simule RPi.GPIO et spidev sur PC
- `RPi_mock.py` : Implémentation des simulateurs
- `install_deps.py` : Script d'installation des dépendances

## Comment utiliser les scripts

### 1. Sur un Raspberry Pi

#### Option 1 : Utiliser le test autonome
```bash
cd ~/2510_RegulationChauffage/soft/src
sudo python3 test_lm70_standalone.py
```

#### Option 2 : Utiliser le test compatible
```bash
cd ~/2510_RegulationChauffage/soft/src
sudo python3 app/test_lm70_compatible.py
```

#### Option 3 : Utiliser la fonction dans main.py
```python
# Dans une console Python après avoir importé main.py
from app.main import test_lm70_spi
test_lm70_spi()
```

### 2. Sur un PC (mode simulation)

```bash
cd 2510_RegulationChauffage/soft/src
python app/test_lm70_compatible.py
```
Le script détectera automatiquement qu'il n'est pas sur un Raspberry Pi et utilisera les simulateurs.

## Connexions du LM70

Pour que le test fonctionne sur un Raspberry Pi, connectez le LM70 comme suit :
- LM70 MISO → GPIO 19 (SPI1_MISO)
- LM70 SCLK → GPIO 21 (SPI1_SCLK)
- LM70 CS → GPIO 5 (ou autre GPIO libre)
- LM70 VDD → 3.3V ou 5V (selon le modèle)
- LM70 GND → GND

## Dépendances

Pour installer les dépendances nécessaires :
```bash
cd 2510_RegulationChauffage/soft/src
python3 install_deps.py
```

## Dépannage

### Erreurs d'importation
Si vous rencontrez des erreurs d'importation dans PyCharm :
1. Assurez-vous que le répertoire `src` est marqué comme racine du code source:
   - Clic droit sur le répertoire `src`
   - "Mark Directory as" > "Sources Root"

2. Exécutez le script `test_imports.py` pour vérifier les importations :
```bash
cd 2510_RegulationChauffage/soft/src
python3 test_imports.py
```

### Problèmes SPI
Sur un Raspberry Pi :
1. Vérifiez que SPI est activé dans `raspi-config`
2. Vérifiez les connexions physiques avec un multimètre
3. Essayez d'utiliser un autre GPIO pour CS

### Problèmes GPIO
1. Vérifiez les permissions (exécutez avec `sudo` si nécessaire)
2. Vérifiez que RPi.GPIO est installé : `pip3 show RPi.GPIO`
