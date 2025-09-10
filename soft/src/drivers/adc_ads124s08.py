# -*- coding: utf-8 -*-
"""
Driver pour le convertisseur analogique-numerique ADS124S08 de Texas Instruments.

Fonctionnalites implementees:
- Communication SPI pour lecture/ecriture des registres
- Configuration des canaux differentiels
- Gestion du gain programmable (PGA)
- Configuration des sources de courant IDAC
- Mesure ratiometrique avec REFP0/REFN0
- Modes de conversion continue/unique
- Gestion du mode chop pour reduction du bruit

Parametres cles:
- Resolution: 24 bits
- Vitesse d'echantillonnage: 2.5 a 4000 SPS
- Gain programmable: 1 a 128
- Sources de courant IDAC: 10 uA a 2 mA

Reference: https://www.ti.com/product/ADS124S08
"""

# ---- Importation des modules necessaires ----
from hw.gpio_cm5 import GPIO          # Interface GPIO pour controler les broches
from time import sleep, monotonic     # Fonctions de temporisation precises
from typing import List, Optional     # Types pour le typage statique

# ---- Commandes SPI (selon datasheet section 8.5.1) ----
# Format des commandes:
# RESET (0000 0110): Reinitialise tous les registres
# START (0000 1000): Demarre les conversions
# STOP  (0000 1010): Arrete les conversions
# RDATA (0001 0010): Lit la derniere conversion
# RREG  (0010 rrrr): Lit le registre a l'adresse rrrr
# WREG  (0100 rrrr): Ecrit dans le registre a l'adresse rrrr
CMD_RESET = 0x06      # Reinitialise l'ADC et tous ses registres
CMD_START = 0x08      # Demarre le cycle de conversion
CMD_STOP  = 0x0A      # Arrete le cycle de conversion
CMD_RDATA = 0x12      # Lecture des donnees de conversion
CMD_RREG  = 0x20      # Lecture d'un registre (adresse = 5 bits LSB)
CMD_WREG  = 0x40      # Ecriture dans un registre (adresse = 5 bits LSB)

# ---- Adresses des registres (section 8.6) ----
REG_ID       = 0x00   # Registre d'identification du composant (lecture seule)
REG_STATUS   = 0x01   # Etat de l'ADC (power-on-reset, erreurs, etc.)
REG_INPMUX   = 0x02   # Configuration du multiplexeur d'entree
REG_PGA      = 0x03   # Configuration du gain programmable (1-128)
REG_DATARATE = 0x04   # Vitesse d'echantillonnage (2.5-4000 SPS)
REG_REF      = 0x05   # Selection de la reference de tension
REG_IDACMAG  = 0x06   # Amplitude du courant IDAC (10uA-2mA)
REG_IDACMUX  = 0x07   # Routage des sources de courant IDAC
REG_VBIAS    = 0x08   # Tension de polarisation des entrees
REG_SYS      = 0x09   # Configuration systeme (chop, etc.)
REG_GPIOCFG  = 0x0B   # Configuration des GPIO
REG_GPIODIR  = 0x0C   # Direction des GPIO
REG_GPIODAT  = 0x0D   # Etat des GPIO

# ---- Tables de correspondance ----
# Table des entrees analogiques (section 8.6.3)
AIN_MAP = {
    # Canaux standards AIN0-AIN11
    **{f"AIN{i}": i for i in range(12)},
    # Canal commun AINCOM
    "AINCOM": 0x0C
}

# Modes de reference de tension (section 8.6.6)
REF_SEL = {
    # Reference interne 2.5V
    "internal_2V5": 0b000,
    # Mode ratiometrique avec REFP0/REFN0
    "ratiometric_REFP0_REFN0": 0b001,
    # Mode ratiometrique avec REFP1/REFN1
    "ratiometric_REFP1_REFN1": 0b010
}

# Vitesses d'echantillonnage en mode SINC3 (section 8.6.5)
# Note: seules les valeurs communes sont listees
DATA_RATE_CODE = {
    2.5: 0x00,    # Plus lent, meilleure resolution
    5: 0x01,
    10: 0x02,
    16.6: 0x03,   # Rejection 50Hz + 60Hz
    20: 0x04,
    50: 0x05,
    60: 0x06,     # Rejection 60Hz
    100: 0x07,
    200: 0x08,
    400: 0x09,
    800: 0x0A,
    1000: 0x0B,
    2000: 0x0C,
    4000: 0x0D    # Plus rapide, resolution reduite
}

