# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.util



class EnclosurePlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.TemplatePlugin, octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin, octoprint.plugin.BlueprintPlugin,
                      octoprint.plugin.EventHandlerPlugin):
    

    # ~~ TemplatePlugin
    # def get_template_configs(self):
    #     return [dict(type="settings", custom_bindings=True), dict(type="tab", custom_bindings=True),
    #         dict(type="navbar", custom_bindings=True, suffix="_1", classes=["dropdown"]),
    #         dict(type="navbar", custom_bindings=True, template="enclosure_navbar_input.jinja2", suffix="_2",
    #              classes=["dropdown"])]

    # ~~ AssetPlugin mixin
    # def get_assets(self):
    #     return dict(js=["js/enclosure.js", "js/bootstrap-colorpicker.min.js"],
    #         css=["css/bootstrap-colorpicker.css", "css/enclosure.css"])

    # ~~ Softwareupdate hook
    # def get_update_information(self):
    #     return dict(enclosure=dict(displayName="Enclosure Plugin", displayVersion=self._plugin_version,
    #         # version check: github repository
    #         type="github_release", user="vitormhenrique", repo="OctoPrint-Enclosure", current=self._plugin_version,
    #         # update method: pip
    #         pip="https://github.com/vitormhenrique/OctoPrint-Enclosure/archive/{target_version}.zip"))

   


__plugin_name__ = "Enclosure Plugin"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = EnclosurePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        # "octoprint.comm.protocol.gcode.queuing"       : __plugin_implementation__.hook_gcode_queuing,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }