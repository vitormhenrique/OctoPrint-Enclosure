# coding=utf-8
from __future__ import absolute_import
from octoprint.events import eventManager, Events
from octoprint.util import RepeatedTimer
from subprocess import Popen, PIPE
import octoprint.plugin
import RPi.GPIO as GPIO
import flask
import time
import sys
import glob
import os
import datetime
import octoprint.util
import requests
import inspect
import threading
import json


#   18b20 sensor serial --> 28-0000062410dc
#   SI7021 addrress --> 40
#   BTN 22 -> active low | close to the blue thing)
#   BTN 23 -> active high
#   LED GREEN -> 17 active on high
#   LED RED -> 24 active on low
#   Neopixel -> pin 18 (needs sudo)


class EnclosurePlugin(octoprint.plugin.StartupPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.BlueprintPlugin,
                      octoprint.plugin.EventHandlerPlugin):

    last_filament_end_detected = 0
    rpi_outputs = []
    rpi_inputs = []
    rpi_outputs_not_changed = []
    notifications = []
    pwm_intances = []
    event_queue = []
    temperature_control_status = []
    temperature_sensor_data = []
    last_filament_end_detected = []

    def start_timer(self):
        """
        Function to start timer that checks enclosure temperature
        """

        self._check_temp_timer = RepeatedTimer(
            10, self.check_enclosure_temp, None, None, True)
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

    # ~~ StartupPlugin mixin
    def on_after_startup(self):
        self.fix_data()
        self.pwm_intances = []
        self.event_queue = []
        self.rpi_outputs_not_changed = []
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.notifications = self._settings.get(["notifications"])
        self.generate_temperature_control_status()
        self.setup_gpio()
        self.configure_gpio()
        self.update_ui()
        self.start_timer()

    # ~~ Blueprintplugin mixin
    @octoprint.plugin.BlueprintPlugin.route("/setEnclosureTemperature", methods=["GET"])
    def set_enclosure_temperature(self):
        set_temperature = self.to_float(
            flask.request.values["set_temperature"])
        index_id = self.to_int(flask.request.values["index_id"])

        for temperature_control in [item for item in self.rpi_outputs if item['index_id'] == index_id]:
            temperature_control['temp_ctr_set_temp'] = set_temperature

        self.handle_temperature_control()
        return flask.jsonify(success=True)

    # @octoprint.plugin.BlueprintPlugin.route("/getEnclosureSetTemperature", methods=["GET"])
    # def get_enclosure_set_temperature(self):
    #     self.update_ui_set_temperature()
    #     return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/clearGPIOMode", methods=["GET"])
    def clear_gpio_mode(self):
        GPIO.cleanup()
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/updateUI", methods=["GET"])
    def update_ui_requested(self):
        self.update_ui()
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/getOutputStatus", methods=["GET"])
    def get_output_status(self):
        gpio_status = []
        for rpi_output in self.rpi_outputs:            
            if rpi_output['output_type'] == 'regular':
                pin = self.to_int(rpi_output['gpio_pin'])
                val = GPIO.input(pin) if not rpi_output['active_low'] else (
                    not GPIO.input(pin))
                index = self.to_int(rpi_output['index_id'])
                # result.append(dict(index_id=rpi_output['index_id'], value=val))
                gpio_status.append(dict(index_id=index, status=val))
        self._logger.warn("######### gpio_status: %s", gpio_status)
        return flask.Response(json.dumps(gpio_status),  mimetype='application/json')

    # @octoprint.plugin.BlueprintPlugin.route("/getEnclosureTemperature", methods=["GET"])
    # def get_enclosure_temperature(self):
    #     self.update_ui_current_temperature()
    #     return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setIO", methods=["GET"])
    def set_io(self):
        gpio_index = flask.request.values["index_id"]
        value = True if flask.request.values["status"] == 'true' else False
        for rpi_output in self.rpi_outputs:
            if self.to_int(gpio_index) == self.to_int(rpi_output['index_id']):
                val = (not value) if rpi_output['active_low'] else value
                self.write_gpio(self.to_int(rpi_output['gpio_pin']), val)
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setPWM", methods=["GET"])
    def set_pwm(self):
        gpio_index = flask.request.values["index_id"]
        pwm_val = flask.request.values["pwmVal"]
        for rpi_output in self.rpi_outputs:
            if self.to_int(gpio_index) == self.to_int(rpi_output['index_id']):
                self.write_pwm(self.to_int(
                    rpi_output['gpio_pin']), self.to_int(pwm_val))
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/sendGcodeCommand", methods=["GET"])
    def requested_gcode_command(self):
        gpio_index = self.to_int(flask.request.values["index_id"])
        rpi_output = [r_out for r_out in self.rpi_outputs if self.to_int(r_out['index_id']) == gpio_index].pop()
        self.send_gcode_command(rpi_output['gcode'])
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setNeopixel", methods=["GET"])
    def set_neopixel(self):
        """ set_neopixel method get request from octoprint and send the comand to arduino or neopixel"""
        gpio_index = flask.request.values["index_id"]
        red = flask.request.values["red"]
        green = flask.request.values["green"]
        blue = flask.request.values["blue"]
        for rpi_output in self.rpi_outputs:
            if self.to_int(gpio_index) == self.to_int(rpi_output['index_id']):
                led_count = rpi_output['neopixel_count']
                led_brightness = rpi_output['neopixel_brightness']
                address = rpi_output['microcontroller_address']
                if not address:
                    self.send_neopixel_command(
                        self.to_int(rpi_output['gpio_pin']),
                        led_count, led_brightness, red, green, blue, address)
                else:
                    self.send_neopixel_command_direct(
                        self.to_int(rpi_output['gpio_pin']),
                        led_count, led_brightness, red, green, blue)
        return flask.jsonify(success=True)

    # ~~ Plugin Internal methods
    def fix_data(self):
        """ Fix setting dada commin from old releases of the plugin"""

        if not self._settings.get(["settingsVersion"]) == "3.6":
            # self._settings.set(["rpi_outputs"], [])
            # self._settings.set(["rpi_inputs"], [])
            # self.rpi_outputs = self._settings.get(["rpi_outputs"])
            # self.rpi_inputs = self._settings.get(["rpi_inputs"])
            self._logger.warn("######### settings not compatible #########")

    def send_neopixel_command(self, led_pin, led_count, led_brightness, red, green, blue, address):
        """Send neopixel command

        Arguments:
            led_pin {int} -- GPIO number
            ledCount {int} -- number of LEDS
            ledBrightness {int} -- brightness from 0 to 255
            red {int} -- red value from 0 to 255
            green {int} -- gren value from 0 to 255
            blue {int} -- blue value from 0 to 255
            address {int} -- i2c address from microcontroler
        """

        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/neopixel.py "
            cmd = "sudo python " + script + str(led_pin) + " " + str(led_count) + " " + str(
                led_brightness) + " " + str(red) + " " + str(green) + " " + str(blue) + " " + str(address)
            if self._settings.get(["debug"]) is True:
                self._logger.info("Sending neopixel cmd: %s", cmd)
            Popen(cmd, shell=True)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def send_neopixel_command_direct(self, led_pin, led_count, led_brightness, red, green, blue):
        """Send neopixel command

        Arguments:
            led_pin {int} -- GPIO number
            ledCount {int} -- number of LEDS
            ledBrightness {int} -- brightness from 0 to 255
            red {int} -- red value from 0 to 255
            green {int} -- gren value from 0 to 255
            blue {int} -- blue value from 0 to 255
        """

        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/neopixel.py "
            cmd = "sudo python " + script + str(led_pin) + " " + str(led_count) + " " + str(
                led_brightness) + " " + str(red) + " " + str(green) + " " + str(blue)
            if self._settings.get(["debug"]) is True:
                self._logger.info("Sending neopixel cmd: %s", cmd)
            Popen(cmd, shell=True)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def check_enclosure_temp(self):
        try:
            sensor_data = []
            for sensor in list(filter(lambda item: item['input_type'] == 'temperature_sensor', self.rpi_inputs)):
                temp, hum = self.get_sensor_data(sensor)
                if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                    self._logger.info(
                        "Sensor %s Temperature: %s humidity %s", sensor['label'], temp, hum)
                sensor_data.append(
                    dict(index_id=sensor['index_id'], temperature=temp, humidity=hum))
            self.temperature_sensor_data = sensor_data
            self.update_ui()
            self.handle_temperature_control()
            self.handle_temperature_events()
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass
    
    def update_ui(self):
        self.update_ui_outputs()
        self.update_ui_current_temperature()
        self.update_ui_set_temperature()

    def update_ui_current_temperature(self):
        self._plugin_manager.send_plugin_message(
            self._identifier, dict(sensor_data=self.temperature_sensor_data))

    def update_ui_set_temperature(self):
        result = []
        for temp_crt_output in list(filter(lambda item:
                                           item['output_type'] == 'temperature_control',
                                           self.rpi_outputs)):
            set_temperature = self.to_float(
                temp_crt_output['temp_ctr_set_temp'])
            result.append(
                dict(index_id=temp_crt_output['index_id'], set_temperature=set_temperature))
            result.append(set_temperature)
        self._plugin_manager.send_plugin_message(
            self._identifier, dict(set_temperature=result))

    def update_ui_outputs(self):
        try:
            gpio_status = []
            pwm_status = []
            for rpi_output in self.rpi_outputs:
                index = self.to_int(rpi_output['index_id'])
                pin = self.to_int(rpi_output['gpio_pin'])
                if rpi_output['output_type'] == 'regular':
                    val = GPIO.input(pin) if not rpi_output['active_low'] else (
                        not GPIO.input(pin))
                    gpio_status.append(dict(index_id=index, status=val))
                if rpi_output['output_type'] == 'pwm':
                    for pwm in self.pwm_intances:
                        if pin in pwm:
                            if 'duty_cycle' in pwm:
                                pwmVal = pwm['duty_cycle']
                                val = self.to_int(pwmVal)
                            else:
                                val = 100
                            pwm_status.append(dict(index_id=index, pwm_value=val))
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(rpi_output=gpio_status, rpi_output_pwm=pwm_status))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def get_sensor_data(self, sensor):
        try:
            if sensor['temp_sensor_type'] in ["11", "22", "2302"]:
                self._logger.info("temp_sensor_type dht")
                temp, hum = self.read_dht_temp(
                    sensor['temp_sensor_type'], sensor['gpio_pin'])
            elif sensor['temp_sensor_type'] == "18b20":
                temp = self.read_18b20_temp(sensor['ds18b20_serial'])
                hum = 0
            elif sensor['temp_sensor_type'] == "bme280":
                temp, hum = self.read_bme280_temp(
                    sensor['temp_sensor_address'])
            elif sensor['temp_sensor_type'] == "si7021":
                temp, hum = self.read_si7021_temp(
                    sensor['temp_sensor_address'])
            elif sensor['temp_sensor_type'] == "tmp102":
                temp = self.read_tmp102_temp(
                    sensor['temp_sensor_address'])
                hum = 0
            else:
                self._logger.info("temp_sensor_type no match")
                temp = 0
                hum = 0
            if temp != -1 and hum != -1:
                temp = round(self.to_float(
                    temp), 1) if not sensor['use_fahrenheit'] else round(self.to_float(temp) * 1.8 + 32, 1)
                hum = round(self.to_float(hum), 1)
                return temp, hum
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def handle_temperature_events(self):
        for temperature_alarm in [item for item in self.rpi_outputs if item['output_type'] == 'temperature_alarm']:
            set_temperature = self.to_float(
                temperature_alarm['alarm_set_temp'])
            if int(set_temperature) is 0:
                continue
            linked_data = [item for item in self.temperature_sensor_data if item['index_id'] ==
                           temperature_alarm['linked_temp_sensor']].pop()
            sensor_temperature = self.to_float(linked_data['temperature'])
            if set_temperature < sensor_temperature:
                for rpi_controlled_output in self.rpi_outputs:
                    if self.to_int(temperature_alarm['controlled_io']) == self.to_int(rpi_controlled_output['index_id']):
                        val = GPIO.LOW if rpi_controlled_output['active_low'] else GPIO.HIGH
                        self.write_gpio(self.to_int(
                            rpi_controlled_output['gpio_pin']), val)
                        for notification in self.notifications:
                            if notification['temperatureAction']:
                                msg = "Temperature action: enclosure temperature exceed " + \
                                    temperature_alarm['setTemp']
                                self.send_notification(msg)

    def read_dht_temp(self, sensor, pin):
        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/getDHTTemp.py "
            cmd = "sudo python " + script + str(sensor) + " " + str(pin)
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("Temperature dht cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("Dht result: %s", stdout)
            temp, hum = stdout.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def read_bme280_temp(self, address):
        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/BME280.py "
            cmd = "sudo python " + script + str(address)
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("Temperature BME280 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("BME280 result: %s", stdout)
            temp, hum = stdout.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def read_si7021_temp(self, address):
        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/SI7021.py "
            cmd = "sudo python " + script + str(address)
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("Temperature SI7021 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("SI7021 result: %s", stdout)
            temp, hum = stdout.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
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
            temp_c = float(temp_string) / 1000.0
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
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("Temperature TMP102 cmd: %s", " ".join(args))
            proc = Popen(args, stdout=PIPE)
            stdout, _ = proc.communicate()
            if self._settings.get(["debug"]) is True and self._settings.get(["debug_temperature_log"]) is True:
                self._logger.info("TMP102 result: %s", stdout)
            return self.to_float(stdout.strip())
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            return 0

    def handle_temperature_control(self):
        try:
            for temperature_control in list(filter(lambda item: item['output_type'] == 'temperature_control', self.rpi_outputs)):

                set_temperature = self.to_float(
                    temperature_control['temp_ctr_set_temp'])
                temp_deadband = self.to_float(
                    temperature_control['temp_ctr_deadband'])
                max_temp = self.to_float(
                    temperature_control['temp_ctr_max_temp'])

                linked_id = temperature_control['linked_temp_sensor']

                previous_status = filter(
                    lambda item: item['index_id'] == temperature_control['index_id'],
                    self.temperature_control_status).pop()['status']

                if set_temperature == 0:
                    current_status = False
                else:
                    linked_data = [
                        data for data in self.temperature_sensor_data if data['index_id'] == linked_id].pop()

                    current_temperature = self.to_float(
                        linked_data['temperature'])

                    if set_temperature - temp_deadband > current_temperature:
                        current_status = True
                    elif set_temperature + temp_deadband < current_temperature:
                        current_status = False
                    else:
                        current_status = previous_status

                    if temperature_control['temp_ctr_type'] is 'cooler':
                        current_status = not current_status

                    if temperature_control['temp_ctr_type'] is 'heater' and int(max_temp) is not 0 and max_temp < current_temperature:
                        temperature_control['temp_ctr_set_temp'] = 0
                        current_status = False
                if current_status != previous_status:
                    if current_status:
                        self._logger.info(
                            "Turning gpio to control temperature on.")
                        val = False if temperature_control['active_low'] else True
                        self.write_gpio(self.to_int(
                            temperature_control['gpio_pin']), val)
                    else:
                        self._logger.info(
                            "Turning gpio to control temperature off.")
                        val = True if temperature_control['active_low'] else False
                        self.write_gpio(self.to_int(
                            temperature_control['gpio_pin']), val)
                    for control_status in self.temperature_control_status:
                        if control_status['index_id'] == temperature_control['index_id']:
                            control_status['status'] = current_status
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)

    def setup_gpio(self):
        try:
            currentMode = GPIO.getmode()
            setMode = GPIO.BOARD if self._settings.get(
                ["useBoardPinNumber"]) else GPIO.BCM
            if currentMode is None:
                outputs = list(filter(lambda item: item['output_type'] == 'regular' or
                                      item['output_type'] == 'pwm' or
                                      item['output_type'] == 'temperature_control' or
                                      item['output_type'] == 'neopixel_direct', self.rpi_outputs))
                inputs = list(filter(
                    lambda item: item['input_type'] == 'gpio', self.rpi_inputs))
                gpios = outputs + inputs
                if gpios:
                    GPIO.setmode(setMode)
                    tempstr = "BOARD" if setMode == GPIO.BOARD else "BCM"
                    self._logger.info("Setting GPIO mode to %s", tempstr)
            elif currentMode != setMode:
                GPIO.setmode(currentMode)
                tempstr = "BOARD" if currentMode == GPIO.BOARD else "BCM"
                self._settings.set(["useBoardPinNumber"],
                                   True if currentMode == GPIO.BOARD else False)
                warn_msg = "GPIO mode was configured before, GPIO mode will be forced to use: " + \
                    tempstr + " as pin numbers. Please update GPIO accordingly!"
                self._logger.info(warn_msg)
                self._plugin_manager.send_plugin_message(
                    self._identifier, dict(isMsg=True, msg=warn_msg))
            GPIO.setwarnings(False)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def clear_gpio(self):
        try:

            for gpio_out in list(filter(lambda item: item['output_type'] == 'regular' or
                                        item['output_type'] == 'pwm' or
                                        item['output_type'] == 'temperature_control' or
                                        item['output_type'] == 'neopixel_direct', self.rpi_outputs)):
                gpio_pin = self.to_int(gpio_out['gpio_pin'])
                if gpio_pin not in self.rpi_outputs_not_changed:
                    GPIO.cleanup(gpio_pin)

            for gpio_in in list(filter(lambda item: item['input_type'] == 'gpio', self.rpi_inputs)):
                try:
                    GPIO.remove_event_detect(
                        self.to_int(gpio_in['gpio_pin']))
                except:
                    pass
                GPIO.cleanup(self.to_int(gpio_in['gpio_pin']))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def clear_channel(self, channel):
        try:
            GPIO.cleanup(self.to_int(channel))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def generate_temperature_control_status(self):
        status = []
        for temperature_control in list(filter(lambda item:
                                               item['output_type'] == 'temperature_control', self.rpi_outputs)):
            status.append(
                dict(index_id=temperature_control['index_id'], status=False))
        self.temperature_control_status = status

    def configure_gpio(self):
        try:

            for gpio_out in list(filter(lambda item: item['output_type'] == 'regular' or
                                        item['output_type'] == 'temperature_control', self.rpi_outputs)):
                initialValue = GPIO.HIGH if gpio_out['active_low'] else GPIO.LOW
                pin = self.to_int(gpio_out['gpio_pin'])
                if pin not in self.rpi_outputs_not_changed:
                    self._logger.info(
                            "Setting GPIO pin %s as OUTPUT with initial value: %s", pin, initialValue)
                    GPIO.setup(pin, GPIO.OUT, initial=initialValue)
            for gpio_out_pwm in list(filter(lambda item: item['output_type'] == 'pwm', self.rpi_outputs)):
                pin = self.to_int(gpio_out_pwm['gpio_pin'])
                index_id = self.to_int(gpio_out_pwm['index_id'])
                self._logger.info(
                        "Setting GPIO pin %s as PWM",pin)
                for pwm in (pwm_dict for pwm_dict in self.pwm_intances if index_id in pwm_dict):
                    self.pwm_intances.remove(pwm)
                self.clear_channel(pin)
                GPIO.setup(pin, GPIO.OUT)
                pwm_instance = GPIO.PWM(pin, self.to_int(
                    gpio_out_pwm['pwm_frequency']))
                self.pwm_intances.append({index_id: pwm_instance})
            for gpio_out_neopixel in list(filter(lambda item: item['output_type'] == 'neopixel_direct', self.rpi_outputs)):
                pin = self.to_int(gpio_out_neopixel['gpio_pin'])
                self.clear_channel(pin)

            for rpi_input in list(filter(lambda item: item['input_type'] == 'gpio', self.rpi_inputs)):
                pullResistor = GPIO.PUD_UP if rpi_input['input_pull_resistor'] == 'input_pull_up' else GPIO.PUD_DOWN
                gpio_pin = self.to_int(rpi_input['gpio_pin'])
                GPIO.setup(gpio_pin, GPIO.IN, pullResistor)
                edge = GPIO.RISING if rpi_input['edge'] == 'rise' else GPIO.FALLING
                if rpi_input['action_type'] == 'output_control':
                    self._logger.info(
                        "Adding GPIO event detect on pin %s with edge: %s", gpio_pin, edge)
                    GPIO.add_event_detect(gpio_pin, edge, callback=self.handle_gpio_control, bouncetime=200)
                if (rpi_input['action_type'] == 'printer_control' and rpi_input['printer_action'] != 'filament'):
                    GPIO.add_event_detect(gpio_pin, edge, callback=self.handle_printer_action, bouncetime=200)
                    self._logger.info(
                        "Adding PRINTER CONTROL event detect on pin %s with edge: %s", gpio_pin, edge)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def handle_filamment_detection(self, channel):
        try:
            for filament_sensor in list(filter(lambda item: item['input_type'] == 'gpio' and
                                               item['action_type'] == 'printer_control' and
                                               item['printer_action'] == 'filament' and
                                               filament_sensor['gpio_pin'] == channel, self.rpi_inputs)):
                if ((filament_sensor['edge'] == 'fall') ^ (GPIO.input(self.to_int(filament_sensor['gpio_pin']))) and
                        filament_sensor['filament_sensor_enabled']):
                    last_detected_time = list(filter(lambda item: item['index_id'] == filament_sensor['index_id'],
                                                     self.last_filament_end_detected)).pop()['time']
                    if time.time() - last_detected_time > self._settings.get_int(["filament_sensor_timeout"]):
                        self._logger.info("Detected end of filament.")
                        for item in self.last_filament_end_detected:
                            if item['index_id'] == filament_sensor['index_id']:
                                item['time'] = time.time()
                        for line in self._settings.get(["filament_sensor_gcode"]).split('\n'):
                            if line:
                                self._printer.commands(line.strip().upper())
                                self._logger.info(
                                    "Sending GCODE command: %s", line.strip().upper())
                                time.sleep(0.2)
                        for notification in self.notifications:
                            if notification['filamentChange']:
                                msg = "Filament change action caused by sensor: " + \
                                    str(filament_sensor['label'])
                                self.send_notification(msg)
                    else:
                        self._logger.info(
                            "Prevented end of filament detection, filament sensor timeout not elapsed.")
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def start_filament_detection(self):
        self.stop_filament_detection()
        try:
            for filament_sensor in list(filter(lambda item: item['input_type'] == 'gpio' and
                                               item['action_type'] == 'printer_control' and
                                               item['printer_action'] == 'filament', self.rpi_inputs)):
                edge = GPIO.RISING if filament_sensor['edge'] == 'rise' else GPIO.FALLING
                if GPIO.input(self.to_int(filament_sensor['gpio_pin'])) == (edge == GPIO.RISING):
                    self._printer.pause_print()
                    self._logger.info("Started printing with no filament.")
                else:
                    self.last_filament_end_detected.append(
                        dict(index_id=filament_sensor['index_id'], time=0))
                    GPIO.add_event_detect(self.to_int(
                        filament_sensor['gpio_pin']), edge, callback=self.handle_filamment_detection, bouncetime=200)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def stop_filament_detection(self):
        try:
            self.last_filament_end_detected = []
            for filament_sensor in list(filter(lambda item: item['input_type'] == 'gpio' and
                                               item['action_type'] == 'printer_control' and
                                               item['printer_action'] == 'filament', self.rpi_inputs)):
                GPIO.remove_event_detect(
                    self.to_int(filament_sensor['gpio_pin']))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def cancel_events_on_event_queue(self):
        for task in self.event_queue:
            task.cancel()

    def handle_gpio_control(self, channel):
        try:
            if self._settings.get(["debug"]) is True:
                self._logger.info("GPIO event triggered on channel %s", channel)
            rpi_input = [r_inp for r_inp in self.rpi_inputs if self.to_int(r_inp['gpio_pin']) == self.to_int(channel)].pop()
            gpio_pin = self.to_int(rpi_input['gpio_pin'])
            controlled_io = self.to_int(rpi_input['controlled_io'])
            if ((rpi_input['edge'] == 'fall') ^ GPIO.input(gpio_pin)):
                rpi_output = [r_out for r_out in self.rpi_outputs if self.to_int(r_out['index_id']) == controlled_io].pop()
                if rpi_output['output_type'] == 'regular':
                    if rpi_input['controlled_io_set_value'] == 'toggle':
                        val = GPIO.LOW if GPIO.input(self.to_int(
                            rpi_output['gpio_pin'])) == GPIO.HIGH else GPIO.HIGH
                    else:
                        val = GPIO.LOW if rpi_input['controlled_io_set_value'] == 'low' else GPIO.HIGH
                    self.write_gpio(self.to_int(
                        rpi_output['gpio_pin']), val)
                    for notification in self.notifications:
                        if notification['gpioAction']:
                            msg = "GPIO control action caused by input " + str(rpi_input['label']) + ". Setting GPIO" + str(
                                rpi_input['controlled_io']) + " to: " + str(rpi_input['controlled_io_set_value'])
                            self.send_notification(msg)
                if rpi_output['output_type'] == 'gcode_output':
                    self.send_gcode_command(rpi_output['gcode'])
                    for notification in self.notifications:
                        if notification['gpioAction']:
                            msg = "GPIO control action caused by input " + str(rpi_input['label']) + ". Sending GCODE command"
                            self.send_notification(msg)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def send_gcode_command(self, command):
        for line in command.split('\n'):
            if line:
                self._printer.commands(line.strip().upper())
                self._logger.info(
                    "Sending GCODE command: %s", line.strip().upper())
                time.sleep(0.2)

    def handle_printer_action(self, channel):
        try:
            for rpi_input in self.rpi_inputs:
                if (channel == self.to_int(rpi_input['gpio_pin']) and
                    rpi_input['action_type'] == 'printer_control' and
                        ((rpi_input['edge'] == 'fall') ^ GPIO.input(self.to_int(rpi_input['gpio_pin'])))):
                    if rpi_input['printer_action'] == 'resume':
                        self._logger.info("Printer action resume.")
                        self._printer.resume_print()
                    elif rpi_input['printer_action'] == 'pause':
                        self._logger.info("Printer action pause.")
                        self._printer.pause_print()
                    elif rpi_input['printer_action'] == 'cancel':
                        self._logger.info("Printer action cancel.")
                        self._printer.cancel_print()
                    elif rpi_input['printer_action'] == 'stop_temperature_control':
                        self._logger.info(
                            "Printer action stoping temperature control.")
                        for rpi_output in self.rpi_outputs:
                            if rpi_output['auto_shutdown'] and rpi_output['output_type'] == 'temperature_control':
                                rpi_output['temp_ctr_set_temp'] = 0
                        self.handle_temperature_control()
                    for notification in self.notifications:
                        if notification['printer_action']:
                            msg = "Printer action: " + \
                                rpi_input['printer_action'] + \
                                " caused by input: " + str(rpi_input['label'])
                            self.send_notification(msg)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def write_gpio(self, gpio, value):
        try:
            GPIO.output(gpio, value)
            if self._settings.get(["debug"]) is True:
                self._logger.info("Writing on gpio: %s value %s", gpio, value)
            self.update_ui()
        except Exception as ex:
            template = "An exception of type {0} occurred on {1} when writing on pin {2}. Arguments:\n{3!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, gpio, ex.args)
            self._logger.warn(message)
            pass

    def write_pwm(self, gpio, pwmValue):
        try:
            for pwm in self.pwm_intances:
                if gpio in pwm:
                    pwm_object = pwm[gpio]
                    pwm['duty_cycle'] = pwmValue
                    pwm_object.stop()
                    pwm_object.start(pwmValue)
                    if self._settings.get(["debug"]) is True:
                        self._logger.info(
                            "Writing PWM on gpio: %s value %s", gpio, pwmValue)
                    self.update_ui()
                    break
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
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
                if self._settings.get(["debug"]) is True:
                    self._logger.info(
                        "Sending notification to: %s with msg: %s with key: %s", provider, message, api_key)
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
                if res.status_code != requests.codes.ok:
                    try:
                        j = res.json()
                    except ValueError:
                        self._logger.info(
                            'Error: Could not parse server response. Event not sent')
                    for err in j['errors']:
                        self._logger.info('Error: {}'.format(err['message']))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def ifttt_notification(self, message, event, api_key):
        url = "https://maker.ifttt.com/trigger/{e}/with/key/{k}/".format(
            e=event, k=api_key)
        payload = {'value1': message}
        return requests.post(url, data=payload)

    # ~~ EventPlugin mixin
    def on_event(self, event, payload):

        if event == Events.CONNECTED:
            self.update_ui()

        if event == Events.PRINT_RESUMED:
            self.start_filament_detection()

        if event == Events.PRINT_STARTED:
            self.cancel_events_on_event_queue()
            self.start_filament_detection()
            for rpi_output in self.rpi_outputs:
                if rpi_output['auto_startup'] and rpi_output['output_type'] == 'regular':
                    value = False if rpi_output['active_low'] else True
                    self.event_queue.append(threading.Timer(self.to_float(rpi_output['startup_time']),
                                                            self.write_gpio,
                                                            args=[self.to_int(rpi_output['gpio_pin']), value]))
                if rpi_output['auto_startup'] and rpi_output['output_type'] == 'pwm':
                    value = self.to_int(rpi_output['duty_cycle'])
                    self.event_queue.append(threading.Timer(self.to_float(rpi_output['startup_time']),
                                                            self.write_pwm,
                                                            args=[self.to_int(rpi_output['gpio_pin']), value]))
                if rpi_output['auto_startup'] and rpi_output['output_type'] == 'neopixel':
                    gpio_pin = rpi_output['gpio_pin']
                    ledCount = rpi_output['neopixel_count']
                    ledBrightness = rpi_output['neopixel_brightness']
                    address = rpi_output['microcontroller_address']
                    stringColor = rpi_output['neopixel_color']
                    stringColor = stringColor.replace('rgb(', '')

                    red = stringColor[:stringColor.index_id(',')]
                    stringColor = stringColor[stringColor.index_id(',') + 1:]
                    green = stringColor[:stringColor.index_id(',')]
                    stringColor = stringColor[stringColor.index_id(',') + 1:]
                    blue = stringColor[:stringColor.index_id(')')]

                    self.event_queue.append(threading.Timer(self.to_float(rpi_output['startup_time']),
                                                            self.send_neopixel_command,
                                                            args=[gpio_pin, ledCount, ledBrightness, red, green, blue, address]))

                if rpi_output['auto_startup'] and rpi_output['output_type'] == 'temperature_control':
                    rpi_output['temp_ctr_set_temp'] = rpi_output['temp_ctr_default_temp']
                self.update_ui()
                self._logger.info("Event queue: %s", self.event_queue)
                for task in self.event_queue:
                    task.start()
                self.event_queue = []
        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            self.stop_filament_detection()
            for rpi_output in self.rpi_outputs:
                if rpi_output['auto_shutdown'] and rpi_output['output_type'] == 'regular':
                    value = True if rpi_output['active_low'] else False
                    self.event_queue.append(threading.Timer(self.to_float(rpi_output['shutdown_time']),
                                                            self.write_gpio,
                                                            args=[self.to_int(rpi_output['gpio_pin']), value]))
                if rpi_output['auto_shutdown'] and rpi_output['output_type'] == 'pwm':
                    value = 0
                    self.event_queue.append(threading.Timer(self.to_float(rpi_output['shutdown_time']),
                                                            self.write_pwm,
                                                            args=[self.to_int(rpi_output['gpio_pin']), value]))
                if rpi_output['auto_shutdown'] and rpi_output['output_type'] == 'neopixel':
                    gpio_pin = rpi_output['gpio_pin']
                    ledCount = rpi_output['neopixel_count']
                    ledBrightness = rpi_output['neopixel_brightness']
                    address = rpi_output['microcontroller_address']
                    self.event_queue.append(threading.Timer(self.to_float(rpi_output['shutdown_time']),
                                                            self.send_neopixel_command,
                                                            args=[gpio_pin, ledCount, 0, 0, 0, 0, address]))

                if rpi_output['auto_shutdown'] and rpi_output['output_type'] == 'temperature_control':
                    rpi_output['temp_ctr_set_temp'] = 0
                self.update_ui()
            for task in self.event_queue:
                task.start()
            self.event_queue = []

        if event == Events.PRINT_DONE:
            for notification in self.notifications:
                if notification['printFinish']:
                    file_name = os.path.basename(payload["file"])
                    elapsed_time_in_seconds = payload["time"]
                    elapsed_time = octoprint.util.get_formatted_timedelta(
                        datetime.timedelta(seconds=elapsed_time_in_seconds))
                    msg = "Print job finished: " + file_name + \
                        "finished printing in " + file_name, elapsed_time
                    self.send_notification(msg)

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

        self._logger.info("Pins not changed: %s", commonPins)

        self.rpi_outputs_not_changed = commonPins
        self.clear_gpio()

        if self._settings.get(["debug"]) is True:
            self._logger.info("rpi_outputs: %s", self.rpi_outputs)
            self._logger.info("rpi_inputs: %s", self.rpi_inputs)
        self.setup_gpio()
        self.configure_gpio()
        self.generate_temperature_control_status()

    def get_settings_defaults(self):
        return dict(
            rpi_outputs=[],
            rpi_inputs=[],
            filament_sensor_gcode="G91  ;Set Relative Mode \n" +
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
            debug=False,
            debug_temperature_log=False,
            useBoardPinNumber=False,
            notification_provider="disabled",
            notification_api_key="",
            notification_event_name="printer_event",
            settingsVersion="",
            notifications=[{'printFinish': True, 'filamentChange': True,
                            'printer_action': True, 'temperatureAction': True, 'gpioAction': True}]
        )

    # ~~ TemplatePlugin
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True),
            dict(type="tab", custom_bindings=True)
        ]

    # ~~ AssetPlugin mixin
    def get_assets(self):
        return dict(
            js=["js/enclosure.js", "js/bootstrap-colorpicker.min.js", "js/bootstrap2-toggle.js"],
            css=["css/bootstrap-colorpicker.css", "css/enclosure.css", "css/bootstrap2-toggle.css"]
        )

    # ~~ Softwareupdate hook
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
