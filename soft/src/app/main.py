#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module principal du système de régulation de chauffage.

Fonctionnalités:
- Acquisition des températures sur 4 canaux
- Communication avec l'API externe
- Gestion de la régulation
- Contrôle du réseau résistif
- Surveillance du système

Le système lit des sondes réelles, calcule une température simulée
à partir des prévisions météo, et applique une résistance équivalente
via un réseau commandé.

Auteur: LeoMendesEsEtml
Date: 2025
Licence: MIT
"""

import threading
import time
import logging
from typing import Dict, Optional

# Imports des modules internes
from config.cm5_config import build_hw, ADC_CHANNELS
from drivers.mux_adg731 import Adg731        # Pilote multiplexeur
from drivers.adc_ads124s08 import ADS124S08  # Pilote ADC
from Metrology.convert import r_to_temp      # Conversion R -> T
from Metrology.sensor_profiles import (       # Profils des capteurs
    SENSOR_DB,
    SensorProfile, 
    ADC_PARAMS_DB
)
from hw.gpio_cm5 import (                    # Gestion GPIO
    GPIO,
    Relay,    # Relais de bypass
    LED       # LED d'état
)
from io.dry_contacts import DryContacts      # Gestion des contacts secs 24V
from api.external import API                 # Communication API
from control.regulation import CTRL          # Algorithme régulation

# Configuration du logging avec rotation des fichiers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('temperature.log'),  # Log dans fichier
        logging.StreamHandler()                  # Log dans console
    ]
)
logger = logging.getLogger(__name__)

class ChannelConfig:
    """
    Configuration d'un canal d'acquisition.
    
    Attributs:
        channel: Identifiant du canal (CH1..CH4)
        profile: Type de capteur (AF60, PT1000, etc)
        mux_card: Index de la carte multiplexeur (0..3)
        mux_channel: Canal sur la carte multiplexeur (0..31)
    """
    def __init__(self, channel: str, profile: str, mux_card: int = 0, mux_channel: int = 0):
        """
        Initialise la configuration du canal.
        
        Args:
            channel: Identifiant du canal
            profile: Type de capteur
            mux_card: Index carte MUX (défaut: 0)
            mux_channel: Canal MUX (défaut: 0)
        """
        self.channel = channel
        self.profile = profile
        self.mux_card = mux_card
        self.mux_channel = mux_channel

# Configuration des canaux ADC avec leur type de capteur
CHANNEL_CONFIGS = [
    ChannelConfig("CH1", "AF60"),        # Sonde extérieure AF60
    ChannelConfig("CH2", "PT1000"),      # Sonde PT1000
    ChannelConfig("CH3", "NTC_10k_3977"),# Thermistance NTC 10k
    ChannelConfig("CH4", "KTY81_210"),   # Sonde KTY81-210
]

class TemperatureAcquisition:
    """
    Gestion de l'acquisition des températures.
    
    Cette classe:
    - Configure l'ADC et les multiplexeurs
    - Effectue les mesures sur chaque canal
    - Gère la conversion en température
    - Surveille les erreurs et exceptions
    """
    def __init__(self):
        """
        Initialise le système d'acquisition.
        
        Configure:
        - Le matériel (GPIO, SPI)
        - Les multiplexeurs ADG731
        - L'ADC ADS124S08
        - Les profils des capteurs
        """
        # Construction de la configuration matérielle
        self.hw = build_hw()
        
        # Initialisation des contacts secs
        self.dry_contacts = DryContacts(GPIO)
        
        # Initialisation du multiplexeur
        self.mux = Adg731(
            spi=self.hw["spi_mux"],           # Bus SPI dédié
            cs_pins=self.hw["pins"]["mux_cs_list"], # Liste des CS
            gpio=GPIO                          # Interface GPIO
        )
        self.adc = ADS124S08(
            spi=self.hw["spi_adc"],
            cs_pin=self.hw["pins"]["CS_ADC"],
            drdy_pin=self.hw["pins"]["ADC_DRDY"],
            start_pin=self.hw["pins"]["ADC_START_SYNC"],
            a0_pin=self.hw["pins"]["ADC_A0"],
            a1_pin=self.hw["pins"]["ADC_A1"],
            gpio=GPIO
        )
        self.running = False
        self.tick_thread = None

    def measure_channel(self, ch_cfg: ChannelConfig) -> Dict:
        """Effectue la mesure pour un canal spécifique"""
        # Récupère la configuration des pins pour le canal
        channel_pins = next((ch for ch in ADC_CHANNELS if ch["name"] == ch_cfg.channel), None)
        if not channel_pins:
            logger.error(f"Channel {ch_cfg.channel} non défini dans ADC_CHANNELS")
            return None

        # Vérifie le profil du capteur
        profile = SENSOR_DB.get(ch_cfg.profile)
        adc_params = ADC_PARAMS_DB.get(ch_cfg.profile)
        if not profile or not adc_params:
            logger.error(f"Profil {ch_cfg.profile} non reconnu")
            return None

        try:
            # Configuration du multiplexeur
            self.mux.select_card(ch_cfg.mux_card)
            self.mux.set_channel(ch_cfg.mux_channel)

            # Configuration et lecture ADC
            self._configure_adc(adc_params, channel_pins)
            raw = self._read_adc_with_timeout()
            ratio = self.adc.code_to_ratio(raw)
            r_sonde = ratio * profile.rref_nom
            temp_c = r_to_temp(profile, r_sonde)

            return {
                "temperature": temp_c,
                "resistance": r_sonde,
                "raw_code": raw,
                "channel": ch_cfg.channel,
                "profile": ch_cfg.profile
            }

        except Exception as e:
            logger.error(f"Erreur mesure canal {ch_cfg.channel}: {str(e)}")
            return None

    def acquisition_loop(self):
        """
        Boucle principale d'acquisition et régulation.
        
        Séquence:
        1. Lecture du contact sec (prioritaire)
        2. Pour chaque canal actif:
           - Mesure de température
           - Récupération paramètres API
           - Calcul régulation
           - Application réseau résistif
        3. Indication visuelle et logging
        4. Gestion des erreurs
        
        La boucle s'exécute en continu avec:
        - Période principale: 5 minutes
        - Délai inter-cycles: 200ms
        - Timeout API: 2s
        """
        while self.running:
            try:
                # 1. Lecture unique des deux canaux de contacts secs au début du cycle (toutes les 5 min)
                states = self.dry_contacts.read_all_channels()
                contact_states = [states[1], states[2]]  # États [Canal 1, Canal 2]
                
                logger.info(f"États des contacts secs : Canal 1={'FERMÉ' if contact_states[0] else 'OUVERT'}, Canal 2={'FERMÉ' if contact_states[1] else 'OUVERT'}")

                # 2. Traitement des canaux actifs
                for ch_cfg in CHANNEL_CONFIGS:
                    result = self.measure_channel(ch_cfg)
                    if result:
                        # Obtention des paramètres de l'API
                        # N: facteur de mélange
                        # kM: coefficient météo
                        # Tprevu: température prévue
                        api_params = API.get_params()
                        
                        # Calcul de la régulation
                        # Détermine la résistance à simuler
                        ctrl_result = CTRL.regulate(
                            result["temperature"],  # T mesurée
                            api_params["N"],       # Facteur mélange
                            api_params["kM"],      # Coeff météo
                            api_params["Tprevu"]   # T prévue
                        )

                        # 3. Indication visuelle
                        LED.short_flash()  # Acquittement mesure OK

                        # 4. Journalisation détaillée
                        logger.info(
                            f"Canal {result['channel']}: "
                            f"T={result['temperature']:.2f}°C, "
                            f"R={result['resistance']:.2f}?, "
                            f"Contacts: C1={'FERMÉ' if contact_states[0] else 'OUVERT'}, C2={'FERMÉ' if contact_states[1] else 'OUVERT'}, "
                            f"Consigne={api_params['Tprevu']}°C"
                        )

            except Exception as e:
                # Gestion des erreurs
                logger.error(f"Erreur boucle acquisition: {str(e)}")
                Relay.off()         # Désactive relais bypass
                LED.blink_2hz()     # Indique erreur (2 Hz)
                time.sleep(5)       # Pause avant retry

            # Délai inter-cycles pour CPU
            time.sleep(0.2)

    def start(self):
        """
        Démarre le système d'acquisition.
        
        Actions:
        1. Active le flag running
        2. Démarre thread de tick périodique
        3. Lance la boucle d'acquisition
        """
        if not self.running:
            self.running = True
            # Thread pour tick périodique 5min
            self.tick_thread = threading.Thread(
                target=self._tick_loop,
                daemon=True  # Arrêt auto avec programme principal
            )
            self.tick_thread.start()
            self.acquisition_loop()  # Boucle principale

    def stop(self):
        """
        Arrête proprement le système.
        
        Actions:
        1. Désactive flag running
        2. Attend fin thread tick
        3. Arrête l'ADC
        4. Nettoie GPIO
        """
        self.running = False
        # Attente propre du thread tick
        if self.tick_thread:
            self.tick_thread.join(timeout=1.0)
        # Arrêt matériel
        self.adc.stop()
        self.adc.powerdown()  # Économie d'énergie
        GPIO.cleanup()  # Nettoyage GPIO

    def _tick_loop(self):
        """
        Boucle de tick périodique (5 minutes).
        
        Cette boucle:
        - Maintient la synchronisation temporelle
        - Déclenche les actions périodiques
        - Log les événements de timing
        """
        while self.running:
            logger.info("Tick 5 minutes")
            time.sleep(300)  # 5 minutes

    def _configure_adc(self, adc_params: Dict, channel_pins: Dict):
        """
        Configure l'ADC pour une mesure.
        
        Configuration:
        - Reset matériel
        - Paramètres de base (gain, vitesse)
        - Mode de référence
        - Sources de courant
        
        Args:
            adc_params: Paramètres ADC du profil
            channel_pins: Configuration des broches
        """
        # Reset complet
        self.adc.reset()
        
        # Configuration de base
        self.adc.basic_setup(
            pga_gain=adc_params["gain"],           # Gain programmable
            data_rate_sps=adc_params["data_rate_sps"], # Vitesse
            ref_mode="ratiometric_REFP0_REFN0",    # Mode ratio
            chop=False                             # Pas de chopping
        )
        # Configuration référence
        self.adc.set_ref_bank(adc_params["ref_bank"])
        
        # Configuration source de courant
        self.adc.route_idac(
            current_uA=adc_params["idac_uA"],     # Courant excitation
            idac1_route=channel_pins["idac_pin"], # Source 1
            idac2_route=None                      # Source 2 désactivée
        )
        self.adc.select_diff_channel(
            pos=channel_pins["adc_pos"],
            neg=channel_pins["adc_neg"]
        )

    def _read_adc_with_timeout(self) -> int:
        """Lit une valeur de l'ADC avec gestion du timeout"""
        self.adc.start_single_shot()
        t0 = time.time()
        while GPIO.input(self.hw["pins"]["ADC_DRDY"]) == 1:
            if time.time() - t0 > 2.0:
                raise TimeoutError("ADC DRDY timeout")
            time.sleep(0.001)
        return self.adc.read_once_blocking()

def main():
    """Point d'entrée principal"""
    try:
        acquisition = TemperatureAcquisition()
        acquisition.start()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {str(e)}")
    finally:
        if 'acquisition' in locals():
            acquisition.stop()

if __name__ == "__main__":
    main()
