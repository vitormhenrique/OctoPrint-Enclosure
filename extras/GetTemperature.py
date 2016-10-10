import sys
import Adafruit_DHT

# Parse command line parameters.
sensor_args = { '11': Adafruit_DHT.DHT11,
                '22': Adafruit_DHT.DHT22,
                '2302': Adafruit_DHT.AM2302 }
if len(sys.argv) == 3 and sys.argv[1] in sensor_args:
    sensor = sensor_args[sys.argv[1]]
    pin = sys.argv[2]
else:
    sys.exit(1)

humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

if temperature is not None:
    print '{0:0.1f}'.format(temperature)
else:
    print 'Failed'
    sys.exit(1)