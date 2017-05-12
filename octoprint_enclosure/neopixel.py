import sys
import smbus
import time

if len(sys.argv) == 8:
    LED_PIN = int(sys.argv[1])
    LED_COUNT = int(sys.argv[2])
    LED_BRIGHTNESS = int(sys.argv[3])
    red = int(sys.argv[4])
    green = int(sys.argv[5])
    blue = int(sys.argv[6])
    address = int(sys.argv[7],16)
else:
    print("fail")
    sys.exit(1)

bus = smbus.SMBus(1)

data = [LED_PIN,LED_COUNT,LED_BRIGHTNESS,red,green,blue]

bus.write_i2c_block_data(address,0, data)
# bus.write_byte(address, LED_PIN)
# bus.write_byte(address, LED_COUNT)
# bus.write_byte(address, LED_BRIGHTNESS)
# bus.write_byte(address, red)
# bus.write_byte(address, green)
# bus.write_byte(address, blue)


print("ok")
