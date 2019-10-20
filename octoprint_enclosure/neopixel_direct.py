from rpi_ws281x import *
import sys
import time

LED_INVERT = False
LED_FREQ_HZ = 800000

if len(sys.argv) == 8:
    LED_PIN = int(sys.argv[1])
    LED_COUNT = int(sys.argv[2])
    LED_BRIGHTNESS = int(sys.argv[3])
    red = int(sys.argv[4])
    green = int(sys.argv[5])
    blue = int(sys.argv[6])
    LED_DMA = int(sys.argv[7])
else:
    print("fail")
    sys.exit(1)

strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT)
strip.begin()

color = Color(red, green, blue)

for i in range(LED_COUNT):
    strip.setPixelColor(i, color)

strip.show()

print("ok")
