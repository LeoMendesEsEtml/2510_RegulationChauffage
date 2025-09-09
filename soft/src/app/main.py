#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module principal du syst�me de r�gulation de chauffage.

Fonctionnalit�s:
- Acquisition des temp�ratures sur 4 canaux
- Communication avec l'API externe
- Gestion de la r�gulation
- Contr�le du r�seau r�sistif
- Surveillance du syst�me

Le syst�me lit des sondes r�elles, calcule une temp�rature simul�e
� partir des pr�visions m�t�o, et applique une r�sistance �quivalente
via un r�seau command�.

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
    LED       # LED d'�tat
)
from io.dry_contacts import DryContacts      # Gestion des contacts secs 24V
from api.external import API                 # Communication API
from control.regulation import CTRL          # Algorithme r�gulation

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
            mux_card: Index carte MUX (d�faut: 0)
            mux_channel: Canal MUX (d�faut: 0)
        """
        self.channel = channel
        self.profile = profile
        self.mux_card = mux_card
        self.mux_channel = mux_channel

# Configuration des canaux ADC avec leur type de capteur
CHANNEL_CONFIGS = [
    ChannelConfig("CH1", "AF60"),        # Sonde ext�rieure AF60
    ChannelConfig("CH2", "PT1000"),      # Sonde PT1000
    ChannelConfig("CH3", "NTC_10k_3977"),# Thermistance NTC 10k
    ChannelConfig("CH4", "KTY81_210"),   # Sonde KTY81-210
]

class TemperatureAcquisition:
    """
    Gestion de l'acquisition des temp�ratures.
    
    Cette classe:
    - Configure l'ADC et les multiplexeurs
    - Effectue les mesures sur chaque canal
    - G�re la conversion en temp�rature
    - Surveille les erreurs et exceptions
    """
    def __init__(self):
        """
        Initialise le syst�me d'acquisition.
        
        Configure:
        - Le mat�riel (GPIO, SPI)
        - Les multiplexeurs ADG731
        - L'ADC ADS124S08
        - Les profils des capteurs
        """
        # Construction de la configuration mat�rielle
        self.hw = build_hw()
        
        # Initialisation des contacts secs
        self.dry_contacts = DryContacts(GPIO)
        
        # Initialisation du multiplexeur
        self.mux = Adg731(
            spi=self.hw["spi_mux"],           # Bus SPI d�di�
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
        """Effectue la mesure pour un canal sp�cifique"""
        # R�cup�re la configuration des pins pour le canal
        channel_pins = next((ch for ch in ADC_CHANNELS if ch["name"] == ch_cfg.channel), None)
        if not channel_pins:
            logger.error(f"Channel {ch_cfg.channel} non d�fini dans ADC_CHANNELS")
            return None

        # V�rifie le profil du capteur
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
        Boucle principale d'acquisition et r�gulation.
        
        S�quence:
        1. Lecture du contact sec (prioritaire)
        2. Pour chaque canal actif:
           - Mesure de temp�rature
           - R�cup�ration param�tres API
           - Calcul r�gulation
           - Application r�seau r�sistif
        3. Indication visuelle et logging
        4. Gestion des erreurs
        
        La boucle s'ex�cute en continu avec:
        - P�riode principale: 5 minutes
        - D�lai inter-cycles: 200ms
        - Timeout API: 2s
        """
        while self.running:
            try:
                # 1. Lecture unique des deux canaux de contacts secs au d�but du cycle (toutes les 5 min)
                states = self.dry_contacts.read_all_channels()
                contact_states = [states[1], states[2]]  # �tats [Canal 1, Canal 2]
                
                logger.info(f"�tats des contacts secs : Canal 1={'FERM�' if contact_states[0] else 'OUVERT'}, Canal 2={'FERM�' if contact_states[1] else 'OUVERT'}")

                # 2. Traitement des canaux actifs
                for ch_cfg in CHANNEL_CONFIGS:
                    result = self.measure_channel(ch_cfg)
                    if result:
                        # Obtention des param�tres de l'API
                        # N: facteur de m�lange
                        # kM: coefficient m�t�o
                        # Tprevu: temp�rature pr�vue
                        api_params = API.get_params()
                        
                        # Calcul de la r�gulation
                        # D�termine la r�sistance � simuler
                        ctrl_result = CTRL.regulate(
                            result["temperature"],  # T mesur�e
                            api_params["N"],       # Facteur m�lange
                            api_params["kM"],      # Coeff m�t�o
                            api_params["Tprevu"]   # T pr�vue
                        )

                        # 3. Indication visuelle
                        LED.short_flash()  # Acquittement mesure OK

                        # 4. Journalisation d�taill�e
                        logger.info(
                            f"Canal {result['channel']}: "
                            f"T={result['temperature']:.2f}�C, "
                            f"R={result['resistance']:.2f}?, "
                            f"Contacts: C1={'FERM�' if contact_states[0] else 'OUVERT'}, C2={'FERM�' if contact_states[1] else 'OUVERT'}, "
                            f"Consigne={api_params['Tprevu']}�C"
                        )

            except Exception as e:
                # Gestion des erreurs
                logger.error(f"Erreur boucle acquisition: {str(e)}")
                Relay.off()         # D�sactive relais bypass
                LED.blink_2hz()     # Indique erreur (2 Hz)
                time.sleep(5)       # Pause avant retry

            # D�lai inter-cycles pour CPU
            time.sleep(0.2)

    def start(self):
        """
        D�marre le syst�me d'acquisition.
        
        Actions:
        1. Active le flag running
        2. D�marre thread de tick p�riodique
        3. Lance la boucle d'acquisition
        """
        if not self.running:
            self.running = True
            # Thread pour tick p�riodique 5min
            self.tick_thread = threading.Thread(
                target=self._tick_loop,
                daemon=True  # Arr�t auto avec programme principal
            )
            self.tick_thread.start()
            self.acquisition_loop()  # Boucle principale

    def stop(self):
        """
        Arr�te proprement le syst�me.
        
        Actions:
        1. D�sactive flag running
        2. Attend fin thread tick
        3. Arr�te l'ADC
        4. Nettoie GPIO
        """
        self.running = False
        # Attente propre du thread tick
        if self.tick_thread:
            self.tick_thread.join(timeout=1.0)
        # Arr�t mat�riel
        self.adc.stop()
        self.adc.powerdown()  # �conomie d'�nergie
        GPIO.cleanup()  # Nettoyage GPIO

    def _tick_loop(self):
        """
        Boucle de tick p�riodique (5 minutes).
        
        Cette boucle:
        - Maintient la synchronisation temporelle
        - D�clenche les actions p�riodiques
        - Log les �v�nements de timing
        """
        while self.running:
            logger.info("Tick 5 minutes")
            time.sleep(300)  # 5 minutes

    def _configure_adc(self, adc_params: Dict, channel_pins: Dict):
        """
        Configure l'ADC pour une mesure.
        
        Configuration:
        - Reset mat�riel
        - Param�tres de base (gain, vitesse)
        - Mode de r�f�rence
        - Sources de courant
        
        Args:
            adc_params: Param�tres ADC du profil
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
        # Configuration r�f�rence
        self.adc.set_ref_bank(adc_params["ref_bank"])
        
        # Configuration source de courant
        self.adc.route_idac(
            current_uA=adc_params["idac_uA"],     # Courant excitation
            idac1_route=channel_pins["idac_pin"], # Source 1
            idac2_route=None                      # Source 2 d�sactiv�e
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

def test_lm70_spi():
    """
    Fonction de test temporaire pour valider la communication SPI avec un capteur LM70.
    
    Cette fonction:
    1. Utilise l'infrastructure SPI existante du projet avec les GPIO mis à jour
    2. Configure le GPIO pour le CS du LM70
    3. Lit la température du capteur LM70
    4. Affiche la température dans les logs
    
    NOTE: Cette fonction est temporaire et devrait être supprimée après validation.
    """
    import time
    from config.cm5_config import build_hw, _open_spi
    from hw.gpio_cm5 import GPIO
    
    try:
        logger.info("Démarrage du test de communication SPI avec LM70...")
        
        # Configuration du matériel
        hw = build_hw()
        
        # Configuration pour le LM70 (utilise SPI1 qui a MISO)
        lm70_config = {
            "bus": 1,            # Utilise SPI1 (SCLK=GPIO 21, MISO=GPIO 19)
            "device": 1,         # Device différent pour ne pas interférer avec l'ADC
            "max_hz": 1000000,   # 1MHz
            "mode": 0,           # Mode 0 (CPOL=0, CPHA=0)
            "bits": 8
        }
        
        # Configuration du CS pour le LM70 (utilise un pin disponible)
        # Choisir un GPIO qui n'est pas déjà utilisé dans le projet
        LM70_CS_PIN = 5  # GPIO 5 - N'est pas utilisé ailleurs dans le projet
        
        # Setup du GPIO pour le CS du LM70
        GPIO.setup(LM70_CS_PIN, GPIO.OUT, initial=GPIO.HIGH)
        
        # Ouvre le SPI pour le LM70
        spi_lm70 = _open_spi(lm70_config)
        
        # Fonction pour lire la température du LM70
        def read_lm70_temp():
            try:
                # Active le CS (actif à l'état bas)
                GPIO.output(LM70_CS_PIN, GPIO.LOW)
                
                # Le LM70 utilise un format 11-bit signé en complément à 2
                # 1. Lecture de 2 octets
                resp = spi_lm70.xfer2([0x00, 0x00])
                
                # 2. Combiner les octets et extraire les 11 bits significatifs (shift de 5 bits)
                raw_value = ((resp[0] << 8) | resp[1]) >> 5
                
                # 3. Gestion du signe (complément à 2)
                if raw_value & 0x400:  # Bit de signe à 1
                    # Valeur négative
                    temp_c = -((~raw_value & 0x7FF) + 1) * 0.125
                else:
                    # Valeur positive
                    temp_c = raw_value * 0.125
                
                return temp_c
                
            finally:
                # Désactive le CS, quelle que soit l'issue
                GPIO.output(LM70_CS_PIN, GPIO.HIGH)
        
        # Lecture répétée pour vérifier la stabilité
        temps = []
        for i in range(10):
            temp = read_lm70_temp()
            temps.append(temp)
            logger.info(f"Lecture LM70 #{i+1}: {temp:.2f}°C")
            time.sleep(1)
        
        # Calcul statistique simple
        avg_temp = sum(temps) / len(temps)
        min_temp = min(temps)
        max_temp = max(temps)
        
        logger.info(f"Test LM70 terminé avec succès")
        logger.info(f"Statistiques: Moyenne={avg_temp:.2f}°C, Min={min_temp:.2f}°C, Max={max_temp:.2f}°C")
        
        # Nettoyage
        spi_lm70.close()
        
    except Exception as e:
        logger.error(f"Erreur test LM70: {str(e)}")
        if 'spi_lm70' in locals():
            spi_lm70.close()
        
def main():
    """Point d'entr�e principal"""
    try:
        # Pour utiliser l'application normale:
        #acquisition = TemperatureAcquisition()
        #acquisition.start()
        
        # Pour tester le LM70, commentez les lignes ci-dessus et décommentez celle ci-dessous:
        test_lm70_spi()
    except KeyboardInterrupt:
        logger.info("Arr�t demand� par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {str(e)}")
    finally:
        if 'acquisition' in locals():
            acquisition.stop()

if __name__ == "__main__":
    main()
