#!/usr/bin/env python3
import minimalmodbus

## setup ##
 # port name, slave address (in decimal)
novus = minimalmodbus.Instrument('/dev/ttyACM0', 1) 
# for Novus 1040 comms documentation see:
# https://www.novusautomation.com/downloads/Arquivos/communication_protocol_n1040_v20x_c_en.pdf
novus.serial.baudrate = 115200
REG_ADDR = {
    'Active SP': 0,
    'PV': 1,
    'dppo': 73
}
## Read decimal point precision setting ##
DP = 3 - novus.read_register(REG_ADDR['dppo'], 0)
#print(f'decimal places: {DP}')
## set up complete ##

class NovusTemp:
    def getTemp(self):
        temperature = novus.read_register(REG_ADDR['PV'], DP)
        return '{0:0.1f}'.format(temperature)
