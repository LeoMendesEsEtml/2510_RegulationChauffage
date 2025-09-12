import spidev
import time

spi = spidev.SpiDev()
spi.open(1, 0)
spi.mode = 1
spi.max_speed_hz = 100000
print("Envoi SPI en boucle infinie...")
try:
    while True:
        spi.xfer2([0xAA])
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Arrêt demandé par l'utilisateur.")
finally:
    spi.close()
    print("Fini.")