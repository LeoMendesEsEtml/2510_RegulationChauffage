# English code, French comments

class Pins:
    # SPI1 for ADC (per report)
    ADC_CS      = 18
    ADC_MISO    = 19
    ADC_MOSI    = 20
    ADC_SCLK    = 21
    ADC_DRDY    = 22
    ADC_START   = 23
    ADC_A0      = 24
    ADC_A1      = 25

    # SPI0 for MUX (serial mux: MOSI + SCLK + 4 CS)
    MUX_MOSI    = 10   # SPI0_SIO[0]
    MUX_SCLK    = 11   # SPI0_SCLK

    # Up to 4 mux chip-selects (use as GPIO-driven CS)
    MUX_CS_1    = 8    # SPI0_CSn[0]
    MUX_CS_2    = 7    # SPI0_CSn[1]
    MUX_CS_3    = 3    # SPI0_CSn[2]
    MUX_CS_4    = 2    # SPI0_CSn[3]

    # 24V IO test lines
    OUT_24V_1   = 13
    SENSE_24V_1 = 14
    OUT_24V_2   = 15
    SENSE_24V_2 = 16

    # Status LED
    FRONTLED   = 27