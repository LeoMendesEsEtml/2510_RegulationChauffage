# -*- coding: utf-8 -*-
"""
@file        adc_ads124s08.py
@brief       Driver pour l'ADC ADS124S08 avec communication SPI.
@details     Ce module fournit une interface complète pour la communication avec
             l'ADC ADS124S08 via SPI en mode 1.0. Supporte la mesure de résistance
             et température avec configuration automatique des registres.
             Séquence: Reset → Configuration → Mesure bloquante avec DRDY.
@author      Léo Mendes
@project     2510_RegulationsChauffage
@Mandant     Oblo_solution
@date        2025-09-18
@version     1.0.0
@copyright   Copyright (c) 2025
"""

from __future__ import annotations
# Bibliothèque pour la communication SPI
import spidev
# Module pour la gestion du temps et délais
import time
# Bibliothèque pour la gestion des GPIO
from periphery import GPIO
# Importation des constantes matérielles CM5
from pins_cm5 import SPI1_BUS, SPI1_DEV0, SPI_ADC_SPEED_HZ, GPIO_CHIP_PATH, ADC_DRDY
# Fonction de conversion résistance vers température
from app.temperature_conversion import resistance_to_temperature_dynamic
# Tables de conversion des différents capteurs
from app.sensor_profiles import SENSOR_TABLES


# ---------------------------------------------------------------------------
# Constantes des registres ADC ADS124S08
# ---------------------------------------------------------------------------

# Registre d'identification de l'ADC
REG_ID        = 0x00
# Registre de statut et flags
REG_STATUS    = 0x01
# Registre de configuration du multiplexeur d'entrée
REG_INPMUX    = 0x02
# Registre de configuration de l'amplificateur programmable
REG_PGA       = 0x03
# Registre de configuration du taux d'échantillonnage
REG_DATARATE  = 0x04
# Registre de configuration de la référence de tension
REG_REF       = 0x05
# Registre de configuration du multiplexeur IDAC
REG_IDACMUX   = 0x07
# Registre de configuration système générale
REG_SYS       = 0x09
# Registre de configuration de la magnitude IDAC
REG_IDACMAG   = 0x06


# ---------------------------------------------------------------------------
# Constantes des commandes ADC ADS124S08
# ---------------------------------------------------------------------------

# Commande de réinitialisation complète de l'ADC
CMD_RESET  = 0x06
# Commande de démarrage d'une conversion
CMD_START  = 0x08
# Commande d'arrêt de conversion
CMD_STOP   = 0x0A
# Commande de lecture des données de conversion
CMD_RDATA  = 0x12


# ---------------------------------------------------------------------------
# Constantes de calcul et mapping
# ---------------------------------------------------------------------------

# Valeur maximale pour un code 24 bits signé (pleine échelle)
FS = (1 << 23) - 1

# Mapping des canaux physiques vers les entrées analogiques de l'ADC
CHANNELS = {
    # Canal 1: entrée positive AIN1, négative AIN2
    1: {"ainp_idx": 1,  "ainn_idx": 2},
    # Canal 2: entrée positive AIN4, négative AIN5
    2: {"ainp_idx": 4,  "ainn_idx": 5},
    # Canal 3: entrée positive AIN7, négative AIN8
    3: {"ainp_idx": 7,  "ainn_idx": 8},
    # Canal 4: entrée positive AIN10, négative AIN11
    4: {"ainp_idx": 10, "ainn_idx": 11}
}


# ---------------------------------------------------------------------------
# Fonctions d'encodage des paramètres ADC
# ---------------------------------------------------------------------------

