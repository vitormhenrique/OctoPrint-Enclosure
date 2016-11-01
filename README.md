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

**Temperature Sensor**

You can choose to use a DHT11, DHT22, AM2302 sensor or a DS18B20.

**For the DHT11, DHT22 and AM2302 follow this steps:**

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

Than you can manually copy the scripts on your octopi rpi: 
```
mkdir -p ~/.octoprint/plugins/OctoPrint-Enclosure/extras/
cd ~/.octoprint/plugins/OctoPrint-Enclosure/extras/
wget https://raw.githubusercontent.com/vitormhenrique/OctoPrint-Enclosure/master/extras/GetHumidity.py
wget https://raw.githubusercontent.com/vitormhenrique/OctoPrint-Enclosure/master/extras/GetTemperature.py
chmod +x ~/.octoprint/plugins/OctoPrint-Enclosure/extras/GetTemperature.py
chmod +x ~/.octoprint/plugins/OctoPrint-Enclosure/extras/GetHumidity.py
```


More info on Adafruit [website](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/software-install-updated)

Note that sometimes you might see an error that the sensor can't be read even if you have your connections setup correctly. 
This is a limitation of reading DHT sensors from Linux--there's no guarantee the program will be given enough priority and time by the Linux kernel to reliably read the sensor.
This plugin will try to read enclosure temperature and humidity every 10 seconds, it will probably fail few times, but again, for the purpose this is ok.

You also need to make the provided scripts to read temperature executable.

If you have octoprint installed on the default location type:
```
chmod +x ~/.octoprint/plugins/OctoPrint-Enclosure/extras/GetTemperature.py
chmod +x ~/.octoprint/plugins/OctoPrint-Enclosure/extras/GetHumidity.py
```

**For the DS18B20 sensor:**

You need to enable your raspberry pie to use one-wire. You also NEED to use pin #4 to connect this type of sensor. 

Follow instructions on [website](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing?view=all) to connect and get the sensor working. 
After that you will need to change on the plugin settings to use the GetTemperature1820.py script to read the temperature and configure the the sensor type that you are using on this case is 1820.  You also need to make the scripts executable:

If you have octoprint installed on the default location type:

```
mkdir -p ~/.octoprint/plugins/OctoPrint-Enclosure/extras/
cd ~/.octoprint/plugins/OctoPrint-Enclosure/extras/
wget https://raw.githubusercontent.com/vitormhenrique/OctoPrint-Enclosure/master/extras/GetTemperature1820.py
chmod +x ~/.octoprint/plugins/OctoPrint-Enclosure/extras/GetTemperature1820.py
```

Note that DS18B20 sensors will not provide  information regarding humidity of the enclosure.

**wiringPi**

To use raspberry pi GPIO without needing to run octoprint as root this plugin uses [wiringPi](http://wiringpi.com)

You must install wiringPi using:


```
git clone git://git.drogon.net/wiringPi
cd wiringPi
git pull origin
cd wiringPi
./build
```

If by any change the git page is offline you can follow *Plan B* on wiringPi website.


## Configuration

Default plugin configuration uses:
Pin 4 connected to Temperature Sensor
Pin 14 connected to the relay that controls the fan
Pin 15 connected to the relay that controls the light
Pin 18 connected to the relay that controls the heater

Those settings are configurable, as well the location of the python scripts to read temperature and humidity.

You can also enable and disable features off the plugin. For example disable the heater feature.
