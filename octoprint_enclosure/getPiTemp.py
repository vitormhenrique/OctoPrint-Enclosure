from gpiozero import CPUTemperature

import ctypes
import struct
import sys

class PiTemp:
    def getTemp(self):
        temp = CPUTemperature()
        return '{0:0.1f}'.format(temp.temperature)