def encode_gain(pga_gain):
    """
    @brief       Encode le gain PGA en code binaire pour le registre.
    @details     Convertit une valeur de gain décimale en code binaire 3 bits
                 pour la configuration du registre PGA de l'ADS124S08.

    @param pga_gain  Valeur du gain PGA (1, 2, 4, 8, 16, 32, 64, 128).

    @return          Code binaire 3 bits correspondant au gain.

    @exception       ValueError si le gain fourni n'est pas supporté.
    @see             configure_channel
    """
    # Gain unitaire (0 dB)
    if pga_gain == 1:
        return 0
    # Gain x2 (6 dB)
    if pga_gain == 2:
        return 1
    # Gain x4 (12 dB)
    if pga_gain == 4:
        return 2
    # Gain x8 (18 dB)
    if pga_gain == 8:
        return 3
    # Gain x16 (24 dB)
    if pga_gain == 16:
        return 4
    # Gain x32 (30 dB)
    if pga_gain == 32:
        return 5
    # Gain x64 (36 dB)
    if pga_gain == 64:
        return 6
    # Gain x128 (42 dB)
    if pga_gain == 128:
        return 7
    # Erreur si gain non supporté
    raise ValueError("PGA gain invalide: " + str(pga_gain))


def encode_idac_uA(idac_uA):
    """
    @brief       Encode la magnitude IDAC en code binaire pour le registre.
    @details     Convertit une valeur de courant IDAC en microampères en code
                 binaire 4 bits pour la configuration du registre IDACMAG.

    @param idac_uA   Courant IDAC en microampères (10, 50, 100, 250, 500, 1000, 1500, 2000).

    @return          Code binaire 4 bits correspondant au courant.

    @exception       ValueError si le courant fourni n'est pas supporté.
    @see             configure_channel
    """
    # Courant IDAC de 10 µA
    if idac_uA == 10:
        return 1
    # Courant IDAC de 50 µA
    if idac_uA == 50:
        return 2
    # Courant IDAC de 100 µA
    if idac_uA == 100:
        return 3
    # Courant IDAC de 250 µA
    if idac_uA == 250:
        return 4
    # Courant IDAC de 500 µA
    if idac_uA == 500:
        return 5
    # Courant IDAC de 1000 µA (1 mA)
    if idac_uA == 1000:
        return 6
    # Courant IDAC de 1500 µA (1.5 mA)
    if idac_uA == 1500:
        return 7
    # Courant IDAC de 2000 µA (2 mA)
    if idac_uA == 2000:
        return 8
    # Erreur si courant non supporté
    raise ValueError("IDAC µA non supporté: " + str(idac_uA))


def sign_extend_24(b0, b1, b2):
    """
    @brief       Étend le signe d'un code ADC 24 bits vers 32 bits.
    @details     Convertit un code ADC 24 bits signé en entier Python 32 bits
                 en préservant le signe selon la représentation en complément à 2.

    @param b0    Octet de poids fort (MSB) du code 24 bits.
    @param b1    Octet du milieu du code 24 bits.
    @param b2    Octet de poids faible (LSB) du code 24 bits.

    @return      Valeur entière signée 32 bits correspondante.

    @note        Nécessaire car Python gère automatiquement les entiers de taille variable.
    @see         read_code24
    """
    # Reconstruction du mot 24 bits
    raw = (b0 << 16) | (b1 << 8) | b2
    # Test du bit de signe (bit 23)
    if (raw & 0x800000) != 0:
        # Extension du signe vers 32 bits
        value = raw | 0xFF000000
        # Conversion en entier signé Python
        value = value - (1 << 32)
        return value
    # Valeur positive, pas d'extension nécessaire
    return raw


# ---------------------------------------------------------------------------
# Classe principale du driver ADC
# ---------------------------------------------------------------------------

