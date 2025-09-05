import time
from config.pins_cm5 import Pins
from config.settings import Settings
# from io.gpio_cm5 import ...  # À compléter
# from app.metrologie import calc_temp  # À créer
# from app.api import get_params  # À créer
# from app.regulation_ctrl import regulate  # À créer

def init_system():
    # Activer relais bypass
    # gpio_set(Pins.RELAY_BYPASS, True)
    # Double flash LED
    # led_double_flash(Pins.FRONTLED)
    # Log init
    print("init_ok")

def main_loop():
    init_system()
    while True:
        print("Attente Tick 5min...")
        time.sleep(300)  # Tick 5 min
        process_cycle()

def process_cycle():
    # Lire contact sec
    # contact_state = gpio_read(Pins.DRY_CONTACT)
    print("Contact_state", "état")  # Logguer état

    # Pour chaque canal actif
    for canal in range(1, 5):
        try:
            # Sélectionner Rref sur TMUX
            # Configurer ADC
            # Lancer conversion, attendre DRDY
            # data = adc_read()
            # Tmes = calc_temp(data)
            # N, kM, Tprevu = get_params()
            # slot, pas, Tsim = regulate(Tmes, N, kM, Tprevu)
            # Programmer MUX
            # led_flash(Pins.FRONTLED)
            print(f"ch_result canal:{canal}")
        except Exception as e:
            # Désactiver bypass, LED 2Hz, logguer faute
            print("fault", str(e))
            return  # Stop cycle sur erreur

if __name__ == "__main__":
    main_loop()