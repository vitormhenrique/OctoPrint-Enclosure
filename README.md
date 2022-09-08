Find the plugin useful? Buy me a coffee
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/VitorHenrique/2)

# THIS PLUGIN IS DEPRACATED! 
I'm moving away from it, and when ready the replacement plugin would be here: https://github.com/vitormhenrique/OctoPrint-Enclosure-V2

# Before opening an issue...

Check the [troubleshooting guide](https://github.com/vitormhenrique/OctoPrint-Enclosure/wiki/Troubleshooting-Guide). Issues with no log, no print screen *will be closed* until the necessary documentation is available.

Also, be aware that upgrading from versions lower than 4.00 will **DELETE** all settings. More information on [release notes](https://github.com/vitormhenrique/OctoPrint-Enclosure/releases/tag/4.00)

# OctoPrint-Enclosure

**Control pretty much everything that you might want to do on your raspberry pi / octoprint / enclosure**

Here is a list of possibilities:
* Add temperature sensors on your enclosure or near your printer
* Add active heaters on your enclosure and keep the temperature nice and high for large ABS 
* PWM controlled outputs
* PWM controlled outputs based on temperature sensor
* Active cooling for good PLA printing
* Schedule GPIO's to turn on and off with a fixed period of time during printing.
* Mechanical buttons to pause and resume printer jobs
* Mechanical buttons to send GCODE to the printer
* Mechanical buttons to control raspberry pi GPIO
* Multiple filament sensors for dual or more extruders
* Alarm when enclosure temperature reaches some sort of value
* Notifications using IFTTT when events happen (temperature trigger / print events / etc)
* Add sub-menus on navbar to quick access outputs and temperature sensors

Check pictures on thingiverse: http://www.thingiverse.com/thing:2245493

## Installation

Install the plugin using the Plugin Manager bundled with OctoPrint, you can search for the Enclosure plugin or just use the url: https://github.com/vitormhenrique/OctoPrint-Enclosure/archive/master.zip.

## Hardware

This plugin support many hardware temperature sensors, led, relays, heater...

Here are detailled instructions on how to setup them.

### Temperature sensors

To control the enclosure temperature or get temperature triggered events, you need to install and configure a temperature sensor. This plugin can support DHT11, DHT22, AM2302, DS18B20, SI7021, BME280 and TMP102 temperature sensors.


#### DHT11, DHT22 and AM2302 sensors

Wire the sensor following the wiring diagram on the pictures on thingiverse; you can use any GPIO pin.

For DHT11 and DHT22 sensors, don't forget to connect a 4.7K - 10K resistor from the data pin to VCC. Also, be aware that DHT sensors some times can not work reliably on linux, this is a limitation of reading DHT sensors from Linux--there's no guarantee the program will be given enough priority and time by the Linux kernel to reliably read the sensor. Another common issue is the power supply. you need a constant and good 3.3V, sometimes a underpowered raspberry pi will not have a solid 3.3V power supply, so you could try powering the sensor with 5V and using a level shifter on the read pin.

You need to install the Adafruit library to use the temperature sensor on Raspberry Pi. Recent versions of this plugin have moved to supporting the CircuitPython-based library on Python3 installed below.

Open a raspberry pi terminal and type:

```
pip3 install adafruit-circuitpython-dht
sudo apt-get update
sudo apt-get install libgpiod2 -y
```

This will install all requirements of the library.

You can test the library by using the sample code from https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup.

#### DS18B20 sensor

Follow the wiring diagram on the pictures on thingiverse. The DS18B20 uses "1-wire" communication protocol, DS18B20 only works on GPIO pin number 4 by default. You also need to add OneWire support for your raspberry pi.

Start by enabling 1-wire support, [follow this tutorial](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/ds18b20).

After rebooting, you can check if the OneWire device was found properly with
```
dmesg | grep onewire
```

You should see something like
```
[    5.216899] gpio-4 (onewire@0): enforced open drain please flag it properly in DT/ACPI DSDT/board file
```

If you're using the internal pullup resistor, you'll need to enable it manually by running these Python commands. Or, you can simply configure the sensor inside of the Enclosure plugin, which will do this for you.

You should be able to test your sensor by rebooting your system with `sudo reboot`. When the Pi is back up and you're logged in again, type the commands you see below into a terminal window. When you are in the 'devices' directory, the directory starting '28-' may have a different name, so `cd` to the name of whatever directory is there.

```
sudo modprobe w1-gpio
sudo modprobe w1-therm
cd /sys/bus/w1/devices
ls
cd 28-xxxx (change this to match what serial number pops up)
cat w1_slave
```

The response will either have `YES` or `NO` at the end of the first line. If it is `YES`, then the temperature will be at the end of the second line, in 1/000 degrees C.

Copy the serial number, you will need to configure the plugin.  Note that for the serial number includes the `28-`, for example `28-0000069834ff`.

The DS18B20 needs a pullup resistor on the data pin. On modern Pi models, you can use a resistor built into the Pi, configured in software. To do this, set the "Input Pull Resistor" option to "Input Pullup". If this doesn't work, you need to use a 4.7K to 10K resistor from the data pin to VCC.

#### SI7021, BME280, TMP102 and MCP9808 sensors

Enable I2C on your raspberry pi, depending on raspi-config version, step by step can be different:

```
sudo raspi-config
```
* Use the down arrow to select 9 Advanced Options
* Arrow down to A7 I2C
* Select yes when it asks you to enable I2C
* Also select yes when it asks about automatically loading the kernel module
* Use the right arrow to select the button
* Select yes when it asks to reboot

Install some packages (on raspberry pi system python not octoprint virtual environment):

```
sudo apt-get install i2c-tools python-pip python-smbus
```

Find the address of the sensor:

```
i2cdetect -y 1
```

### Neopixel

If your setup does not have pip install pip:
`sudo apt-get install python-pip`

Install the required library:
`sudo pip install rpi_ws281x`

rpi_ws281x really needs sudo, and you need to setup up so your rpi does not ask for a password when runing a python script, so run:

`sudo visudo`

and add `pi ALL=(ALL) NOPASSWD: ALL` to the end of the file.

Also backlist the audio kernel:

`sudo nano /etc/modprobe.d/snd-blacklist.conf`

add the `blacklist snd_bcm2835` to the end of the file.

### GPIO

This release uses RPi.GPIO to control IO of raspberry pi, it should install and work automatically. If it doesn't please update your octoprint with the latest release of octopi.
You can use relays / mosfets to control you lights, heater, lockers etc... If you want to control mains voltage I recommend using [PowerSwitch Tail II](http://www.powerswitchtail.com/).

### Relay

The relays module that I used couple [SainSmart 2-Channel Relay Module](https://www.amazon.com/gp/product/B0057OC6D8?ie=UTF8&tag=3dpstuff-20&camp=1789&linkCode=xm2&creativeASIN=B0057OC6D8). Those relays are active low, that means that they will turn on when you put LOW on the output of your pin. In order to not fry your Raspberry Pi pay attention on your wiring connection: remove the jumper link and connect 3.3v to VCC, 5V to JD-VCC and Ground to GND.

### Heater

For heating my enclosure I got a $15 lasko inside my enclosure. I opened it and added a relay to the mains wire. If you’re uncomfortable soldering or dealing with high voltage, please check out the [PowerSwitch Tail II](http://www.powerswitchtail.com/). It is fully enclosed, making it a lot safer.

**CAUTION: VOLTAGE ON MAINS WIRE CAN KILL YOU, ONLY ATTEMPT TO DO THIS IF YOU KNOW WHAT YOU ARE DOING, AND DO AT YOUR OWN RISK**

**CAUTION 2: THIS HEATER IS NOT INTENDED TO FUNCTION THIS WAY AND IT MIGHT BE A FIRE HAZARD. DO IT AT YOUR OWN RISK**

### Cooler

You can get a [USB Mini Desktop Fan](https://www.amazon.com/gp/product/B00WM7TRTY?ie=UTF8&tag=3dpstuff-20&camp=1789&linkCode=xm2&creativeASIN=B00WM7TRTY) and control it over a relay.

### Filament sensor

You have the ability to add a filament sensor to the enclosure, it will automatically pause the print and run a gcode command to change the filament if you run out of filament, I can be any type of filament sensor, the sensor should connect to ground if is set as an "active low" when the filament run out or 3.3v if the sensor is set as "active high" when detected the end of filament, it does not matter if it is normally open or closed, that will only interfere on your wiring. I'm using the following sensor:

http://www.thingiverse.com/thing:1698397

## Plugin configuration

You need to enable what do you want the plugin to control. Settings from plugin version < 3.6 are not compatible anymore, you will loose all settings after upgrading the plugin.

There are mainly two types of configuration on the plugin, Inputs and Outputs.

Outputs are meant to control THINGS (temperature, lights, locker, extra enclosure fans etc...) You can even use a PowerSwitch Tail II and completely shut down your printer after the print job is done. 

Outputs can be set to the following types:

* Regular GPIO
* PWM GPIO
* Neopixel Control via Microcontroler
* Neopixel Control directly from raspberry pi
* Temperature and Humidity Control
* Temperature Alarm
* Gcode Output

Most outputs create UI elements on enclosure plugin tab that let you set values / turn on or off gpios etc. You have the ability to automatically turn on or off outputs when the printer starts or finishes. You can even specify a hour on HH:MM 24 hour format, events will only be schedule when the print starts, and will only be triggered for the very next time that hour occur.

Temperature Alarm will control another GPIO output after a certain temperature is met. This is useful if you want to add some sort of alarm near your printer, or even build some fire extinguisher on your enclosure. Note that I'm not responsible for any damage caused by fires, you should have proper smoke detectors on your house installed by professionals.

Inputs are methods that trigger actions or input values to the plugin (temperature sensor, GPIO trigger)

Inputs can be of two different types:

* Temperature Sensors
* GPIO

Temperature Sensors will be used to input temperature and humidity data, they can be linked to a especial output like temperature control and temperature alarm.

GPIO inputs will trigger events for the plugin, this feature can be used to add buttons to the enclosure and cause pressing those buttons to act on the printer or other pre-configured outputs.

After selecting GPIO for the input type, and selecting output control on the action type, the button will be able to turn on / off or toggle linked regular_gpio outputs, basically being able to control your lights / fan using mechanical buttons instead of the octoprint interface. You can also use buttons to send g-code commands.

Selecting print control on the action type will trigger printer actions when the configured GPIO receives a signal. The actions can be Resume and Pause a print job or Change Filament. You can use the "change filament" action and set up the input GPIO according to your filament sensor, for example, if your filament sensor connects to ground when detects the end of the filament, you should choose PULL UP resistors and detect the event on the falling edge.
You can also add mechanical buttons to pause, resume and change filaments near your printer for convenience.

## Advanced Area

If you want to enable notifications check the following [issue](https://github.com/vitormhenrique/OctoPrint-Enclosure/issues/36)

You can control outputs using a simple [API](https://github.com/vitormhenrique/OctoPrint-Enclosure/wiki/API-Control)

Or use [g-code](https://github.com/vitormhenrique/OctoPrint-Enclosure/wiki/G-CODE-Control) commands

### Tab Order

I often use more this plugin than the time-lapse  tab, so having the plugin appear before the timelapse is better for me.

You can do this by changing the config.yaml file as instructed on [octoprint documentation ](http://docs.octoprint.org/en/master/configuration/config_yaml.html). Unless defined differently via the command line config.yaml is located at `~/.octoprint`.

You just need to add the following section:

```
appearance:
  components:
    order:
      tab:
      - temperature
      - control
      - gcodeviewer
      - terminal
      - plugin_enclosure
```
