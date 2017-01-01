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
import os

scheduler = sched.scheduler(time.time, time.sleep)

class EnclosureGPIO():
    def __init__(self, pinNumber, label, activeLow, enable, autoShutDown,isOutput,timeDelay):
        self.pinNumber = pinNumber
        self.label = label
        self.activeLow = activeLow
        self.enable = enable
        self.autoShutDown = autoShutDown
        self.isOutput = isOutput
        self.timeDelay = timeDelay

    def configureGPIO(self):
        if self.isOutput:
            if self.activeLow: #if is active low, we start disabelling it by making it high!
                GPIO.setup(self.pinNumber, GPIO.OUT, initial=GPIO.HIGH)
            else:
                GPIO.setup(self.pinNumber, GPIO.OUT, initial=GPIO.LOW)
        else:
            GPIO.setup(self.pinNumber, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def write(self,active):
        if self.activeLow:
            active = not active

        GPIO.output(self.pinNumber, active)

class EnclosurePlugin(octoprint.plugin.StartupPlugin,
            octoprint.plugin.TemplatePlugin,
            octoprint.plugin.SettingsPlugin,
            octoprint.plugin.AssetPlugin,
            octoprint.plugin.BlueprintPlugin,
            octoprint.plugin.EventHandlerPlugin):

    enclosureSetTemperature=0.0
    enclosureCurrentTemperature=0.0
    enclosureCurrentHumidity=0.0
    def startGPIO(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.io1 = EnclosureGPIO(self._settings.get_int(["io1Pin"]),self._settings.get(["io1Label"]),self._settings.get(["io1ActiveLow"]),
            self._settings.get(["io1Enable"]),self._settings.get(["io1AutoShutDown"]),True,self._settings.get(["io1TimeDelay"]))

        self.io2 = EnclosureGPIO(self._settings.get_int(["io2Pin"]),self._settings.get(["io2Label"]),self._settings.get(["io2ActiveLow"]),
            self._settings.get(["io2Enable"]),self._settings.get(["io2AutoShutDown"]),True,self._settings.get(["io2TimeDelay"]))

        self.io3 = EnclosureGPIO(self._settings.get_int(["io3Pin"]),self._settings.get(["io3Label"]),self._settings.get(["io3ActiveLow"]),
            self._settings.get(["io3Enable"]),self._settings.get(["io3AutoShutDown"]),True,self._settings.get(["io3TimeDelay"]))

        self.io4 = EnclosureGPIO(self._settings.get_int(["io4Pin"]),self._settings.get(["io4Label"]),self._settings.get(["io4ActiveLow"]),
            self._settings.get(["io4Enable"]),self._settings.get(["io4AutoShutDown"]),True,self._settings.get(["io4TimeDelay"]))

        self.heater = EnclosureGPIO(self._settings.get_int(["heaterPin"]),"heater",self._settings.get(["heaterActiveLow"]), self._settings.get(["heaterEnable"]),True,True,0)

        self.filamentSensor = EnclosureGPIO(self._settings.get_int(["filamentSensorPin"]),"filamentSensor",False,self._settings.get(["filamentSensorEnable"]),False,False,0)

        self.io1.configureGPIO()
        self.io2.configureGPIO()
        self.io3.configureGPIO()
        self.io4.configureGPIO()
        self.heater.configureGPIO()
        self.filamentSensor.configureGPIO()

    def startTimer(self):
        self._checkTempTimer = RepeatedTimer(10, self.checkEnclosureTemp, None, None, True)
        self._checkTempTimer.start()

    def toFloat(self, value):
        try:
            val = float(value)
            return val
        except:
            self._logger.info("Failed to convert to float")
            return 0

    def checkEnclosureTemp(self):
        if self._settings.get(["dhtModel"]) == 1820 or self._settings.get(["dhtModel"]) == '1820':
            stdout = Popen("sudo "+self._settings.get(["getTempScript"])+" "+str(self._settings.get(["dhtModel"])), shell=True, stdout=PIPE).stdout
        else:
            stdout = Popen("sudo "+self._settings.get(["getTempScript"])+" "+str(self._settings.get(["dhtModel"]))+" "+str(self._settings.get(["dhtPin"])), shell=True, stdout=PIPE).stdout
        sTemp = stdout.read()
        sTemp.replace(" ", "")
        if sTemp.find("Failed") != -1:
            self._logger.info("Failed to read Temperature")
        else:
            #self._logger.info(sTemp)
            self.enclosureCurrentTemperature = self.toFloat(sTemp)
            #self._logger.info("enclosureCurrentTemperature is: %s",self.enclosureCurrentTemperature)

        if self._settings.get(["dhtModel"]) != '1820':
            stdout = Popen("sudo "+self._settings.get(["getHumiScript"])+" "+str(self._settings.get(["dhtModel"]))+" "+str(self._settings.get(["dhtPin"])), shell=True, stdout=PIPE).stdout
            sHum = stdout.read()
            sHum.replace(" ", "")
            if sHum.find("Failed") != -1:
                self._logger.info("Failed to read Humidity")
            else:
                # self._logger.info(sHum)
                self.enclosureCurrentHumidity = self.toFloat(sHum)
        self._plugin_manager.send_plugin_message(self._identifier, dict(enclosuretemp=self.enclosureCurrentTemperature,enclosureHumidity=self.enclosureCurrentHumidity))
        self.heaterHandler()

    def heaterHandler(self):
        if self.enclosureCurrentTemperature<float(self.enclosureSetTemperature) and self.heater.enable:
            self._logger.info("Turning heater on.")
            self.heater.write(True)
        else:
            self._logger.info("Turning heater off.")
            self.heater.write(False)

    def startFilamentDetection(self):
        if not GPIO.input(self.filamentSensor.pinNumber):
            self._logger.info("Started printing with no filament.")
            self._printer.toggle_pause_print()
        try:
            GPIO.remove_event_detect(self.filamentSensor.pinNumber)
        except:
            pass
        if self.filamentSensor.pinNumber != -1:
            self._logger.info("Started filament detection.")
            GPIO.add_event_detect(self.filamentSensor.pinNumber, GPIO.FALLING, callback=self.handleFilamentDetection, bouncetime=300) 

    def handleFilamentDetection(self,channel):
        if not GPIO.input(self.filamentSensor.pinNumber) and self._printer.is_printing():
            self._logger.info("Detected end of filament.")
            self._printer.toggle_pause_print()

    def stopFilamentDetection(self):
        try:
            GPIO.remove_event_detect(self.filamentSensor.pinNumber)
        except:
            pass

    #~~ StartupPlugin mixin
    def on_after_startup(self):
        self.startTimer()
        self.startGPIO()
    #~~ Blueprintplugin mixin
    @octoprint.plugin.BlueprintPlugin.route("/setEnclosureTemperature", methods=["GET"])
    def setEnclosureTemperature(self):
        self.enclosureSetTemperature = flask.request.values["enclosureSetTemp"]
        self.heaterHandler()
        return flask.jsonify(enclosureSetTemperature=self.enclosureSetTemperature,enclosureCurrentTemperature=self.enclosureCurrentTemperature)

    @octoprint.plugin.BlueprintPlugin.route("/getEnclosureSetTemperature", methods=["GET"])
    def getEnclosureSetTemperature(self):
        return str(self.enclosureSetTemperature)

    @octoprint.plugin.BlueprintPlugin.route("/getEnclosureTemperature", methods=["GET"])
    def getEnclosureTemperature(self):
        return str(self.enclosureCurrentTemperature)

    @octoprint.plugin.BlueprintPlugin.route("/setIO", methods=["GET"])
    def setIO(self):
        io = flask.request.values["io"]
        value = True if flask.request.values["status"] == "on" else False

        if io == "io1": 
            self.io1.write(value)
        elif io == "io2":
            self.io2.write(value)
        elif io == "io3":
            self.io3.write(value)
        elif io == "io4":
            self.io4.write(value)

        return flask.jsonify(success=True)

    #~~ EventPlugin mixin
    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            if self.filamentSensor.enable:
                self.startFilamentDetection()
        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            if self.filamentSensor.enable:
                self.stopFilamentDetection()

            if  self.heater.enable:
                    self.enclosureSetTemperature = 0

            if self.io1.autoShutDown:
                scheduler.enter(self.toFloat(self.io1.timeDelay), 1, self.io1.write, (False,))
            if self.io2.autoShutDown:
                scheduler.enter(self.toFloat(self.io2.timeDelay), 1, self.io2.write, (False,))
            if self.io3.autoShutDown:
                scheduler.enter(self.toFloat(self.io3.timeDelay), 1, self.io3.write, (False,))
            if self.io4.autoShutDown:
                scheduler.enter(self.toFloat(self.io4.timeDelay), 1, self.io4.write, (False,))
            scheduler.run()


    #~~ SettingsPlugin mixin
    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.startGPIO()

    def get_settings_defaults(self):
        return dict(
            heaterEnable=False,
            heaterPin=17,
            heaterActiveLow=True,
            dhtPin=4,
            filamentSensorPin=24,
            filamentSensorEnable=True,
            dhtModel=2302,
            io1Pin=18,
            io2Pin=23,
            io3Pin=22,
            io4Pin=27,
            io1Label="Light",
            io2Label="Fan",
            io3Label="IO3",
            io4Label="IO4",
            io1ActiveLow=True,
            io2ActiveLow=True,
            io3ActiveLow=True,
            io4ActiveLow=True,
            io1Enable=False,
            io2Enable=False,
            io3Enable=False,
            io4Enable=False,
            io1AutoShutDown=True,
            io2AutoShutDown=True,
            io3AutoShutDown=True,
            io4AutoShutDown=True,
            io1TimeDelay=0,
            io2TimeDelay=0,
            io3TimeDelay=0,
            io4TimeDelay=0,
            getTempScript="~/.octoprint/plugins/OctoPrint-Enclosure/extras/GetTemperature.py",
            getHumiScript="~/.octoprint/plugins/OctoPrint-Enclosure/extras/GetHumidity.py"
        )
    #~~ TemplatePlugin
    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=False)]

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

