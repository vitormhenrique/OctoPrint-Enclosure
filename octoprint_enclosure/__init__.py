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


class EnclosurePlugin(octoprint.plugin.StartupPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.AssetPlugin,
                      octoprint.plugin.BlueprintPlugin,
                      octoprint.plugin.EventHandlerPlugin):



    previous_temp_control_status = False
    current_temp_control_status = False
    enclosure_set_temperature = 0.0
    enclosure_current_temperature = 0.0
    enclosure_current_humidity = 0.0
    last_filament_end_detected = 0
    temperature_reading = []
    temperature_control = []
    rpi_outputs = []
    rpi_inputs = []
    previous_rpi_outputs = []
    notifications = []

    pwm_intances = []
    queue = []

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
        self.pwm_intances = []
        self.queue = []
        self.temperature_reading = self._settings.get(["temperature_reading"])
        self.temperature_control = self._settings.get(["temperature_control"])
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.notifications = self._settings.get(["notifications"])
        self.fix_data()
        self.previous_rpi_outputs = []
        self.start_timer()
        self.start_gpio()
        self.configure_gpio()
        self.update_output_ui()

    # ~~ Blueprintplugin mixin
    @octoprint.plugin.BlueprintPlugin.route("/setEnclosureTemperature", methods=["GET"])
    def set_enclosure_temperature(self):
        self.enclosure_set_temperature = flask.request.values["enclosureSetTemp"]
        if self._settings.get(["debug"]) is True:
            self._logger.info(
                "DEBUG -> Seting enclosure temperature: %s", self.enclosure_set_temperature)
        self.handle_temperature_control()
        return flask.jsonify(enclosureSetTemperature=self.enclosure_set_temperature, enclosureCurrentTemperature=self.enclosure_current_temperature)

    @octoprint.plugin.BlueprintPlugin.route("/getEnclosureSetTemperature", methods=["GET"])
    def get_enclosure_set_temperature(self):
        return str(self.enclosure_set_temperature)

    @octoprint.plugin.BlueprintPlugin.route("/clearGPIOMode", methods=["GET"])
    def clear_gpio_mode(self):
        GPIO.cleanup()
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/getUpdateBtnStatus", methods=["GET"])
    def get_update_btn_status(self):
        self.update_output_ui()
        return flask.make_response("Ok.", 200)

    @octoprint.plugin.BlueprintPlugin.route("/getOutputStatus", methods=["GET"])
    def get_output_status(self):
        result = ''
        for rpi_output in self.rpi_outputs:
            pin = self.to_int(rpi_output['gpioPin'])
            if rpi_output['outputType'] == 'regular':
                val = GPIO.input(pin) if not rpi_output['activeLow'] else (
                    not GPIO.input(pin))
            if result:
                result = result + ', '
            result = result + \
                '"' + str(pin) + '": ' + str(val).lower()
        return '{' + result + '}'

    @octoprint.plugin.BlueprintPlugin.route("/getEnclosureTemperature", methods=["GET"])
    def get_enclosure_temperature(self):
        return str(self.enclosure_current_temperature)

    @octoprint.plugin.BlueprintPlugin.route("/setIO", methods=["GET"])
    def set_io(self):
        gpio = flask.request.values["io"]
        value = True if flask.request.values["status"] == "on" else False
        for rpi_output in self.rpi_outputs:
            if self.to_int(gpio) == self.to_int(rpi_output['gpioPin']):
                val = (not value) if rpi_output['activeLow'] else value
                self.write_gpio(self.to_int(gpio), val)
        return flask.jsonify(success=True)

    @octoprint.plugin.BlueprintPlugin.route("/setPWM", methods=["GET"])
    def set_pwm(self):
        gpio = flask.request.values["io"]
        pwm_val = flask.request.values["pwmVal"]
        self.write_pwm(self.to_int(gpio), self.to_int(pwm_val))
        return flask.make_response("Ok.", 200)

    @octoprint.plugin.BlueprintPlugin.route("/setNeopixel", methods=["GET"])
    def set_neopixel(self):
        """ set_neopixel method get request from octoprint and send the comand to arduino or neopixel"""
        gpio = flask.request.values["io"]
        red = flask.request.values["red"]
        green = flask.request.values["green"]
        blue = flask.request.values["blue"]
        for rpi_output in self.rpi_outputs:
            if self.to_int(gpio) == self.to_int(rpi_output['gpioPin']) and rpi_output['outputType'] == 'neopixel':
                led_count = rpi_output['neopixelCount']
                led_brightness = rpi_output['neopixelBrightness']
                address = rpi_output['microAddress']
                self.send_neopixel_command(
                    gpio, led_count, led_brightness, red, green, blue, address)
        return flask.make_response("Ok.", 200)

    # ~~ Plugin Internal methods
    def fix_data(self):
        """ Fix setting dada commin from old releases of the plugin"""

        if not self._settings.get(["settingsVersion"]) == "3.6":
            self._settings.set(["rpi_outputs"], [])
            self._settings.set(["rpi_inputs"], [])

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
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def check_enclosure_temp(self):
        try:
            for temp_reader in self.temperature_reading:
                if temp_reader['isEnabled']:
                    if temp_reader['sensorType'] in ["11", "22", "2302"]:
                        self._logger.info("sensorType dht")
                        temp, hum = self.read_dht_temp(
                            temp_reader['sensorType'], temp_reader['gpioPin'])
                    elif temp_reader['sensorType'] == "18b20":
                        temp = self.read_18b20_temp()
                        hum = 0
                    elif temp_reader['sensorType'] == "bme280":
                        temp, hum = self.read_bme280_temp(
                            temp_reader['sensorAddress'])
                    elif temp_reader['sensorType'] == "si7021":
                        temp, hum = self.read_si7021_temp(
                            temp_reader['sensorAddress'])
                    elif temp_reader['sensorType'] == "tmp102":
                        temp = self.read_tmp102_temp(
                            temp_reader['sensorAddress'])
                        hum = 0
                    else:
                        self._logger.info("sensorType no match")
                        temp = 0
                        hum = 0

                    if temp != -1 and hum != -1:
                        self.enclosure_current_temperature = round(self.to_float(
                            temp), 1) if not temp_reader['useFahrenheit'] else round(self.to_float(temp) * 1.8 + 32, 1)
                        self.enclosure_current_humidity = round(
                            self.to_float(hum), 1)

                    if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                        self._logger.info(
                            "Temperature: %s humidity %s", self.enclosure_current_temperature, self.enclosure_current_humidity)

                    self._plugin_manager.send_plugin_message(self._identifier, dict(
                        enclosuretemp=self.enclosure_current_temperature, enclosureHumidity=self.enclosure_current_humidity))
                    self.handle_temperature_control()
                    self.handle_temperature_events()
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def handle_temperature_events(self):
        for rpi_input in self.rpi_inputs:
            if self.to_float(rpi_input['setTemp']) == 0:
                continue
            if rpi_input['actionType'] == 'temperature' and (self.to_float(rpi_input['setTemp']) < self.to_float(self.enclosure_current_temperature)):
                for rpi_output in self.rpi_outputs:
                    if self.to_int(rpi_input['controlledIO']) == self.to_int(rpi_output['gpioPin']):
                        val = GPIO.LOW if rpi_output['activeLow'] else GPIO.HIGH
                        self.write_gpio(self.to_int(rpi_output['gpioPin']), val)
                        for notification in self.notifications:
                            if notification['temperatureAction']:
                                msg = "Temperature action: enclosure temperature exceed " + \
                                    rpi_input['setTemp']
                                self.send_notification(msg)

    def read_dht_temp(self, sensor, pin):
        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/getDHTTemp.py "
            cmd = "sudo python " + script + str(sensor) + " " + str(pin)
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("Temperature dht cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("Dht result: %s", stdout)
            temp, hum = stdout.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def read_bme280_temp(self, address):
        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/BME280.py "
            cmd = "sudo python " + script + str(address)
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("Temperature BME280 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("BME280 result: %s", stdout)
            temp, hum = stdout.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def read_si7021_temp(self, address):
        try:
            script = os.path.dirname(
                os.path.realpath(__file__)) + "/SI7021.py "
            cmd = "sudo python " + script + str(address)
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("Temperature SI7021 cmd: %s", cmd)
            stdout = (Popen(cmd, shell=True, stdout=PIPE).stdout).read()
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("SI7021 result: %s", stdout)
            temp, hum = stdout.split("|")
            return (self.to_float(temp.strip()), self.to_float(hum.strip()))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            return (0, 0)

    def read_18b20_temp(self):
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')

        lines = self.read_raw_18b20_temp()
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = self.read_raw_18b20_temp()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            temp_c = float(temp_string) / 1000.0
            return '{0:0.1f}'.format(temp_c)
        return 0

    def read_raw_18b20_temp(self):
        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'
        device_file_result = open(device_file, 'r')
        lines = device_file_result.readlines()
        device_file_result.close()
        return lines

    def read_tmp102_temp(self, address):
        try:
            script = os.path.dirname(os.path.realpath(__file__)) + "/tmp102.py"
            args = ["python", script, str(address)]
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("Temperature TMP102 cmd: %s", " ".join(args))
            proc = Popen(args, stdout=PIPE)
            stdout, _ = proc.communicate()
            if self._settings.get(["debug"]) is True and self._settings.get(["enableTemperatureLog"]) is True:
                self._logger.info("TMP102 result: %s", stdout)
            return self.to_float(stdout.strip())
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            return 0

    def handle_temperature_control(self):
        for control in self.temperature_control:
            if control['isEnabled'] is True:
                if control['controlType'] is 'heater':
                    self.current_temp_control_status = self.to_float(
                        self.enclosure_current_temperature) < self.to_float(self.enclosure_set_temperature)
                else:
                    if self.to_float(self.enclosure_set_temperature) == 0:
                        self.current_temp_control_status = False
                    else:
                        self.current_temp_control_status = self.to_float(
                            self.enclosure_current_temperature) > self.to_float(self.enclosure_set_temperature)
                if self.current_temp_control_status != self.previous_temp_control_status:
                    if self.current_temp_control_status:
                        self._logger.info(
                            "Turning gpio to control temperature on.")
                        val = False if control['activeLow'] else True
                        self.write_gpio(self.to_int(control['gpioPin']), val)
                    else:
                        self._logger.info(
                            "Turning gpio to control temperature off.")
                        val = True if control['activeLow'] else False
                        self.write_gpio(self.to_int(control['gpioPin']), val)
                    self.previous_temp_control_status = self.current_temp_control_status

    def start_gpio(self):
        try:
            currentMode = GPIO.getmode()
            setMode = GPIO.BOARD if self._settings.get(
                ["useBoardPinNumber"]) else GPIO.BCM
            if currentMode is None:
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
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def clear_gpio(self):
        try:
            for control in self.temperature_control:
                if control['isEnabled']:
                    GPIO.cleanup(self.to_int(control['gpioPin']))
            for rpi_output in self.rpi_outputs:
                if self.to_int(rpi_output['gpioPin']) not in self.previous_rpi_outputs:
                    GPIO.cleanup(self.to_int(rpi_output['gpioPin']))
            for rpi_input in self.rpi_inputs:
                try:
                    GPIO.remove_event_detect(self.to_int(rpi_input['gpioPin']))
                except:
                    pass
                GPIO.cleanup(self.to_int(rpi_input['gpioPin']))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def clear_channel(self, channel):
        try:
            GPIO.cleanup(self.to_int(channel))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def configure_gpio(self):
        try:
            for control in self.temperature_control:
                if control['isEnabled']:
                    GPIO.setup(self.to_int(
                        control['gpioPin']), GPIO.OUT, initial=GPIO.HIGH if control['activeLow'] else GPIO.LOW)
            for rpi_output in self.rpi_outputs:
                pin = self.to_int(rpi_output['gpioPin'])
                if rpi_output['outputType'] == 'regular':
                    if self.to_int(rpi_output['gpioPin']) not in self.previous_rpi_outputs:
                        initialValue = GPIO.HIGH if rpi_output['activeLow'] else GPIO.LOW
                        GPIO.setup(pin, GPIO.OUT, initial=initialValue)
                if rpi_output['outputType'] == 'pwm':
                    for pwm in (pwm for pwm in self.pwm_intances if pin in pwm):
                        self.pwm_intances.remove(pwm)
                    self.clear_channel(pin)
                    GPIO.setup(pin, GPIO.OUT)
                    p = GPIO.PWM(pin, self.to_int(rpi_output['frequency']))
                    self.pwm_intances.append({pin: p})
                if rpi_output['outputType'] == 'neopixel':
                    self.clear_channel(pin)
            for rpi_input in self.rpi_inputs:
                pullResistor = pull_up_down = GPIO.PUD_UP if rpi_input[
                    'inputPull'] == 'inputPullUp' else GPIO.PUD_DOWN
                GPIO.setup(self.to_int(
                    rpi_input['gpioPin']), GPIO.IN, pullResistor)
                if rpi_input['actionType'] == 'gpio' and self.to_int(rpi_input['gpioPin']) != 0:
                    edge = GPIO.RISING if rpi_input['edge'] == 'rise' else GPIO.FALLING
                    GPIO.add_event_detect(self.to_int(
                        rpi_input['gpioPin']), edge, callback=self.handle_gpio_Control, bouncetime=200)
                if rpi_input['actionType'] == 'printer' and rpi_input['printerAction'] != 'filament' and self.to_int(rpi_input['gpioPin']) != 0:
                    edge = GPIO.RISING if rpi_input['edge'] == 'rise' else GPIO.FALLING
                    GPIO.add_event_detect(self.to_int(
                        rpi_input['gpioPin']), edge, callback=self.handle_printer_action, bouncetime=200)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def handle_filamment_detection(self, channel):
        try:
            for rpi_input in self.rpi_inputs:
                if channel == self.to_int(rpi_input['gpioPin']) and rpi_input['actionType'] == 'printer' and rpi_input['printerAction'] == 'filament' \
                        and ((rpi_input['edge'] == 'fall') ^ GPIO.input(self.to_int(rpi_input['gpioPin']))):
                    if time.time() - self.last_filament_end_detected > self._settings.get_int(["filamentSensorTimeout"]):
                        self._logger.info("Detected end of filament.")
                        self.last_filament_end_detected = time.time()
                        for line in self._settings.get(["filamentSensorGcode"]).split('\n'):
                            if line:
                                self._printer.commands(line.strip().upper())
                                self._logger.info(
                                    "Sending GCODE command: %s", line.strip().upper())
                                time.sleep(0.2)
                        for notification in self.notifications:
                            if notification['filamentChange']:
                                msg = "Filament change action caused by sensor: " + \
                                    str(rpi_input['label'])
                                self.send_notification(msg)
                    else:
                        self._logger.info(
                            "Prevented end of filament detection, filament sensor timeout not elapsed.")
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def start_filament_detection(self):
        self.stop_filament_detection()
        try:
            for rpi_input in self.rpi_inputs:
                if rpi_input['actionType'] == 'printer' and rpi_input['printerAction'] == 'filament' and self.to_int(rpi_input['gpioPin']) != 0:
                    edge = GPIO.RISING if rpi_input['edge'] == 'rise' else GPIO.FALLING
                    if GPIO.input(self.to_int(rpi_input['gpioPin'])) == (edge == GPIO.RISING):
                        self._printer.pause_print()
                        self._logger.info("Started printing with no filament.")
                    else:
                        GPIO.add_event_detect(self.to_int(
                            rpi_input['gpioPin']), edge, callback=self.handle_filamment_detection, bouncetime=200)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def stop_filament_detection(self):
        try:
            for rpi_input in self.rpi_inputs:
                if rpi_input['actionType'] == 'printer' and rpi_input['printerAction'] == 'filament':
                    GPIO.remove_event_detect(self.to_int(rpi_input['gpioPin']))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def cancel_events_on_queue(self):
        for task in self.queue:
            task.cancel()

    def handle_gpio_Control(self, channel):
        try:
            for rpi_input in self.rpi_inputs:
                if channel == self.to_int(rpi_input['gpioPin']) and rpi_input['actionType'] == 'gpio' and \
                        ((rpi_input['edge'] == 'fall') ^ GPIO.input(self.to_int(rpi_input['gpioPin']))):
                    for rpi_output in self.rpi_outputs:
                        if self.to_int(rpi_input['controlledIO']) == self.to_int(rpi_output['gpioPin']) and rpi_output['outputType'] == 'regular':
                            if rpi_input['setControlledIO'] == 'toggle':
                                val = GPIO.LOW if GPIO.input(self.to_int(
                                    rpi_output['gpioPin'])) == GPIO.HIGH else GPIO.HIGH
                            else:
                                val = GPIO.LOW if rpi_input['setControlledIO'] == 'low' else GPIO.HIGH
                            self.write_gpio(self.to_int(
                                rpi_output['gpioPin']), val)
                            for notification in self.notifications:
                                if notification['gpioAction']:
                                    msg = "GPIO control action caused by input " + str(rpi_input['label']) + ". Setting GPIO" + str(
                                        rpi_input['controlledIO']) + " to: " + str(rpi_input['setControlledIO'])
                                    self.send_notification(msg)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def handle_printer_action(self, channel):
        try:
            for rpi_input in self.rpi_inputs:
                if channel == self.to_int(rpi_input['gpioPin']) and rpi_input['actionType'] == 'printer' and \
                        ((rpi_input['edge'] == 'fall') ^ GPIO.input(self.to_int(rpi_input['gpioPin']))):
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
                        self._logger.info(
                            "Printer action stoping temperature control.")
                        self.enclosure_set_temperature = 0
                        self.handle_temperature_control()
                    for notification in self.notifications:
                        if notification['printerAction']:
                            msg = "Printer action: " + \
                                rpi_input['printerAction'] + \
                                " caused by input: " + str(rpi_input['label'])
                            self.send_notification(msg)
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def write_gpio(self, gpio, value):
        try:
            GPIO.output(gpio, value)
            if self._settings.get(["debug"]) is True:
                self._logger.info("Writing on gpio: %s value %s", gpio, value)
            self.update_output_ui()
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def write_pwm(self, gpio, pwmValue):
        try:
            for pwm in self.pwm_intances:
                if gpio in pwm:
                    pwm_object = pwm[gpio]
                    pwm['dutycycle'] = pwmValue
                    pwm_object.stop()
                    pwm_object.start(pwmValue)
                    if self._settings.get(["debug"]) is True:
                        self._logger.info(
                            "Writing PWM on gpio: %s value %s", gpio, pwmValue)
                    self.update_output_ui()
                    break
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def update_output_ui(self):
        try:
            result = []
            result_pwm = []

            for rpi_output in self.rpi_outputs:
                pin = self.to_int(rpi_output['gpioPin'])
                if rpi_output['outputType'] == 'regular':
                    val = GPIO.input(pin) if not rpi_output['activeLow'] else (
                        not GPIO.input(pin))
                    result.append({pin: val})
                if rpi_output['outputType'] == 'pwm':
                    for pwm in self.pwm_intances:
                        if pin in pwm:
                            if 'dutycycle' in pwm:
                                pwmVal = pwm['dutycycle']
                                val = self.to_int(pwmVal)
                            else:
                                val = 100
                            result_pwm.append({pin: val})
                        # self._logger.info("result_pwm: %s", result_pwm)
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(rpi_output=result, rpi_output_pwm=result_pwm))
        except Exception as ex:
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
            message = template.format(
                type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
            self._logger.warn(message)
            pass

    def get_output_list(self):
        result = []
        for rpi_output in self.rpi_outputs:
            result.append(self.to_int(rpi_output['gpioPin']))
        return result

    def send_notification(self, message):
        try:
            provider = self._settings.get(["notificationProvider"])
            if provider == 'ifttt':
                event = self._settings.get(["event_name"])
                api_key = self._settings.get(["apiKEY"])
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
            template = "An exception of type {0} occurred on {1}. Arguments:\n{1!r}"
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
            self.update_output_ui()

        if event == Events.PRINT_RESUMED:
            self.start_filament_detection()

        if event == Events.PRINT_STARTED:
            self.cancel_events_on_queue()
            self.start_filament_detection()
            for rpi_output in self.rpi_outputs:
                if rpi_output['autoStartup'] and rpi_output['outputType'] == 'regular':
                    value = False if rpi_output['activeLow'] else True
                    self.queue.append(threading.Timer(self.to_float(rpi_output['startupTimeDelay']),
                                                      self.write_gpio,
                                                      args=[self.to_int(rpi_output['gpioPin']), value]))
                if rpi_output['autoStartup'] and rpi_output['outputType'] == 'pwm':
                    value = self.to_int(rpi_output['dutycycle'])
                    self.queue.append(threading.Timer(self.to_float(rpi_output['startupTimeDelay']),
                                                      self.write_pwm,
                                                      args=[self.to_int(rpi_output['gpioPin']), value]))
                if rpi_output['autoStartup'] and rpi_output['outputType'] == 'neopixel':
                    gpioPin = rpi_output['gpioPin']
                    ledCount = rpi_output['neopixelCount']
                    ledBrightness = rpi_output['neopixelBrightness']
                    address = rpi_output['microAddress']
                    stringColor = rpi_output['color']
                    stringColor = stringColor.replace('rgb(', '')

                    red = stringColor[:stringColor.index(',')]
                    stringColor = stringColor[stringColor.index(',') + 1:]
                    green = stringColor[:stringColor.index(',')]
                    stringColor = stringColor[stringColor.index(',') + 1:]
                    blue = stringColor[:stringColor.index(')')]

                    self.queue.append(threading.Timer(self.to_float(rpi_output['startupTimeDelay']),
                                                      self.send_neopixel_command,
                                                      args=[gpioPin, ledCount, ledBrightness, red, green, blue, address]))
                for task in self.queue:
                    task.start()
            for control in self.temperature_control:
                if control['autoStartup'] is True:
                    self.enclosure_set_temperature = self.to_int(
                        control['defaultTemp'])
                    self._plugin_manager.send_plugin_message(
                        self._identifier, dict(enclosureSetTemp=self.enclosure_set_temperature))

        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            self.stop_filament_detection()
            self.enclosure_set_temperature = 0
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(enclosureSetTemp=self.enclosure_set_temperature))
            for rpi_output in self.rpi_outputs:
                if rpi_output['autoShutdown'] and rpi_output['outputType'] == 'regular':
                    value = True if rpi_output['activeLow'] else False
                    self.queue.append(threading.Timer(self.to_float(rpi_output['shutdownTimeDelay']),
                                                      self.write_gpio,
                                                      args=[self.to_int(rpi_output['gpioPin']), value]))
                if rpi_output['autoShutdown'] and rpi_output['outputType'] == 'pwm':
                    value = 0
                    self.queue.append(threading.Timer(self.to_float(rpi_output['shutdownTimeDelay']),
                                                      self.write_pwm,
                                                      args=[self.to_int(rpi_output['gpioPin']), value]))
                if rpi_output['autoShutdown'] and rpi_output['outputType'] == 'neopixel':
                    gpioPin = rpi_output['gpioPin']
                    ledCount = rpi_output['neopixelCount']
                    ledBrightness = rpi_output['neopixelBrightness']
                    address = rpi_output['microAddress']
                    self.queue.append(threading.Timer(self.to_float(rpi_output['shutdownTimeDelay']),
                                                      self.send_neopixel_command,
                                                      args=[gpioPin, ledCount, 0, 0, 0, 0, address]))
            for task in self.queue:
                task.start()

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

        self._logger.info("data: %s", data)

        outputsBeforeSave = self.get_output_list()
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.temperature_reading = self._settings.get(["temperature_reading"])
        self.temperature_control = self._settings.get(["temperature_control"])
        self.rpi_outputs = self._settings.get(["rpi_outputs"])
        self.rpi_inputs = self._settings.get(["rpi_inputs"])
        self.notifications = self._settings.get(["notifications"])
        outputsAfterSave = self.get_output_list()

        commonPins = list(set(outputsBeforeSave) & set(outputsAfterSave))

        for pin in (pin for pin in outputsBeforeSave if pin not in commonPins):
            self.clear_channel(pin)

        self.previous_rpi_outputs = commonPins
        self.clear_gpio()

        if self._settings.get(["debug"]) is True:
            self._logger.info("temperature_reading: %s",
                              self.temperature_reading)
            self._logger.info("temperature_control: %s",
                              self.temperature_control)
            self._logger.info("rpi_outputs: %s", self.rpi_outputs)
            self._logger.info("rpi_inputs: %s", self.rpi_inputs)
        self.start_gpio()
        self.configure_gpio()

    def get_settings_defaults(self):
        return dict(
            temperature_reading=[{'isEnabled': False, 'gpioPin': 4,
                                  'useFahrenheit': False, 'sensorType': '', 'sensorAddress': 0}],
            temperature_control=[{'isEnabled': False, 'controlType': 'heater',
                                  'gpioPin': 17, 'activeLow': True, 'autoStartup': False, 'defaultTemp': 0}],
            rpi_outputs=[],
            rpi_inputs=[],
            filamentSensorGcode="G91  ;Set Relative Mode \n" +
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
            enableTemperatureLog=False,
            useBoardPinNumber=False,
            filamentSensorTimeout=120,
            notificationProvider="disabled",
            apiKEY="",
            event_name="printer_event",
            showTempNavbar=False,
            settingsVersion="",
            notifications=[{'printFinish': True, 'filamentChange': True,
                            'printerAction': True, 'temperatureAction': True, 'gpioAction': True}]
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
            js=["js/enclosure.js", "js/bootstrap-colorpicker.min.js"],
            css=["css/bootstrap-colorpicker.css"]
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
