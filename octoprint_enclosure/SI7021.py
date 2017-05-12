import smbus
import time
import sys


if len(sys.argv) == 2:
    address = int(sys.argv[1],16)
else:
    print('-1 | -1')
    sys.exit(1)

# Get I2C bus
bus = smbus.SMBus(1)

# SI7021 address, 0x40(64)
#		0xF5(245)	Select Relative Humidity NO HOLD master mode
bus.write_byte(address, 0xF5)

time.sleep(0.3)

# SI7021 address, 0x40(64)
# Read data back, 2 bytes, Humidity MSB first
data0 = bus.read_byte(address)
data1 = bus.read_byte(address)

# Convert the data
humidity = ((data0 * 256 + data1) * 125 / 65536.0) - 6

time.sleep(0.3)

# SI7021 address, 0x40(64)
#		0xF3(243)	Select temperature NO HOLD master mode
bus.write_byte(address, 0xF3)

time.sleep(0.3)

# SI7021 address, 0x40(64)
# Read data back, 2 bytes, Temperature MSB first
data0 = bus.read_byte(address)
data1 = bus.read_byte(address)

# Convert the data
cTemp = ((data0 * 256 + data1) * 175.72 / 65536.0) - 46.85

print('{0:0.1f} | {1:0.1f}'.format(cTemp, humidity))
