"""
Module HAL GPIO
Abstraction des entrées/sorties numériques pour tous les drivers du projet.
Permet d'utiliser les GPIO sans dépendance directe au matériel.
"""
from typing import Callable, Literal, Optional
from Metrology.exceptions import HardwareError

class GPIO:
    # Constantes pour la configuration
    IN = "in"
    OUT = "out"
    PUD_OFF = 0
    PUD_DOWN = 1
    PUD_UP = 2
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"

    def setup_out(self, pin: int, initial: int = 0) -> None:
        """
        Configure une broche en sortie.
        
        Args:
            pin: Numéro de la broche GPIO
            initial: État initial (0 ou 1)
            
        Raises:
            HardwareError: Si la configuration échoue
        """
        raise NotImplementedError

    def setup_in(self, pin: int, pull_up_down: int = PUD_OFF) -> None:
        """
        Configure une broche en entrée.
        
        Args:
            pin: Numéro de la broche GPIO
            pull_up_down: Configuration des résistances de pull-up/down
                         PUD_OFF, PUD_DOWN, ou PUD_UP
                         
        Raises:
            HardwareError: Si la configuration échoue
        """
        raise NotImplementedError

    def write(self, pin: int, value: int) -> None:
        """
        Écrit une valeur sur une broche.
        
        Args:
            pin: Numéro de la broche GPIO
            value: Valeur à écrire (0 ou 1)
            
        Raises:
            HardwareError: Si l'écriture échoue
        """
        raise NotImplementedError

    def read(self, pin: int) -> int:
        """
        Lit la valeur d'une broche.
        
        Args:
            pin: Numéro de la broche GPIO
            
        Returns:
            int: Valeur lue (0 ou 1)
            
        Raises:
            HardwareError: Si la lecture échoue
        """
        raise NotImplementedError

    def attach_interrupt(self, pin: int, 
                        callback: Callable[[int], None],
                        edge: Literal["rising", "falling", "both"]) -> None:
        """
        Attache une interruption sur une broche.
        
        Args:
            pin: Numéro de la broche GPIO
            callback: Fonction appelée lors de l'interruption
            edge: Type de front ("rising", "falling", "both")
            
        Raises:
            HardwareError: Si l'attachement échoue
        """
        raise NotImplementedError