class Ads124s08:
    """
    @brief       Driver pour l'ADC ADS124S08 avec interface SPI.
    @details     Cette classe encapsule toutes les fonctionnalités nécessaires
                 pour communiquer avec l'ADC ADS124S08 via SPI en mode 1.0.
                 Supporte la configuration automatique, la mesure de résistance
                 et la conversion en température.

    @note        L'ADC doit être connecté via SPI1 et le signal DRDY sur GPIO.
    @see         configure_channel, measure_resistance, measure_temperature
    """

    def __init__(self):
        """
        @brief       Constructeur de la classe Ads124s08.
        @details     Initialise la communication SPI, configure le GPIO DRDY,
                     effectue un reset de l'ADC et vérifie la communication
                     en lisant le registre d'identification.

        @exception   Peut lever des exceptions SPI ou GPIO en cas d'échec.
        @post        L'ADC est prêt pour la configuration et les mesures.
        """
        # Initialisation de l'interface SPI avec les paramètres du CM5
        # Création de l'objet SPI
        self.spi = spidev.SpiDev()
        # Ouverture du bus SPI1, device 0
        self.spi.open(SPI1_BUS, SPI1_DEV0)
        # Configuration en mode SPI 1.0 (CPOL=0, CPHA=1)
        self.spi.mode = 1
        # Configuration de la vitesse SPI selon CM5
        self.spi.max_speed_hz = SPI_ADC_SPEED_HZ
        # Configuration de la taille des mots SPI à 8 bits
        self.spi.bits_per_word = 8

        # Initialisation du GPIO pour le signal DRDY (Data Ready)
        # Configuration du GPIO DRDY en entrée
        self.gpio_drdy = GPIO(GPIO_CHIP_PATH, ADC_DRDY, "in")

        # Séquence de réinitialisation de l'ADC
        # Envoi de la commande RESET via SPI
        self.spi.xfer2([CMD_RESET])
        # Délai d'attente post-reset (2 ms minimum)
        time.sleep(0.002)

        # Purge des flags de statut après reset
        # Effacement des flags du registre STATUS
        self._wreg(REG_STATUS, [0x00])

        # Vérification de la communication avec l'ADC via lecture du registre ID
        # Lecture du registre d'identification
        adc_id = self.read_id()
        # Test de validité de la réponse
        if adc_id is None:
            # Erreur de communication
            print("[ADC] Erreur: aucune réponse sur le registre ID (0x00)")
        else:
            # Affichage de l'ID pour vérification
            print("[ADC] ID (0x00) = 0x" + format(adc_id, "02X"))

    def read_id(self):
        """
        @brief       Lit le registre d'identification de l'ADC.
        @details     Effectue une lecture du registre ID (0x00) pour vérifier
                     la communication SPI et identifier le type d'ADC connecté.

        @return      Valeur du registre ID (0x00-0xFF) ou None en cas d'erreur.

        @note        Utilisé principalement pour la vérification de communication.
        @see         __init__
        """
        # Commande RREG pour registre 0x00, 1 byte
        rx = self.spi.xfer2([0x20, 0x00, 0x00])
        # Vérification de la longueur de réponse
        if len(rx) >= 3:
            # Retour de la valeur du registre ID
            return rx[2]
        # Erreur de communication SPI
        return None

    def close(self):
        """
        @brief       Ferme les interfaces SPI et GPIO proprement.
        @details     Libère les ressources système utilisées par le driver.
                     Méthode à appeler avant la destruction de l'objet.

        @return      Rien.

        @note        Ignore les erreurs de fermeture pour éviter les exceptions.
        @see         __init__
        """
        try:
            # Fermeture de l'interface SPI
            self.spi.close()
        # Ignore les erreurs de fermeture SPI
        except Exception:
            pass
        try:
            # Fermeture de l'interface GPIO DRDY
            self.gpio_drdy.close()
        # Ignore les erreurs de fermeture GPIO
        except Exception:
            pass

    def _rreg(self, addr, nbytes):
        """
        @brief       Lit un ou plusieurs registres de l'ADC via SPI.
        @details     Utilise la commande RREG de l'ADS124S08 pour lire
                     des registres consécutifs starting à l'adresse donnée.

        @param addr     Adresse du premier registre à lire (0x00-0x1F).
        @param nbytes   Nombre d'octets à lire.

        @return         Liste des valeurs lues depuis les registres.

        @note           Méthode privée pour les opérations internes du driver.
        @see            _wreg
        """
        # Construction de la commande RREG
        cmd = 0x20 | (addr & 0x1F)
        # Calcul du compteur (nbytes - 1)
        count = nbytes - 1
        # Initialisation du buffer de transmission
        tx = [cmd, count]
        # Index de boucle pour les octets dummy
        index = 0
        # Ajout des octets dummy pour la lecture
        while index < nbytes:
            # Octet dummy pour chaque byte à lire
            tx.append(0x00)
            # Incrémentation de l'index
            index = index + 1
        # Transmission SPI bidirectionnelle
        rx = self.spi.xfer2(tx)
        # Extraction des données (après cmd et count)
        data = rx[2:]
        # Retour des données lues
        return data

    def _wreg(self, addr, data_bytes):
        """
        @brief       Écrit dans un ou plusieurs registres de l'ADC via SPI.
        @details     Utilise la commande WREG de l'ADS124S08 pour écrire
                     des données dans des registres consécutifs.

        @param addr        Adresse du premier registre à écrire (0x00-0x1F).
        @param data_bytes  Liste des octets à écrire dans les registres.

        @return            Rien.

        @note              Méthode privée pour les opérations internes du driver.
        @see               _rreg
        """
        # Construction de la commande WREG
        cmd = 0x40 | (addr & 0x1F)
        # Calcul du compteur (nbytes - 1)
        count = len(data_bytes) - 1
        # Initialisation du buffer de transmission
        tx = [cmd, count]
        # Ajout des données à transmettre
        tx = tx + list(data_bytes)
        # Transmission SPI (pas de données retour)
        self.spi.xfer2(tx)

    def _sclk_nudge(self):
        """
        @brief       Envoie un coup de pouce sur SCLK pour synchroniser DRDY.
        @details     Effectue une lecture factice du registre STATUS pour générer
                     des transitions sur SCLK et forcer DRDY à l'état HIGH.

        @return      Rien.

        @note        Utilisé quand DRDY reste bloqué à LOW de manière inattendue.
        @see         _ensure_drdy_high
        """
        # Lecture factice pour générer des transitions SCLK
        _ = self._rreg(REG_STATUS, 1)
        # Délai court pour la stabilisation
        time.sleep(0.0001)

    def _ensure_drdy_high(self, timeout_ms):
        """
        @brief       Assure que le signal DRDY est à l'état HIGH.
        @details     Attend que DRDY passe à HIGH avec possibilité de coup de pouce
                     sur SCLK si nécessaire. Timeout configurable.

        @param timeout_ms  Timeout en millisecondes pour l'attente.

        @return            True si DRDY est HIGH, False en cas de timeout.

        @note              Méthode critique pour la synchronisation des conversions.
        @see               wait_drdy_falling_edge
        """
        # Timestamp de début d'attente
        t0 = time.time()
        # Flag pour éviter les multiples coups de pouce
        kicked = False
        # Boucle d'attente infinie avec timeout
        while True:
            # Lecture de l'état actuel de DRDY
            val = self.gpio_drdy.read()
            # Test si DRDY est passé à HIGH
            if val is True:
                # Succès: DRDY est HIGH
                return True
            # Premier passage avec DRDY LOW
            if kicked is False:
                # Coup de pouce sur SCLK
                self._sclk_nudge()
                # Marquer le coup de pouce comme effectué
                kicked = True
            # Test du timeout en secondes
            if time.time() - t0 > float(timeout_ms) / 1000.0:
                # Échec: timeout atteint
                return False
            # Délai court entre les lectures
            time.sleep(0.001)

    def wait_drdy_falling_edge(self, timeout_s):
        """
        @brief       Attend un front descendant sur DRDY (HIGH -> LOW) avec timeout.
        @details     Surveille le signal DRDY pour détecter une transition de HIGH
                     vers LOW, indiquant qu'une nouvelle conversion est disponible.

        @param timeout_s   Timeout en secondes pour l'attente du front.

        @return            True si front descendant détecté, False en cas de timeout.

        @note              Méthode cruciale pour la synchronisation des mesures.
        @see               measure_resistance
        """
        # Timestamp de début d'attente
        t0 = time.time()
        # État initial de DRDY
        prev = self.gpio_drdy.read()
        # Boucle d'attente infinie avec timeout
        while True:
            # Lecture de l'état actuel de DRDY
            val = self.gpio_drdy.read()
            # Détection du front descendant
            if prev is True and val is False:
                # Message de confirmation
                print("[ADC] Front descendant DRDY détecté")
                # Succès: front descendant détecté
                return True
            # Mémorisation de l'état précédent
            prev = val
            # Test du timeout
            if time.time() - t0 > float(timeout_s):
                # Message d'erreur timeout
                print("[ADC] Timeout DRDY front descendant !")
                # Échec: timeout atteint
                return False
            # Délai court entre les lectures
            time.sleep(0.001)

    def set_single_shot_lowlatency(self, dr_nibble):
        """
        @brief       Configure le mode single-shot low-latency de l'ADC.
        @details     Configure le registre DATARATE pour utiliser le mode
                     single-shot avec filtre low-latency et data rate spécifié.

        @param dr_nibble   Code de data rate (4 bits, 0x00-0x0F).

        @return            Rien.

        @note              Mode optimisé pour des mesures rapides et ponctuelles.
        @see               configure_channel
        """
        # Initialisation de la valeur du registre
        value = 0
        # MODE=1 pour single-shot
        value = value | (1 << 5)
        # FILTER=1 pour low-latency
        value = value | (1 << 4)
        # DR=data rate (4 bits bas)
        value = value | (dr_nibble & 0x0F)
        # Écriture dans le registre DATARATE
        self._wreg(REG_DATARATE, [value])

    def configure_channel(self, channel_index, pga_gain, idac_uA):
        """
        @brief       Configure un canal ADC avec ses paramètres de mesure.
        @details     Configure complètement un canal ADC avec le gain PGA,
                     le courant IDAC et le routage des entrées analogiques.
                     Effectue une configuration séquentielle de tous les registres.

        @param channel_index   Index du canal physique (1-4).
        @param pga_gain        Gain de l'amplificateur programmable (1-128).
        @param idac_uA         Courant IDAC en microampères (10-2000).

        @return                Rien.

        @exception             ValueError si le canal ou les paramètres sont invalides.
        @see                   encode_gain, encode_idac_uA
        """
        # Validation du canal demandé
        # Test de validité du canal
        if channel_index not in CHANNELS:
            # Exception si canal invalide
            raise ValueError("Canal ADC inconnu: " + str(channel_index))
        # Récupération des paramètres du canal
        ch = CHANNELS[channel_index]
        # Index de l'entrée positive
        ainp = ch["ainp_idx"]
        # Index de l'entrée négative
        ainn = ch["ainn_idx"]
        print("[ADC] Configuration canal " + str(channel_index) + " gain=" + str(pga_gain) + " IDAC=" + str(idac_uA) + "uA")

        # Configuration du multiplexeur d'entrée (INPMUX)
        # Construction de la valeur INPMUX
        inpmux_val = ((ainp & 0x0F) << 4) | (ainn & 0x0F)
        # Affichage pour debug
        print("[ADC] INPMUX=0x" + format(inpmux_val, "02X"))
        # Écriture dans le registre INPMUX
        self._wreg(REG_INPMUX, [inpmux_val])

        # Configuration de l'amplificateur programmable (PGA)
        # Encodage du gain en code binaire
        gain_code = encode_gain(pga_gain)
        # Initialisation de la valeur PGA
        pga_val = 0
        # PGA_EN = 1 (activation du PGA)
        pga_val = pga_val | (1 << 3)
        # GAIN = code du gain (3 bits)
        pga_val = pga_val | (gain_code & 0x07)
        # Affichage pour debug
        print("[ADC] PGA=0x" + format(pga_val, "02X"))
        # Écriture dans le registre PGA
        self._wreg(REG_PGA, [pga_val])
        # Lecture de vérification
        val = self._rreg(REG_PGA, 1)
        # Affichage de la valeur lue
        print("[ADC DEBUG] PGA readback: 0x" + format(val[0], "02X"))

        # Configuration du mode de conversion (single-shot low-latency)
        # DR=0x04 pour data rate optimisé
        self.set_single_shot_lowlatency(0x04)

        # Configuration de la référence de tension (REF)
        # REFSEL=00 (REFP0/REFN0), REFCON=10 (ref interne ON)
        print("[ADC] REF=0x12")
        # Écriture dans le registre REF
        self._wreg(REG_REF, [0x12])
        # Attente pour stabilisation de la référence interne
        time.sleep(0.006)
        # Lecture de vérification
        val = self._rreg(REG_REF, 1)
        # Affichage de la valeur lue
        print("[ADC DEBUG] REF readback: 0x" + format(val[0], "02X"))

        # Configuration de la magnitude IDAC
        # Encodage du courant IDAC
        mag_code = encode_idac_uA(idac_uA)
        # Affichage pour debug
        print("[ADC] IDACMAG=0x" + format(mag_code & 0x0F, "02X"))
        # Écriture dans le registre IDACMAG
        self._wreg(REG_IDACMAG, [mag_code & 0x0F])
        # Lecture de vérification
        val = self._rreg(REG_IDACMAG, 1)
        # Affichage de la valeur lue
        print("[ADC DEBUG] IDACMAG readback: 0x" + format(val[0], "02X"))

        # Configuration du routage IDAC (IDACMUX)
        # Calcul du routage IDAC1: 0, 3, 6, 9
        idac1_route = 0 + (channel_index - 1) * 3
        # Limitation basse du routage
        if idac1_route < 0:
            idac1_route = 0
        # Limitation haute du routage
        if idac1_route > 15:
            idac1_route = 15
        # IDAC2 déconnecté (0x0F)
        idac2_route = 0x0F
        # Construction de la valeur IDACMUX
        idacmux_val = ((idac2_route & 0x0F) << 4) | (idac1_route & 0x0F)
        # Affichage pour debug
        print("[ADC] IDACMUX=0x" + format(idacmux_val, "02X"))
        # Écriture dans le registre IDACMUX
        self._wreg(REG_IDACMUX, [idacmux_val])
        # Lecture de vérification
        val = self._rreg(REG_IDACMUX, 1)
        # Affichage de la valeur lue
        print("[ADC DEBUG] IDACMUX readback: 0x" + format(val[0], "02X"))

        # Délai de stabilisation après configuration complète
        # Attente pour stabilisation des paramètres
        time.sleep(0.001)

        # Lecture de tous les registres clés pour debug final
        reg_map = {
            "INPMUX": REG_INPMUX,
            "PGA": REG_PGA,
            "DATARATE": REG_DATARATE,
            "REF": REG_REF,
            "IDACMAG": REG_IDACMAG,
            "IDACMUX": REG_IDACMUX
        }
        # Parcours de tous les registres importants
        for name, addr in reg_map.items():
            # Lecture de chaque registre
            val = self._rreg(addr, 1)
            # Affichage de l'état final
            print(f"[ADC] {name} (0x{addr:02X}) = 0x{val[0]:02X}")

    def start(self):
        """
        @brief       Démarre une conversion ADC.
        @details     Assure que DRDY est à HIGH puis envoie la commande START
                     pour initier une nouvelle conversion sur le canal configuré.

        @return      Rien.

        @note        DRDY doit être HIGH avant le START pour une conversion valide.
        @see         stop, wait_drdy_falling_edge
        """
        # Attente que DRDY remonte à HIGH avant le démarrage
        # Timestamp de début d'attente
        t0 = time.time()
        # Boucle tant que DRDY n'est pas HIGH
        while self.gpio_drdy.read() is not True:
            # Lecture du registre STATUS pour kick SCLK
            self._rreg(REG_STATUS, 1)
            # Délai court entre les tentatives
            time.sleep(0.001)
            # Timeout de 1 seconde
            if time.time() - t0 > 1.0:
                # Message d'erreur
                print("[ADC] Timeout: DRDY n'est pas remonté HIGH avant START !")
                # Sortie de boucle en cas de timeout
                break
        # Envoi de la commande START pour débuter la conversion
        # Transmission de la commande START via SPI
        self.spi.xfer2([CMD_START])

    def stop(self):
        """
        @brief       Arrête une conversion ADC en cours.
        @details     Envoie la commande STOP pour interrompre toute conversion
                     en cours et remettre l'ADC en état idle.

        @return      Rien.

        @note        Utilisé après lecture des données ou en cas d'erreur.
        @see         start, read_code24
        """
        # Transmission de la commande STOP via SPI
        self.spi.xfer2([CMD_STOP])

    def read_code24(self):
        """
        @brief       Lit un code de données 24 bits depuis l'ADC.
        @details     Utilise la commande RDATA pour lire les 3 octets de données
                     de conversion et les convertit en entier signé.

        @return      Valeur signée 24 bits ou None en cas d'erreur SPI.

        @note        Doit être appelé après détection du front descendant DRDY.
        @see         sign_extend_24, measure_resistance
        """
        # Commande RDATA + 3 octets dummy
        rx = self.spi.xfer2([CMD_RDATA, 0x00, 0x00, 0x00])
        # Vérification de la longueur de réponse
        if len(rx) < 4:
            # Message d'erreur
            print("[ADC] Erreur: réponse SPI trop courte " + str(rx))
            # Retour d'erreur
            return None
        # Octet de poids fort (MSB)
        b0 = rx[1]
        # Octet du milieu
        b1 = rx[2]
        # Octet de poids faible (LSB)
        b2 = rx[3]
        # Extension du signe vers 32 bits
        value = sign_extend_24(b0, b1, b2)
        # Retour de la valeur signée
        return value

    def measure_resistance(self, rref_ohm, pga_gain, timeout_s):
        """
        @brief       Mesure la résistance d'une sonde via l'ADC.
        @details     Effectue une mesure complète: démarrage de conversion,
                     attente DRDY, lecture du code et calcul de la résistance
                     selon la formule ratiométrique.

        @param rref_ohm    Résistance de référence en ohms.
        @param pga_gain    Gain PGA utilisé pour la mesure.
        @param timeout_s   Timeout en secondes pour la conversion.

        @return            Résistance mesurée en ohms ou None en cas d'erreur.

        @note              Utilise la formule: R = |code|/FS * (Rref / gain) * (I1 / (I1 + I2)).
        @see               measure_temperature, configure_channel
        """
        print("[ADC] Mesure résistance: rref=" + str(rref_ohm) + " gain=" + str(pga_gain) + " timeout=" + str(timeout_s))

        # Démarrage de la conversion ADC
        # Envoi de la commande START
        self.start()

        # Attente du signal DRDY indiquant la fin de conversion
        # Attente du front descendant DRDY
        ok = self.wait_drdy_falling_edge(timeout_s)
        # Test du résultat de l'attente
        if ok is False:
            # Arrêt de la conversion en cas de timeout
            self.stop()
            # Message d'erreur
            print("[ADC] Erreur: DRDY non détecté, mesure annulée")
            # Retour d'erreur
            return None

        # Lecture du code de conversion 24 bits
        # Lecture des données de conversion
        code = self.read_code24()
        # Arrêt de la conversion
        self.stop()

        # Validation du code lu
        # Test de validité du code
        if code is None:
            # Message d'erreur
            print("[ADC] Erreur: code ADC non lu")
            # Retour d'erreur
            return None

        # Affichage des paramètres de debug
        # Affichage du code brut
        print(f"[ADC DEBUG] Code brut: {code}")
        # Affichage de la pleine échelle
        print(f"[ADC DEBUG] FS: {FS}")
        # Affichage des paramètres de calcul
        print(f"[ADC DEBUG] Rref: {rref_ohm} / Gain: {pga_gain}")
        
        # Prise de la valeur absolue du code pour le calcul
        # Test du signe du code
        if code < 0:
            # Prise de la valeur absolue
            code = -code

        # Calcul de la résistance selon la formule ratiométrique
        # R = |code|/FS * (Rref / gain) * (I1 / (I1 + I2))  # Équation détaillée ratiométrique mise à jour
        # Calcul du ratio code/pleine échelle
        ratio = float(code) / float(FS)
        # Calcul de la résistance de la sonde avec facteur de correction IDAC
        # Le facteur (I1 / (I1 + I2)) = 0.5 car I1 = I2 dans notre configuration
        idac_correction_factor = 0.5
        r_sonde = ratio * (float(rref_ohm) / float(pga_gain)) * idac_correction_factor

        # Affichage du résultat
        print(f"[ADC] Résistance mesurée: {r_sonde:.1f} ohms")
        # Retour de la résistance mesurée
        return r_sonde

    def measure_temperature(self, sensor_name, rref_ohm, pga_gain, timeout_s):
        """
        @brief       Mesure la température d'un capteur via l'ADC.
        @details     Effectue une mesure de résistance puis utilise les tables
                     de conversion de capteurs pour obtenir la température
                     correspondante en degrés Celsius.

        @param sensor_name   Nom du capteur (doit exister dans SENSOR_TABLES).
        @param rref_ohm      Résistance de référence en ohms.
        @param pga_gain      Gain PGA utilisé pour la mesure.
        @param timeout_s     Timeout en secondes pour la conversion.

        @return              Température mesurée en °C ou None si erreur.

        @exception           Retourne None si capteur inconnu ou hors plage.
        @see                 measure_resistance, resistance_to_temperature_dynamic
        """
        # Mesure de la résistance du capteur
        # Appel de la mesure de résistance
        resistance = self.measure_resistance(rref_ohm, pga_gain, timeout_s)
        # Test de validité de la mesure
        if resistance is None:
            # Message d'erreur
            print("[ADC] Erreur: Résistance non mesurée ou saturation détectée.")
            # Retour d'erreur
            return None

        # Vérification de l'existence de la table de conversion
        # Test de présence du capteur
        if sensor_name not in SENSOR_TABLES:
            # Message d'erreur
            print(f"[ADC] Erreur: Table de conversion introuvable pour le capteur {sensor_name}.")
            # Retour d'erreur
            return None

        # Conversion de la résistance en température
        # Appel de la conversion
        temperature = resistance_to_temperature_dynamic(resistance, sensor_name)
        # Test de validité de la conversion
        if temperature is None:
            # Message d'erreur
            print("[ADC] Erreur: Température non calculable (hors plage de la table).")
            # Retour d'erreur
            return None

        # Affichage du résultat
        print(f"[ADC] Température mesurée: {temperature:.2f} °C")
        # Retour de la température mesurée
        return temperature

    def read_gain(self):
        """
        @brief       Lit le registre de gain PGA pour diagnostic.
        @details     Effectue une lecture du registre PGA et affiche sa valeur
                     pour vérification de la configuration du gain.

        @return      Valeur brute du registre PGA (0x00-0xFF).

        @note        Utilisé principalement pour le debug et la vérification.
        @see         configure_channel
        """
        # Lecture du registre PGA
        val = self._rreg(REG_PGA, 1)
        # Affichage de la valeur lue
        print(f"[ADC DEBUG] PGA Gain Register: 0x{val[0]:02X}")
        # Retour de la valeur du registre
        return val[0]

    def read_ref(self):
        """
        @brief       Lit le registre de configuration de la référence.
        @details     Effectue une lecture du registre REF et affiche sa valeur
                     pour vérification de la configuration de la référence.

        @return      Valeur brute du registre REF (0x00-0xFF).

        @note        Utilisé principalement pour le debug et la vérification.
        @see         configure_channel
        """
        # Lecture du registre REF
        val = self._rreg(REG_REF, 1)
        # Affichage de la valeur lue
        print(f"[ADC DEBUG] Reference Register: 0x{val[0]:02X}")
        # Retour de la valeur du registre
        return val[0]

    def read_inpmux(self):
        """
        @brief       Lit le registre de configuration du multiplexeur d'entrée.
        @details     Effectue une lecture du registre INPMUX et affiche sa valeur
                     pour vérification du routage des entrées analogiques.

        @return      Valeur brute du registre INPMUX (0x00-0xFF).

        @note        Utilisé principalement pour le debug et la vérification.
        @see         configure_channel
        """
        # Lecture du registre INPMUX
        val = self._rreg(REG_INPMUX, 1)
        # Affichage de la valeur lue
        print(f"[ADC DEBUG] INPMUX Register: 0x{val[0]:02X}")
        # Retour de la valeur du registre
        return val[0]