import sys
import time
import adafruit_dht
import board 

# Parse command line parameters.
sensor_args =   {
                    '11': adafruit_dht.DHT11,
                    '22': adafruit_dht.DHT22,
                    '2302': adafruit_dht.DHT22
                }
board_args = {
        '1': board.D1,
        '2': board.D2,
        '3': board.D3,
        '4': board.D4,
        '5': board.D5,
        '6': board.D6,
        '7': board.D7,
        '8': board.D8,
        '9': board.D9,
       '10': board.D10,
       '11': board.D11,
       '12': board.D12,
       '13': board.D13,
       '14': board.D14,
        }

if len(sys.argv) == 3 and sys.argv[1] in sensor_args:
    sensor = sensor_args[sys.argv[1]]
    pin = board_args[sys.argv[2]]
else:
    sys.exit(1)

dht_dev = sensor(pin)

# DHT sensor read fails quite often, causing enclosure plugin to report value of 0.
# If this happens, retry as suggested in the adafruit_dht docs.
max_retries = 3
retry_count = 0
while retry_count <= max_retries:
    try:
        humidity = dht_dev.humidity
        temperature = dht_dev.temperature

        if humidity is not None and temperature is not None:
            print('{0:0.1f} | {1:0.1f}'.format(temperature, humidity))
            sys.exit(0)
    except RuntimeError as e:
        time.sleep(2)
        retry_count += 1
        continue
    except Exception as e:
        dht_dev.exit()
        raise e

    time.sleep(1)
    retry_count += 1

print('-1 | -1')
sys.exit(1)
