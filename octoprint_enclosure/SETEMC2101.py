import sys
import board
from adafruit_emc2101.emc2101_lut import EMC2101_LUT as EMC2101

i2c = board.I2C()  # uses board.SCL and board.SDA
FAN_MAX_RPM = 1700
emc = EMC2101(i2c)


 

def main():
	# total arguments
	n = len(sys.argv)
	if n != 2:
		print("No_duty_cycle_specified")
		sys.exit(2) 

	dutyCycle=int(sys.argv[1])
	emc.manual_fan_speed = dutyCycle

if __name__ == "__main__":
	main()
