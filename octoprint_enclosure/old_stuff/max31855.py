import ctypes
import struct
import sys

import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855


def main():
    # Get bus address if provided or use default address
    SPI_DEVICE = 0
    if len(sys.argv) >= 2:
        SPI_DEVICE = int(sys.argv[1], 0)

    if not 0 <= SPI_DEVICE <= 1:
        raise ValueError("Invalid address value")

   # Raspberry Pi hardware SPI configuration.
    SPI_PORT   = 0
    sensor = MAX31855.MAX31855(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))

    temp = sensor.readTempC()

    print('{0:0.1f}'.format(temp))

if __name__ == "__main__":
    main()
