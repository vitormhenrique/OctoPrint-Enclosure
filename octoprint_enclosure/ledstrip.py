"""
copyright 2017 Tim Richardson, github profile: https://github.com/GeekyTim

This file is part of https://github.com/GeekyTim/Open-Smart-RGB-LED-Strip-Driver-for-Raspberry-Pi
Open-Smart-RGB-LED-Strip-Driver-for-Raspberry-Pi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Open-Smart-RGB-LED-Strip-Driver-for-Raspberry-Pi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Open-Smart-RGB-LED-Strip-Driver-for-Raspberry-Pi. If not, see <http://www.gnu.org/licenses/>.


LEDStrip Class
--------------
A Python class that drives the Open-Smart RGB LED Strip from a Raspberry Pi.
Hardware Obtained from http://www.dx.com/p/full-color-rgb-led-strip-driver-module-for-arduino-blue-black-314667

Code originally developed by Philip Leder (https://github.com/schlank/Catalex-Led-Strip-Driver-Raspberry-Pi)

Pin Connections
Choose any two GPIO Pins; one to provide the Clock signal (CLK), the other the Data (DAT)

Pi    Open-Smart Controller
Gnd   Gnd
+5v   Vcc
DAT   Din
CLK   Cin

Place this file in the same directory as your code.
In your code, import the file:
    from ledstrip import LEDStrip

Create a new LED Strip which uses your chosen pins (CLK and DAT) with, e.g.:
    CLK = 17
    DAT = 18
    strip = LEDStrip(CLK, DAT)

Set the colour of the LED strip with
    strip.setcolor(red, green, blue):

The following methods are public:
    setcolourrgb(r, g, b) - Sets the LED strip to colour rgb where r, g, b are in the range 0 to 255
    setcolourwhite() - Sets the strip to white
    setcolourred() - Sets the strip to Red
    setcolourgreen() - Sets the strip to Green
    setcolourblue() - Sets the strip to Blue
    setcolouroff() - Turns the strip off
    setcolourhex('hex') - Sets the LED strip to the hex colour 'hex' in range '000000' to 'FFFFFF'
"""

import time
import RPi.GPIO as GPIO


class LEDStrip:
    def __init__(self, clock, data):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        self.__clock = clock
        self.__data = data
        self.__delay = 0
        GPIO.setup(self.__clock, GPIO.OUT)
        GPIO.setup(self.__data, GPIO.OUT)

    def __sendclock(self):
        GPIO.output(self.__clock, False)
        time.sleep(self.__delay)
        GPIO.output(self.__clock, True)
        time.sleep(self.__delay)

    def __send32zero(self):
        for x in range(32):
            GPIO.output(self.__data, False)
            self.__sendclock()

    def __senddata(self, dx):
        self.__send32zero()
        for x in range(32):
            if ((dx & 0x80000000) != 0):
                GPIO.output(self.__data, True)
            else:
                GPIO.output(self.__data, False)
            dx <<= 1
            self.__sendclock()
        self.__send32zero()

    def __getcode(self, dat):
        tmp = 0
        if ((dat & 0x80) == 0):
            tmp |= 0x02
        if ((dat & 0x40) == 0):
            tmp |= 0x01
        return tmp

    def setcolourrgb(self, red, green, blue):
        dx = 0
        dx |= 0x03 << 30
        dx |= self.__getcode(blue)
        dx |= self.__getcode(green)
        dx |= self.__getcode(red)

        dx |= blue << 16
        dx |= green << 8
        dx |= red

        self.__senddata(dx)

    def setcolourwhite(self):
        self.setcolourrgb(255, 255, 255)

    def setcolouroff(self):
        self.setcolourrgb(0, 0, 0)

    def setcolourred(self):
        self.setcolourrgb(255, 0, 0)

    def setcolourgreen(self):
        self.setcolourrgb(0, 255, 0)

    def setcolourblue(self):
        self.setcolourrgb(0, 0, 255)

    def setcolourhex(self, hex):
        print('Hex')
        try:
            hexcolour = int(hex, 16)
            red = int((hexcolour & 255 * 255 * 255) / (255 * 255))
            green = int((hexcolour & 255 * 255) / 255)
            blue = hexcolour & 255
            self.setcolourrgb(red, green, blue)
        except:
            hexcolour = 0
            print("Error converting Hex input (%s) a colour." % hex)

    def cleanup(self):
        self.setcolouroff()
        GPIO.cleanup()