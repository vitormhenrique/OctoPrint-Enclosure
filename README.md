# OctoPrint-Enclosure

**Control pretty much everything that you might want to do on your raspberry pi / octoprint / enclosure**


Here is a list of possibilities:
* Temperature sensor on your enclosure or near your printer
* Heater on your enclosure and keep the temperature nice and high for large ABS 
* Active cooling for good PLA printing
* Mechanical buttons to pause and resume printer jobs
* Multiple filament sensors for dual or more extrusion
* Alarm when enclosure temperature reaches some sort of value

Check pictures and more information on thingiverse: http://www.thingiverse.com/thing:2245493

**Software**

Install the plugin using the Plugin Manager bundled with OctoPrint, you can search for the Enclosure plugin or just use the url: https://github.com/vitormhenrique/OctoPrint-Enclosure/archive/master.zip.

To control the encosure temperature or get temperature trigged events, you need to install and configure a temperature sensor. This plugin can support DHT11, DHT22, AM2302 and DS18B20 temperature sensors.

* For the DHT11, DHT22 and AM2302 follow this steps:

Wire the sensor following the wiring diagram on the pictures on thingiverse, you can use any GPIO pin.

For DHT11 and DHT22 sensors, don't forget to connect a 4.7K - 10K resistor from the data pin to VCC

You need to install Adafruit library to use the temperature sensor on raspberry pi.

Open raspberry pi terminal and type:

<pre><code>cd ~
git clone https://github.com/adafruit/Adafruit_Python_DHT.git
cd Adafruit_Python_DHT
sudo apt-get update
sudo apt-get install build-essential python-dev python-openssl
sudo python setup.py install</code></pre>

You can test the library by using:

<pre><code>cd examples
sudo ./AdafruitDHT.py 2302 4</code></pre>

Note that the first argument is the temperature sensor (11, 22, or 2302), and the second argument is the GPIO  that the sensor was connected.

* For the DS18B20 sensor:

Follow the wiring diagram on the pictures on thingiverse. The DS18B20 uses "1-wire" communication protocol, you need to use 4.7K to 10K resistor from the data pin to VCC, DS18B20 only works on GPIO pin number 4. You also need to add OneWire support for your raspberry pi.

Start by adding the following line to /boot/config.txt

<pre><code>dtoverlay=w1-gpio</code></pre>

You should be able to test your sensor by rebooting your system with sudo reboot. When the Pi is back up and you're logged in again, type the commands you see below into a terminal window. When you are in the 'devices' directory, the directory starting '28-' may have a different name, so cd to the name of whatever directory is there.

<pre><code>sudo modprobe w1-gpio
sudo modprobe w1-therm
cd /sys/bus/w1/devices
ls
cd 28-xxxx (change this to match what serial number pops up)
cat w1_slave</code></pre>

The response will either have YES or NO at the end of the first line. If it is yes, then the temperature will be at the end of the second line, in 1/000 degrees C.

* GPIO

This release uses RPi.GPIO to control IO of raspberry pi, it should install and work automatically. If it doesn't please update your octoprint with the latest release of octopi.

**Hardware**

You can use relays / mosfets to control you lights, heater, lockers etc... If toy want to control mains voltage I recomend using PowerSwitch Tail II.

* Relay

The relays module that I used can be found [here](https://www.amazon.com/gp/product/B0057OC6D8?psc=1&redirect=true&ref_=oh_aui_search_detailpage). Those relays are active low, that means that they will turn on when you put LOW on the output of your pin. In order to not fry your Raspberry Pi pay attention on your wiring connection: remove the jumper link and connect 3.3v to VCC, 5V to JD-VCC and Ground to GND.

* Heater

For heating my enclosure I got a $15 lasko inside my enclosure. I opened it and added a relay to the mains wire. If you’re uncomfortable soldering or dealing with high voltage, please check out the [PowerSwitch Tail II](http://www.powerswitchtail.com/Pages/default.aspx) . The PowerSwitch Tail II is fully enclosed, making it a lot safer.

**CAUTION: VOLTAGE ON MAINS WIRE CAN KILL YOU, ONLY ATTEMPT TO DO THIS IF YOU KNOW WHAT YOU ARE DOING, AND DO AT YOUR OWN RISK**

**CAUTION 2: THIS HEATER IS NOT INTENDED TO FUNCTION THIS WAY AND IT MIGHT BE A FIRE HAZARD. DO IT AT YOUR OWN RISK**

* Cooler

You can get a [5V small fan](https://www.amazon.com/gp/product/B003FO0LG6/ref=oh_aui_search_detailpage?ie=UTF8&psc=1) and control it over a relay.

* Filament sensor

You have the ability to add a filament sensor to the enclosure, it will automatically pause the print and run a gcode command to change the filament if you run out of filament, I can be any type of filament sensor, the sensor should connect to ground if is set as an "active low" when the filament run out or 3.3v if the sensor is set as "active high" when detected the end of filament, it does not matter if it is normally open or closed, that will only interfere on your wiring. I'm using the following sensor:

http://www.thingiverse.com/thing:1698397

**Configuration**

You need to enable what do you want the plugin to control.

Open the setting screen and find the plugin configuration. You can enable temperature reading and temperature control, You must select the type of sensor that you are using and the GPIO pin that is connected to.

For temperature control you can enable automatically starting up the temperature control once the print starts with a set temperature.

Outputs are meant to control anything, lights, locker, extra enclosure fans etc... You can even use a PowerSwitch Tail II and completely shut down your printer after the print job is done. You can add delays and automatically start and shutdown the GPIO. 

Inputs have basically three different types:

* Temperature
* Printer
* GPIO

Temperature inputs will control a GPIO output after a certain temperature is met. This is useful if you want to add some sort of alarm near your printer, or even build some fire extinguisher on your enclosure. Note that I'm not responsible for any damage caused by fires, you should have proper smoke detectors on your house installed by professionals.

Printer inputs will trigger Printer actions when the configured GPIO receives a signal. The actions can be Resume and Pause a print job or Change Filament. You can use the "change filament" action and set up the input GPIO according to your filament sensor, for example, if your filament sensor connects to ground when detects the end of the filament, you should choose PULL UP resistors and detect the event on the falling edge.
You can also add mechanical buttons to pause, resume and change filaments near or printer for convenience.

GPIO events will control GPIO outputs when a condition is met, for example detect a press of a button.
You can use this to control any previous configured OUTPUTS, basically being able to control your lights / fan using mechanical buttons instead of the octoprint interface.

**Road map**
There are still SOME features that I'll add to this plugin:
* Control neopixels \ dotstart
* Enable GCODE control for each setting

Let me know about improvements that you might think.

**Tab Order**

I often use more this plugin than the time lapse tab, so having the plugin appear before the timelapse is better for me.

You can do this by changing the config.yaml file as instructed on [octoprint documentation ](http://docs.octoprint.org/en/master/configuration/config_yaml.html). Unless defined differently via the command line config.yaml is located at ~/.octoprint.

You just need to add the following section:

<pre><code>appearance:
  components:
    order:
      tab:
      - temperature
      - control
      - gcodeviewer
      - terminal
      - plugin_enclosure
      - timelapse<code><pre>
