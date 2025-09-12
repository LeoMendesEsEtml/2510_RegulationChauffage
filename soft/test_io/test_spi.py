import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.mode = 1
spi.max_speed_hz = 100000
print("Envoi SPI...")
for i in range(10):
    spi.xfer2([0xAA])
    time.sleep(0.5)
spi.close()
print("Fini.")