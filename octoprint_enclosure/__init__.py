# coding=utf-8
from __future__ import absolute_import
from octoprint.events import eventManager, Events
from octoprint.util import RepeatedTimer
from subprocess import Popen, PIPE
from .ledstrip import LEDStrip
import octoprint.plugin
import RPi.GPIO as GPIO
from flask import jsonify, request, make_response, Response
from octoprint.server.util.flask import restricted_access
from werkzeug.exceptions import BadRequest
import time
import sys
import glob
import os
from datetime import datetime
from datetime import timedelta
import octoprint.util
import requests
import inspect
import threading
import json
import copy
from smbus2 import SMBus
from .getPiTemp import PiTemp
import struct


#Function that returns Boolean output state of the GPIO inputs / outputs
def PinState_Boolean(pin, ActiveLow) :
    try:
        state = GPIO.input(pin)
        if ActiveLow and not state: return True
        if not ActiveLow and state: return True
        return False
    except:
        return "ERROR: Unable to read pin"

#Function that returns human-readable output state of the GPIO inputs / outputs
def PinState_Human(pin, ActiveLow):
    PinState = PinState_Boolean(pin, ActiveLow)
    if PinState == True :
        return " ON "
    elif PinState == False:
        return " OFF "
    else:
        return PinState

#Translates the Pull-Up/Pull-Down GPIO resistor setting to ActiveLow/ActiveHigh boolean
def CheckInputActiveLow(Input_Pull_Resistor):
    #input_pull_up
    #input_pull_down
    if Input_Pull_Resistor == "input_pull_up":
        return True
    else:
        return False

class EnclosurePlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.TemplatePlugin, octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin, octoprint.plugin.BlueprintPlugin,
                      octoprint.plugin.EventHandlerPlugin):
    rpi_outputs = []
    rpi_inputs = []
    waiting_temperature = []
    rpi_outputs_not_changed = []
    notifications = []
    pwm_instances = []
    event_queue = []
    temp_hum_control_status = []
    temperature_sensor_data = []
    last_filament_end_detected = []
    print_complete = False
    development_mode = False
    dummy_value = 30.0
    dummy_delta = 0.5
    
    def __init__(self):
        # mqtt helper
        self.mqtt_publish = lambda *args, **kwargs: None
        # hardcoded
        self.mqtt_root_topic = "octoprint/plugins/enclosure"
        self.mqtt_sensor_topic = self.mqtt_root_topic + "/" + "enclosure"
        self.mqtt_message = "{\"temperature\": 0, \"humidity\": 0}"
  
    def start_timer(self):
        """
        Function to start timer that checks enclosure temperature
        """

        self._check_temp_timer = RepeatedTimer(10, self.check_enclosure_temp, None, None, True)
        self._check_temp_timer.start()

    @staticmethod
    def to_float(value):
        """Converts value to flow
        Arguments:
            value {any} -- value to be
        Returns:
            float -- value converted
        """

        try:
            val = float(value)
            return val
        except:
            return 0

    @staticmethod
    def to_int(value):
        try:
            val = int(value)
            return val
        except:
            return 0

    @staticmethod
    def is_hour(value):
        try:
            datetime.strptime(value, '%H:%M')
            return True
        except:
            return False

    @staticmethod
    def create_date(value):
        temp_string = datetime.now().strftime('%m/%d/%Y') + " " + value
        return datetime.strptime(temp_string, '%m/%d/%Y %H:%M')

    @staticmethod
    def constrain(n, minn, maxn):
        return max(min(maxn, n), minn)

    @staticmethod
    def get_gcode_value(command_string, gcode):
        semicolon = command_string.find(';')
        if not semicolon == -1:
            command_string = command_string[:semicolon]

        for command in command_string.split(' '):
            index = command.upper().find(gcode.upper())
            if not index == -1:
                return command.replace(gcode, '')
        return -1

    # ~~ StartupPlugin mixin
    def on_after_startup(self):   
        helpers = self._plugin_manager.get_helpers("mqtt", "mqtt_publish", "mqtt_subscribe", "mqtt_unsubscribe")
        
        if helpers:
            if "mqtt_publish" in helpers:
                self.mqtt_publish = helpers["mqtt_publish"]
        else:
            self._logger.info("mqtt helpers not found. mqtt functions won't work")       
        
        self.pwm_instances = []
        self.event_queue = []
        self.rpi_outputs_not_changed = []
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.notifications = self._settings.get(["notifications"])
        self.generate_temp_hum_control_status()
        self.setup_gpio()
        self.configure_gpio()
        self.update_ui()
        self.start_outpus_with_server()
        self.handle_initial_gpio_control()
        self.start_timer()
        self.print_complete = False

    def get_settings_version(self):
        return 10

    def on_settings_migrate(self, target, current=None):
        self._logger.warn("######### current settings version %s target settings version %s #########", current, target)
        self._logger.info("#########        Current settings        #########")
        self._logger.info("rpi_outputs: %s", self.rpi_outputs)
        self._logger.info("rpi_inputs: %s", self.rpi_inputs)
        self._logger.info("#########        End Current Settings        #########")
        if current >= 4 and target == 10:
            self._logger.warn("######### migrating settings to v10 #########")
            old_outputs = self._settings.get(["rpi_outputs"])
            old_inputs = self._settings.get(["rpi_inputs"])
            for rpi_output in old_outputs:
                if 'shutdown_on_failed' not in rpi_output:
                    rpi_output['shutdown_on_failed'] = False
                if 'shell_script' not in rpi_output:
                    rpi_output['shell_script'] = ""
                if 'gpio_i2c_enabled' not in rpi_output:
                    rpi_output['gpio_i2c_enabled'] = False
                if 'gpio_i2c_bus' not in rpi_output:
                    rpi_output['gpio_i2c_bus'] = 1
                if 'gpio_i2c_address' not in rpi_output:
                    rpi_output['gpio_i2c_address'] = 1
                if 'gpio_i2c_register' not in rpi_output:
                    rpi_output['gpio_i2c_register'] = 1
                if 'gpio_i2c_data_on' not in rpi_output:
                    rpi_output['gpio_i2c_data_on'] = 1
                if 'gpio_i2c_data_off' not in rpi_output:
                    rpi_output['gpio_i2c_data_off'] = 0
                if 'gpio_i2c_register_status' not in rpi_output:
                    rpi_output['gpio_i2c_register_status'] = 1
                if 'shutdown_on_error' not in rpi_output:
                        rpi_output['shutdown_on_error'] = False
            self._settings.set(["rpi_outputs"], old_outputs)

            old_inputs = self._settings.get(["rpi_inputs"])
            for rpi_input in old_inputs:
                if 'temp_i2c_bus' not in rpi_input:
                    rpi_input['temp_i2c_bus'] = 1
                if 'temp_i2c_address' not in rpi_input:
                    rpi_input['temp_i2c_address'] = 1
                if 'temp_i2c_register' not in rpi_input:
                    rpi_input['temp_i2c_register'] = 1
                if 'show_graph_temp' not in rpi_input:
                    rpi_input['show_graph_temp'] = False
                if 'show_graph_humidity' not in rpi_input:
                    rpi_input['show_graph_humidity'] = False
            self._settings.set(["rpi_inputs"], old_inputs)
        else:
            self._logger.warn("######### settings not compatible #########")
            self._settings.set(["rpi_outputs"], [])
            self._settings.set(["rpi_inputs"], [])
            self.rpi_inputs = self._settings.get(["rpi_inputs"])

    #Scan all configured inputs and outputs and return the pin value
    @octoprint.plugin.BlueprintPlugin.route("/ReadPin/<int:identifier>", methods=["GET"])
    def ReadSinglePin(self, identifier):
        Resp = []
        MatchFound = False
        for rpi_input in self.rpi_inputs:
            if identifier == self.to_int(rpi_input['gpio_pin']):
                MatchFound = True
                ConfiguredAs = "Input"
                ActiveLow = CheckInputActiveLow(rpi_input['input_pull_resistor'])
                pin = self.to_int(rpi_input['gpio_pin'])
                val = PinState_Human(pin,ActiveLow)
                label = rpi_input['label']
                Resp.append(dict(Configured_As=ConfiguredAs, label=label, GPIO_Pin=pin, Active_Low=ActiveLow, State=val))
        for rpi_output in self.rpi_outputs:
            if identifier == self.to_int(rpi_output['gpio_pin']):
                MatchFound = True
                ConfiguredAs = "Output"
                ActiveLow = CheckInputActiveLow(rpi_output['active_low'])
                pin = self.to_int(rpi_output['gpio_pin'])
                if rpi_output['gpio_i2c_enabled']:
                    b = self.gpio_i2c_input(rpi_output, ActiveLow)
                    val = " ON " if b else " OFF "
                else:
                    val = PinState_Human(pin,ActiveLow)
                label = rpi_output['label']
                Resp.append(dict(Configured_As=ConfiguredAs, label=label, GPIO_Pin=pin, Active_Low=ActiveLow, State=val))
        if MatchFound == False:
            pin = int(identifier)
            ConfiguredAs = "Unknown"
            ActiveLow = "Unknown"
            try:
                val = GPIO.input(pin)
            except:
                val = "GPIO pin not initialized."
            Resp.append(dict(Configured_As=ConfiguredAs, GPIO_Pin=pin, Active_Low=ActiveLow, State=val))
        return Response(json.dumps(Resp), mimetype='application/json')

    # ~~ Blueprintplugin mixin
    @octoprint.plugin.BlueprintPlugin.route("/inputs", methods=["GET"])
    def get_inputs(self):
        inputs = []
        for rpi_input in self.rpi_inputs:
            index = self.to_int(rpi_input['index_id'])
            label = rpi_input['label']
            ActiveLow = CheckInputActiveLow(rpi_input['input_pull_resistor'])
            pin = self.to_int(rpi_input['gpio_pin'])
            val = PinState_Human(pin,ActiveLow)
            inputs.append(dict(index_id=index, label=label, GPIO_Pin=pin, State=val))
        return Response(json.dumps(inputs), mimetype='application/json')

    @octoprint.plugin.BlueprintPlugin.route("/inputs/<int:identifier>", methods=["GET"])
    def get_input_status(self, identifier):
        for rpi_input in self.rpi_inputs:
            if identifier == self.to_int(rpi_input['index_id']):
                return Response(json.dumps(rpi_input), mimetype='application/json')
        return make_response('', 404)


    @octoprint.plugin.BlueprintPlugin.route("/temperature/<int:identifier>", methods=["PATCH"])
    @restricted_access
    def set_enclosure_temp_humidity(self, identifier):
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'temperature' not in data:
            return make_response("missing temperature attribute", 406)

        set_value = data["temperature"]

        for temp_hum_control in [item for item in self.rpi_outputs if item['index_id'] == identifier]:
            temp_hum_control['temp_ctr_set_value'] = set_value

        self.handle_temp_hum_control()
        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/filament/<int:identifier>", methods=["PATCH"])
    @restricted_access
    def set_filament_sensor(self, identifier):
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'status' not in data:
            return make_response("missing status attribute", 406)

        value = data["status"]

        for sensor in self.rpi_inputs:
            if identifier == self.to_int(sensor['index_id']):
                sensor['filament_sensor_enabled'] = value
                self._logger.info("Setting filament sensor for input %s to : %s", str(identifier), value)
        self._settings.set(["rpi_inputs"], self.rpi_inputs)
        return make_response('', 204)

    @octoprint.plugin.BlueprintPlugin.route("/outputs", methods=["GET"])
    def get_outputs(self):
        outputs = []
        for rpi_output in self.rpi_outputs:
            if rpi_output['output_type'] == 'regular':
                index = self.to_int(rpi_output['index_id'])
                label = rpi_output['label']
                pin = self.to_int(rpi_output['gpio_pin'])          
                ActiveLow = rpi_output['active_low']
                if rpi_output['gpio_i2c_enabled']:
                    b = self.gpio_i2c_input(rpi_output, ActiveLow)
                    val = " ON " if b else " OFF "
                else:
                    val = PinState_Human(pin,ActiveLow)
                outputs.append(dict(index_id=index, label=label, GPIO_Pin=pin, State=val))
        return Response(json.dumps(outputs), mimetype='application/json')


    @octoprint.plugin.BlueprintPlugin.route("/outputs/<int:identifier>", methods=["GET"])
    def get_output_status(self, identifier):
        for rpi_output in self.rpi_outputs:
            if identifier == self.to_int(rpi_output['index_id']):
                out = copy.deepcopy(rpi_output)
                pin = self.to_int(rpi_output['gpio_pin'])
                if rpi_output['gpio_i2c_enabled']:
                    out['current_value'] = self.gpio_i2c_input(rpi_output, rpi_output['active_low'])
                else:
                    out['current_value'] = PinState_Boolean(pin, rpi_output['active_low'] )
                return Response(json.dumps(out), mimetype='application/json')
        return make_response('', 404)


    @octoprint.plugin.BlueprintPlugin.route("/outputs/<int:identifier>", methods=["PATCH"])
    @restricted_access
    def set_io(self, identifier):
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'status' not in data:
            return make_response("missing status attribute", 406)

        value = data["status"]

        for rpi_output in self.rpi_outputs:
            if identifier == self.to_int(rpi_output['index_id']):
                val = (not value) if rpi_output['active_low'] else value
                if rpi_output['gpio_i2c_enabled']:
                    self.gpio_i2c_write(rpi_output, val)
                else:
                    self.write_gpio(self.to_int(rpi_output['gpio_pin']), val)
        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/outputs/<int:identifier>/auto-startup", methods=["PATCH"])
    @restricted_access
    def set_auto_startup(self, identifier):
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'status' not in data:
            return make_response("missing status attribute", 406)

        value = data["status"]

        if not value:
            suffix = 'auto_startup'
            queue_id = '{0!s}_{1!s}'.format(str(identifier), suffix)
            self.stop_queue_item(queue_id)
        for output in self.rpi_outputs:
            if identifier == self.to_int(output['index_id']):
                output['auto_startup'] = value
                self._logger.info("Setting auto startup for output %s to : %s", str(identifier), value)
        self._settings.set(["rpi_outputs"], self.rpi_outputs)
        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/outputs/<int:identifier>/auto-shutdown", methods=["PATCH"])
    @restricted_access
    def set_auto_shutdown(self, identifier):
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'status' not in data:
            return make_response("missing status attribute", 406)

        value = data["status"]

        if not value:
            suffix = 'auto_shutdown'
            queue_id = '{0!s}_{1!s}'.format(str(identifier), suffix)
            self.stop_queue_item(queue_id)

        for output in self.rpi_outputs:
            if identifier == self.to_int(output['index_id']):
                output['auto_shutdown'] = value
                self._logger.info("Setting auto shutdown for output %s to : %s", str(identifier), value)
        self._settings.set(["rpi_outputs"], self.rpi_outputs)
        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/pwm/<int:identifier>", methods=["PATCH"])
    @restricted_access
    def set_pwm(self, identifier):
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'duty_cycle' not in data:
            return make_response("missing duty_cycle attribute", 406)

        set_value = self.to_int(data['duty_cycle'])
        for rpi_output in [item for item in self.rpi_outputs if item['index_id'] == identifier]:
            rpi_output['duty_cycle'] = set_value
            rpi_output['new_duty_cycle'] = ""
            gpio = self.to_int(rpi_output['gpio_pin'])
            self.write_pwm(gpio, set_value)
        return make_response('', 204)

    @octoprint.plugin.BlueprintPlugin.route("/emc/<int:identifier>", methods=["PATCH"])
    @restricted_access
    def set_emc2101(self, identifier):
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)
        if 'duty_cycle' not in data:
            return make_response("missing duty_cycle attribute", 406)
        set_value = self.to_int(data['duty_cycle'])
        script = os.path.dirname(os.path.realpath(__file__)) + "/SETEMC2101.py"
        cmd = [sys.executable, script, str(set_value)]
        if self._settings.get(["use_sudo"]):
             cmd.insert(0, "sudo")
        stdout = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        output, errors = stdout.communicate()
        if self._settings.get(["debug_temperature_log"]) is True:
            if len(errors) > 0:
                self._logger.error("EMC2101 error: %s", errors)
            else:
                self._logger.debug("EMC2101 result: %s", output)
        self._logger.debug(output + " " + errors)
        return make_response('', 204)

    
    @octoprint.plugin.BlueprintPlugin.route("/rgb-led/<int:identifier>", methods=["PATCH"])
    @restricted_access
    def set_ledstrip_color(self, identifier):
        """ set_ledstrip_color method get request from octoprint and send the command to Open-Smart RGB LED Strip"""
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'rgb' not in data:
            return make_response("missing rgb attribute", 406)
        rgb = data['rgb']

        for rpi_output in self.rpi_outputs:
            if identifier == self.to_int(rpi_output['index_id']):
                self.ledstrip_set_rgb(rpi_output, rgb)

        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/neopixel/<int:identifier>", methods=["PATCH"])
    @restricted_access
    def set_neopixel(self, identifier):
        """ set_neopixel method get request from octoprint and send the command to arduino or neopixel"""
        if "application/json" not in request.headers["Content-Type"]:
            return make_response("expected json", 400)
        try:
            data = request.json
        except BadRequest:
            return make_response("malformed request", 400)

        if 'red' not in data:
            return make_response("missing red attribute", 406)
        if 'green' not in data:
            return make_response("missing green attribute", 406)
        if 'blue' not in data:
            return make_response("missing blue attribute", 406)

        red = data['red']
        green = data['green']
        blue = data['blue']

        for rpi_output in self.rpi_outputs:
            if identifier == self.to_int(rpi_output['index_id']):
                led_count = rpi_output['neopixel_count']
                led_brightness = rpi_output['neopixel_brightness']
                address = rpi_output['microcontroller_address']

                neopixel_dirrect = rpi_output['output_type'] == 'neopixel_direct'

                self.send_neopixel_command(self.to_int(rpi_output['gpio_pin']), led_count, led_brightness, red, green,
                    blue, address, neopixel_dirrect, identifier)

        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/clear-gpio", methods=["POST"])
    @restricted_access
    def clear_gpio_mode(self):
        GPIO.cleanup()
        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/update", methods=["POST"])
    @restricted_access
    def update_ui_requested(self):
        self.update_ui()
        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/shell/<int:identifier>", methods=["POST"])
    @restricted_access
    def send_shell_command(self, identifier):
        rpi_output = [r_out for r_out in self.rpi_outputs if self.to_int(r_out['index_id']) == identifier].pop()

        command = rpi_output['shell_script']
        self.shell_command(command)
        return make_response('', 204)


    @octoprint.plugin.BlueprintPlugin.route("/gcode/<int:identifier>", methods=["POST"])
    @restricted_access
    def requested_gcode_command(self, identifier):
        rpi_output = [r_out for r_out in self.rpi_outputs if self.to_int(r_out['index_id']) == identifier].pop()
        self.send_gcode_command(rpi_output['gcode'])
        return make_response('', 204)





    """
    DEPRECATION
    This API will be deprecated in a future version
    """

    # ~~ Blueprintplugin mixin
    @octoprint.plugin.BlueprintPlugin.route("/setEnclosureTempHum", methods=["GET"])
    def set_enclosure_temp_humidity_old(self):
        set_value = self.to_float(request.values["set_temperature"])
        index_id = self.to_int(request.values["index_id"])

        for temp_hum_control in [item for item in self.rpi_outputs if item['index_id'] == index_id]:
            temp_hum_control['temp_ctr_set_value'] = set_value

        self.handle_temp_hum_control()
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/clearGPIOMode", methods=["GET"])
    def clear_gpio_mode_old(self):
        GPIO.cleanup()
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/updateUI", methods=["GET"])
    def update_ui_requested_old(self):
        self.update_ui()
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/getOutputStatus", methods=["GET"])
    def get_output_status_old(self):
        gpio_status = []
        for rpi_output in self.rpi_outputs:
            if rpi_output['output_type'] == 'regular':
                pin = self.to_int(rpi_output['gpio_pin'])
                ActiveLow = rpi_output['active_low']
                if rpi_output['gpio_i2c_enabled']:
                    val = self.gpio_i2c_input(rpi_output, rpi_output['active_low'])
                else:
                    val = PinState_Boolean(pin, ActiveLow)
                val2 = PinState_Human(pin, ActiveLow)
                index = self.to_int(rpi_output['index_id'])
                gpio_status.append(dict(index_id=index, status=val, State=val2))
        return Response(json.dumps(gpio_status), mimetype='application/json')

    @octoprint.plugin.BlueprintPlugin.route("/setIO", methods=["GET"])
    def set_io_old(self):
        index = request.values["index_id"]
        value = True if request.values["status"] == 'true' else False
        for rpi_output in self.rpi_outputs:
            if self.to_int(index) == self.to_int(rpi_output['index_id']):
                val = (not value) if rpi_output['active_low'] else value
                if rpi_output['gpio_i2c_enabled']:
                    self.gpio_i2c_write(rpi_output, val)
                else:
                    self.write_gpio(self.to_int(rpi_output['gpio_pin']), val)
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/sendShellCommand", methods=["GET"])
    def send_shell_command_old(self):
        output_index = self.to_int(request.values["index_id"])

        rpi_output = [r_out for r_out in self.rpi_outputs if self.to_int(r_out['index_id']) == output_index].pop()

        command = rpi_output['shell_script']
        self.shell_command(command)
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setAutoStartUp", methods=["GET"])
    def set_auto_startup_old(self):
        index = request.values["index_id"]
        value = True if request.values["status"] == 'true' else False

        if not value:
            suffix = 'auto_startup'
            queue_id = '{0!s}_{1!s}'.format(index, suffix)
            self.stop_queue_item(queue_id)
        for output in self.rpi_outputs:
            if self.to_int(index) == self.to_int(output['index_id']):
                output['auto_startup'] = value
                self._logger.info("Setting auto startup for output %s to : %s", index, value)
        self._settings.set(["rpi_outputs"], self.rpi_outputs)
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setAutoShutdown", methods=["GET"])
    def set_auto_shutdown_old(self):
        index = request.values["index_id"]
        value = True if request.values["status"] == 'true' else False

        if not value:
            suffix = 'auto_shutdown'
            queue_id = '{0!s}_{1!s}'.format(index, suffix)
            self.stop_queue_item(queue_id)

        for output in self.rpi_outputs:
            if self.to_int(index) == self.to_int(output['index_id']):
                output['auto_shutdown'] = value
                self._logger.info("Setting auto shutdown for output %s to : %s", index, value)
        self._settings.set(["rpi_outputs"], self.rpi_outputs)
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setFilamentSensor", methods=["GET"])
    def set_filament_sensor_old(self):
        index = request.values["index_id"]
        value = True if request.values["status"] == 'true' else False
        for sensor in self.rpi_inputs:
            if self.to_int(index) == self.to_int(sensor['index_id']):
                sensor['filament_sensor_enabled'] = value
                self._logger.info("Setting filament sensor for input %s to : %s", index, value)
        self._settings.set(["rpi_inputs"], self.rpi_inputs)
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setPWM", methods=["GET"])
    def set_pwm_old(self):
        set_value = self.to_int(request.values["new_duty_cycle"])
        index_id = self.to_int(request.values["index_id"])
        for rpi_output in [item for item in self.rpi_outputs if item['index_id'] == index_id]:
            rpi_output['duty_cycle'] = set_value
            rpi_output['new_duty_cycle'] = ""
            gpio = self.to_int(rpi_output['gpio_pin'])
            self.write_pwm(gpio, set_value)
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/sendGcodeCommand", methods=["GET"])
    def requested_gcode_command_old(self):
        gpio_index = self.to_int(request.values["index_id"])
        rpi_output = [r_out for r_out in self.rpi_outputs if self.to_int(r_out['index_id']) == gpio_index].pop()
        self.send_gcode_command(rpi_output['gcode'])
        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setNeopixel", methods=["GET"])
    def set_neopixel_old(self):
        """ set_neopixel method get request from octoprint and send the command to arduino or neopixel"""
        gpio_index = self.to_int(request.values["index_id"])
        red = request.values["red"]
        green = request.values["green"]
        blue = request.values["blue"]
        for rpi_output in self.rpi_outputs:
            if gpio_index == self.to_int(rpi_output['index_id']):
                led_count = rpi_output['neopixel_count']
                led_brightness = rpi_output['neopixel_brightness']
                address = rpi_output['microcontroller_address']

                neopixel_dirrect = rpi_output['output_type'] == 'neopixel_direct'

                self.send_neopixel_command(self.to_int(rpi_output['gpio_pin']), led_count, led_brightness, red, green,
                    blue, address, neopixel_dirrect, gpio_index)

        return jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setLedstripColor", methods=["GET"])
    def set_ledstrip_color_old(self):
        """ set_ledstrip_color method get request from octoprint and send the command to Open-Smart RGB LED Strip"""
        gpio_index = self.to_int(request.values["index_id"])
        rgb = request.values["rgb"]
        for rpi_output in self.rpi_outputs:
            if gpio_index == self.to_int(rpi_output['index_id']):
                self.ledstrip_set_rgb(rpi_output, rgb)

        return jsonify(success=True)

    # DEPREACTION END


    # GPIO over i2c

    def gpio_i2c_input(self, output, active_low=None):
        state = False
        try:
            i2cbus = self.to_int(output['gpio_i2c_bus'])
            i2caddr = self.to_int(output['gpio_i2c_address'])
            i2creg = self.to_int(output['gpio_i2c_register_status'])
            data_on = self.to_int(output['gpio_i2c_data_on'])

            with SMBus(i2cbus) as bus:
                data = bus.read_i2c_block_data(i2caddr, i2creg, 1)
                if data[0] == data_on:
                    state = True

            self._logger.debug("gpio_i2c_input(i2cbus=%s, i2caddr=%s, i2creg=%s, data_on=%s) data == %s",
                                i2cbus, i2caddr, i2creg, data_on, data)

            if active_low is None and state: return state

        except Exception as ex:
            self.log_error(ex)

        if active_low and not state: return True
        if not active_low and state: return True
        return False

    def gpio_i2c_write(self, output, state, queue_id=None):
        try:
            i2cbus = self.to_int(output['gpio_i2c_bus'])
            i2caddr = self.to_int(output['gpio_i2c_address'])
            i2creg = self.to_int(output['gpio_i2c_register'])
            data_on = self.to_int(output['gpio_i2c_data_on'])
            data_off = self.to_int(output['gpio_i2c_data_off'])

            with SMBus(i2cbus) as bus:
                data = []
                if state:
                    data.append(data_on)
                else:
                    data.append(data_off)

                bus.write_i2c_block_data(i2caddr, i2creg, data)

            if queue_id is not None:
                self._logger.debug("Running scheduled queue id %s", queue_id)
            self._logger.debug("Writing on GPIO (i2c): %s/%s value %s", output['gpio_i2c_address'], output['gpio_i2c_register'], state)
            self.update_ui()
            if queue_id is not None:
                self.stop_queue_item(queue_id)

        except Exception as ex:
            template = "An exception of type {0} occurred on {1} when writing on i2c address {2}, reg {3}. Arguments:\n{4!r}"
            message = template.format(type(ex).__name__, inspect.currentframe().f_code.co_name, output['gpio_i2c_address'], output['gpio_i2c_register'], ex.args)
            self._logger.warn(message)
            pass


    def send_neopixel_command(self, led_pin, led_count, led_brightness, red, green, blue, address, neopixel_dirrect,
                              index_id, queue_id=None):
        """Send neopixel command
        Arguments:
            led_pin {int} -- GPIO number
            ledCount {int} -- number of LEDS
            ledBrightness {int} -- brightness from 0 to 255
            red {int} -- red value from 0 to 255
            green {int} -- green value from 0 to 255
            blue {int} -- blue value from 0 to 255
            address {int} -- i2c address from microcontroller
        """

        try:

            for rpi_output in self.rpi_outputs:
                if self.to_int(index_id) == self.to_int(rpi_output['index_id']):
                    rpi_output['neopixel_color'] = 'rgb({0!s},{1!s},{2!s})'.format(red, green, blue)

            if address == '':
                address = 0

            if neopixel_dirrect:
                script = os.path.dirname(os.path.realpath(__file__)) + "/neopixel_direct.py "
            else:
                script = os.path.dirname(os.path.realpath(__file__)) + "/neopixel_indirect.py "

            if self._settings.get(["use_sudo"]):
                sudo_str = "sudo "
            else:
                sudo_str = ""

            cmd = sudo_str + "python " + script + str(led_pin) + " " + str(led_count) + " " + str(
                led_brightness) + " " + str(red) + " " + str(green) + " " + str(blue) + " "

            if neopixel_dirrect:
                dma = self._settings.get(["neopixel_dma"]) or 10
                cmd = cmd + str(dma)
            else:
                cmd = cmd + str(address)

                if queue_id is not None:
                    self._logger.debug("running scheduled queue id %s", queue_id)
                self._logger.debug("Sending neopixel cmd: %s", cmd)
            Popen(cmd, shell=True)
            if queue_id is not None:
                self.stop_queue_item(queue_id)
        except Exception as ex:
            self.log_error(ex)

    def check_enclosure_temp(self):
        try:
            sensor_data = []
            for sensor in list(filter(lambda item: item['input_type'] == 'temperature_sensor', self.rpi_inputs)):
                temp, hum, airquality = self.get_sensor_data(sensor)
                if  self._settings.get(["debug_temperature_log"]) is True:
                    self._logger.debug("Sensor %s Temperature: %s humidity %s Airquality %s", sensor['label'], temp, hum, airquality)
                if temp is not None and hum is not None and airquality is not None:
                    sensor["temp_sensor_temp"] = temp
                    sensor["temp_sensor_humidity"] = hum
                    sensor_data.append(dict(index_id=sensor['index_id'], temperature=temp, humidity=hum, airquality=airquality))
                    self.temperature_sensor_data = sensor_data
                    self.handle_temp_hum_control()
                    self.handle_temperature_events()
                    self.handle_pwm_linked_temperature()
                    self.handle_emc_linked_temperature()
                    self.update_ui()
                    self.mqtt_sensor_topic = self.mqtt_root_topic + "/" + sensor['label']
                    self.mqtt_message = {"temperature":  temp, "humidity": hum}
                    self.mqtt_publish(self.mqtt_sensor_topic, self.mqtt_message)
        except Exception as ex:
            self.log_error(ex)

    def toggle_output(self, output_index, first_run=False):
        for output in [item for item in self.rpi_outputs if item['index_id'] == output_index]:
            gpio_pin = self.to_int(output['gpio_pin'])
            index_id = self.to_int(output['index_id'])

            if output['output_type'] == 'regular':
                if output['gpio_i2c_enabled']:
                    current_value = self.gpio_i2c_input(output)
                else:
                    if first_run:
                        current_value = False
                    else:
                        current_value = (not GPIO.input(gpio_pin)) if output['active_low'] else GPIO.input(gpio_pin)

                if current_value:
                    time_delay = self.to_int(output['toggle_timer_off'])
                else:
                    time_delay = self.to_int(output['toggle_timer_on'])

                if not self.print_complete:
                    if output['gpio_i2c_enabled']:
                        self.gpio_i2c_write(output, not current_value)
                    else:
                        self.write_gpio(gpio_pin, not current_value)
                    thread = threading.Timer(time_delay, self.toggle_output, args=[index_id])
                    thread.start()
                else:
                    off_value = True if output['active_low'] else False
                    if output['gpio_i2c_enabled']:
                        self.gpio_i2c_write(output, off_value)
                    else:
                        self.write_gpio(gpio_pin, off_value)
                self.update_ui_outputs()
                return

            if output['output_type'] == 'pwm':
                for pwm in self.pwm_instances:
                    if gpio_pin in pwm:
                        if first_run:
                            current_pwm_value = 0
                        else:
                            if 'duty_cycle' in pwm:
                                current_pwm_value = pwm['duty_cycle']
                                current_pwm_value = self.to_int(current_pwm_value)
                            else:
                                current_pwm_value = 0

                        if not current_pwm_value == 0:
                            time_delay = self.to_int(output['toggle_timer_off'])
                            write_value = 0
                        else:
                            time_delay = self.to_int(output['toggle_timer_on'])
                            write_value = self.to_int(output['default_duty_cycle'])

                        if not self.print_complete:
                            self.write_pwm(gpio_pin, write_value)
                            thread = threading.Timer(time_delay, self.toggle_output, args=[index_id])
                            thread.start()
                        else:
                            self.write_pwm(self.to_int(output['gpio_pin']), 0)
                        self.update_ui_outputs()
                        return

    def update_ui(self):
        self.update_ui_outputs()
        self.update_ui_current_temperature()
        self.update_ui_set_temperature()
        self.update_ui_inputs()

    def update_ui_current_temperature(self):
        self._plugin_manager.send_plugin_message(self._identifier, dict(sensor_data=self.temperature_sensor_data))

    def update_ui_set_temperature(self):
        result = []
        for temp_crt_output in list(filter(lambda item: item['output_type'] == 'temp_hum_control', self.rpi_outputs)):
            set_temperature = self.to_float(temp_crt_output['temp_ctr_set_value'])
            result.append(dict(index_id=temp_crt_output['index_id'], set_temperature=set_temperature))
            result.append(set_temperature)
        self._plugin_manager.send_plugin_message(self._identifier, dict(set_temperature=result))

    def stop_queue_item(self, queue_id):
        old_list = self.event_queue
        self._logger.debug("Stopping queue id %s...", queue_id)
        for task in self.event_queue:
            self._logger.debug("Queue id found...")
            if task['queue_id'] == queue_id:
                task['thread'].cancel()
                self.event_queue.remove(task)
                self._logger.debug("Queue id stopped and removed from list...")
                self._logger.debug("Old queue list: %s", old_list)
                self._logger.debug("New queue list: %s", self.event_queue)

    def update_ui_outputs(self):
        try:
            regular_status = []
            pwm_status = []
            neopixel_status = []
            temp_control_status = []
            for output in self.rpi_outputs:
                index = self.to_int(output['index_id'])
                pin = self.to_int(output['gpio_pin'])
                startup = output['auto_startup']
                shutdown = output['auto_shutdown']

                if output['output_type'] == 'regular':
                    if output['gpio_i2c_enabled']:
                        val = self.gpio_i2c_input(output)
                    else:
                        val = GPIO.input(pin) if not output['active_low'] else (not GPIO.input(pin))
                    regular_status.append(
                        dict(index_id=index, status=val, auto_startup=startup, auto_shutdown=shutdown))
                if output['output_type'] == 'temp_hum_control':
                    if output['gpio_i2c_enabled']:
                        val = self.gpio_i2c_input(output)
                    else:
                        val = GPIO.input(pin) if not output['active_low'] else (not GPIO.input(pin))
                    temp_control_status.append(
                        dict(index_id=index, status=val, auto_startup=startup, auto_shutdown=shutdown))
                if output['output_type'] == 'neopixel_indirect' or output['output_type'] == 'neopixel_direct':
                    val = output['neopixel_color']
                    neopixel_status.append(
                        dict(index_id=index, color=val, auto_startup=startup, auto_shutdown=shutdown))
                if output['output_type'] == 'pwm':
                    for pwm in self.pwm_instances:
                        if pin in pwm:
                            if 'duty_cycle' in pwm:
                                pwm_val = pwm['duty_cycle']
                                val = self.to_int(pwm_val)
                            else:
                                val = 0
                            pwm_status.append(
                                dict(index_id=index, pwm_value=val, auto_startup=startup, auto_shutdown=shutdown))
            self._plugin_manager.send_plugin_message(self._identifier,
                                                     dict(rpi_output_regular=regular_status, rpi_output_pwm=pwm_status,
                                                          rpi_output_neopixel=neopixel_status,
                                                          rpi_output_temp_hum_ctrl=temp_control_status))
        except Exception as ex:
            self.log_error(ex)

    def update_ui_inputs(self):
        try:
            sensor_status = []
            for sensor in self.rpi_inputs:
                if sensor['input_type'] == 'gpio' and sensor['action_type'] == 'printer_control' and sensor[
                    'printer_action'] == 'filament':
                    index = self.to_int(sensor['index_id'])
                    value = sensor['filament_sensor_enabled']
                    sensor_status.append(dict(index_id=index, filament_sensor_enabled=value))
            self._plugin_manager.send_plugin_message(self._identifier, dict(filament_sensor_status=sensor_status))
        except Exception as ex:
            self.log_error(ex)

    def get_sensor_data(self, sensor):
        try:
            if self.development_mode:
                temp, hum, airquality = self.read_dummy_temp()
            else:
                if sensor['temp_sensor_type'] in ["11", "22", "2302"]:
                    temp, hum = self.read_dht_temp(sensor['temp_sensor_type'], sensor['gpio_pin'])
                    airquality = 0
                elif sensor['temp_sensor_type'] == "20":
                    temp, hum = self.read_dht20_temp(sensor['temp_sensor_address'], sensor['temp_sensor_i2cbus'])
                    airquality = 0
                elif sensor['temp_sensor_type'] == "18b20":
                    temp = self.read_18b20_temp(sensor['ds18b20_serial'])
                    hum = 0
                    airquality = 0
                elif sensor['temp_sensor_type'] == "emc2101":
                    temp, hum = self.read_emc2101_temp(sensor['temp_sensor_address'], sensor['temp_sensor_i2cbus'])
                    hum =0
                    airquality = 0
                elif sensor['temp_sensor_type'] == "bme280":
                    temp, hum = self.read_bme280_temp(sensor['temp_sensor_address'])
                    airquality = 0
                elif sensor['temp_sensor_type'] == "bme680":
                    temp, hum, airquality = self.read_bme680_temp(sensor['temp_sensor_address'])
                elif sensor['temp_sensor_type'] == "am2320":
                    temp, hum = self.read_am2320_temp() # sensor has fixed address
                    airquality = 0
                elif sensor['temp_sensor_type'] == "aht10":
                    temp, hum = self.read_aht10_temp(sensor['temp_sensor_address'], sensor['temp_sensor_i2cbus'])
                    airquality = 0
                elif sensor['temp_sensor_type'] == "rpi":
                    temp = self.read_rpi_temp() # rpi CPU Temp
                    hum = 0
                    airquality = 0
                elif sensor['temp_sensor_type'] == "si7021":
                    temp, hum = self.read_si7021_temp(sensor['temp_sensor_address'], sensor['temp_sensor_i2cbus'])
                    airquality = 0
                elif sensor['temp_sensor_type'] == "tmp102":
                    temp = self.read_tmp102_temp(sensor['temp_sensor_address'])
                    hum = 0
                    airquality = 0
                elif sensor['temp_sensor_type'] == "max31855":
                    temp = self.read_max31855_temp(sensor['temp_sensor_address'])
                    hum = 0
                    airquality = 0
                elif sensor['temp_sensor_type'] == "mcp9808":
                    temp = self.read_mcp_temp(sensor['temp_sensor_address'], sensor['temp_sensor_i2cbus'])
                    hum = 0
                    airquality = 0
                elif sensor['temp_sensor_type'] == "temp_raw_i2c":
                    temp, hum = self.read_raw_i2c_temp(sensor)
                    airquality = 0
                elif sensor['temp_sensor_type'] == "hum_raw_i2c":
                    hum, temp = self.read_raw_i2c_temp(sensor)
                    airquality = 0
                else:
                    self._logger.info("temp_sensor_type no match")
                    temp = None
                    hum = None
                    airquality = 0
            if temp != -1 and hum != -1 and airquality != -1:
                temp = round(self.to_float(temp), 1) if not sensor['use_fahrenheit'] else round(
                    self.to_float(temp) * 1.8 + 32, 1)
                hum = round(self.to_float(hum), 1)
                airquality = round(self.to_float(airquality), 1)
                return temp, hum, airquality
            return None, None, None
        except Exception as ex:
            self.log_error(ex)

    def handle_temperature_events(self):
        for temperature_alarm in [item for item in self.rpi_outputs if item['output_type'] == 'temperature_alarm']:
            set_temperature = self.to_float(temperature_alarm['alarm_set_temp'])
            if int(set_temperature) is 0:
                continue
            linked_data = [item for item in self.temperature_sensor_data if
                           item['index_id'] == temperature_alarm['linked_temp_sensor']].pop()
            sensor_temperature = self.to_float(linked_data['temperature'])
            if set_temperature < sensor_temperature:
                for rpi_controlled_output in self.rpi_outputs:
                    if self.to_int(temperature_alarm['controlled_io']) == self.to_int(
                            rpi_controlled_output['index_id']):
                        if rpi_controlled_output['gpio_i2c_enabled']:
                            val = False if temperature_alarm['controlled_io_set_value'] == 'low' else True
                            self.gpio_i2c_write(rpi_controlled_output, val)
                        else:
                            val = GPIO.LOW if temperature_alarm['controlled_io_set_value'] == 'low' else GPIO.HIGH
                            self.write_gpio(self.to_int(rpi_controlled_output['gpio_pin']), val)
                        for notification in self.notifications:
                            if notification['temperatureAction']:
                                msg = ("Temperature action: enclosure temperature exceed " + temperature_alarm[
                                    'alarm_set_temp'])
                                self.send_notification(msg)

    def read_dummy_temp(self):
        current_value = self.dummy_value
        if current_value > 40 or current_value < 30:
            self.dummy_delta = - self.dummy_delta

        return_value = current_value + self.dummy_delta

        self.dummy_value = return_value

        return return_value, return_value, return_value

    def read_raw_i2c_temp(self, sensor):
        try:
            i2cbus = self.to_int(sensor['temp_i2c_bus'])
            i2caddr = self.to_int(sensor['temp_i2c_address'])
            i2creg = self.to_int(sensor['temp_i2c_register'])

            with SMBus(i2cbus) as bus:
                data = bus.read_i2c_block_data(i2caddr, i2creg, 8)
                fval1 = struct.unpack('f', bytearray(data[0:4]))[0]
                if fval1 != fval1:
                    fval1 = 0
                fval2 = struct.unpack('f', bytearray(data[4:8]))[0]
                if fval2 != fval2:
                    fval2 = 0
                
                self._logger.debug("read_raw_i2c_temp(i2cbus=%s, i2caddr=%s, i2creg=%s) data == %s (%s, %s)",
                                    i2cbus, i2caddr, i2creg, data, fval1, fval2)

                return (fval1, fval2)

        except Exception as ex:
            template = "An exception of type {0} occurred on {1} when reading on i2c address {2}, reg {3}. Arguments:\n{4!r}"
            message = template.format(type(ex).__name__, inspect.currentframe().f_code.co_name, i2caddr, i2creg, ex.args)
            self._logger.warn(message)
            return str(-1)

    def read_mcp_temp(self, address, i2cbus):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/mcp9808.py"
            args = ["python", script, str(i2cbus), str(address)]
            if self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature MCP9808 cmd: %s", " ".join(args))
            proc = Popen(args, stdout=PIPE)
            stdout, _ = proc.communicate()
            if self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("MCP9808 result: %s", stdout)
            return self.to_float(stdout.decode("utf-8").strip())
        except Exception as ex:
            self._logger.info("Failed to execute python scripts, try disabling use SUDO on advanced section.")
            self.log_error(ex)
            return 0

    def read_dht_temp(self, sensor, pin):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/getDHTTemp.py "
            if self._settings.get(["use_sudo"]):
                sudo_str = "sudo "
            else:
                sudo_str = ""
            cmd = sudo_str + "python3 " + script + str(sensor) + " " + str(pin)
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature dht cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Dht result: %s", stdout)
            temp, hum = stdout.decode("utf-8").split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0)

    def read_dht20_temp(self, address, i2cbus):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/DHT20.py "
            if self._settings.get(["use_sudo"]):
                sudo_str = "sudo "
            else:
                sudo_str = ""
            cmd = sudo_str + "python " + script + str(address) + " " + str(i2cbus)
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature DHT20 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("DHT20 result: %s", stdout)
            temp, hum = stdout.decode("utf-8").split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0)

    def read_bme280_temp(self, address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/BME280.py"
            cmd = [sys.executable, script, str(address)]
            if self._settings.get(["use_sudo"]):
                cmd.insert(0, "sudo")
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature BME280 cmd: %s", cmd)

            stdout = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            output, errors = stdout.communicate()

            if self._settings.get(["debug_temperature_log"]) is True:
                if len(errors) > 0:
                    self._logger.error("BME280 error: %s", errors)
                else:
                    self._logger.debug("BME280 result: %s", output)

            temp, hum = output.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0)

    def read_bme680_temp(self, address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/BME680.py"
            cmd = [sys.executable, script, str(address)]
            if self._settings.get(["use_sudo"]):
                cmd.insert(0, "sudo")
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature BME680 cmd: %s", cmd)

            stdout = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            output, errors = stdout.communicate()

            if  self._settings.get(["debug_temperature_log"]) is True:
                if len(errors) > 0:
                    self._logger.error("BME680 error: %s", errors)
                else:
                    self._logger.debug("BME680 result: %s", output)
            temp, hum, airq = output.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()), self.to_float(airq.strip()))
        except Exception as ex:
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0, 0)

    def read_am2320_temp(self):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/AM2320.py "
            if self._settings.get(["use_sudo"]):
                sudo_str = "sudo "
            else:
                sudo_str = ""
            cmd = sudo_str + "python " + script # sensor has fixed address 0x5C
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature AM2320 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("AM2320 result: %s", stdout)
            temp, hum = stdout.decode("utf-8").split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0)
            
    def read_emc2101_temp(self, address, i2cbus):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/EMC2101.py"
            cmd = [sys.executable, script, str(address), str(i2cbus)]
            if self._settings.get(["use_sudo"]):
                 cmd.insert(0, "sudo")
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature EMC2101 cmd: %s", cmd)
            stdout = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            output, errors = stdout.communicate()
            if self._settings.get(["debug_temperature_log"]) is True:
                if len(errors) > 0:
                    self._logger.error("EMC2101 error: %s", errors)
                else:
                    self._logger.debug("EMC2101 result: %s", output)
            temp, fanspeed = output.split("|")
            print (temp + " , " + fanspeed )
            return (self.to_float(temp.strip()), 0.0 )
        except Exception as ex:
            print(ex)
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0)

    def read_aht10_temp(self, address, i2cbus):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/AHT10.py"
            cmd = [sys.executable, script, str(address), str(i2cbus)]
            if self._settings.get(["use_sudo"]):
                 cmd.insert(0, "sudo")
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature AHT10 cmd: %s", cmd)
            self._logger.debug(cmd)
            stdout = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            output, errors = stdout.communicate()
            if self._settings.get(["debug_temperature_log"]) is True:
                if len(errors) > 0:
                    self._logger.error("AHT10 error: %s", errors)
                else:
                    self._logger.debug("AHT10 result: %s", output)
            self._logger.debug(output + " " + errors)
            temp, hum = output.split("|")
            print (temp + " , " + hum )
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            print(ex)
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0)

    def read_rpi_temp(self):
        try:
            pitemp = PiTemp()
            temp = pitemp.getTemp()
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Pi CPU result: %s", temp)
            return temp
        except Exception as ex:
            self._logger.info(
                "Failed to get pi cpu temperature")
            self.log_error(ex)
            return 0

    def read_si7021_temp(self, address, i2cbus):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/SI7021.py "
            if self._settings.get(["use_sudo"]):
                sudo_str = "sudo "
            else:
                sudo_str = ""
            cmd = sudo_str + "python " + script + str(address) + " " + str(i2cbus)
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature SI7021 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("SI7021 result: %s", stdout)
            temp, hum = stdout.decode("utf-8").split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            self._logger.info(
                "Failed to execute python scripts, try disabling use SUDO on advanced section of the plugin.")
            self.log_error(ex)
            return (0, 0)

    def read_18b20_temp(self, serial_number):
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')

        lines = self.read_raw_18b20_temp(serial_number)
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = self.read_raw_18b20_temp(serial_number)
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            temp_c = float(temp_string) / 1000.
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("DS18B20 result: %s", temp_c)
            return '{0:0.1f}'.format(temp_c)
        return 0

    def read_raw_18b20_temp(self, serial_number):
        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + str(serial_number) + '*')[0]
        device_file = device_folder + '/w1_slave'
        device_file_result = open(device_file, 'r')
        lines = device_file_result.readlines()
        device_file_result.close()
        return lines

    def read_tmp102_temp(self, address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/tmp102.py"
            args = ["python", script, str(address)]
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature TMP102 cmd: %s", " ".join(args))
            proc = Popen(args, stdout=PIPE)
            stdout, _ = proc.communicate()
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("TMP102 result: %s", stdout)
            return self.to_float(stdout.decode("utf-8").strip())
        except Exception as ex:
            self._logger.info("Failed to execute python scripts, try disabling use SUDO on advanced section.")
            self.log_error(ex)
            return 0

    def read_max31855_temp(self, address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/max31855.py"
            args = ["python", script, str(address)]
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("Temperature MAX31855 cmd: %s", " ".join(args))
            proc = Popen(args, stdout=PIPE)
            stdout, _ = proc.communicate()
            if  self._settings.get(["debug_temperature_log"]) is True:
                self._logger.debug("MAX31855 result: %s", stdout)
            return self.to_float(stdout.decode("utf-8").strip())
        except Exception as ex:
            self._logger.info("Failed to execute python scripts, try disabling use SUDO on advanced section.")
            self.log_error(ex)
            return 0



    def handle_emc_linked_temperature(self):
        try:
            for pwm_output in list(filter(lambda item: item['output_type'] == 'emc',
                                          self.rpi_outputs)):
                if self._printer.is_printing():
                    index_id = self.to_int(pwm_output['index_id'])
                    linked_id = self.to_int(pwm_output['linked_temp_sensor'])
                    linked_data = self.get_linked_temp_sensor_data(linked_id)
                    current_temp = self.to_float(linked_data['temperature'])

                    duty_a = self.to_float(pwm_output['duty_a'])
                    duty_b = self.to_float(pwm_output['duty_b'])
                    temp_a = self.to_float(pwm_output['temperature_a'])
                    temp_b = self.to_float(pwm_output['temperature_b'])

                    try:
                        calculated_duty = ((current_temp - temp_a) * (duty_b - duty_a) / (temp_b - temp_a)) + duty_a

                        if current_temp < temp_a:
                            calculated_duty = 0
                    except:
                        calculated_duty = 0

                    self._logger.debug("Calculated duty for EMC %s is %s", index_id, calculated_duty)
                elif self.print_complete:
                    calculated_duty = self.to_int(pwm_output['default_duty_cycle'])
                else:
                    calculated_duty = self.to_int(pwm_output['default_duty_cycle'])
            script = os.path.dirname(os.path.realpath(__file__)) + "/SETEMC2101.py"
            cmd = [sys.executable, script, str(int(calculated_duty))]
            if self._settings.get(["use_sudo"]):
                cmd.insert(0, "sudo")
            self._logger.info("Calculated fan speed is ", calculated_duty)
            stdout = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            output, errors = stdout.communicate()
            if self._settings.get(["debug_temperature_log"]) is True:
                if len(errors) > 0:
                    self._logger.error("EMC2101 error: %s", errors)
                else:
                    self._logger.debug("EMC2101 result: %s", output)
            self._logger.debug(output + " " + errors)
        

        except Exception as ex:
            self.log_error(ex)


    def handle_pwm_linked_temperature(self):
        try:
            for pwm_output in list(filter(lambda item: item['output_type'] == 'pwm' and item['pwm_temperature_linked'],
                                          self.rpi_outputs)):
                gpio_pin = self.to_int(pwm_output['gpio_pin'])
                if self._printer.is_printing():
                    index_id = self.to_int(pwm_output['index_id'])
                    linked_id = self.to_int(pwm_output['linked_temp_sensor'])
                    linked_data = self.get_linked_temp_sensor_data(linked_id)
                    current_temp = self.to_float(linked_data['temperature'])

                    duty_a = self.to_float(pwm_output['duty_a'])
                    duty_b = self.to_float(pwm_output['duty_b'])
                    temp_a = self.to_float(pwm_output['temperature_a'])
                    temp_b = self.to_float(pwm_output['temperature_b'])

                    try:
                        calculated_duty = ((current_temp - temp_a) * (duty_b - duty_a) / (temp_b - temp_a)) + duty_a

                        if current_temp < temp_a:
                            calculated_duty = 0
                    except:
                        calculated_duty = 0

                    self._logger.debug("Calculated duty for PWM %s is %s", index_id, calculated_duty)
                elif self.print_complete:
                    calculated_duty = self.to_int(pwm_output['duty_cycle'])
                else:
                    calculated_duty = 0

                self.write_pwm(gpio_pin, self.constrain(calculated_duty, 0, 100))

        except Exception as ex:
            self.log_error(ex)

    def get_linked_temp_sensor_data(self, linked_id):
        try:
            linked_data = [data for data in self.temperature_sensor_data if data['index_id'] == linked_id].pop()
            return linked_data
        except:
            self._logger.warn("No linked temperature sensor found for %s", linked_id)
            return None

    def handle_temp_hum_control(self):
        try:
            for temp_hum_control in list(
                    filter(lambda item: item['output_type'] == 'temp_hum_control', self.rpi_outputs)):

                set_temperature = self.to_float(temp_hum_control['temp_ctr_set_value'])
                temp_deadband = self.to_float(temp_hum_control['temp_ctr_deadband'])
                max_temp = self.to_float(temp_hum_control['temp_ctr_max_temp'])

                linked_id = temp_hum_control['linked_temp_sensor']

                previous_status = list(filter(lambda item: item['index_id'] == temp_hum_control['index_id'],
                    self.temp_hum_control_status)).pop()['status']

                if set_temperature == 0:
                    current_status = False
                else:
                    linked_data = self.get_linked_temp_sensor_data(linked_id)

                    control_type = str(temp_hum_control['temp_ctr_type'])

                    if control_type == 'dehumidifier':
                        current_value = self.to_float(linked_data['humidity'])
                        temp_deadband = 0
                    else:
                        current_value = self.to_float(linked_data['temperature'])

                    if control_type == 'cooler' or control_type == 'dehumidifier':
                        if current_value <= set_temperature and current_value >= (set_temperature - temp_deadband):
                            current_status = previous_status
                        elif current_value < set_temperature:
                            current_status = False
                        else:
                            current_status = True
                    else:
                        if current_value <= set_temperature and current_value >= (set_temperature - temp_deadband):
                            current_status = previous_status
                        elif current_value > set_temperature:
                            current_status = False
                        else:
                            current_status = True

                    if control_type == 'heater' and max_temp > 0.0 and max_temp < current_value:
                        self._logger.debug("Maximum temperature reached for temperature control %s",
                                temp_hum_control['index_id'])
                        temp_hum_control['temp_ctr_set_value'] = 0
                        current_status = False

                if current_status != previous_status:
                    if current_status:
                        self._logger.info("Turning gpio to control temperature on.")
                        val = False if temp_hum_control['active_low'] else True
                        if temp_hum_control['gpio_i2c_enabled']:
                            self.gpio_i2c_write(temp_hum_control, val)
                        else:
                            self.write_gpio(self.to_int(temp_hum_control['gpio_pin']), val)
                    else:
                        index_id = temp_hum_control['index_id']
                        if index_id in self.waiting_temperature:
                            self.waiting_temperature.remove(index_id)

                        if not self.waiting_temperature and self._printer.is_paused():
                            self._printer.resume_print()

                        self._logger.info("Turning gpio to control temperature off.")
                        val = True if temp_hum_control['active_low'] else False
                        if temp_hum_control['gpio_i2c_enabled']:
                            self.gpio_i2c_write(temp_hum_control, val)
                        else:
                            self.write_gpio(self.to_int(temp_hum_control['gpio_pin']), val)
                    for control_status in self.temp_hum_control_status:
                        if control_status['index_id'] == temp_hum_control['index_id']:
                            control_status['status'] = current_status
        except Exception as ex:
            self.log_error(ex)

    def log_error(self, ex):
        template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
        message = template.format(type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
        self._logger.warn(message, exc_info = True)

    def setup_gpio(self):
        try:
            current_mode = GPIO.getmode()
            set_mode = GPIO.BOARD if self._settings.get(["use_board_pin_number"]) else GPIO.BCM
            if current_mode is None:
                outputs = list(filter(
                    lambda item: (item['output_type'] == 'regular' or item['output_type'] == 'pwm' or item[
                        'output_type'] == 'temp_hum_control' or item['output_type'] == 'neopixel_direct') and
                        item['gpio_i2c_enabled'] == False,
                    self.rpi_outputs))
                inputs = list(filter(lambda item: item['input_type'] == 'gpio', self.rpi_inputs))
                gpios = outputs + inputs
                if gpios:
                    GPIO.setmode(set_mode)
                    tempstr = "BOARD" if set_mode == GPIO.BOARD else "BCM"
                    self._logger.info("Setting GPIO mode to %s", tempstr)
            elif current_mode != set_mode:
                GPIO.setmode(current_mode)
                tempstr = "BOARD" if current_mode == GPIO.BOARD else "BCM"
                self._settings.set(["use_board_pin_number"], True if current_mode == GPIO.BOARD else False)
                warn_msg = "GPIO mode was configured before, GPIO mode will be forced to use: " + tempstr + " as pin numbers. Please update GPIO accordingly!"
                self._logger.info(warn_msg)
                self._plugin_manager.send_plugin_message(self._identifier,
                    dict(is_msg=True, msg=warn_msg, msg_type="error"))
            GPIO.setwarnings(False)
        except Exception as ex:
            self.log_error(ex)

    def clear_gpio(self):
        try:

            for gpio_out in list(filter(
                    lambda item: (item['output_type'] == 'regular' or item['output_type'] == 'pwm' or item[
                        'output_type'] == 'temp_hum_control' or item['output_type'] == 'neopixel_direct') and
                        item['gpio_i2c_enabled'] == False,
                    self.rpi_outputs)):
                gpio_pin = self.to_int(gpio_out['gpio_pin'])
                if gpio_pin not in self.rpi_outputs_not_changed:
                    GPIO.cleanup(gpio_pin)

            for gpio_in in list(filter(lambda item: item['input_type'] == 'gpio', self.rpi_inputs)):
                try:
                    GPIO.remove_event_detect(self.to_int(gpio_in['gpio_pin']))
                except:
                    pass
                GPIO.cleanup(self.to_int(gpio_in['gpio_pin']))
        except Exception as ex:
            self.log_error(ex)

    def clear_channel(self, channel):
        try:
            GPIO.cleanup(self.to_int(channel))
            self._logger.debug("Clearing channel %s", channel)
        except Exception as ex:
            self.log_error(ex)

    def generate_temp_hum_control_status(self):
        status = []
        for temp_hum_control in list(filter(lambda item: item['output_type'] == 'temp_hum_control', self.rpi_outputs)):
            status.append(dict(index_id=temp_hum_control['index_id'], status=False))
        self.temp_hum_control_status = status

    def configure_gpio(self):
        try:

            for gpio_out in list(
                    filter(lambda item: (item['output_type'] == 'regular' or item['output_type'] == 'temp_hum_control') and
                            item['gpio_i2c_enabled'] == False,
                           self.rpi_outputs)):
                initial_value = GPIO.HIGH if gpio_out['active_low'] else GPIO.LOW
                pin = self.to_int(gpio_out['gpio_pin'])
                if pin not in self.rpi_outputs_not_changed:
                    self._logger.info("Setting GPIO pin %s as OUTPUT with initial value: %s", pin, initial_value)
                    GPIO.setup(pin, GPIO.OUT, initial=initial_value)
            for gpio_out_pwm in list(filter(lambda item: item['output_type'] == 'pwm', self.rpi_outputs)):
                pin = self.to_int(gpio_out_pwm['gpio_pin'])
                self._logger.info("Setting GPIO pin %s as PWM", pin)
                for pwm in (pwm_dict for pwm_dict in self.pwm_instances if pin in pwm_dict):
                    self.pwm_instances.remove(pwm)
                self.clear_channel(pin)
                GPIO.setup(pin, GPIO.OUT)
                pwm_instance = GPIO.PWM(pin, self.to_int(gpio_out_pwm['pwm_frequency']))
                self._logger.info("starting PWM on pin %s", pin)
                pwm_instance.start(0)
                self.pwm_instances.append({pin: pwm_instance})
            for gpio_out_neopixel in list(
                    filter(lambda item: item['output_type'] == 'neopixel_direct', self.rpi_outputs)):
                pin = self.to_int(gpio_out_neopixel['gpio_pin'])
                self.clear_channel(pin)

            for rpi_input in list(filter(lambda item: item['input_type'] == 'gpio', self.rpi_inputs)):
                gpio_pin = self.to_int(rpi_input['gpio_pin'])
                pull_resistor = GPIO.PUD_UP if rpi_input['input_pull_resistor'] == 'input_pull_up' else GPIO.PUD_DOWN
                GPIO.setup(gpio_pin, GPIO.IN, pull_resistor)
                edge = GPIO.RISING if rpi_input['edge'] == 'rise' else GPIO.FALLING

                inputs_same_gpio = list(
                    [r_inp for r_inp in self.rpi_inputs if self.to_int(r_inp['gpio_pin']) == gpio_pin])

                if len(inputs_same_gpio) > 1:
                    GPIO.remove_event_detect(gpio_pin)
                    for other_input in inputs_same_gpio:
                        if other_input['edge'] is not edge:
                            edge = GPIO.BOTH

                if rpi_input['action_type'] == 'output_control':
                    self._logger.info("Adding GPIO event detect on pin %s with edge: %s", gpio_pin, edge)
                    GPIO.add_event_detect(gpio_pin, edge, callback=self.handle_gpio_control, bouncetime=200)
                if (rpi_input['action_type'] == 'printer_control' and rpi_input['printer_action'] != 'filament'):
                    GPIO.add_event_detect(gpio_pin, edge, callback=self.handle_printer_action, bouncetime=200)
                    self._logger.info("Adding PRINTER CONTROL event detect on pin %s with edge: %s", gpio_pin, edge)
            
            for rpi_input in list(filter(lambda item: item['input_type'] == 'temperature_sensor', self.rpi_inputs)):
                gpio_pin = self.to_int(rpi_input['gpio_pin'])
                if rpi_input['input_pull_resistor'] == 'input_pull_up':
                    pull_resistor = GPIO.PUD_UP
                elif rpi_input['input_pull_resistor'] == 'input_pull_down':
                    pull_resistor = GPIO.PUD_DOWN
                else:
                    pull_resistor = GPIO.PUD_OFF
                GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=pull_resistor)
        except Exception as ex:
            self.log_error(ex)

    def handle_filamment_detection(self, channel):
        try:
            for filament_sensor in list(filter(
                    lambda item: item['input_type'] == 'gpio' and item['action_type'] == 'printer_control' and item[
                        'printer_action'] == 'filament' and self.to_int(item['gpio_pin']) == self.to_int(channel),
                    self.rpi_inputs)):
                if ((filament_sensor['edge'] == 'fall') ^ (GPIO.input(self.to_int(filament_sensor['gpio_pin']))) and
                        filament_sensor['filament_sensor_enabled']):
                    last_detected_time = list(filter(lambda item: item['index_id'] == filament_sensor['index_id'],
                                                     self.last_filament_end_detected)).pop()['time']
                    time_now = time.time()
                    time_difference = self.to_int(time_now - last_detected_time)
                    time_out_value = self.to_int(filament_sensor['filament_sensor_timeout'])
                    if time_difference > time_out_value:
                        self._logger.info("Detected end of filament.")
                        for item in self.last_filament_end_detected:
                            if item['index_id'] == filament_sensor['index_id']:
                                item['time'] = time_now
                        for line in self._settings.get(["filament_sensor_gcode"]).split('\n'):
                            if line:
                                self._printer.commands(line.strip())
                                self._logger.info("Sending GCODE command: %s", line.strip())
                                time.sleep(0.2)
                        for notification in self.notifications:
                            if notification['filamentChange']:
                                msg = "Filament change action caused by sensor: " + str(filament_sensor['label'])
                                self.send_notification(msg)
                    else:
                        self._logger.info("Prevented end of filament detection, filament sensor timeout not elapsed.")
        except Exception as ex:
            self.log_error(ex)

    def start_filament_detection(self):
        self.stop_filament_detection()
        try:
            for filament_sensor in list(filter(
                    lambda item: item['input_type'] == 'gpio' and item['action_type'] == 'printer_control' and item[
                        'printer_action'] == 'filament', self.rpi_inputs)):
                edge = GPIO.RISING if filament_sensor['edge'] == 'rise' else GPIO.FALLING
                if GPIO.input(self.to_int(filament_sensor['gpio_pin'])) == (edge == GPIO.RISING):
                    self._printer.pause_print()
                    self._logger.info("Started printing with no filament.")
                else:
                    self.last_filament_end_detected.append(dict(index_id=filament_sensor['index_id'], time=0))
                    self._logger.info("Adding GPIO event detect on pin %s with edge: %s", filament_sensor['gpio_pin'],
                        edge)
                    GPIO.add_event_detect(self.to_int(filament_sensor['gpio_pin']), edge,
                        callback=self.handle_filamment_detection, bouncetime=200)
        except Exception as ex:
            self.log_error(ex)

    def stop_filament_detection(self):
        try:
            self.last_filament_end_detected = []
            for filament_sensor in list(filter(
                    lambda item: item['input_type'] == 'gpio' and item['action_type'] == 'printer_control' and item[
                        'printer_action'] == 'filament', self.rpi_inputs)):
                GPIO.remove_event_detect(self.to_int(filament_sensor['gpio_pin']))
        except Exception as ex:
            self.log_error(ex)

    def cancel_all_events_on_queue(self):
        for task in self.event_queue:
            try:
                task['thread'].cancel()
            except:
                self._logger.warn("Failed to stop task %s.", task)
                pass

    def handle_initial_gpio_control(self):
        try:
            for rpi_input in list(
                    filter(lambda item: item['input_type'] == 'gpio' and item['action_type'] == 'output_control',
                           self.rpi_inputs)):
                gpio_pin = self.to_int(rpi_input['gpio_pin'])
                controlled_io = self.to_int(rpi_input['controlled_io'])
                if (rpi_input['edge'] == 'fall') ^ GPIO.input(gpio_pin):
                    rpi_output = [r_out for r_out in self.rpi_outputs if
                                  self.to_int(r_out['index_id']) == controlled_io].pop()
                    if rpi_output['output_type'] == 'regular':
                        if rpi_output['gpio_i2c_enabled']:
                            val = False if rpi_input['controlled_io_set_value'] == 'low' else True
                            self.gpio_i2c_write(rpi_output, val)    
                        else:
                            val = GPIO.LOW if rpi_input['controlled_io_set_value'] == 'low' else GPIO.HIGH
                            self.write_gpio(self.to_int(rpi_output['gpio_pin']), val)
        except Exception as ex:
            self.log_error(ex)
            pass

    def shell_command(self, command):
        try:
            stdout = (Popen(command, shell=True, stdout=PIPE).stdout).read()
            self._plugin_manager.send_plugin_message(self._identifier,
                dict(is_msg=True, msg=stdout, msg_type="success"))
        except Exception as ex:
            self.log_error(ex)
            self._plugin_manager.send_plugin_message(self._identifier,
                dict(is_msg=True, msg="Could not execute shell script", msg_type="error"))

    def handle_gpio_control(self, channel):

        try:
            self._logger.debug("GPIO event triggered on channel %s", channel)
            for rpi_input in list(
                    filter(lambda item: self.to_int(item['gpio_pin']) == self.to_int(channel), self.rpi_inputs)):
                gpio_pin = self.to_int(rpi_input['gpio_pin'])
                controlled_io = self.to_int(rpi_input['controlled_io'])
                if (rpi_input['edge'] == 'fall') ^ GPIO.input(gpio_pin):
                    rpi_output = [r_out for r_out in self.rpi_outputs if
                                  self.to_int(r_out['index_id']) == controlled_io].pop()
                    if rpi_output['output_type'] == 'regular':
                        if rpi_input['controlled_io_set_value'] == 'toggle':
                            val = GPIO.LOW if GPIO.input(
                                self.to_int(rpi_output['gpio_pin'])) == GPIO.HIGH else GPIO.HIGH
                        else:
                            val = GPIO.LOW if rpi_input['controlled_io_set_value'] == 'low' else GPIO.HIGH
                        if rpi_output['gpio_i2c_enabled']:
                            self.gpio_i2c_write(rpi_output, val)
                        else:
                            self.write_gpio(self.to_int(rpi_output['gpio_pin']), val)
                        for notification in self.notifications:
                            if notification['gpioAction']:
                                msg = "GPIO control action caused by input " + str(
                                    rpi_input['label']) + ". Setting GPIO" + str(
                                    rpi_input['controlled_io']) + " to: " + str(rpi_input['controlled_io_set_value'])
                                self.send_notification(msg)
                    if rpi_output['output_type'] == 'gcode_output':
                        self.send_gcode_command(rpi_output['gcode'])
                        for notification in self.notifications:
                            if notification['gpioAction']:
                                msg = "GPIO control action caused by input " + str(
                                    rpi_input['label']) + ". Sending GCODE command"
                                self.send_notification(msg)
                    if rpi_output['output_type'] == 'shell_output':
                        command = rpi_output['shell_script']
                        self.shell_command(command)
        except Exception as ex:
            self.log_error(ex)
            pass

    def send_gcode_command(self, command):
        for line in command.split('\n'):
            if line:
                self._printer.commands(line.strip())
                self._logger.info("Sending GCODE command: %s", line.strip())
                time.sleep(0.2)

    def handle_printer_action(self, channel):
        try:
            for rpi_input in self.rpi_inputs:
                if (channel == self.to_int(rpi_input['gpio_pin']) and rpi_input[
                    'action_type'] == 'printer_control' and (
                        (rpi_input['edge'] == 'fall') ^ GPIO.input(self.to_int(rpi_input['gpio_pin'])))):
                    if rpi_input['printer_action'] == 'resume':
                        self._logger.info("Printer action resume.")
                        self._printer.resume_print()
                    elif rpi_input['printer_action'] == 'pause':
                        self._logger.info("Printer action pause.")
                        self._printer.pause_print()
                    elif rpi_input['printer_action'] == 'cancel':
                        self._logger.info("Printer action cancel.")
                        self._printer.cancel_print()
                    elif rpi_input['printer_action'] == 'toggle':
                        self._logger.info("Printer action toggle.")
                        if self._printer.is_operational():
                            self._printer.toggle_pause_print()
                        else:
                            self._printer.connect()
                    elif rpi_input['printer_action'] == 'start':
                        self._logger.info("Printer action start.")
                        self._printer.start_print()
                    elif rpi_input['printer_action'] == 'toggle_job':
                        self._logger.info("Printer action toggle_job.")
                        if self._printer.is_operational():
                            if self._printer.is_printing():
                                self._printer.cancel_print()
                            elif self._printer.is_ready():
                                self._printer.start_print()
                        else:
                            self._printer.connect()
                    elif rpi_input['printer_action'] == 'stop_temp_hum_control':
                        self._logger.info("Printer action stopping temperature control.")
                        for rpi_output in self.rpi_outputs:
                            if rpi_output['auto_shutdown'] and rpi_output['output_type'] == 'temp_hum_control':
                                rpi_output['temp_ctr_set_value'] = 0
                        self.handle_temp_hum_control()
                    for notification in self.notifications:
                        if notification['printer_action']:
                            msg = "Printer action: " + rpi_input['printer_action'] + " caused by input: " + str(
                                rpi_input['label'])
                            self.send_notification(msg)
        except Exception as ex:
            self.log_error(ex)
            pass

    def write_gpio(self, gpio, value, queue_id=None):
        try:
            GPIO.output(gpio, value)
            if queue_id is not None:
                self._logger.debug("Running scheduled queue id %s", queue_id)
            self._logger.debug("Writing on GPIO: %s value %s", gpio, value)
            self.update_ui()
            if queue_id is not None:
                self.stop_queue_item(queue_id)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1} when writing on pin {2}. Arguments:\n{3!r}"
            message = template.format(type(ex).__name__, inspect.currentframe().f_code.co_name, gpio, ex.args)
            self._logger.warn(message)
            pass

    def write_pwm(self, gpio, pwm_value, queue_id=None):
        try:
            if queue_id is not None:
                self._logger.debug("running scheduled queue id %s", queue_id)
            for pwm in self.pwm_instances:
                if gpio in pwm:
                    pwm_object = pwm[gpio]
                    old_pwm_value = pwm['duty_cycle'] if 'duty_cycle' in pwm else -1
                    if not self.to_int(old_pwm_value) == self.to_int(pwm_value):
                        pwm['duty_cycle'] = pwm_value
                        pwm_object.start(pwm_value) #should be changed back to pwm_object.ChangeDutyCycle() but this
                        # was causing errors.
                        self._logger.debug("Writing PWM on gpio: %s value %s", gpio, pwm_value)
                    self.update_ui()
                    if queue_id is not None:
                        self.stop_queue_item(queue_id)
                    break
        except Exception as ex:
            self.log_error(ex)
            pass

    def get_output_list(self):
        result = []
        for rpi_output in self.rpi_outputs:
            if rpi_output['output_type'] == 'regular':
                result.append(self.to_int(rpi_output['gpio_pin']))
        return result

    def send_notification(self, message):
        try:
            provider = self._settings.get(["notification_provider"])
            if provider == 'ifttt':
                event = self._settings.get(["notification_event_name"])
                api_key = self._settings.get(["notification_api_key"])
                self._logger.debug("Sending notification to: %s with msg: %s with key: %s", provider, message,
                        api_key)
                try:
                    res = self.ifttt_notification(message, event, api_key)
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
                if res.status_code != requests.codes['ok']:
                    try:
                        j = res.json()
                    except ValueError:
                        self._logger.info('Error: Could not parse server response. Event not sent')
                    for err in j['errors']:
                        self._logger.info('Error: {}'.format(err['message']))
        except Exception as ex:
            self.log_error(ex)
            pass

    def ifttt_notification(self, message, event, api_key):
        url = "https://maker.ifttt.com/trigger/{e}/with/key/{k}/".format(e=event, k=api_key)
        payload = {'value1': message}
        return requests.post(url, data=payload)

    # ~~ EventPlugin mixin
    def on_event(self, event, payload):
        if event == Events.CONNECTED:
            self.update_ui()

        if event == Events.CLIENT_OPENED:
            self.update_ui()

        if event == Events.PRINT_RESUMED:
            self.start_filament_detection()

        if event == Events.PRINT_STARTED:
            self.print_complete = False
            self.cancel_all_events_on_queue()
            self.event_queue = []
            self.start_filament_detection()
            for rpi_output in self.rpi_outputs:
                if rpi_output['auto_startup']:
                    delay_seconds = self.get_startup_delay_from_output(rpi_output)
                    self.schedule_auto_startup_outputs(rpi_output, delay_seconds)
                if rpi_output['toggle_timer']:
                    if rpi_output['output_type'] == 'regular' or rpi_output['output_type'] == 'pwm':
                        self.toggle_output(rpi_output['index_id'], True)
                if self.is_hour(rpi_output['shutdown_time']):
                    shutdown_delay_seconds = self.get_shutdown_delay_from_output(rpi_output)
                    self.schedule_auto_shutdown_outputs(rpi_output, shutdown_delay_seconds)
            self.run_tasks()
            self.update_ui()

        elif event == Events.PRINT_DONE:
            self.stop_filament_detection()
            self.print_complete = True
            for rpi_output in self.rpi_outputs:
                shutdown_time = rpi_output['shutdown_time']
                if rpi_output['output_type'] == 'pwm' and rpi_output['pwm_temperature_linked']:
                    rpi_output['duty_cycle'] = rpi_output['default_duty_cycle']
                if rpi_output['auto_shutdown'] and not self.is_hour(shutdown_time):
                    delay_seconds = self.to_float(shutdown_time)
                    self.schedule_auto_shutdown_outputs(rpi_output, delay_seconds)
            self.run_tasks()
            self.update_ui()

        elif event in (Events.PRINT_CANCELLED, Events.PRINT_FAILED):
            self.stop_filament_detection()
            self.cancel_all_events_on_queue()
            self.event_queue = []
            for rpi_output in self.rpi_outputs:
                if rpi_output['shutdown_on_failed']:
                    shutdown_time = rpi_output['shutdown_time']
                    if rpi_output['output_type'] == 'pwm' and rpi_output['pwm_temperature_linked']:
                        rpi_output['duty_cycle'] = rpi_output['default_duty_cycle']
                    if rpi_output['auto_shutdown'] and not self.is_hour(shutdown_time):
                        delay_seconds = self.to_float(shutdown_time)
                        self.schedule_auto_shutdown_outputs(rpi_output, delay_seconds)
                        if rpi_output['output_type'] == 'temp_hum_control':
                            rpi_output['temp_ctr_set_value'] = 0
            self.run_tasks()

        if event == Events.PRINT_DONE:
            for notification in self.notifications:
                if notification['printFinish']:
                    file_name = os.path.basename(payload["path"])
                    elapsed_time_in_seconds = payload["time"]
                    elapsed_time = octoprint.util.get_formatted_timedelta(timedelta(seconds=elapsed_time_in_seconds))
                    msg = "Print job finished: " + file_name + "finished printing in " + file_name, elapsed_time
                    self.send_notification(msg)

        if event in (Events.ERROR, Events.DISCONNECTED):
            self._logger.info("Detected Error or Disconnect in %s will call listeners for shutdown_on_error!", event)
            for rpi_output in self.rpi_outputs:
                if rpi_output['shutdown_on_error']:
                    self._logger.debug("Schedule shutdown for: %s", rpi_output["index_id"])
                    self.schedule_auto_shutdown_outputs(rpi_output, 0)
            self.run_tasks()
        
        if event == Events.PRINTER_STATE_CHANGED:
            if "error" in payload["state_string"].lower():
                self._logger.info("Detected Error in %s id: %s state: %s  will call listeners for shutdown_on_error!", event, payload["state_id"], payload["state_string"])
                for rpi_output in self.rpi_outputs:
                    if rpi_output['shutdown_on_error']:
                        self._logger.debug("Schedule shutdown for: %s", rpi_output["index_id"])
                        self.schedule_auto_shutdown_outputs(rpi_output, 0)
                self.run_tasks()

    def run_tasks(self):
        for task in self.event_queue:
            if not task['thread'].is_alive():
                task['thread'].start()

    def schedule_auto_shutdown_outputs(self, rpi_output, shutdown_delay_seconds):
        sufix = 'auto_shutdown'
        if rpi_output['output_type'] == 'regular':
            value = True if rpi_output['active_low'] else False
            self.add_regular_output_to_queue(shutdown_delay_seconds, rpi_output, value, sufix)
        if rpi_output['output_type'] == 'ledstrip':
            self.ledstrip_set_rgb(rpi_output)
        if rpi_output['output_type'] == 'pwm' and not rpi_output['pwm_temperature_linked']:
            value = 0
            self.add_pwm_output_to_queue(shutdown_delay_seconds, rpi_output, value, sufix)
        if rpi_output['output_type'] == 'pwm' and rpi_output['pwm_temperature_linked']:
            self.schedule_pwm_duty_on_queue(shutdown_delay_seconds, rpi_output, 0, sufix)
        if (rpi_output['output_type'] == 'neopixel_indirect' or rpi_output['output_type'] == 'neopixel_direct'):
            self.add_neopixel_output_to_queue(rpi_output, shutdown_delay_seconds, 0, 0, 0, sufix)
        if rpi_output['output_type'] == 'temp_hum_control':
            value = 0
            self.add_temperature_output_temperature_queue(shutdown_delay_seconds, rpi_output, value, sufix)
        self._logger.debug("Events scheduled to run %s", self.event_queue)

    def ledstrip_set_rgb(self, rpi_output, rgb=None):
        clk = rpi_output["ledstrip_gpio_clk"]
        data = rpi_output["ledstrip_gpio_dat"]
        if clk is not None and data is not None:
            ledstrip = LEDStrip(self.to_int(clk), self.to_int(data))
            if rgb is None:
                red, green, blue = self.get_color_from_rgb(rpi_output['default_ledstrip_color'])
            else:
                red, green, blue = self.get_color_from_rgb(rgb)

            self._logger.info("LEDSTRIP set rgb color: %s, %s, %s", red, green, blue)
            ledstrip.setcolourrgb(self.to_int(red), self.to_int(green), self.to_int(blue))

    def start_outpus_with_server(self):
        for rpi_output in self.rpi_outputs:
            if rpi_output['startup_with_server']:
                gpio = self.to_int(rpi_output['gpio_pin'])
                if rpi_output['output_type'] == 'regular':
                    value = False if rpi_output['active_low'] else True
                    if rpi_output['gpio_i2c_enabled']:
                        self.gpio_i2c_write(rpi_output, value)
                    else:
                        self.write_gpio(gpio, value)
                if rpi_output['output_type'] == 'ledstrip':
                    self.ledstrip_set_rgb(rpi_output)
                if rpi_output['output_type'] == 'pwm' and not rpi_output['pwm_temperature_linked']:
                    value = self.to_int(rpi_output['default_duty_cycle'])
                    self.write_pwm(gpio, value)
                if (rpi_output['output_type'] == 'neopixel_indirect' or rpi_output['output_type'] == 'neopixel_direct'):
                    red, green, blue = self.get_color_from_rgb(rpi_output['default_neopixel_color'])
                    led_count = rpi_output['neopixel_count']
                    led_brightness = rpi_output['neopixel_brightness']
                    address = rpi_output['microcontroller_address']
                    index_id = self.to_int(rpi_output['index_id'])
                    neopixel_direct = rpi_output['output_type'] == 'neopixel_direct'
                    self.send_neopixel_command(self.to_int(rpi_output['gpio_pin']), led_count, led_brightness, red,
                                               green, blue, address, neopixel_direct, index_id)
                if rpi_output['output_type'] == 'temp_hum_control':
                    rpi_output['temp_ctr_set_value'] = rpi_output['temp_ctr_default_value']

    def schedule_auto_startup_outputs(self, rpi_output, delay_seconds):
        sufix = 'auto_startup'
        if rpi_output['output_type'] == 'regular':
            value = False if rpi_output['active_low'] else True
            self.add_regular_output_to_queue(delay_seconds, rpi_output, value, sufix)
        if rpi_output['output_type'] == 'ledstrip':
            self.ledstrip_set_rgb(rpi_output)
        if rpi_output['output_type'] == 'pwm' and not rpi_output['pwm_temperature_linked']:
            value = self.to_int(rpi_output['default_duty_cycle'])
            self.add_pwm_output_to_queue(delay_seconds, rpi_output, value, sufix)
        if (rpi_output['output_type'] == 'neopixel_indirect' or rpi_output['output_type'] == 'neopixel_direct'):
            red, green, blue = self.get_color_from_rgb(rpi_output['default_neopixel_color'])
            self.add_neopixel_output_to_queue(rpi_output, delay_seconds, red, green, blue, sufix)
        if rpi_output['output_type'] == 'temp_hum_control':
            value = rpi_output['temp_ctr_default_value']
            self.add_temperature_output_temperature_queue(delay_seconds, rpi_output, value, sufix)
        self._logger.debug("Events scheduled to run %s", self.event_queue)

    def get_color_from_rgb(self, stringColor):
        stringColor = stringColor.replace('rgb(', '')
        red = stringColor[:stringColor.index(',')]
        stringColor = stringColor[stringColor.index(',') + 1:]
        green = stringColor[:stringColor.index(',')]
        stringColor = stringColor[stringColor.index(',') + 1:]
        blue = stringColor[:stringColor.index(')')]
        return red, green, blue

    def get_shutdown_delay_from_output(self, rpi_output):
        shutdown_time = rpi_output['shutdown_time']

        shut_down_date_time = self.create_date(shutdown_time)

        if shut_down_date_time < datetime.now():
            shut_down_date_time = shut_down_date_time + timedelta(days=1)

        delay_seconds = (shut_down_date_time - datetime.now()).total_seconds()

        return delay_seconds

    def add_neopixel_output_to_queue(self, rpi_output, delay_seconds, red, green, blue, sufix):
        gpio_pin = rpi_output['gpio_pin']
        ledCount = rpi_output['neopixel_count']
        ledBrightness = rpi_output['neopixel_brightness']
        address = rpi_output['microcontroller_address']
        neopixel_direct = rpi_output['output_type'] == 'neopixel_direct'
        index_id = self.to_int(rpi_output['index_id'])

        queue_id = '{0!s}_{1!s}'.format(index_id, sufix)

        self._logger.debug("Scheduling neopixel output id %s for on %s delay_seconds", queue_id, delay_seconds)

        thread = threading.Timer(delay_seconds, self.send_neopixel_command,
                                 args=[gpio_pin, ledCount, ledBrightness, red, green, blue, address, neopixel_direct,
                                       index_id, queue_id])

        self.event_queue.append(dict(queue_id=queue_id, thread=thread))

    def add_pwm_output_to_queue(self, delay_seconds, rpi_output, value, sufix):
        queue_id = '{0!s}_{1!s}'.format(rpi_output['index_id'], sufix)

        self._logger.debug("Scheduling pwm output id %s for on %s delay_seconds", queue_id, delay_seconds)

        thread = threading.Timer(delay_seconds, self.write_pwm,
                                 args=[self.to_int(rpi_output['gpio_pin']), value, queue_id])

        self.event_queue.append(dict(queue_id=queue_id, thread=thread))

    def schedule_pwm_duty_on_queue(self, delay_seconds, rpi_output, value, sufix):
        queue_id = '{0!s}_{1!s}_{2!s}'.format(rpi_output['index_id'], "pwm_linked_temp", sufix)
        thread = threading.Timer(delay_seconds, self.set_pwm_duty_cycle, args=[rpi_output, value, queue_id])

        self._logger.debug("Scheduling pwm linked temp output id %s on %s delay_seconds", queue_id, delay_seconds)

        self.event_queue.append(dict(queue_id=queue_id, thread=thread))

    def set_pwm_duty_cycle(self, rpi_output, value, queue_id):
        rpi_output['duty_cycle'] = value
        if queue_id is not None:
            self.stop_queue_item(queue_id)

    def add_regular_output_to_queue(self, delay_seconds, rpi_output, value, sufix):
        queue_id = '{0!s}_{1!s}'.format(rpi_output['index_id'], sufix)

        self._logger.debug("Scheduling regular output id %s on %s delay_seconds", queue_id, delay_seconds)

        if rpi_output['gpio_i2c_enabled']:
            thread = threading.Timer(delay_seconds, self.gpio_i2c_write,
                                     args=[rpi_output, value, queue_id])
        else:
            thread = threading.Timer(delay_seconds, self.write_gpio,
                                     args=[self.to_int(rpi_output['gpio_pin']), value, queue_id])

        self.event_queue.append(dict(queue_id=queue_id, thread=thread))

    def add_temperature_output_temperature_queue(self, delay_seconds, rpi_output, value, sufix):
        queue_id = '{0!s}_{1!s}'.format(rpi_output['index_id'], sufix)
        self._logger.debug("Scheduling temperature control id %s on %s delay_seconds", queue_id, delay_seconds)

        thread = threading.Timer(delay_seconds, self.write_temperature_to_output,
                                 args=[self.to_int(rpi_output['index_id']), value, queue_id])

        self.event_queue.append(dict(queue_id=queue_id, thread=thread))

    def write_temperature_to_output(self, rpi_output_index, value, queue_id=None):
        try:
            rpi_output = [r_out for r_out in self.rpi_outputs if
                          self.to_int(r_out['index_id']) == rpi_output_index].pop()

            if rpi_output['output_type'] == 'temp_hum_control':
                rpi_output['temp_ctr_set_value'] = value

                if queue_id is not None:
                    self._logger.debug("running scheduled queue id %s", queue_id)
                self._logger.debug("Setting temperature to output index: %s value %s", rpi_output['index_id'], value)

            self.update_ui()
            if queue_id is not None:
                self.stop_queue_item(queue_id)

        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{3!r}"
            message = template.format(type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def get_startup_delay_from_output(self, rpi_output):
        start_up_time = rpi_output['startup_time']
        if self.is_hour(start_up_time):
            start_up_date_time = self.create_date(start_up_time)
            if start_up_date_time < datetime.now():
                delay_seconds = 0.0
            else:
                delay_seconds = (start_up_date_time - datetime.now()).total_seconds()
        else:
            delay_seconds = self.to_float(rpi_output['startup_time'])
        return delay_seconds

    # ~~ SettingsPlugin mixin
    def on_settings_save(self, data):
        outputsBeforeSave = self.get_output_list()
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.notifications = self._settings.get(["notifications"])
        outputsAfterSave = self.get_output_list()

        commonPins = list(set(outputsBeforeSave) & set(outputsAfterSave))

        for pin in (pin for pin in outputsBeforeSave if pin not in commonPins):
            self.clear_channel(pin)

        self.rpi_outputs_not_changed = commonPins
        self.clear_gpio()

        self._logger.debug("rpi_outputs: %s", self.rpi_outputs)
        self._logger.debug("rpi_inputs: %s", self.rpi_inputs)
        self.setup_gpio()
        self.configure_gpio()
        self.generate_temp_hum_control_status()

    def get_settings_defaults(self):
        return dict(rpi_outputs=[], rpi_inputs=[],
            filament_sensor_gcode="G91  ;Set Relative Mode \n" + "G1 E-5.000000 F500 ;Retract 5mm\n" + "G1 Z15 F300         ;move Z up 15mm\n" + "G90            ;Set Absolute Mode\n " + "G1 X20 Y20 F9000      ;Move to hold position\n" + "G91            ;Set Relative Mode\n" + "G1 E-40 F500      ;Retract 40mm\n" + "M0            ;Idle Hold\n" + "G90            ;Set Absolute Mode\n" + "G1 F5000         ;Set speed limits\n" + "G28 X0 Y0         ;Home X Y\n" + "M82            ;Set extruder to Absolute Mode\n" + "G92 E0         ;Set Extruder to 0",
            use_sudo=True, neopixel_dma=10, debug=False, gcode_control=False, debug_temperature_log=False,
            use_board_pin_number=False, notification_provider="disabled", notification_api_key="",
            notification_event_name="printer_event", notifications=[{
                                                                        'printFinish'      : True,
                                                                        'filamentChange'   : True,
                                                                        'printer_action'   : True,
                                                                        'temperatureAction': True, 'gpioAction': True
                                                                    }])

    # ~~ TemplatePlugin
    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=True), dict(type="tab", custom_bindings=True),
            dict(type="navbar", custom_bindings=True, suffix="_1", classes=["dropdown"]),
            dict(type="navbar", custom_bindings=True, template="enclosure_navbar_input.jinja2", suffix="_2",
                 classes=["dropdown"])]

    # ~~ AssetPlugin mixin
    def get_assets(self):
        return dict(js=["js/enclosure.js", "js/bootstrap-colorpicker.min.js"],
            css=["css/bootstrap-colorpicker.css", "css/enclosure.css"])

    # ~~ Softwareupdate hook
    def get_update_information(self):
        return dict(enclosure=dict(displayName="Enclosure Plugin", displayVersion=self._plugin_version,
            # version check: github repository
            type="github_release", user="vitormhenrique", repo="OctoPrint-Enclosure", current=self._plugin_version,
            # update method: pip
            pip="https://github.com/vitormhenrique/OctoPrint-Enclosure/archive/{target_version}.zip"))

    def hook_gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if self._settings.get(["gcode_control"]) is False:
            return

        if cmd.strip().startswith("ENC"):
            self._logger.debug("Gcode queuing: %s", cmd)
            index_id = self.to_int(self.get_gcode_value(cmd, 'O'))
            for output in [item for item in self.rpi_outputs if item['index_id'] == index_id]:
                if output['output_type'] == 'regular':
                    set_value = self.to_int(self.get_gcode_value(cmd, 'S'))
                    set_value = self.constrain(set_value, 0, 1)
                    value = True if set_value == 1 else False
                    value = (not value) if output['active_low'] else value
                    if output['gpio_i2c_enabled']:
                        self.gpio_i2c_write(output, value)
                    else:
                        self.write_gpio(self.to_int(output['gpio_pin']), value)
                    comm_instance._log("Setting REGULAR output %s to value %s" % (index_id, value))
                    return
                if output['output_type'] == 'pwm':
                    set_value = self.to_int(self.get_gcode_value(cmd, 'S'))
                    set_value = self.constrain(set_value, 0, 100)
                    output['duty_cycle'] = set_value
                    self.write_pwm(self.to_int(output['gpio_pin']), set_value)
                    comm_instance._log("Setting PWM output %s to value %s" % (index_id, set_value))
                    return
                if output['output_type'] == 'neopixel_indirect' or output['output_type'] == 'neopixel_direct':
                    red = self.get_gcode_value(cmd, 'R')
                    green = self.get_gcode_value(cmd, 'G')
                    blue = self.get_gcode_value(cmd, 'B')

                    led_count = output['neopixel_count']
                    led_brightness = output['neopixel_brightness']
                    address = output['microcontroller_address']

                    index_id = self.to_int(output['index_id'])

                    neopixel_direct = output['output_type'] == 'neopixel_direct'

                    self.send_neopixel_command(self.to_int(output['gpio_pin']), led_count, led_brightness, red, green,
                        blue, address, neopixel_direct, index_id)
                    comm_instance._log(
                        "Setting NEOPIXEL output %s to red: %s green: %s blue: %s" % (index_id, red, green, blue))
                    return
                if output['output_type'] == 'temp_hum_control':
                    set_value = self.to_float(self.get_gcode_value(cmd, 'S'))
                    should_wait = self.to_int(self.get_gcode_value(cmd, 'W'))
                    if should_wait == 1 and self._printer.is_printing():
                        self._printer.pause_print()
                        self.waiting_temperature.append(index_id)
                    output['temp_ctr_set_value'] = set_value
                    self.update_ui_set_temperature()
                    self.handle_temp_hum_control()
                    comm_instance._log("Setting TEMP/HUM control output %s to value %s" % (index_id, set_value))
                    return

    def get_graph_data(self, comm, parsed_temps):
        for sensor in list(filter(lambda item: item['input_type'] == 'temperature_sensor', self.rpi_inputs)):
            if sensor["show_graph_temp"]:
                parsed_temps[str(sensor["label"])] = (sensor['temp_sensor_temp'], None)
            if sensor["show_graph_humidity"]:
                parsed_temps[str(sensor["label"])+" Humidity"] = (sensor['temp_sensor_humidity'], None)

        return parsed_temps


__plugin_name__ = "Enclosure Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = EnclosurePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.queuing"       : __plugin_implementation__.hook_gcode_queuing,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.temperatures.received": (__plugin_implementation__.get_graph_data, 1)
    }
