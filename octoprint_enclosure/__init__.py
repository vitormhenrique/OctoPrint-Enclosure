# coding=utf-8
from __future__ import absolute_import

import json
from abc import ABC
from enum import Enum
from uuid import UUID, uuid4

import flask
import octoprint.plugin
import octoprint.util
from flask import Response, jsonify, make_response, request, abort


# class OutputType(Enum):
#     ACTION_BASED_INPUT = 0
#     STATE_BASED_INPUT = 1


# class OutputPeripheral(ABC):
#     def __init__(self, id: UUID, name: str, type: OutputType) -> None:
#         super().__init__()

#     def run_action(self):
#         """
#         Output peripheral can be action based when it's:
#         - GCODE command
#         - Shell script

#         Returns:
#             Bool: Success
#         """
#         pass

#     def set_state(self, state):
#         """
#         Output peripheral can be state based when it's:
#         - GPIO: it can be set to on / off / toggle
#         - Led Strip: it can be set to a color in RGB
#         - Neopixel
#         - PWM

#         Returns:
#             Bool: Success
#         """
#         pass


class EnclosurePlugin(octoprint.plugin.StartupPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.BlueprintPlugin,
                      octoprint.plugin.EventHandlerPlugin):

    def __init__(self):
        super().__init__()
        self._sub_plugins = dict()
        self._ids = []


    @octoprint.plugin.BlueprintPlugin.route("/uuid", methods=["GET"])
    def get_available_id(self):
        return Response(json.dumps(str(uuid4())), mimetype='application/json')

    # ~~ TemplatePlugin
    def get_template_configs(self):
        return [
            dict(
                type="settings",
                template="enclosure_settings.jinja2",
                custom_bindings=True
            )
        ]

    # ~~ AssetPlugin mixin
    def get_assets(self):
        return dict(
            js=["js/enclosure.js", ],
            css=["css/enclosure.css"]
        )

    # ~~ SettingsPlugin
    def get_settings_defaults(self):
        return dict()

    # ~~ SettingsPlugin mixin
    def on_settings_save(self, data):

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

    # ~~ Softwareupdate hook
    def get_update_information(self):
        return dict(
            enclosure=dict(
                displayName="Enclosure Plugin",
                displayVersion=self._plugin_version,
                type="github_release",
                user="vitormhenrique",
                repo="OctoPrint-Enclosure",
                current=self._plugin_version,
                pip="https://github.com/vitormhenrique/OctoPrint-Enclosure/archive/{target_version}.zip"
            )
        )

    def _get_plugin_key(self, implementation):
        for k, v in self._plugin_manager.plugin_implementations.items():
            if v == implementation:
                return k

    def register_plugin(self, implementation):
        k = self._get_plugin_key(implementation)

        self._logger.debug("Registering plugin - {}".format(k))

        if k not in self._sub_plugins:
            self._logger.info("Registered plugin - {}".format(k))
            self._sub_plugins[k] = implementation

    def output_peripheral_set_state(self):
        pass

    def register_output_peripheral(self):
        pass

    def register_input_peripheral(self):
        pass

    # def get_id(self):
    #     return uuid4()


__plugin_name__ = "Enclosure Plugin"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = EnclosurePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        # get_id = __plugin_implementation__.get_id,
        output_peripheral_set_state= __plugin_implementation__.output_peripheral_set_state,
        register_plugin= __plugin_implementation__.register_plugin,
        register_output_peripheral= __plugin_implementation__.register_output_peripheral,
        register_input_peripheral= __plugin_implementation__.register_input_peripheral,
    )
