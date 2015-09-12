# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.util import RepeatedTimer

class EnclosurePlugin(octoprint.plugin.StartupPlugin,
						octoprint.plugin.TemplatePlugin,
                      	octoprint.plugin.SettingsPlugin):

    def on_after_startup(self):
        self._logger.info("Starting Timer")
        self.startTimer(5)

    def startTimer(self, interval):
        self._checkTempTimer = RepeatedTimer(interval, self.checkEnclosureTemp, None, None, True)
        self._checkTempTimer.start()

    def checkEnclosureTemp(self):
    	self._logger.info("Checking eclosure temp...")
       	import random
       	def randrange_float(start, stop, step):
        	return random.randint(0, int((stop - start) / step)) * step + start
        p = randrange_float(5, 60, 0.1)
        self._logger.info("temp:: %s" % p)
        self._plugin_manager.send_plugin_message(self._identifier, dict(enclosureTemp=p))

	##~~ SettingsPlugin
    def get_settings_defaults(self):
    	return dict(heaterPin=17,
    				heaterFrequency=5,
    				heaterEnable=False,
    				fanEnable=False,
    				fanPin=18,
    				lightEnable=True,
    				lightPin=20
    		)

    def get_template_configs(self):
		return [
	        dict(type="settings", custom_bindings=False)	        
	        ]


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Enclosure Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = EnclosurePlugin()

	# global __plugin_hooks__
	# __plugin_hooks__ = {
	#    "some.octoprint.hook": __plugin_implementation__.some_hook_handler
	# }

