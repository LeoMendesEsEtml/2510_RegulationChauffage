# -*- coding: utf-8 -*-
"""
Interface GPIO pour la carte CM5.

Fournit une abstraction pour:
- Configuration des GPIO
- Lecture/ecriture des entrees/sorties
- Gestion des interruptions
- Configuration SPI/I2C
"""

import RPi.GPIO as GPIO
from typing import Callable, Optional, Dict, List
import logging
from utils_module.logging_config import setup_module_logger
from utils_module.error_handler import handle_errors, HardwareError

# Logger
logger = setup_module_logger(__name__)

# Definition des broches
GPIO_PINS = {
    # ADC
    "ADC_CS": 8,      # CE0
    "ADC_DRDY": 25,   # Data Ready
    "ADC_START": 24,  # Start Conversion
    "ADC_RESET": 23,  # Reset
    
    # MUX
    "MUX_CS": 7,      # CE1
    "MUX_RESET": 22,  # Reset
    
    # SPI
    "SPI_SCLK": 11,   # Clock
    "SPI_MOSI": 10,   # Master Out
    "SPI_MISO": 9,    # Master In
    
    # I2C
    "I2C_SDA": 2,     # Data
    "I2C_SCL": 3,     # Clock
    
    # GPIO generiques
    "GPIO_1": 17,
    "GPIO_2": 18,
    "GPIO_3": 27,
    "GPIO_4": 4
}

