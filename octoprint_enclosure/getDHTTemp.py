import sys
import adafruit_dht


# Parse command line parameters.
sensor_args =   {   
                    '11': adafruit_dht.DHT11,
                    '22': adafruit_dht.DHT22,
                    '2302': adafruit_dht.DHT22
                }

if len(sys.argv) == 3 and sys.argv[1] in sensor_args:
    sensor = sensor_args[sys.argv[1]]
    pin = sys.argv[2]
else:
    sys.exit(1)

dht_dev = sensor(pin)
humidity = dht_dev.humidity
temperature = dht_dev.temperature

if humidity is not None and temperature is not None:
    print('{0:0.1f} | {1:0.1f}'.format(temperature, humidity))
else:
    print('-1 | -1')

sys.exit(1)
