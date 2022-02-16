import time
import board
from adafruit_emc2101.emc2101_lut import EMC2101_LUT as EMC2101

i2c = board.I2C()  # uses board.SCL and board.SDA
FAN_MAX_RPM = 1700
emc = EMC2101(i2c)


def getTemp():
	return(emc.internal_temperature)

def getSpeed():
    return(emc.fan_speed)

def main():

	try:
		temperature = getTemp()
		fanspeed = getSpeed()
		print('{0:0.1f} | {1:0.1f}'.format(temperature, fanspeed))
	except:
		print('-1 | -1')

if __name__ == "__main__":
	main()
