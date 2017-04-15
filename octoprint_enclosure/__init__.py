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
        self.temperature_reading = self._settings.get(["temperature_reading"])
        self.temperature_control = self._settings.get(["temperature_control"])
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.startTimer()
        self.startGPIO()
        self.clearGPIO()
        self.configureGPIO()

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

    #~~ Plugin Internal methods
    def checkEnclosureTemp(self):
        try:
            for temp_reader in self.temperature_reading:
                if temp_reader['isEnabled']:
                    if temp_reader['sensorType'] in ["11", "22", "2303"]:
                        self._logger.info("sensorType dht")
                        temp, hum = self.readDhtTemp(temp_reader['sensorType'],temp_reader['gpioPin'])

                        if temp!=-1:
                            self.enclosureCurrentTemperature = temp

                        if hum!=-1:
                            self.enclosureHumidity = hum

                    elif temp_reader['sensorType'] == "18b20":
                        self.enclosureCurrentTemperature = self.read18b20Temp()
                    else:
                        self._logger.info("sensorType no match")
                        self.enclosureCurrentTemperature = 0

                    if temp_reader['useFahrenheit']:
                        self.enclosureCurrentTemperature  = self.enclosureCurrentTemperature*1.8 + 32

                    if self._settings.get(["debug"]) == True:
                        self._logger.info("Temperature read was: %s", self.enclosureCurrentTemperature)

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

    def readDhtTemp(self,sensor,pin):
        try:
            cmd ="sudo python " + (os.path.realpath(__file__)).replace("__init__.pyc","")+"getDHTTemp.py "+str(sensor)+" "+str(pin)
            self._logger.info(cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            temp,hum = stdout.split("|")
            return (self.toFloat(temp.strip()),self.toFloat(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on readDhtTemp. Arguments:\n{1!r}"
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

    def handleTemperatureControl(self):
        if self.enclosureSetTemperature == 0:
            return
        for control in self.temperature_control:
            if control['isEnabled'] == True:
                if control['controlType'] == 'heater':
                    self.currentTempControlStatus = self.toFloat(self.enclosureCurrentTemperature)<self.toFloat(self.enclosureSetTemperature)
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
            if currentMode== None:
                currentMode = setMode
            if currentMode != setMode:
                GPIO.setmode(currentMode)
                tempstr = "BOARD" if currentMode == GPIO.BOARD else "BCM"
                self._settings.set(["useBoardPinNumber"],True if currentMode == GPIO.BOARD else False)
                self._plugin_manager.send_plugin_message(self._identifier,dict(isMsg=True,msg="GPIO mode was configured before, GPIO mode will be forced to use: " + tempstr + " as pin numbers. Please update GPIO accordingly!"))
            else:
                GPIO.setmode(setMode)
            GPIO.setwarnings(False)
        except Exception as ex:
            template = "An exception of type {0} occurred on startGPIO. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            self._logger.warn(message)
            pass

    def clearGPIO(self):
        try:
            for control in self.temperature_control:
                GPIO.cleanup(self.toInt(control['gpioPin']))
            for rpi_output in self.rpi_outputs:
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

    def configureGPIO(self):
        try:
            for control in self.temperature_control:
                 GPIO.setup(self.toInt(control['gpioPin']), GPIO.OUT, initial=GPIO.HIGH if control['activeLow'] else GPIO.LOW)
            for rpi_output in self.rpi_outputs:
                GPIO.setup(self.toInt(rpi_output['gpioPin']), GPIO.OUT, initial=GPIO.HIGH if rpi_output['activeLow'] else GPIO.LOW)
            for rpi_input in self.rpi_inputs:
                GPIO.setup(self.toInt(rpi_input['gpioPin']), GPIO.IN, pull_up_down=GPIO.PUD_UP if rpi_input['inputPull'] == 'inputPullUp' else GPIO.PUD_DOWN)
                if rpi_input['eventType'] == 'gpio' and self.toInt(rpi_input['gpioPin']) != 0:
                    edge =  GPIO.RISING if rpi_input['edge'] == 'hise' else  GPIO.FALLING
                    GPIO.add_event_detect(self.toInt(rpi_input['gpioPin']), edge, callback= self.handleGPIOControl, bouncetime=200)
                if rpi_input['eventType'] == 'printer' and rpi_input['printerAction'] != 'filament' and self.toInt(rpi_input['gpioPin']) != 0:
                    edge =  GPIO.RISING if rpi_input['edge'] == 'hise' else  GPIO.FALLING
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
                    if time.time() - self.lastFilamentEndDetected >  self._settings.get(["filamentSensorTimeout"]):
                        self._logger.info("Detected end of filament.")
                        self.lastFilamentEndDetected = time.time()
                        for line in self._settings.get(["filamentSensorGcode"]).split(';'):
                            if line:
                                self._printer.commands(line.strip().capitalize())
                                self._logger.info("Sending GCODE command: %s",line.strip().capitalize())
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
                    edge =  GPIO.RISING if rpi_input['edge'] == 'hise' else GPIO.FALLING
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
                        if self.toInt(rpi_input['controlledIO']) == self.toInt(rpi_output['gpioPin']):
                            val = GPIO.LOW if rpi_input['setControlledIO']=='low' else GPIO.HIGH
                            self.writeGPIO(self.toInt(rpi_output['gpioPin']),val)
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

    def updateOutputUI(self):
        result = []
        i=0
        for rpi_output in self.rpi_outputs:
            pin = self.toInt(rpi_output['gpioPin'])
            val = GPIO.input(pin) if not rpi_output['activeLow'] else (not GPIO.input(pin))
            result.append({pin:val})
        self._plugin_manager.send_plugin_message(self._identifier, dict(rpi_output=result))

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
                if rpi_output['autoStartup']:
                    value = False if rpi_output['activeLow'] else True
                    scheduler.enter(self.toFloat(rpi_output['startupTimeDelay']), 1, self.writeGPIO, (self.toInt(rpi_output['gpioPin']),value,))
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
                if rpi_output['autoShutdown']:
                    value = True if rpi_output['activeLow'] else False
                    scheduler.enter(self.toFloat(rpi_output['shutdownTimeDelay']), 1, self.writeGPIO, (self.toInt(rpi_output['gpioPin']),value,))
            scheduler.run()

    #~~ SettingsPlugin mixin
    def on_settings_save(self, data):
        self.clearGPIO()
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.temperature_reading = self._settings.get(["temperature_reading"])
        self.temperature_control = self._settings.get(["temperature_control"])
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        if self._settings.get(["debug"]) == True:
            self._logger.info("temperature_reading: %s", self.temperature_reading)
            self._logger.info("temperature_control: %s", self.temperature_control)
            self._logger.info("rpi_outputs: %s", self.rpi_outputs)
            self._logger.info("rpi_inputs: %s", self.rpi_inputs)
        self.startGPIO()
        self.configureGPIO()


    def get_settings_defaults(self):
        return dict(
            temperature_reading = [{ 'isEnabled': False, 'gpioPin': 4, 'useFahrenheit':False, 'sensorType':''}],
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
            filamentSensorTimeout=120
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
            js=["js/enclosure.js"]
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
