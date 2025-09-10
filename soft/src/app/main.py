#!/usr/bin/env python3
# Module principal du systeme de regulation chauffage (commentaires ASCII sans accent)
# Fonctions :
# - Acquisition temperature sur 4 canaux
# - Communication avec API externe
# - Controle regulation
# - Gestion reseau resistif
# - Surveillance du systeme
import threading
import time
import logging
import sys
import os
from typing import Dict
from config_module.cm5_config import build_hw, ADC_CHANNELS
from drivers_module.mux_adg731 import Adg731
from drivers_module.adc_ads124s08 import ADS124S08
from metrology_module.convert import r_to_temp
from metrology_module.sensor_profiles import SENSOR_DB, ADC_PARAMS_DB
from hw_module.gpio_cm5 import GPIO, Relay, LED
from io_module.dry_contacts import DryContacts
from api_module.external import API
from control_module.regulation import CTRL

class TemperatureAcquisition:
    def __init__(self):
        self.hw = build_hw()
        self.dry_contacts = DryContacts(GPIO)
        self.mux = Adg731(
            spi=self.hw["spi_mux"],
            cs_pins=self.hw["pins"]["mux_cs_list"],
            gpio=GPIO
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
        self.logger = logging.getLogger(__name__)

    # Classe ChannelConfig
class ChannelConfig:
    def __init__(self, channel: str, profile: str, mux_card: int = 0, mux_channel: int = 0):
        self.channel = channel
        self.profile = profile
        self.mux_card = mux_card
        self.mux_channel = mux_channel

    def measure_channel(self, adc_channels, sensor_db, adc_params_db, mux, adc) -> dict:
        """Mesure pour un canal specifique"""
        # Recupere la config des pins pour le canal
        channel_pins = next((ch for ch in adc_channels if ch["name"] == self.channel), None)
        if not channel_pins:
            self.logger.error(f"Canal {self.channel} non defini dans ADC_CHANNELS")
            return None

    # Verifie le profil du capteur
        profile = sensor_db.get(self.profile)
        adc_params = adc_params_db.get(self.profile)
        if not profile or not adc_params:
            self.logger.error(f"Profil {self.profile} non reconnu")
            return None

        try:
            # Configuration du multiplexeur
            mux.select_card(self.mux_card)
            mux.set_channel(self.mux_channel)

            # Configuration et lecture ADC
            adc._configure_adc(adc_params, channel_pins)
            raw = adc._read_adc_with_timeout()
            ratio = adc.code_to_ratio(raw)
            r_sonde = ratio * profile.rref_nom
            temp_c = r_to_temp(profile, r_sonde)

            return {
                "temperature": temp_c,
                "resistance": r_sonde,
                "raw_code": raw,
                "channel": self.channel,
                "profile": self.profile
            }

        except Exception as e:
            self.logger.error(f"Erreur mesure canal {self.channel}: {str(e)}")
            return None

    def acquisition_loop(self):
        """
        Boucle principale acquisition et regulation.
        Sequence :
        1. Lecture contact sec (priorite)
        2. Pour chaque canal actif :
           - Mesure temperature
           - Recupere parametres API
           - Calcul regulation
           - Applique reseau resistif
        3. Indication visuelle et log
        4. Gestion erreurs
        La boucle tourne en continu :
        - Periode principale : 5 minutes
        - Delai inter-cycle : 200ms
        - Timeout API : 2s
        """
        while self.running:
            try:
            # 1. Lecture unique des deux canaux de contacts secs au debut du cycle (toutes les 5 min)
                states = self.dry_contacts.read_all_channels()
                contact_states = [states[1], states[2]]  # Etats [Canal 1, Canal 2]
                
                self.logger.info(f"Etats contacts secs : Canal 1={'FERME' if contact_states[0] else 'OUVERT'}, Canal 2={'FERME' if contact_states[1] else 'OUVERT'}")

                # 2. Traitement des canaux actifs
                # Ajout de la liste CHANNEL_CONFIGS manquante
                CHANNEL_CONFIGS = [
                    ChannelConfig("CH1", "AF60"),
                    ChannelConfig("CH2", "PT1000"),
                    ChannelConfig("CH3", "NTC_10k_3977"),
                    ChannelConfig("CH4", "KTY81_210"),
                ]
                for ch_cfg in CHANNEL_CONFIGS:
                    result = self.measure_channel(ch_cfg)
                    if result:
                        # Recupere parametres API
                        # N: facteur melange
                        # kM: coefficient meteo
                        # Tprevu: temperature prevue
                        api_params = API.get_params()
                        
                        # Calcul regulation
                        # Determine resistance a simuler
                        ctrl_result = CTRL.regulate(
                            result["temperature"],  # Temperature mesuree
                            api_params["N"],       # Facteur melange
                            api_params["kM"],      # Coefficient meteo
                            api_params["Tprevu"]   # Temperature prevue
                        )

                        # 3. Indication visuelle
                        LED.short_flash()  # Acquittement mesure OK

                        # 4. Log detaille
                        self.logger.info(
                            f"Canal {result['channel']}: "
                            f"T={result['temperature']:.2f}C, "
                            f"R={result['resistance']:.2f} Ohm, "
                            f"Contacts: C1={'FERME' if contact_states[0] else 'OUVERT'}, C2={'FERME' if contact_states[1] else 'OUVERT'}, "
                            f"Consigne={api_params['Tprevu']}C"
                        )

            except Exception as e:
                # Gestion erreurs
                self.logger.error(f"Erreur boucle acquisition: {str(e)}")
                Relay.off()         # Desactive relais bypass
                LED.blink_2hz()     # Indique erreur (2 Hz)
                time.sleep(5)       # Pause avant retry

            # Delai inter-cycle CPU
            time.sleep(0.2)

    def start(self):
        """
        Demarre le systeme d'acquisition.
        Actions :
        1. Active le flag running
        2. Demarre thread tick periodique
        3. Lance la boucle acquisition
        """
        if not self.running:
            self.running = True
            # Thread tick periodique 5min
            self.tick_thread = threading.Thread(
                target=self._tick_loop,
                daemon=True  # Arr�t auto avec programme principal
            )
            self.tick_thread.start()
            self.acquisition_loop()  # Boucle principale

    def stop(self):
        """
        Arrete proprement le systeme.
        Actions :
        1. Desactive flag running
        2. Attend fin thread tick
        3. Arrete ADC
        4. Nettoie GPIO
        """
        self.running = False
        # Attente propre du thread tick
        if self.tick_thread:
            self.tick_thread.join(timeout=1.0)
        # Arret materiel
        self.adc.stop()
        self.adc.powerdown()  # Economie energie
        GPIO.cleanup()  # Nettoyage GPIO

    def _tick_loop(self):
        """
        Boucle tick periodique (5 minutes).
        Cette boucle :
        - Maintient la synchronisation temporelle
        - Declenche les actions periodiques
        - Log les evenements de timing
        """
        while self.running:
            self.logger.info("Tick 5 minutes")
            time.sleep(300)  # 5 minutes

    def _configure_adc(self, adc_params: Dict, channel_pins: Dict):
        """
        Configure ADC pour une mesure.
        Configuration :
        - Reset materiel
        - Parametres de base (gain, vitesse)
        - Mode reference
        - Sources de courant
        Args :
            adc_params : Parametres ADC du profil
            channel_pins : Configuration des broches
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
        self.adc.set_ref_bank(adc_params["ref_bank"])
        # Reference configuration
        self.adc.set_ref_bank(adc_params["ref_bank"])
        
    # Configuration source courant
        self.adc.route_idac(
            current_uA=adc_params["idac_uA"],     # Courant excitation
            idac1_route=channel_pins["idac_pin"], # Source 1
            idac2_route=None                      # Source 2 desactivee
        )
        self.adc.select_diff_channel(
            pos=channel_pins["adc_pos"],
            neg=channel_pins["adc_neg"]
        )

    def _read_adc_with_timeout(self) -> int:
        """Lit une valeur ADC avec gestion du timeout"""
        self.adc.start_single_shot()
        t0 = time.time()
        while GPIO.input(self.hw["pins"]["ADC_DRDY"]) == 1:
            if time.time() - t0 > 2.0:
                raise TimeoutError("ADC DRDY timeout")
            time.sleep(0.001)
        return self.adc.read_once_blocking()

        
def main():
    """Point d'entree principal"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('temperature.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    try:
        acquisition = TemperatureAcquisition()
        acquisition.start()
    except KeyboardInterrupt:
        logger.info("Arret demande par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {str(e)}")
    finally:
        if 'acquisition' in locals():
            acquisition.stop()

if __name__ == "__main__":
    main()
