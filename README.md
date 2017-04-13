# OctoPrint-Enclosure

This plugin is intended to control your printer enclosure using raspberry pi GPIO (At the moment this plugin only support raspberry pi).

You can control lights, fans and heaters, enclosure locker of your enclosure. You can also add events that should be trigged on certain especific cases.
Cases can be a certain temperature reach, an GPIO falling or rising or end of fillament detection

## Temperature Sensor

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

More info on Adafruit [website](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/software-install-updated)

Note that sometimes you might see an error that the sensor can't be read even if you have your connections setup correctly.
This is a limitation of reading DHT sensors from Linux--there's no guarantee the program will be given enough priority and time by the Linux kernel to reliably read the sensor.
This plugin will try to read enclosure temperature and humidity every 10 seconds, it will probably fail few times, but again, for the purpose this is ok.

**For the DS18B20 sensor:**

You need to enable your raspberry pie to use one-wire. You also NEED to use pin #4 to connect this type of sensor.

Follow instructions on [website](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing?view=all) to connect and get the sensor working.
After that you will need to change on the plugin settings to use the GetTemperature1820.py script to read the temperature and configure the the sensor type that you are using on this case is 1820.  You also need to make the scripts executable:

Note that DS18B20 sensors will not provide  information regarding humidity of the enclosure.

## Temperature Control

To enable temperature control, you need to have a temperature sensor added to your enclosure connected to your raspberry pi.
Temperature control can be a heater or a cooler.

## Raspberry Pi Outputs

Outputs will create buttons on the enclosure tab that will control gpio pins, here your imagination is the limit.
You can use relays or mosfets connected to the raspberry pi to control fans, lights or anything else.

## Raspberry Pi Inputs

Inputs are events that will trigger actions based on the configuration

**Temperature:**

You can add events that should be triggered when the enclosure temperature reaches a certain temperature, this is particularly helpful for a little extra safety, so you can add an alarm light, turn off the printer, or even try to build some sort of fire extinguisher.

**CAUTION: DO NOT RELY ON THIS PLUGIN AS PRIMARY FIRE DETECTION, YOU NEED TO HAVE PROPER SMOKE DETECTORS ON YOUR HOUSE**

**Filament sensor:**

You have the hability to add a filament sensor to the enclosure, it will automatically pause the print if you run out of filament, I can be any type of filament sensor, the sensor should connect to ground if is set as an "active low" when the fillament run out or 3.3v if the sensor is set as "active high" when detected the end of filament, it does not matter if it is normally open or closed, that will only interfere on your wiring. I'm using the following sensor:

http://www.thingiverse.com/thing:1698397

**GPIO:**

Last type of events are GPIO, you can control outputs based on input, this is helpfull if you want to add buttons to your enclosure to turn on and off lights, fans, etc. After the button is pressed it thrigger the event and will keep that signal.


## General Information

I used relays connected to the raspberry pi to control my heaters, fan and lights.

For heating my enclosure I got a $15 [lasko](http://www.amazon.com/gp/product/B003XDTWN2?psc=1&redirect=true&ref_=oh_aui_search_detailpage) inside my encosure. I opened it and added a relay to the mains wire.  If you’re uncomfortable soldering or dealing with high voltage, please check out the [PowerSwitch Tail II](http://www.powerswitchtail.com/Pages/default.aspx). The PowerSwitch Tail II is fully enclosed, making it a lot safer.

**CAUTION: VOLTAGE ON MAINS WIRE CAN KILL YOU, ONLY ATTEMPT TO DO THIS IF YOU KNOW WHAT YOU ARE DOING, AND DO AT YOUR OWN RISK**

**CAUTION 2: THIS HEATER IS NOT INTENDED TO FUNCTION THIS WAY AND IT MIGHT BE A FIRE HAZARD. DO IT AT YOUR OWN RISK**

The relays module that I used can be found [here](http://www.amazon.com/gp/product/B0057OC6D8?psc=1&redirect=true&ref_=oh_aui_search_detailpage). Those relays are active low, that means that they will turn on when you put LOW on the output of your pin. In orther to not fry your r-pi connect 3.3v to VCC, 5V to JD-VCC and Ground to GND.

**GPIO Library**
This release uses RPi.GPIO to control IO of raspberry pi, it should install and work automatically. If it doesn't please update your octoprint with the latest release of octopi.