class ADS124S08:
    """
    Classe de pilotage du convertisseur ADS124S08.
    """
    
    def __init__(self, spi, cs_pin: int, drdy_pin: int, start_pin: int,
                 a0_pin: int, a1_pin: int, gpio=GPIO):
        """
        Initialise l'interface avec l'ADS124S08.
        
        Args:
            spi: Instance du bus SPI configure
            cs_pin: Numero de broche GPIO pour Chip Select
            drdy_pin: Numero de broche GPIO pour Data Ready
            start_pin: Numero de broche GPIO pour Start
            a0_pin: Numero de broche GPIO pour A0 (selection reference)
            a1_pin: Numero de broche GPIO pour A1 (selection reference)
            gpio: Interface GPIO a utiliser
        """
        # Stockage des parametres
        self.spi = spi              # Interface SPI
        self.gpio = gpio            # Interface GPIO
        self.cs = cs_pin           # Broche Chip Select
        self.drdy = drdy_pin       # Broche Data Ready
        self.start = start_pin     # Broche Start/Sync
        self.a0 = a0_pin          # Broche A0 selection reference
        self.a1 = a1_pin          # Broche A1 selection reference

        # Configuration des broches GPIO
        # Sorties: CS, START, A0, A1 (etat initial haut)
        for pin in [self.cs, self.start, self.a0, self.a1]:
            self.gpio.setup(pin, self.gpio.OUT, initial=1)
            
        # Entree: DRDY avec pull-up
        self.gpio.setup(self.drdy, self.gpio.IN, 
                       pull_up_down=self.gpio.PUD_UP)

    def set_ref_bank(self, bank: int) -> None:
        """
        Configure le selecteur de reference TMUX 2 bits.
        
        Les broches A0/A1 selectionnent la banque de resistances:
          0 -> A1=0, A0=0 : Premiere banque
          1 -> A1=0, A0=1 : Deuxieme banque
          2 -> A1=1, A0=0 : Troisieme banque
          3 -> A1=1, A0=1 : Quatrieme banque
          
        Args:
            bank: Index de la banque (0-3)
            
        Raises:
            ValueError: Si l'index est hors limites
        """
        # Validation de l'index
        if not 0 <= bank <= 3:
            raise ValueError("L'index de banque doit etre entre 0 et 3")

        # Decodage des niveaux logiques
        if bank == 0:
            a1_level = 0
            a0_level = 0
        elif bank == 1:
            a1_level = 0
            a0_level = 1
        elif bank == 2:
            a1_level = 1
            a0_level = 0
        else:  # bank == 3
            a1_level = 1
            a0_level = 1

        # Configuration des broches TMUX
        self.gpio.output(self.a1, a1_level)   # A1
        self.gpio.output(self.a0, a0_level)   # A0

    # ---- Methodes bas niveau SPI ----
    
    def _cs_low(self) -> None:
        """Active le chip select (etat bas)."""
        self.gpio.output(self.cs, 0)

    def _cs_high(self) -> None:
        """Desactive le chip select (etat haut)."""
        self.gpio.output(self.cs, 1)

    def _cmd(self, opcode: int) -> None:
        """
        Envoie une commande simple sur le bus SPI.
        
        Args:
            opcode: Code de la commande (8 bits)
        """
        self._cs_low()                       # Active CS
        self.spi.xfer2([opcode & 0xFF])      # Envoie la commande
        self._cs_high()                      # Desactive CS

    def _wreg(self, addr: int, data: List[int]) -> None:
        """
        Ecrit des donnees dans un ou plusieurs registres.
        
        Format: WREG (0100 aaaa) + count + data
        aaaa = adresse du premier registre (0-31)
        count = nombre de registres - 1
        
        Args:
            addr: Adresse du premier registre
            data: Liste des valeurs a ecrire
        """
        self._cs_low()
        # Commande WREG + adresse (5 bits) + nombre de registres
        self.spi.xfer2([
            CMD_WREG | (addr & 0x1F),    # Commande + adresse
            (len(data)-1) & 0x1F         # Nombre de registres - 1
        ] + data)                        # Donnees
        self._cs_high()

    def _rreg(self, addr: int, n: int) -> List[int]:
        """
        Lit un ou plusieurs registres.
        
        Format: RREG (0010 aaaa) + count + donnees
        aaaa = adresse du premier registre (0-31)
        count = nombre de registres - 1
        
        Args:
            addr: Adresse du premier registre
            n: Nombre de registres a lire
            
        Returns:
            Liste des valeurs lues
        """
        self._cs_low()
        # Commande RREG + adresse (5 bits) + nombre de registres
        self.spi.xfer2([
            CMD_RREG | (addr & 0x1F),    # Commande + adresse
            (n-1) & 0x1F                 # Nombre de registres - 1
        ])
        out = self.spi.readbytes(n)      # Lecture des donnees
        self._cs_high()
        return out

    # ---- Methodes de controle ----

    def reset(self) -> None:
        """
        Reinitialise l'ADC avec la commande RESET.
        Attend 10ms pour la stabilisation.
        """
        self._cmd(CMD_RESET)             # Envoie commande RESET
        sleep(0.01)                      # Attend 10ms

    def start_continuous(self) -> None:
        """
        Demarre les conversions continues.
        Utilise la commande START (plutot que la broche).
        """
        self._cmd(CMD_START)

    def stop(self) -> None:
        """Arrete les conversions."""
        self._cmd(CMD_STOP)

    def powerdown(self) -> None:
        """
        Met l'ADC en mode basse consommation.
        La commande STOP suffit pour une consommation minimale.
        """
        self.stop()

    # ---- Methodes de configuration ----

    def basic_setup(self, pga_gain: int = 1, 
                   data_rate_sps: float = 20,
                   ref_mode: str = "ratiometric_REFP0_REFN0",
                   chop: bool = False) -> None:
        """
        Configure les parametres de base de l'ADC.
        
        Args:
            pga_gain: Gain du PGA (1,2,4,8,16,32,64,128)a
            data_rate_sps: Vitesse en echantillons/seconde
            ref_mode: Mode de reference
            chop: Active/desactive le mode chop
            
        Raises:
            ValueError: Si les parametres sont invalides
        """
        # Configuration du gain PGA
        pga_bits = {
            1:0, 2:1, 4:2, 8:3, 16:4, 32:5, 64:6, 128:7
        }[pga_gain] << 0
        self._wreg(REG_PGA, [pga_bits])

        # Configuration de la vitesse d'echantillonnage
        dr = DATA_RATE_CODE.get(data_rate_sps, DATA_RATE_CODE[20])
        self._wreg(REG_DATARATE, [dr])

        # Configuration de la reference
        refsel = REF_SEL[ref_mode] & 0x7
        self._wreg(REG_REF, [refsel])

        # Configuration du mode chop (bit 0 du registre SYS)
        sys_val = 0x01 if chop else 0x00a
        self._wreg(REG_SYS, [sys_val])

    def select_diff_channel(self, pos: str, neg: str) -> None:
        """
        Configure une paire d'entrées différentielles.
        
        Args:
            pos: Entrée positive ("AIN0"-"AIN11" ou "AINCOM")
            neg: Entrée négative ("AIN0"-"AIN11" ou "AINCOM")
            
        Raises:
            ValueError: Si les entrées sont invalides
        """
        # Conversion des noms en codes
        p = AIN_MAP[pos]
        n = AIN_MAP[neg]
        
        # Configuration du multiplexeur (pos dans MSB, neg dans LSB)
        self._wreg(REG_INPMUX, [(p<<4) | (n & 0x0F)])

    def route_idac(self, current_uA: int = 100,
                  idac1_route: Optional[str] = "AIN0",
                  idac2_route: Optional[str] = None) -> None:
        """
        Configure les sources de courant IDAC.
        
        Args:
            current_uA: Courant en uA (10-2000)
            idac1_route: Canal pour IDAC1 ou None pour desactiver
            idac2_route: Canal pour IDAC2 ou None pour desactiver
            
        Raises:
            ValueError: Si les parametres sont invalides
        """
        # Table des courants IDAC
        mag_tbl = {
            10:0, 50:1, 100:2, 250:3, 500:4,
            750:5, 1000:6, 1500:7, 2000:8
        }
        
        # Configuration du courant
        self._wreg(REG_IDACMAG, [mag_tbl[current_uA]])

        # Configuration du routage
        def map_route(name: Optional[str]) -> int:
            if name is None:
                return 0x0F  # Desactive
            return AIN_MAP[name] & 0x0F
            
        # IDAC1 dans MSB, IDAC2 dans LSB
        route = (map_route(idac1_route)<<4) | map_route(idac2_route)
        self._wreg(REG_IDACMUX, [route])

    # ---- Methodes de lecture ----

    def _wait_drdy(self, timeout_s: float = 0.5) -> None:
        """
        Attend que DRDY passe a l'etat bas.
        
        Args:
            timeout_s: Delai maximum d'attente en secondes
            
        Raises:
            TimeoutError: Si le delai est depasse
        """
        t0 = monotonic()
        while self.gpio.input(self.drdy) == 1:
            if (monotonic() - t0) > timeout_s:
                raise TimeoutError("Timeout en attente de DRDY")

    def read_once_blocking(self) -> int:
        """
        Lit une conversion unique en mode bloquant.
        
        Returns:
            int: Valeur convertie (24 bits signes)
            
        Raises:
            TimeoutError: Si pas de donnees disponibles
        """
        self._wait_drdy()           # Attend donnees prêtes
        
        self._cs_low()
        self.spi.xfer2([CMD_RDATA]) # Commande de lecture
        b = self.spi.readbytes(3)   # Lit 3 octets (24 bits)
        self._cs_high()
        
        # Assemblage en entier 24 bits signe
        val = (b[0]<<16) | (b[1]<<8) | b[2]
        if val & 0x800000:  # Si bit de signe
            val -= 1<<24
        return val

    def code_to_ratio(self, code: int, gain: Optional[int] = None) -> float:
        """
        Convertit le code ADC en ratio Rsonde/Rref.
        
        En mode ratiometrique:
        code = (VIN / VREF) * (2^23)/gain
        ratio = code / (2^23) * gain
        
        Args:
            code: Code ADC 24 bits signe
            gain: Gain utilise (si None, lu depuis le registre PGA)
            
        Returns:
            float: Ratio Rsonde/Rref
        """
        if gain is None:
            # Lit le gain depuis le registre PGA
            g = ((self._rreg(REG_PGA, 1)[0]) & 0x07)
            gain = {0:1,1:2,2:4,3:8,4:16,5:32,6:64,7:128}[g]
            
        return (code / float(1<<23)) * gain
