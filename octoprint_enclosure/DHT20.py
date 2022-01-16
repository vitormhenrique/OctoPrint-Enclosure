import time
import smbus
import sys

class DHT20Error(Exception):
    """ Bast class for exception """

if len(sys.argv) == 2 or len(sys.argv) == 3:
    address = int(sys.argv[1],16)
    if len(sys.argv) == 3:
        busNum = int(sys.argv[2],16)
    else:
        busNum = 1
else:
    print('-1 | -1')
    sys.exit(1)


sensor = smbus.SMBus(busNum)

data = sensor.read_i2c_block_data(address,0x71,1)
if(data[0] | 0x08) == 0:
    raise DHT20Error('Initialization error')


def getValue(bus):
    bus.write_i2c_block_data(address,0xac,[0x33,0x00])
    data = bus.read_i2c_block_data(address,0x71,7)
    Traw = ((data[3] & 0xf) << 16) + (data[4] << 8) + data[5]
    Hraw = ((data[3] & 0xf0) << 4) + (data[1] << 12) + (data[2] << 4)
    temp = 200*float(Traw)/2**20 - 50
    humi = 100*float(Hraw)/2**20
    return temp,humi

def main():
    try:
        temperature,humidity = getValue(sensor)
        print('{0:0.1f} | {1:0.1f}'.format(temperature, humidity))
    except:
        print('-1 | -1')

if __name__ == "__main__":
    main()
