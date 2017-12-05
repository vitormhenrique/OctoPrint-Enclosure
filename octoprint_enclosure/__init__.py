# coding=utf-8
from __future__ import absolute_import
from octoprint.events import eventManager, Events
from octoprint.util import RepeatedTimer
from subprocess import Popen, PIPE
import octoprint.plugin
import RPi.GPIO as GPIO
import flask
import sched
import time
import sys
import glob
import os
import datetime
import octoprint.util
import requests

scheduler = sched.scheduler(time.time, time.sleep)

class EnclosurePlugin(octoprint.plugin.StartupPlugin,
            octoprint.plugin.TemplatePlugin,
            octoprint.plugin.SettingsPlugin,
            octoprint.plugin.AssetPlugin,
            octoprint.plugin.BlueprintPlugin,
            octoprint.plugin.EventHandlerPlugin):

    previousTempControlStatus = False
    currentTempControlStatus = False
    enclosureSetTemperature=0.0
    enclosureCurrentTemperature=0.0
    enclosureCurrentHumidity=0.0
    lastFilamentEndDetected=0
    temperature_reading = []
    temperature_control = []
    rpi_outputs = []
    rpi_inputs = []
    previous_rpi_outputs = []
    notifications = []

    PWM_INSTANCES = []
    disable_temeprature_log = True

    def startTimer(self):
        self._checkTempTimer = RepeatedTimer(10, self.checkEnclosureTemp, None, None, True)
        self._checkTempTimer.start()

    def toFloat(self, value):
        try:
            val = float(value)
            return val
        except:
            return 0

    def toInt(self, value):
        try:
            val = int(value)
            return val
        except:
            return 0

    #~~ StartupPlugin mixin
    def on_after_startup(self):

        self.PWM_INSTANCES = []
        self.temperature_reading = self._settings.get(["temperature_reading"])
        self.temperature_control = self._settings.get(["temperature_control"])
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.notifications = self._settings.get(["notifications"])
        self.fixData()
        self.previous_rpi_outputs = []
        self.startTimer()
        self.startGPIO()
        # self.clearGPIO()
        self.configureGPIO()
        self.updateOutputUI()

    #~~ Blueprintplugin mixin
    @octoprint.plugin.BlueprintPlugin.route("/setEnclosureTemperature", methods=["GET"])
    def setEnclosureTemperature(self):
        self.enclosureSetTemperature = flask.request.values["enclosureSetTemp"]
        if self._settings.get(["debug"]) == True:
            self._logger.info("DEBUG -> Seting enclosure temperature: %s",self.enclosureSetTemperature)
        self.handleTemperatureControl()
        return flask.jsonify(enclosureSetTemperature=self.enclosureSetTemperature,enclosureCurrentTemperature=self.enclosureCurrentTemperature)

    @octoprint.plugin.BlueprintPlugin.route("/getEnclosureSetTemperature", methods=["GET"])
    def getEnclosureSetTemperature(self):
        return str(self.enclosureSetTemperature)

    @octoprint.plugin.BlueprintPlugin.route("/clearGPIOMode", methods=["GET"])
    def clearGPIOMode(self):
        GPIO.cleanup()
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/getUpdateBtnStatus", methods=["GET"])
    def getUpdateBtnStatus(self):
        self.updateOutputUI()
        return flask.make_response("Ok.", 200)

    @octoprint.plugin.BlueprintPlugin.route("/getOutputStatus", methods=["GET"])
    def getOutputStatus(self):
        getOutputStatusresult = ''
        
        for rpi_output in self.rpi_outputs:
            pin = self.toInt(rpi_output['gpioPin'])
            if rpi_output['outputType']=='regular':
                val = GPIO.input(pin) if not rpi_output['activeLow'] else (not GPIO.input(pin))
             if (not getOutputStatusresult)
                    getOutputStatusresult = getOutputStatusresult + ', '
                getOutputStatusresult = getOutputStatusresult + '"' + str(pin) + '":' + str(val)
                
        return '{' + getOutputStatusresult + '}'


    @octoprint.plugin.BlueprintPlugin.route("/getTest", methods=["GET"])
    def getTest(self):
        return flask.jsonify(success=True)
    

    @octoprint.plugin.BlueprintPlugin.route("/getEnclosureTemperature", methods=["GET"])
    def getEnclosureTemperature(self):
        return str(self.enclosureCurrentTemperature)

    @octoprint.plugin.BlueprintPlugin.route("/setIO", methods=["GET"])
    def setIO(self):
        io = flask.request.values["io"]
        value = True if flask.request.values["status"] == "on" else False
        for rpi_output in self.rpi_outputs:
            if self.toInt(io) == self.toInt(rpi_output['gpioPin']):
                val = (not value) if rpi_output['activeLow'] else value
                self.writeGPIO(self.toInt(io), val)
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setPWM", methods=["GET"])
    def setPWM(self):
        io = flask.request.values["io"]
        pwmVal = flask.request.values["pwmVal"]
        self.writePWM(self.toInt(io),self.toInt(pwmVal))
        return flask.make_response("Ok.", 200)

    @octoprint.plugin.BlueprintPlugin.route("/setNeopixel", methods=["GET"])
    def setNeopixel(self):
        io = flask.request.values["io"]
        red = flask.request.values["red"]
        green = flask.request.values["green"]
        blue = flask.request.values["blue"]
        for rpi_output in self.rpi_outputs:
            if self.toInt(io) == self.toInt(rpi_output['gpioPin']) and rpi_output['outputType']=='neopixel':
                ledCount = rpi_output['neopixelCount']
                ledBrightness = rpi_output['neopixelBrightness']
                address = rpi_output['microAddress']
                self.sendNeopixelCommand(io,ledCount,ledBrightness,red,green,blue,address)
        return flask.make_response("Ok.", 200)

    #~~ Plugin Internal methods
    def fixData(self):
        for rpi_output in self.rpi_outputs:
            if not 'outputType' in rpi_output:
                rpi_output['outputType'] = 'regular'
            if not 'frequency' in rpi_output:
                rpi_output['frequency'] = 50
            if not 'dutycycle' in rpi_output:
                rpi_output['dutycycle'] = 0
            if not 'color' in rpi_output:
                rpi_output['color'] = 'rgb(255,0,0)'
            if not 'neopixelCount' in rpi_output:
                rpi_output['neopixelCount'] = 0
            if not 'microAddress' in rpi_output:
                rpi_output['microAddress'] = 0
            if not 'neopixelBrightness' in rpi_output:
                rpi_output['neopixelBrightness'] = 255

        for temp_reader in self.temperature_reading:
            if not 'sensorAddress' in temp_reader:
                temp_reader['sensorAddress'] = 0

        self._settings.set(["rpi_outputs"],self.rpi_outputs)
        self._settings.set(["temperature_reading"],self.temperature_reading)

    def sendNeopixelCommand(self,ledPin,ledCount,ledBrightness,red,green,blue,address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/neopixel.py "
            cmd ="sudo python " +script +str(ledPin)+" "+str(ledCount)+" "+str(ledBrightness)+" "+str(red)+" "+str(green)+" "+str(blue)+" "+str(address)
            if self._settings.get(["debug"]) == True:
                self._logger.info("Sending neopixel cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
        except Exception as ex:
            template = "An exception of type {0} occurred on sendNeopixelCommand. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def checkEnclosureTemp(self):
        try:
            for temp_reader in self.temperature_reading:
                if temp_reader['isEnabled']:
                    if temp_reader['sensorType'] in ["11", "22", "2302"]:
                        self._logger.info("sensorType dht")
                        temp, hum = self.readDhtTemp(temp_reader['sensorType'],temp_reader['gpioPin'])
                    elif temp_reader['sensorType'] == "18b20":
                        temp = self.read18b20Temp()
                        hum = 0
                    elif temp_reader['sensorType'] == "bme280":
                        temp, hum = self.readBME280Temp(temp_reader['sensorAddress'])
                    elif temp_reader['sensorType'] == "si7021":
                        temp, hum = self.readSI7021Temp(temp_reader['sensorAddress'])
                    elif temp_reader['sensorType'] == "tmp102":
                        temp = self.readTmp102Temp(temp_reader['sensorAddress'])
                        hum = 0
                    else:
                        self._logger.info("sensorType no match")
                        temp = 0
                        hum = 0

                    if temp != -1 and hum != -1:
                        self.enclosureCurrentTemperature = round(self.toFloat(temp),1) if not temp_reader['useFahrenheit'] else round(self.toFloat(temp)*1.8 + 32,1)
                        self.enclosureCurrentHumidity = round(self.toFloat(hum),1)

                    if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                        self._logger.info("Temperature: %s humidity %s", self.enclosureCurrentTemperature,self.enclosureCurrentHumidity)

                    self._plugin_manager.send_plugin_message(self._identifier, dict(enclosuretemp=self.enclosureCurrentTemperature,enclosureHumidity=self.enclosureCurrentHumidity))
                    self.handleTemperatureControl()
                    self.handleTemperatureEvents()
        except Exception as ex:
            template = "An exception of type {0} occurred on checkEnclosureTemp. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def handleTemperatureEvents(self):
        for rpi_input in self.rpi_inputs:
            if self.toFloat(rpi_input['setTemp']) == 0:
                continue
            if rpi_input['eventType']=='temperature' and (self.toFloat(rpi_input['setTemp']) < self.toFloat(self.enclosureCurrentTemperature)):
                for rpi_output in self.rpi_outputs:
                    if self.toInt(rpi_input['controlledIO']) == self.toInt(rpi_output['gpioPin']):
                        val = GPIO.LOW if rpi_output['activeLow'] else GPIO.HIGH
                        self.writeGPIO(self.toInt(rpi_output['gpioPin']), val)
                        for notification in self.notifications:
                            if notification['temperatureAction']:
                                msg = "Temperature action: enclosure temperature exceed " +rpi_input['setTemp']
                                self.sendNotification(msg)

    def readDhtTemp(self,sensor,pin):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/getDHTTemp.py "
            cmd ="sudo python " +script+str(sensor)+" "+str(pin)
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("Temperature dht cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("Dht result: %s", stdout)
            temp,hum = stdout.split("|")
            return (self.toFloat(temp.strip()),self.toFloat(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on readDhtTemp. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def readBME280Temp(self,address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/BME280.py "
            cmd ="sudo python " +script +str(address)
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("Temperature BME280 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("BME280 result: %s", stdout)
            temp,hum = stdout.split("|")
            return (self.toFloat(temp.strip()),self.toFloat(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on readBME280Temp. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def readSI7021Temp(self,address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/SI7021.py "
            cmd ="sudo python " +script +str(address)
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("Temperature SI7021 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("SI7021 result: %s", stdout)
            temp,hum = stdout.split("|")
            return (self.toFloat(temp.strip()),self.toFloat(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on readSI7021Temp. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def read18b20Temp(self):
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')

        lines = self.readraw18b20Temp()
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = self.readraw18b20Temp()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            return '{0:0.1f}'.format(temp_c)
        return 0

    def readraw18b20Temp(self):
        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines

    def readTmp102Temp(self, address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/tmp102.py"
            args = ["python", script, str(address)]
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("Temperature TMP102 cmd: %s", " ".join(args))
            proc = Popen(args, stdout=PIPE)
            stdout, _ = proc.communicate()
            if self._settings.get(["debug"]) == True and not self.disable_temeprature_log:
                self._logger.info("TMP102 result: %s", stdout)
            return self.toFloat(stdout.strip())
        except Exception as ex:
            template = "An exception of type {0} occurred on readTmp102Temp. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            return 0


    def handleTemperatureControl(self):
        for control in self.temperature_control:
            if control['isEnabled'] == True:
                if control['controlType'] == 'heater':
                    self.currentTempControlStatus = self.toFloat(self.enclosureCurrentTemperature)<self.toFloat(self.enclosureSetTemperature)
                else:
                    if self.toFloat(self.enclosureSetTemperature) == 0:
                        self.currentTempControlStatus = False
                    else:
                        self.currentTempControlStatus = self.toFloat(self.enclosureCurrentTemperature)>self.toFloat(self.enclosureSetTemperature)
                if self.currentTempControlStatus != self.previousTempControlStatus:
                    if self.currentTempControlStatus:
                        self._logger.info("Turning gpio to control temperature on.")
                        val =  False if control['activeLow'] else True
                        self.writeGPIO(self.toInt(control['gpioPin']),val)
                    else:
                        self._logger.info("Turning gpio to control temperature off.")
                        val = True if control['activeLow'] else False
                        self.writeGPIO(self.toInt(control['gpioPin']), val)
                    self.previousTempControlStatus = self.currentTempControlStatus

    def startGPIO(self):
        try:
            currentMode = GPIO.getmode()
            setMode = GPIO.BOARD if self._settings.get(["useBoardPinNumber"]) else GPIO.BCM
            if currentMode == None:
                GPIO.setmode(setMode)
                tempstr = "BOARD" if setMode == GPIO.BOARD else "BCM"
                self._logger.info("Setting GPIO mode to %s",tempstr)
            elif currentMode != setMode:
                GPIO.setmode(currentMode)
                tempstr = "BOARD" if currentMode == GPIO.BOARD else "BCM"
                self._settings.set(["useBoardPinNumber"],True if currentMode == GPIO.BOARD else False)
                warn_msg = "GPIO mode was configured before, GPIO mode will be forced to use: " + tempstr + " as pin numbers. Please update GPIO accordingly!"
                self._logger.info(warn_msg)
                self._plugin_manager.send_plugin_message(self._identifier,dict(isMsg=True,msg=warn_msg))
            GPIO.setwarnings(False)
        except Exception as ex:
            template = "An exception of type {0} occurred on startGPIO. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def clearGPIO(self):
        try:
            for control in self.temperature_control:
                if control['isEnabled']:
                    GPIO.cleanup(self.toInt(control['gpioPin']))
            for rpi_output in self.rpi_outputs:
                if self.toInt(rpi_output['gpioPin']) not in self.previous_rpi_outputs:
                    GPIO.cleanup(self.toInt(rpi_output['gpioPin']))
            for rpi_input in self.rpi_inputs:
                try:
                    GPIO.remove_event_detect(self.toInt(rpi_input['gpioPin']))
                except:
                    pass
                GPIO.cleanup(self.toInt(rpi_input['gpioPin']))
        except Exception as ex:
            template = "An exception of type {0} occurred on clearGPIO. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def clearChannel(self,channel):
        try:
            GPIO.cleanup(self.toInt(channel))
        except Exception as ex:
            template = "An exception of type {0} occurred on clearChannel. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def configureGPIO(self):
        try:
            for control in self.temperature_control:
                if control['isEnabled']:
                    GPIO.setup(self.toInt(control['gpioPin']), GPIO.OUT, initial=GPIO.HIGH if control['activeLow'] else GPIO.LOW)
            for rpi_output in self.rpi_outputs:
                pin = self.toInt(rpi_output['gpioPin'])
                if rpi_output['outputType'] == 'regular':
                    if self.toInt(rpi_output['gpioPin']) not in self.previous_rpi_outputs :
                        initialValue = GPIO.HIGH if rpi_output['activeLow'] else GPIO.LOW
                        GPIO.setup(pin, GPIO.OUT,initial=initialValue)
                if rpi_output['outputType'] == 'pwm':
                        for pwm in (pwm for pwm in self.PWM_INSTANCES if pin in pwm):
                            self.PWM_INSTANCES.remove(pwm)
                        self.clearChannel(pin)
                        GPIO.setup(pin, GPIO.OUT)
                        p = GPIO.PWM(pin, self.toInt(rpi_output['frequency']))
                        self.PWM_INSTANCES.append({pin:p})
                if rpi_output['outputType'] == 'neopixel':
                        self.clearChannel(pin)
            for rpi_input in self.rpi_inputs:
                pullResistor = pull_up_down=GPIO.PUD_UP if rpi_input['inputPull'] == 'inputPullUp' else GPIO.PUD_DOWN
                GPIO.setup(self.toInt(rpi_input['gpioPin']), GPIO.IN, pullResistor)
                if rpi_input['eventType'] == 'gpio' and self.toInt(rpi_input['gpioPin']) != 0:
                    edge =  GPIO.RISING if rpi_input['edge'] == 'rise' else  GPIO.FALLING
                    GPIO.add_event_detect(self.toInt(rpi_input['gpioPin']), edge, callback= self.handleGPIOControl, bouncetime=200)
                if rpi_input['eventType'] == 'printer' and rpi_input['printerAction'] != 'filament' and self.toInt(rpi_input['gpioPin']) != 0:
                    edge =  GPIO.RISING if rpi_input['edge'] == 'rise' else  GPIO.FALLING
                    GPIO.add_event_detect(self.toInt(rpi_input['gpioPin']), edge, callback= self.handlePrinterAction, bouncetime=200)
        except Exception as ex:
            template = "An exception of type {0} occurred on configureGPIO. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def handleFilammentDetection(self,channel):
        try:
            for rpi_input in self.rpi_inputs:
                if channel == self.toInt(rpi_input['gpioPin']) and rpi_input['eventType'] == 'printer' and rpi_input['printerAction'] == 'filament' \
                and ((rpi_input['edge']=='fall') ^ GPIO.input(self.toInt(rpi_input['gpioPin']))):
                    if time.time() - self.lastFilamentEndDetected >  self._settings.get_int(["filamentSensorTimeout"]):
                        self._logger.info("Detected end of filament.")
                        self.lastFilamentEndDetected = time.time()
                        for line in self._settings.get(["filamentSensorGcode"]).split('\n'):
                            if line:
                                self._printer.commands(line.strip().capitalize())
                                self._logger.info("Sending GCODE command: %s",line.strip( ).upper())
                                time.sleep(0.2)
                        for notification in self.notifications:
                            if notification['filamentChange']:
                                msg = "Filament change action caused by sensor: " + str(rpi_input['label'])
                                self.sendNotification(msg)
                    else:
                        self._logger.info("Prevented end of filament detection, filament sensor timeout not elapsed.")
        except Exception as ex:
            template = "An exception of type {0} occurred on handleFilammentDetection. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def startFilamentDetection(self):
        self.stopFilamentDetection()
        try:
            for rpi_input in self.rpi_inputs:
                if rpi_input['eventType'] == 'printer' and rpi_input['printerAction'] == 'filament' and self.toInt(rpi_input['gpioPin']) != 0:
                    edge =  GPIO.RISING if rpi_input['edge'] == 'rise' else GPIO.FALLING
                    if GPIO.input(self.toInt(rpi_input['gpioPin'])) == (edge == GPIO.RISING):
                        self._printer.pause_print()
                        self._logger.info("Started printing with no filament.")
                    else:
                        GPIO.add_event_detect(self.toInt(rpi_input['gpioPin']), edge, callback= self.handleFilammentDetection, bouncetime=200)
        except Exception as ex:
            template = "An exception of type {0} occurred on startFilamentDetection. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def stopFilamentDetection(self):
        try:
            for rpi_input in self.rpi_inputs:
                if rpi_input['eventType'] == 'printer' and rpi_input['printerAction'] == 'filament':
                    GPIO.remove_event_detect(self.toInt(rpi_input['gpioPin']))
        except Exception as ex:
            template = "An exception of type {0} occurred on stopFilamentDetection. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def handleGPIOControl(self,channel):
        try:
            for rpi_input in self.rpi_inputs:
                if channel == self.toInt(rpi_input['gpioPin']) and rpi_input['eventType']=='gpio' and \
                ((rpi_input['edge']=='fall') ^ GPIO.input(self.toInt(rpi_input['gpioPin']))):
                    for rpi_output in self.rpi_outputs:
                        if self.toInt(rpi_input['controlledIO']) == self.toInt(rpi_output['gpioPin']) and rpi_output['outputType']=='regular':
                            if rpi_input['setControlledIO']=='toggle':
                                val = GPIO.LOW if GPIO.input(self.toInt(rpi_output['gpioPin']))==GPIO.HIGH else GPIO.HIGH
                            else:
                                val = GPIO.LOW if rpi_input['setControlledIO']=='low' else GPIO.HIGH
                            self.writeGPIO(self.toInt(rpi_output['gpioPin']),val)
                            for notification in self.notifications:
                                if notification['gpioAction']:
                                    msg = "GPIO control action caused by input " + str(rpi_input['label']) + ". Setting GPIO" + str(rpi_input['controlledIO']) + " to: " + str(rpi_input['setControlledIO'])
                                    self.sendNotification(msg)
        except Exception as ex:
            template = "An exception of type {0} occurred on handleGPIOControl. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def handlePrinterAction(self,channel):
        try:
            for rpi_input in self.rpi_inputs:
                if channel == self.toInt(rpi_input['gpioPin']) and rpi_input['eventType']=='printer' and \
                ((rpi_input['edge']=='fall') ^ GPIO.input(self.toInt(rpi_input['gpioPin']))):
                    if rpi_input['printerAction'] == 'resume':
                        self._logger.info("Printer action resume.")
                        self._printer.resume_print()
                    elif rpi_input['printerAction'] == 'pause':
                        self._logger.info("Printer action pause.")
                        self._printer.pause_print()
                    elif rpi_input['printerAction'] == 'cancel':
                        self._logger.info("Printer action cancel.")
                        self._printer.cancel_print()
                    elif rpi_input['printerAction'] == 'stopTemperatureControl':
                        self._logger.info("Printer action stoping temperature control.")
                        self.enclosureSetTemperature = 0;
                        self.handleTemperatureControl()
                    for notification in self.notifications:
                        if notification['printerAction']:
                            msg = "Printer action: " +  rpi_input['printerAction'] + " caused by input: " + str(rpi_input['label'])
                            self.sendNotification(msg)
        except Exception as ex:
            template = "An exception of type {0} occurred on handlePrinterAction. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def writeGPIO(self,gpio,value):
        try:
            GPIO.output(gpio, value)
            if self._settings.get(["debug"]) == True:
                self._logger.info("Writing on gpio: %s value %s", gpio,value)
            self.updateOutputUI()
        except Exception as ex:
            template = "An exception of type {0} occurred on writeGPIO. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def writePWM(self,gpio,pwmValue):
        try:
            for pwm in self.PWM_INSTANCES:
                if gpio in pwm:
                    pwm_object = pwm[gpio]
                    pwm['dutycycle']=pwmValue
                    pwm_object.stop()
                    pwm_object.start(pwmValue)
                    if self._settings.get(["debug"]) == True:
                        self._logger.info("Writing PWM on gpio: %s value %s", gpio,pwmValue)
                    self.updateOutputUI()
                    break
        except Exception as ex:
            template = "An exception of type {0} occurred on writePWM. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def updateOutputUI(self):
        try:
            result = []
            result_pwm = []

            for rpi_output in self.rpi_outputs:
                pin = self.toInt(rpi_output['gpioPin'])
                if rpi_output['outputType']=='regular':
                    val = GPIO.input(pin) if not rpi_output['activeLow'] else (not GPIO.input(pin))
                    result.append({pin:val})
                if rpi_output['outputType']=='pwm':
                    # self._logger.info("outputType is PWM")
                    # self._logger.info("Got pin number: %s",pin)
                    # self._logger.info("PWM_INSTANCES: %s",self.PWM_INSTANCES)
                    for pwm in self.PWM_INSTANCES:
                        if pin in pwm:
                            if 'dutycycle' in pwm:
                                pwmVal = pwm['dutycycle'];
                                val = self.toInt(pwmVal)
                            else:
                                val = 100
                            result_pwm.append({pin:val})
                        # self._logger.info("result_pwm: %s", result_pwm)
            self._plugin_manager.send_plugin_message(self._identifier, dict(rpi_output=result,rpi_output_pwm=result_pwm))
        except Exception as ex:
            template = "An exception of type {0} occurred on updateOutputUI. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def getOutputList(self):
        result = []
        for rpi_output in self.rpi_outputs:
            result.append(self.toInt(rpi_output['gpioPin']))
        return result

    def sendNotification(self, message):
        try:
            provider  = self._settings.get(["notificationProvider"])
            if provider == 'ifttt':
                event  = self._settings.get(["event_name"])
                api_key  = self._settings.get(["apiKEY"])
                if self._settings.get(["debug"]) == True:
                    self._logger.info("Sending notification to: %s with msg: %s with key: %s", provider,message,api_key)
                try:
                    res = self.iftttNotification(message,event,api_key)
                except requests.exceptions.ConnectionError:
                    self._logger.info("Error: Could not connect to IFTTT")
                except requests.exceptions.HTTPError:
                    self._logger.info("Error: Received invalid response")
                except requests.exceptions.Timeout:
                    self._logger.info("Error: Request timed out")
                except requests.exceptions.TooManyRedirects:
                    self._logger.info("Error: Too many redirects")
                except requests.exceptions.RequestException as reqe:
                    self._logger.info("Error: {e}".format(e=reqe))
                if res.status_code != requests.codes.ok:
                    try:
                        j = res.json()
                    except ValueError:
                        self._logger.info('Error: Could not parse server response. Event not sent')
                    for err in j['errors']:
                        self._logger.info('Error: {}'.format(err['message']))
        except Exception as ex:
            template = "An exception of type {0} occurred on sendNotification. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def iftttNotification(self,message,event,api_key):
        url = "https://maker.ifttt.com/trigger/{e}/with/key/{k}/".format(e=event,k=api_key)
        payload = {'value1': message}
        return requests.post(url, data=payload)

    #~~ EventPlugin mixin
    def on_event(self, event, payload):

        if event == Events.CONNECTED:
            self.updateOutputUI()

        if event == Events.PRINT_RESUMED:
            self.startFilamentDetection()

        if event == Events.PRINT_STARTED:
            map(scheduler.cancel, scheduler.queue)
            self.startFilamentDetection()
            for rpi_output in self.rpi_outputs:
                if rpi_output['autoStartup'] and rpi_output['outputType']=='regular':
                    value = False if rpi_output['activeLow'] else True
                    scheduler.enter(self.toFloat(rpi_output['startupTimeDelay']), 1, self.writeGPIO, (self.toInt(rpi_output['gpioPin']),value,))
                if rpi_output['autoStartup'] and rpi_output['outputType']=='pwm':
                    value = self.toInt(rpi_output['dutycycle'])
                    scheduler.enter(self.toFloat(rpi_output['startupTimeDelay']), 1, self.writePWM, (self.toInt(rpi_output['gpioPin']),value,))
                if rpi_output['autoStartup'] and rpi_output['outputType']=='neopixel':
                    gpioPin = rpi_output['gpioPin']
                    ledCount = rpi_output['neopixelCount']
                    ledBrightness = rpi_output['neopixelBrightness']
                    address = rpi_output['microAddress']
                    stringColor = rpi_output['color']
                    stringColor = stringColor.replace('rgb(','')

                    red =    stringColor[:stringColor.index(',')]
                    stringColor = stringColor[stringColor.index(',')+1:]
                    green =    stringColor[:stringColor.index(',')]
                    stringColor = stringColor[stringColor.index(',')+1:]
                    blue = stringColor[:stringColor.index(')')]

                    scheduler.enter(self.toFloat(rpi_output['startupTimeDelay']), 1, self.sendNeopixelCommand, (gpioPin,ledCount,ledBrightness,red,green,blue,address,))
            scheduler.run()
            for control in self.temperature_control:
                if control['autoStartup'] == True:
                    self.enclosureSetTemperature = self.toInt(control['defaultTemp'])
                    self._plugin_manager.send_plugin_message(self._identifier, dict(enclosureSetTemp=self.enclosureSetTemperature))

        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            self.stopFilamentDetection()
            self.enclosureSetTemperature = 0
            self._plugin_manager.send_plugin_message(self._identifier, dict(enclosureSetTemp=self.enclosureSetTemperature))
            for rpi_output in self.rpi_outputs:
                if rpi_output['autoShutdown'] and rpi_output['outputType']=='regular':
                    value = True if rpi_output['activeLow'] else False
                    scheduler.enter(self.toFloat(rpi_output['shutdownTimeDelay']), 1, self.writeGPIO, (self.toInt(rpi_output['gpioPin']),value,))
                if rpi_output['autoShutdown'] and rpi_output['outputType']=='pwm':
                    value = 0
                    scheduler.enter(self.toFloat(rpi_output['startupTimeDelay']), 1, self.writePWM, (self.toInt(rpi_output['gpioPin']),value,))
                if rpi_output['autoShutdown'] and rpi_output['outputType']=='neopixel':
                    gpioPin = rpi_output['gpioPin']
                    ledCount = rpi_output['neopixelCount']
                    ledBrightness = rpi_output['neopixelBrightness']
                    address = rpi_output['microAddress']
                    scheduler.enter(self.toFloat(rpi_output['startupTimeDelay']), 1, self.sendNeopixelCommand, (gpioPin,ledCount,0,0,0,0,address,))
            scheduler.run()

        if event == Events.PRINT_DONE:
            for notification in self.notifications:
                if notification['printFinish']:
                    file_name = os.path.basename(payload["file"])
                    elapsed_time_in_seconds = payload["time"]
                    elapsed_time = octoprint.util.get_formatted_timedelta(datetime.timedelta(seconds=elapsed_time_in_seconds))
                    msg = "Print job finished: " + file_name + "finished printing in " + file_name,elapsed_time
                    self.sendNotification(msg)


    #~~ SettingsPlugin mixin
    def on_settings_save(self, data):

        self._logger.info("data: %s", data)

        outputsBeforeSave = self.getOutputList()
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.temperature_reading = self._settings.get(["temperature_reading"])
        self.temperature_control = self._settings.get(["temperature_control"])
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.notifications = self._settings.get(["notifications"])
        outputsAfterSave = self.getOutputList()

        commonPins = list(set(outputsBeforeSave) & set(outputsAfterSave))

        for pin in (pin for pin in outputsBeforeSave if pin not in commonPins):
            self.clearChannel(pin)

        self.previous_rpi_outputs = commonPins;
        self.clearGPIO()

        if self._settings.get(["debug"]) == True:
            self._logger.info("temperature_reading: %s", self.temperature_reading)
            self._logger.info("temperature_control: %s", self.temperature_control)
            self._logger.info("rpi_outputs: %s", self.rpi_outputs)
            self._logger.info("rpi_inputs: %s", self.rpi_inputs)
        self.startGPIO()
        self.configureGPIO()


    def get_settings_defaults(self):
        return dict(
            temperature_reading = [{ 'isEnabled': False, 'gpioPin': 4, 'useFahrenheit':False, 'sensorType':'','sensorAddress':0}],
            temperature_control = [{ 'isEnabled': False, 'controlType':'heater', 'gpioPin': 17, 'activeLow': True, 'autoStartup': False,'defaultTemp':0}],
            rpi_outputs = [],
            rpi_inputs = [],
            filamentSensorGcode =  "G91  ;Set Relative Mode \n" +
                                    "G1 E-5.000000 F500 ;Retract 5mm\n" +
                                    "G1 Z15 F300         ;move Z up 15mm\n" +
                                    "G90            ;Set Absolute Mode\n " +
                                    "G1 X20 Y20 F9000      ;Move to hold position\n" +
                                    "G91            ;Set Relative Mode\n" +
                                    "G1 E-40 F500      ;Retract 40mm\n" +
                                    "M0            ;Idle Hold\n" +
                                    "G90            ;Set Absolute Mode\n" +
                                    "G1 F5000         ;Set speed limits\n" +
                                    "G28 X0 Y0         ;Home X Y\n" +
                                    "M82            ;Set extruder to Absolute Mode\n" +
                                    "G92 E0         ;Set Extruder to 0",
            debug=True,
            useBoardPinNumber=False,
            filamentSensorTimeout=120,
            notificationProvider = "disabled",
            apiKEY = "",
            event_name="printer_event",
            showTempNavbar=False,
            notifications=[{'printFinish':True,'filamentChange':True,'printerAction':True,'temperatureAction':True,'gpioAction':True}]
        )

    #~~ TemplatePlugin
    def get_template_configs(self):
        return [
                dict(type="settings", custom_bindings=True),
                dict(type="tab", custom_bindings=True)
        ]

    ##~~ AssetPlugin mixin
    def get_assets(self):
        return dict(
            js=["js/enclosure.js","js/bootstrap-colorpicker.min.js"],
            css=["css/bootstrap-colorpicker.css"]
        )

    ##~~ Softwareupdate hook
    def get_update_information(self):
        return dict(
            enclosure=dict(
                displayName="Enclosure Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="vitormhenrique",
                repo="OctoPrint-Enclosure",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/vitormhenrique/OctoPrint-Enclosure/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "Enclosure Plugin"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = EnclosurePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
