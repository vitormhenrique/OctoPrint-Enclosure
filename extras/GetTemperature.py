#!/usr/bin/python
import sys
import Adafruit_DHT
import os
import glob
import time


# Parse command line parameters.
sensor_args = {'11': Adafruit_DHT.DHT11, '22': Adafruit_DHT.DHT22, '2302': Adafruit_DHT.AM2302}

if len(sys.argv) == 3 and sys.argv[1] in sensor_args:
    sensor = sensor_args[sys.argv[1]]
    pin = sys.argv[2]
    isDHTSensor = True
elif len(sys.argv) == 2 and sys.argv[1] == '1820':
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')
    base_dir = '/sys/bus/w1/devices/'
    device_folder = glob.glob(base_dir + '28*')[0]
    device_file = device_folder + '/w1_slave'
    isDHTSensor = False
else:
    sys.exit(1)


def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c


def read_dht_temp():
    hum, temp = Adafruit_DHT.read_retry(sensor, pin)
    return temp

if isDHTSensor = True:
    temperature = read_dht_temp()
    if temperature is not None:
        print '{0:0.1f}'.format(temperature)
    else:
        print 'Failed'
        sys.exit(1)
else:
    temperature = read_temp()
    print '{0:0.1f}'.format(temperature)
    sys.exit(1)