class GPIOManager:
    """
    Gestionnaire des GPIO.
    
    Configure et controle les broches GPIO.
    Gere les callbacks d'interruption.
    """
    
    def __init__(self):
        """
        Initialise le gestionnaire GPIO.
        Configure le mode BCM et prepare les broches.
        """
        # Configuration mode BCM
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Etat des broches
        self._pin_states: Dict[int, bool] = {}
        
        # Callbacks d'interruption
        self._callbacks: Dict[int, List[Callable]] = {}
        
        # Initialisation des broches
        self._setup_pins()
        
        logger.info("Gestionnaire GPIO initialise")
        
    def _setup_pins(self) -> None:
        """
        Configure les broches par defaut.
        """
        try:
            # ADC
            self.setup_pin(GPIO_PINS["ADC_CS"], GPIO.OUT, initial=GPIO.HIGH)
            self.setup_pin(GPIO_PINS["ADC_DRDY"], GPIO.IN)
            self.setup_pin(GPIO_PINS["ADC_START"], GPIO.OUT, initial=GPIO.LOW)
            self.setup_pin(GPIO_PINS["ADC_RESET"], GPIO.OUT, initial=GPIO.HIGH)
            
            # MUX
            self.setup_pin(GPIO_PINS["MUX_CS"], GPIO.OUT, initial=GPIO.HIGH)
            self.setup_pin(GPIO_PINS["MUX_RESET"], GPIO.OUT, initial=GPIO.HIGH)
            
            # SPI
            self.setup_pin(GPIO_PINS["SPI_SCLK"], GPIO.OUT)
            self.setup_pin(GPIO_PINS["SPI_MOSI"], GPIO.OUT)
            self.setup_pin(GPIO_PINS["SPI_MISO"], GPIO.IN)
            
            # I2C
            self.setup_pin(GPIO_PINS["I2C_SDA"], GPIO.OUT)
            self.setup_pin(GPIO_PINS["I2C_SCL"], GPIO.OUT)
            
            logger.info("Broches GPIO configurees")
            
        except Exception as e:
            logger.error(f"Erreur configuration GPIO: {str(e)}")
            raise HardwareError(f"Erreur configuration GPIO: {str(e)}")
            
    def setup_pin(
        self,
        pin: int,
        direction: int,
        pull_up_down: Optional[int] = None,
        initial: Optional[int] = None
    ) -> None:
        """
        Configure une broche GPIO.
        
        Args:
            pin: Numero de la broche
            direction: GPIO.IN ou GPIO.OUT
            pull_up_down: GPIO.PUD_UP, GPIO.PUD_DOWN ou None
            initial: Etat initial pour sortie
        """
        try:
            if pull_up_down is not None:
                GPIO.setup(pin, direction, pull_up_down=pull_up_down)
            else:
                GPIO.setup(pin, direction)

            if direction == GPIO.OUT and initial is not None:
                GPIO.output(pin, initial)
                self._pin_states[pin] = bool(initial)
        except Exception as e:
            raise HardwareError(f"Erreur lors de la configuration de la broche {pin}: {str(e)}")
            
    @handle_errors
    def cleanup(self) -> None:
        """
        Nettoie les GPIO a la fermeture.
        """
        GPIO.cleanup()
        self._pin_states.clear()
        self._callbacks.clear()
        logger.info("GPIO nettoyes")
        
    @handle_errors
    def set_pin(self, pin: int, state: bool) -> None:
        """
        Change l'etat d'une sortie.
        
        Args:
            pin: Numero de la broche
            state: Nouvel etat
        """
        GPIO.output(pin, state)
        self._pin_states[pin] = state
        
    @handle_errors
    def get_pin(self, pin: int) -> bool:
        """
        Lit l'etat d'une entree.
        
        Args:
            pin: Numero de la broche
            
        Returns:
            Etat de la broche
        """
        return bool(GPIO.input(pin))
        
    @handle_errors
    def toggle_pin(self, pin: int) -> None:
        """
        Inverse l'etat d'une sortie.
        
        Args:
            pin: Numero de la broche
        """
        state = not self._pin_states.get(pin, False)
        self.set_pin(pin, state)
        
    @handle_errors
    def add_event_callback(
        self,
        pin: int,
        callback: Callable,
        edge: int = GPIO.BOTH,
        bouncetime: int = 100
    ) -> None:
        """
        Ajoute un callback sur evenement.
        
        Args:
            pin: Numero de la broche
            callback: Fonction de callback
            edge: Type de front (RISING, FALLING, BOTH)
            bouncetime: Anti-rebond en ms
        """
        if pin not in self._callbacks:
            self._callbacks[pin] = []
            GPIO.add_event_detect(
                pin,
                edge,
                callback=self._event_handler,
                bouncetime=bouncetime
            )
            
        self._callbacks[pin].append(callback)
        
    @handle_errors
    def remove_event_callback(self, pin: int, callback: Callable) -> None:
        """
        Supprime un callback.
        
        Args:
            pin: Numero de la broche
            callback: Fonction de callback
        """
        if pin in self._callbacks:
            self._callbacks[pin].remove(callback)
            if not self._callbacks[pin]:
                GPIO.remove_event_detect(pin)
                del self._callbacks[pin]
                
    def _event_handler(self, pin: int) -> None:
        """
        Gestionnaire d'evenements GPIO.
        
        Args:
            pin: Numero de la broche
        """
        if pin in self._callbacks:
            state = self.get_pin(pin)
            for callback in self._callbacks[pin]:
                try:
                    callback(pin, state)
                except Exception as e:
                    logger.error(f"Erreur dans callback GPIO: {str(e)}")

# Instance globale
gpio_manager = GPIOManager()

class Relay:
    def __init__(self, pin: int):
        self.pin = pin

    def activate(self):
        gpio_manager.set_pin(self.pin, True)
        logger.info(f"Relay on pin {self.pin} activated.")

    def deactivate(self):
        gpio_manager.set_pin(self.pin, False)
        logger.info(f"Relay on pin {self.pin} deactivated.")

class LED:
    def __init__(self, pin: int):
        self.pin = pin

    def turn_on(self):
        gpio_manager.set_pin(self.pin, True)
        logger.info(f"LED on pin {self.pin} turned on.")

    def turn_off(self):
        gpio_manager.set_pin(self.pin, False)
        logger.info(f"LED on pin {self.pin} turned off.")
