# OctoPrint-Enclosure

This plugin is intended to control your printer enclosure using raspberry pi GPIO (At the moment this plugin only support raspberry pi).

You can control lights, fans and heaters of your enclosure. To use the heater you need to have a temperature sensor added to your enclosure connected to your raspberry pi.

This plugin can support DHT11, DHT22 and AM2302. They are not *very* accurate but work for the purpose.

I used relays connected to the raspberry pi to control my heaters, fan and lights.

For heating my enclosure I got a $15 [lasko](http://www.amazon.com/gp/product/B003XDTWN2?psc=1&redirect=true&ref_=oh_aui_search_detailpage) inside my encosure. I opened it and added a relay to the mains wire.

**CAUTION: VOLTAGE ON MAINS WIRE CAN KILL YOU, ONLY ATTEMPT TO DO THIS IF YOU KNOW WHAT YOU ARE DOING, AND DO AT YOUR OWN RISK**

**CAUTION 2: THIS HEATER IS NOT INTENDED TO FUNCTION THIS WAY AND IT MIGHT BE A FIRE HAZARD. DO IT AT YOUR OWN RISK**

The relays module that I used can be found [here](http://www.amazon.com/gp/product/B0057OC6D8?psc=1&redirect=true&ref_=oh_aui_search_detailpage). Those relays are active low, that means that they will turn on when you put LOW on the output of your pin. In orther to not fry your r-pi connect 3.3v to VCC, 5V to JD-VCC and Ground to GND.

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/vitormhenrique/OctoPrint-Enclosure/archive/master.zip

You need to install Adafruit library to use the temperature sensor on raspberry pi. 

Open raspberry pi terminal and type:

```
cd ~
git clone https://github.com/adafruit/Adafruit_Python_DHT.git
cd Adafruit_Python_DHT
sudo apt-get update
sudo apt-get install build-essential python-dev python-openssl
sudo python setup.py install
```

More info on Adafruit [website](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/software-install-updated)

Note that sometimes you might see an error that the sensor can't be read even if you have your connections setup correctly. 
This is a limitation of reading DHT sensors from Linux--there's no guarantee the program will be given enough priority and time by the Linux kernel to reliably read the sensor.
This plugin will try to read enclosure temperature and humidity every 10 seconds, it will probably fail few times, but again, for the purpose this is ok.

You also need to make the provided scripts to read temperature executable.

If you have octoprint installed on the default location type:
```
chmod +x ~/.octoprint/plugins/OctoPrint-Enclosure/SensorScript/GetTemperature.py
chmod +x ~/.octoprint/plugins/OctoPrint-Enclosure/SensorScript/GetHumidity.py
```

**PLEASE NOTE**
Sometimes raspbery pi don't want to obey the command to set the pin on GPIO correctly. If your relays are not working as expected try manually turning them on on terminal using: 

```
sudo su
echo **XX** > /sys/class/gpio/export 
echo out > /sys/class/gpio/gpio**XX**/direction
echo **XX** > /sys/class/gpio/gpio11/value

```

Where XX is the pin on raspberry pi.

## Configuration

Default plugin configuration uses:
Pin 4 connected to Temperature Sensor
Pin 14 connected to the relay that controls the fan
Pin 15 connected to the relay that controls the light
Pin 18 connected to the relay that controls the heater

Those settings are configurable, as well the location of the python scripts to read temperature and humidity.

You can also enable and disable features off the plugin. For example disable the heater feature.
