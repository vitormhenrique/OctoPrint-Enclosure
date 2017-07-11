import ctypes
import struct
import sys

import smbus


def main():
    # Get bus address if provided or use default address
    address = 0x48
    if len(sys.argv) >= 2:
        address = int(sys.argv[1], 0)

    if not 0x48 <= address <= 0x4b:
        raise ValueError("Invalid address value")

    # Connect to I2C bus (use 0 on original Raspberry Pi, 1 on later models)
    bus = smbus.SMBus(1)

    # Set pointer to the temperature register
    bus.write_byte(address, 0)

    # Read two byte value
    temp = bus.read_word_data(address, 0)

    # Disconnect from bus
    bus.close()

    # Byte swap
    temp = struct.unpack(">H", struct.pack("<H", temp))[0]

    # Shift
    temp = temp >> 4

    # Convert to 2 byte twos compliment negative if negative
    if ((temp & 0x800) != 0):
        temp |= 0xF800

    # Convert into a signed number
    temp = ctypes.c_short(temp).value

    # Divide by 16 to get value in celsius
    temp /= 16.0

    print temp

if __name__ == "__main__":
    main()
