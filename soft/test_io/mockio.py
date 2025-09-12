# mockio.py
# Mock definitions for GPIO and SPI pins based on hardware mapping

MOCK_PINS = {
    # SPI0 → MUX ADG731 (CM5, banque A0)
    'MUX_SCLK':      {'GPIO': 11, 'Patte_CM5': 38, 'Fonction': 'A0', 'Alt': 'SPI0_SCLK',   'Direction': 'Sortie', 'Remarque': 'Horloge vers MUX'},
    'MUX_MOSI':      {'GPIO': 10, 'Patte_CM5': 44, 'Fonction': 'A0', 'Alt': 'SPI0_SIO[0]', 'Direction': 'Sortie', 'Remarque': 'Donnees vers MUX'},
    'MUX_MISO':      {'GPIO': 9,  'Patte_CM5': None, 'Fonction': 'A0', 'Alt': 'SPI0_SIO[1]', 'Direction': 'Entrée', 'Remarque': 'Non câblé sur le matériel'},
    'MUX_CS_1':      {'GPIO': 8,  'Patte_CM5': 39, 'Fonction': 'A0', 'Alt': 'SPI0_CSn[0]', 'Direction': 'Sortie', 'Remarque': 'Chip Select carte 0'},
    'MUX_CS_2':      {'GPIO': 7,  'Patte_CM5': 37, 'Fonction': 'A0', 'Alt': 'SPI0_CSn[1]', 'Direction': 'Sortie', 'Remarque': 'Chip Select carte 1'},
    'MUX_CS_3':      {'GPIO': 3,  'Patte_CM5': 56, 'Fonction': 'A0', 'Alt': 'SPI0_CSn[2]', 'Direction': 'Sortie', 'Remarque': 'Chip Select carte 2'},
    'MUX_CS_4':      {'GPIO': 2,  'Patte_CM5': 58, 'Fonction': 'A0', 'Alt': 'SPI0_CSn[3]', 'Direction': 'Sortie', 'Remarque': 'Chip Select carte 3'},

    # SPI1 → ADC (ADS124S08) (CM5, banque A0)
    'SPI_SCLK_ADC':  {'GPIO': 21, 'Patte_CM5': 25, 'Fonction': 'A0', 'Alt': 'SPI1_SCLK',   'Direction': 'Sortie', 'Remarque': 'Horloge vers ADC'},
    'SPI_MOSI_ADC':  {'GPIO': 20, 'Patte_CM5': 26, 'Fonction': 'A0', 'Alt': 'SPI1_SIO[0]', 'Direction': 'Sortie', 'Remarque': 'Donnees vers ADC'},
    'SPI_MISO_ADC':  {'GPIO': 19, 'Patte_CM5': 49, 'Fonction': 'A0', 'Alt': 'SPI1_SIO[1]', 'Direction': 'Entrée', 'Remarque': 'Donnees depuis ADC'},
    'CS_ADC':        {'GPIO': 18, 'Patte_CM5': 50, 'Fonction': 'A0', 'Alt': 'SPI1_CSn[0]', 'Direction': 'Sortie', 'Remarque': 'Chip Select ADC'},

    # GPIO divers (banque A6 = PIO[x])
    'CM_24V_OUT_1':  {'GPIO': 13, 'Patte_CM5': 31, 'Fonction': 'A6', 'Alt': 'PIO[13]',     'Direction': 'Sortie', 'Remarque': 'Commande sortie 24V canal 1'},
    'CM_24V_SENSE_1':{'GPIO': 14, 'Patte_CM5': 8,  'Fonction': 'A6', 'Alt': 'PIO[14]',     'Direction': 'Entrée', 'Remarque': 'Retour/sense 24V canal 1'},
    'CM_24V_OUT_2':  {'GPIO': 15, 'Patte_CM5': 5,  'Fonction': 'A6', 'Alt': 'PIO[15]',     'Direction': 'Sortie', 'Remarque': 'Commande sortie 24V canal 2'},
    'CM_24V_SENSE_2':{'GPIO': 16, 'Patte_CM5': 29, 'Fonction': 'A6', 'Alt': 'PIO[16]',     'Direction': 'Entrée', 'Remarque': 'Retour/sense 24V canal 2'},
    'CMD_RELAY':     {'GPIO': 17, 'Patte_CM5': 20, 'Fonction': 'A6', 'Alt': 'PIO[17]',     'Direction': 'Sortie', 'Remarque': 'Commande relais'},
    'ADC_DRDY':      {'GPIO': 22, 'Patte_CM5': 46, 'Fonction': 'A6', 'Alt': 'PIO[22]',     'Direction': 'Entrée', 'Remarque': 'Data Ready ADC (actif bas typique)'},
    'ADC_START_SYNC':{'GPIO': 23, 'Patte_CM5': 47, 'Fonction': 'A6', 'Alt': 'PIO[23]',     'Direction': 'Sortie', 'Remarque': 'Démarrage/Sync conversions ADC'},
    'ADC_A0':        {'GPIO': 24, 'Patte_CM5': 45, 'Fonction': 'A6', 'Alt': 'PIO[24]',     'Direction': 'Sortie', 'Remarque': 'Séléction banque/référence ADC A0'},
    'ADC_A1':        {'GPIO': 25, 'Patte_CM5': 41, 'Fonction': 'A6', 'Alt': 'PIO[25]',     'Direction': 'Sortie', 'Remarque': 'Séléction banque/référence ADC A1'},
    'FRONT_LED':     {'GPIO': 27, 'Patte_CM5': 24, 'Fonction': 'A6', 'Alt': 'PIO[27]',     'Direction': 'Sortie', 'Remarque': 'LED façade'},
}

# Example mock functions for GPIO/SPI

def get_pin_info(name):
    """Return pin info dict for a given logical name."""
    return MOCK_PINS.get(name)

# Add more mock functions/classes as needed for testing
