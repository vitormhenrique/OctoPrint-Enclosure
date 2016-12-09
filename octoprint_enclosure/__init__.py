# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import flask
from octoprint.util import RepeatedTimer
import os
from subprocess import Popen, PIPE

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
        self.configureGPIO(self._settings.get_int(["heaterPin"]))
        self.configureGPIO(self._settings.get_int(["io1"]))
        self.configureGPIO(self._settings.get_int(["io2"]))
        self.configureGPIO(self._settings.get_int(["io3"]))
        self.configureGPIO(self._settings.get_int(["io4"]))
    
    def configureGPIO(self, pin):
        os.system("gpio -g mode "+str(pin)+" out")
        os.system("gpio -g write "+str(pin)+" 1")
        
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
                self._logger.info(sHum)
                self.enclosureCurrentHumidity = self.toFloat(sHum)
        self._plugin_manager.send_plugin_message(self._identifier, dict(enclosuretemp=self.enclosureCurrentTemperature,enclosureHumidity=self.enclosureCurrentHumidity))
        self.heaterHandler()

    def heaterHandler(self):
        command=""
        if self.enclosureCurrentTemperature<float(self.enclosureSetTemperature) and self._settings.get_boolean(["heaterEnable"]):
            os.system("gpio -g write "+str(self._settings.get_int(["heaterPin"]))+" 0")
        else:
            os.system("gpio -g write "+str(self._settings.get_int(["heaterPin"]))+" 1")
        os.system(command)

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

    @octoprint.plugin.BlueprintPlugin.route("/handleIO", methods=["GET"])
    def handleIO(self):
        io = flask.request.values["pin"]
        if flask.request.values["value"] == "on":
            os.system("gpio -g write "+str(self._settings.get_int([io]))+" 0")
        else:
            os.system("gpio -g write "+str(self._settings.get_int([io]))+" 1")
        return flask.jsonify(success=True)
        
    #~~ EventPlugin mixin
    def on_event(self, event, payload):
        
        if event != "PrintDone":
            return
        
        if  self._settings.get(['heaterEnable']):
            self.enclosureSetTemperature = 0
                     
    #~~ SettingsPlugin mixin
    def on_settings_save(self, data):
        old_heaterPin = self._settings.get_int(["heaterPin"])
        old_dhtPin = self._settings.get_int(["dhtPin"])
        old_io1 = self._settings.get_int(["io1"])
        old_io2 = self._settings.get_int(["io2"])
        old_io3 = self._settings.get_int(["io3"])
        old_io4 = self._settings.get_int(["io4"])
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        new_heaterPin = self._settings.get_int(["heaterPin"])
        new_dhtPin = self._settings.get_int(["dhtPin"])
        new_io1 = self._settings.get_int(["io1"])
        new_io2 = self._settings.get_int(["io2"])
        new_io3 = self._settings.get_int(["io3"])
        new_io4 = self._settings.get_int(["io4"])
        if new_heaterPin != old_heaterPin:
            self.configureGPIO(new_heaterPin)
        if old_dhtPin != new_dhtPin:
            self.configureGPIO(new_dhtPin)
        if old_io1 != new_io1:
            self.configureGPIO(new_io1)
        if old_io2 != new_io2:
            self.configureGPIO(new_io2)
        if old_io3 != new_io3:
            self.configureGPIO(new_io3)
        if old_io4 != new_io4:
            self.configureGPIO(new_io4)

    def get_settings_defaults(self):
        return dict(
            heaterEnable=False,
            heaterPin=18,
            io1=17,
            io2=18,
            io3=21,
            io4=22,
            dhtPin=4,
            dhtModel=22,
            io1Enable=False,
            io2Enable=False,
            io3Enable=False,
            io4Enable=False,
            io1Label="IO1",
            io2Label="IO2",
            io3Label="IO3",
            io4Label="IO4",
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

