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
		self.configureGPIO(self._settings.get_int(["fanPin"]))
		self.configureGPIO(self._settings.get_int(["lightPin"]))
	
	def configureGPIO(self, pin):
		os.system("gpio -g mode "+str(pin)+" out")
		os.system("gpio -g write "+str(pin)+" 1")
		
	def startTimer(self):
		self._checkTempTimer = RepeatedTimer(10, self.checkEnclosureTemp, None, None, True)
		self._checkTempTimer.start()

	def checkEnclosureTemp(self):
		stdout = Popen("sudo "+self._settings.get(["getTempScript"])+" "+str(self._settings.get(["dhtModel"]))+" "+str(self._settings.get(["dhtPin"])), shell=True, stdout=PIPE).stdout
		sTemp = stdout.read()
		if sTemp.find("Failed") != -1:
			self._logger.info("Failed to read Temperature")
		else:
			self.enclosureCurrentTemperature = float(sTemp)

		stdout = Popen("sudo "+self._settings.get(["getHumiScript"])+" "+str(self._settings.get(["dhtModel"]))+" "+str(self._settings.get(["dhtPin"])), shell=True, stdout=PIPE).stdout
		sTemp = stdout.read()
		if sTemp.find("Failed") != -1:
			self._logger.info("Failed to read Humidity")
		else:
			self.enclosureCurrentHumidity = float(sTemp)

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
		
	@octoprint.plugin.BlueprintPlugin.route("/handleFan", methods=["GET"])
	def handleFan(self):
		if self._settings.get_boolean(["fanEnable"]):
			if flask.request.values["status"] == "on":
				os.system("gpio -g write "+str(self._settings.get_int(["fanPin"]))+" 0")
			else:
				os.system("gpio -g write "+str(self._settings.get_int(["fanPin"]))+" 1")
		return flask.jsonify(success=True)
		
	@octoprint.plugin.BlueprintPlugin.route("/handleLight", methods=["GET"])
	def handleLight(self):
		if self._settings.get_boolean(["lightEnable"]):
			if flask.request.values["status"] == "on":
				os.system("gpio -g write "+str(self._settings.get_int(["lightPin"]))+" 0")
			else:
				os.system("gpio -g write "+str(self._settings.get_int(["lightPin"]))+" 1")
		return flask.jsonify(success=True)
		
	#~~ EventPlugin mixin
	def on_event(self, event, payload):
		
		if event != "PrintDone":
			return
		
		if  self._settings.get(['heaterEnable']):
			self.enclosureSetTemperature = 0
			
		if  self._settings.get(['fanEnable']):
			os.system("gpio -g write "+str(self._settings.get_int(["lightPin"]))+" 1")
			
	#~~ SettingsPlugin mixin
	def on_settings_save(self, data):
		old_heaterPin = self._settings.get_int(["heaterPin"])
		old_dhtPin = self._settings.get_int(["dhtPin"])
		old_fanPin = self._settings.get_int(["fanPin"])
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		new_heaterPin = self._settings.get_int(["heaterPin"])
		new_dhtPin = self._settings.get_int(["dhtPin"])
		new_fanPin = self._settings.get_int(["fanPin"])
		if new_heaterPin != old_heaterPin:
			self.configureGPIO(new_heaterPin)
		if old_dhtPin != new_dhtPin:
			self.configureGPIO(new_dhtPin)
		if old_fanPin != new_fanPin:
			self.configureGPIO(new_fanPin)

	def get_settings_defaults(self):
		return dict(
			heaterEnable=False,
			heaterPin=18,
			fanPin=23,
			lightPin=15,
			dhtPin=4,
			dhtModel=22,
			fanEnable=False,
			lightEnable=False,
			getTempScript="~/.octoprint/plugins/OctoPrint-Enclosure/SensorScript/GetTemperature.py",
			getHumiScript="~/.octoprint/plugins/OctoPrint-Enclosure/SensorScript/GetHumidity.py"
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

