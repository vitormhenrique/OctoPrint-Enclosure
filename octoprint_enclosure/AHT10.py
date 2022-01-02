#!/usr/bin/python3
#i2cdetect -y 0
import smbus
import time
import sys

if len(sys.argv) == 3:
     DEVICE = int(sys.argv[1],16)
     bus = smbus.SMBus(int(sys.argv[2],16))
else:
    print('-1 | -1')
    sys.exit(1)


def getAll(bus,addr=DEVICE):
    #Set config
    config = [0x08, 0x00]
    bus.write_i2c_block_data(addr, 0xE1, config)
    #time.sleep(0.1)
    byt = bus.read_byte(addr)
    #Send MeasureCMD and read data
    MeasureCmd = [0x33, 0x00]
    bus.write_i2c_block_data(addr, 0xAC, MeasureCmd)
    #time.sleep(0.1)
    data = bus.read_i2c_block_data(addr,0x00)
    temp = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
    ctemp = ((temp*200) / 1048576) - 50

    hum = ((data[1] << 16) | (data[2] << 8) | data[3]) >> 4
    chum = int(hum * 100 / 1048576)
    return ctemp,chum
def main():
    try:
        temperature,humidity=getAll(bus)
        print('{0:0.1f} | {1:0.1f}'.format(temperature, humidity))
    except:
        print('-1 | -1')

if __name__=="__main__":
   main()
