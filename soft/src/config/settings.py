class Settings:
    # ADC SPI (ADS124S0x)
    ADC_BUS          = 1
    ADC_CS_INDEX     = 0           # /dev/spidev1.0
    ADC_MODE         = 1           # CPOL=0, CPHA=1 per datasheet
    ADC_SPEED_HZ     = 1000000     # 1 MHz safe
    ADC_FULL_SCALE   = (1 << 23)   # 24-bit signed, full-scale code for ratio

    # MUX SPI on SPI0, manual CS via GPIO
    MUX_BUS          = 0
    MUX_MODE         = 0
    MUX_SPEED_HZ     = 1000000
    MUX_CS_PINS      = [8, 7, 3, 2]   # BCM list, order defines mux index 0..3

    # API
    API_BASE_URL     = "http://192.168.1.100:8080/api"  # à adapter
    API_DEVICE_ID    = "cm5-2510-a"
    API_TIMEOUT_S    = 2.0

    # Measurement loop
    LOOP_PERIOD_S    = 1.0

    # Table de correspondance température -> index MUX (32 points)
    # TODO: renseigner la table réelle selon ton réseau résistif mesuré
    TEMP_TABLE_C     = [-20.0 + (i * 2.0) for i in range(32)]  # placeholder
