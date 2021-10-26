import sys
import smbus2
import bme280

# Rev 2 Pi, Pi 2 & Pi 3 uses bus 1
# Rev 1 Pi uses bus 0
port = 1
bus = smbus2.SMBus(port)

if len(sys.argv) == 2:
    DEVICE = int(sys.argv[1], 16)
else:
    print('-1 | -1')
    sys.exit(1)

def main():
  try:
    calibration_params = bme280.load_calibration_params(bus, DEVICE)

    # the sample method will take a single reading and return a
    # compensated_reading object
    data = bme280.sample(bus, DEVICE, calibration_params)

    print('{0:0.1f} | {1:0.1f}'.format(data.temperature, data.humidity))
  except Exception:
     print('-1 | -1')
