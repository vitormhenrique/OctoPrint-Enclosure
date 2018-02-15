$(function () {
  function EnclosureViewModel(parameters) {
    var self = this;

    self.pluginName = "enclosure";

    self.settingsViewModel = parameters[0];
    self.connectionViewModel = parameters[1];
    self.printerStateViewModel = parameters[2];

    self.rpi_outputs = ko.observableArray();
    self.rpi_inputs = ko.observableArray();

    self.rpi_outputs_regular = ko.pureComputed(function () {
      return ko.utils.arrayFilter(self.settingsViewModel.settings.plugins.enclosure.rpi_outputs(), function (item) {
        return (item.output_type() === "regular");
      });
    });

    self.rpi_outputs_pwm = ko.pureComputed(function () {
      return ko.utils.arrayFilter(self.settingsViewModel.settings.plugins.enclosure.rpi_outputs(), function (item) {
        return (item.output_type() === "pwm");
      });
    });

    self.rpi_inputs_temperature_sensors = ko.pureComputed(function () {
      return ko.utils.arrayFilter(self.settingsViewModel.settings.plugins.enclosure.rpi_inputs(), function (item) {
        return (item.input_type() === "temperature_sensor");
      });
    });

    self.debug = ko.observable();
    self.debug_temperature_log = ko.observable();
    self.filament_sensor_gcode = ko.observable();
    self.notification_provider = ko.observable();
    self.notification_event_name = ko.observable();
    self.notification_api_key = ko.observable();
    self.notifications = ko.observable();

    self.humidityCapableSensor = function(sensor){
      if (['11', '22'].indexOf(sensor) >= 0){
        return true;
      }
      return false;
    };

    self.linkedTemperatureControl = function(sensor_index){
      return ko.pureComputed(function () {
        return ko.utils.arrayFilter(self.settingsViewModel.settings.plugins.enclosure.rpi_outputs(), function (item) {
          return (item.linked_temperature_sensor() == sensor_index);
        });
      });
    };

    self.hasAnySensorWithHumidity = function(){
      self.rpi_inputs_temperature_sensors().forEach(function (sensor) {
        if (self.humidityCapableSensor(sensor.temperature_sensor_type())) {
          return true;
        } 
      });
      return false;
    };

    self.onDataUpdaterPluginMessage = function (plugin, data) {
      if (plugin != "enclosure") {
        return;
      }

      if (data.hasOwnProperty("sensor_data")) {
        data.sensor_data.forEach(function (sensor_data) {
          var linked_temperature_sensor = ko.utils.arrayFilter(self.rpi_inputs(), function (temperature_sensor) {
            return (sensor_data['id'] == temperature_sensor.index_id());
          }).pop();

          if (linked_temperature_sensor){
            linked_temperature_sensor.temperature_sensor_temperature(sensor_data['temperature'])
            linked_temperature_sensor.temperature_sensor_humidity(sensor_data['humidity'])
          }

        })
        // linked_item.temperature_sensor_temperature()
      };




      // if (data.hasOwnProperty("enclosureHumidity")) {
      //   self.enclosureHumidity(data.enclosureHumidity);
      //   self.navbarHum(_.sprintf("Hum: %.1f%%", data.enclosureHumidity));
      // }

      // if (data.hasOwnProperty("enclosureSetTemp")) {
      //   if (parseFloat(data.enclosureSetTemp) > 0.0) {
      //     $("#enclosureSetTemp").attr("placeholder", data.enclosureSetTemp);
      //   } else {
      //     $("#enclosureSetTemp").attr("placeholder", "off");
      //   }
      // }

      // if (!data.rpi_output) {
      //   data.rpi_output = self.previous_gpio_status;
      // }

      // if (!data.rpi_output_pwm) {
      //   data.rpi_output_pwm = self.previous_gpio_pwm_status;
      // }

      // if (data.rpi_output) {
      //   data.rpi_output.forEach(function (gpio) {
      //     key = Object.keys(gpio)[0];
      //     if (gpio[key]) {
      //       $("#btn_off_" + key).removeClass('active');
      //       $("#btn_on_" + key).addClass('active');
      //     } else {
      //       $("#btn_off_" + key).addClass('active');
      //       $("#btn_on_" + key).removeClass('active');
      //     }
      //   });
      //   self.previous_gpio_status = data.rpi_output;
      // }

      // if (data.rpi_output_pwm) {
      //   data.rpi_output_pwm.forEach(function (gpio) {
      //     key = Object.keys(gpio)[0];
      //     val = gpio[key];
      //     if (parseFloat(val) != 100) {
      //       $("#duty_cycle_" + key).attr("placeholder", val);
      //     } else {
      //       $("#duty_cycle_" + key).attr("placeholder", "off");
      //     }
      //   });
      //   self.previous_gpio_pwm_status = data.rpi_output_pwm;
      // }

      if (data.isMsg) {
        new PNotify({
          title: "Enclosure",
          text: data.msg,
          type: "error"
        });
      }
    };

    self.enableBtn = ko.computed(function () {
      // return self.connectionViewModel.loginState.isUser() && self.printerStateViewModel.isOperational();
      return self.connectionViewModel.loginState.isUser();
    });


    self.getCleanTemperature = function (temp) {
      if (temp === undefined || isNaN(parseFloat(temp))) return "-";
      if (temp < 10) return String("off");
      return temp;
    }


    self.onBeforeBinding = function () {

      self.rpi_outputs(self.settingsViewModel.settings.plugins.enclosure.rpi_outputs());
      self.rpi_inputs(self.settingsViewModel.settings.plugins.enclosure.rpi_inputs());

      self.debug(self.settingsViewModel.settings.plugins.enclosure.debug())
      self.debug_temperature_log(self.settingsViewModel.settings.plugins.enclosure.debug_temperature_log())
      self.filament_sensor_gcode(self.settingsViewModel.settings.plugins.enclosure.filament_sensor_gcode())
      self.notification_provider(self.settingsViewModel.settings.plugins.enclosure.notification_provider())
      self.notification_event_name(self.settingsViewModel.settings.plugins.enclosure.notification_event_name())
      self.notification_api_key(self.settingsViewModel.settings.plugins.enclosure.notification_api_key())
      self.notifications(self.settingsViewModel.settings.plugins.enclosure.notifications())

      // self.settings = self.settingsViewModel.settings.plugins.enclosure;
      // self.temperature_reading(self.settings.temperature_reading());
      // // self.temperature_control(self.settings.temperature_control.slice(0));
    };

    self.onStartupComplete = function () {
      // var test = self.linkedTemperatureControl(1);
      // console.log(test());
    };

    self.onDataUpdaterReconnect = function () {
      // self.getUpdateBtnStatus();
    };

    self.onSettingsShown = function () {

    };

    self.showColorPicker = function () {
      $('[name=colorpicker]').colorpicker({
        format: 'rgb'
      });
    }

    self.onSettingsHidden = function () {
      // self.getUpdateBtnStatus();
    };

    self.getRegularOutputs = function () {
      return self.settingsViewModel.settings.plugins.enclosure.rpi_outputs().filter(function (rpi_outputs) {
        return rpi_outputs.output_type == 'regular';
      });
    };
    self.setTemperature = function (item, form) {

      var newSetTemperature = item.temperature_control_new_temperature();
      if (form !== undefined) {
        $(form).find("input").blur();
      }

      if(self.isNumeric(newSetTemperature)){
        var request = {set_temperature:newSetTemperature, index_id:item.index_id()};
        $.ajax({
          url: self.buildPluginUrl("/setEnclosureTemperature"),
          type: "GET",
          dataType: "json",
          data: request,
          success: function (data) {
            item.temperature_control_new_temperature("");
            item.temperature_control_set_temperature(newSetTemperature);
          },
          error: function (textStatus, errorThrown) {
            new PNotify({
              title: "Enclosure",
              text: "Error setting temperature",
              type: "error"
            });
        }
        });
      }else{
        new PNotify({
          title: "Enclosure",
          text: "Invalid set temperature",
          type: "error"
        });
      } 
    };

    self.addRpiOutput = function () {

      var arrRelaysLength = self.settingsViewModel.settings.plugins.enclosure.rpi_outputs().length;

      var nextIndex = arrRelaysLength == 0 ? 1 : self.settingsViewModel.settings.plugins.enclosure.rpi_outputs()[arrRelaysLength - 1].index_id() + 1;

      self.settingsViewModel.settings.plugins.enclosure.rpi_outputs.push({
        index_id: ko.observable(nextIndex),
        label: ko.observable("Ouput " + nextIndex),
        output_type: ko.observable("regular"),
        gpio_pin: ko.observable(0),
        gpio_status: ko.observable(0),
        active_low: ko.observable(true),
        auto_startup: ko.observable(false),
        controlled_io: ko.observable(0),
        controlled_io_set_value: ko.observable("Low"),
        startup_time: ko.observable(0),
        auto_shutdown: ko.observable(false),
        shutdown_time: ko.observable(0),
        linked_temperature_sensor: ko.observable(),
        alarm_set_temperature: ko.observable(0),
        temperature_control_type: ko.observable(""),
        temperature_control_deadband: ko.observable(0),
        temperature_control_set_temperature: ko.observable(0),
        temperature_control_new_temperature: ko.observable(""),
        temperature_control_default_temperature: ko.observable(0),
        temperature_control_max_temperature: ko.observable(0),
        pwm_frequency: ko.observable(50),
        pwm_status: ko.observable(50),
        duty_cycle: ko.observable(0),
        neopixel_color: ko.observable("rgb(255,0,0)"),
        neopixel_count: ko.observable(0),
        neopixel_brightness: ko.observable(255),
        microcontroller_address: ko.observable(0),
        gcode: ko.observable("")
      });

      // var test = self.settingsViewModel.settings.plugins.enclosure.rpi_outputs();

      // console.log(self.rpi_outputs_regular());
    };

    self.removeRpiOutput = function (data) {
      self.settingsViewModel.settings.plugins.enclosure.rpi_outputs.remove(data);
    };

    self.addRpiInput = function () {

      var arrRelaysLength = self.settingsViewModel.settings.plugins.enclosure.rpi_inputs().length;

      var nextIndex = arrRelaysLength == 0 ? 1 : self.settingsViewModel.settings.plugins.enclosure.rpi_inputs()[arrRelaysLength - 1].index_id() + 1;

      self.settingsViewModel.settings.plugins.enclosure.rpi_inputs.push({
        index_id: ko.observable(nextIndex),
        label: ko.observable("Input " + nextIndex),
        input_type: ko.observable("gpio"),
        gpio_pin: ko.observable(0),
        input_pull_resistor: ko.observable("input_pull_up"),
        temperature_sensor_type: ko.observable("DS18B20"),
        temperature_sensor_address: ko.observable(""),
        temperature_sensor_temperature: ko.observable(0),
        temperature_sensor_humidity: ko.observable(0),
        ds18b20_serial: ko.observable(""),
        use_fahrenheit: ko.observable(false),
        action_type: ko.observable("gpio_control"),
        controlled_io: ko.observable(""),
        controlled_io_set_value: ko.observable("low"),
        edge: ko.observable("fall"),
        printer_action: ko.observable("filament"),
        temperature_sensor_navbar: ko.observable(true),
        filament_sensor_timeout: ko.observable(120),
        filament_sensor_enabled: ko.observable(true)
      });
    };

    self.removeRpiInput = function (definition) {
      self.settingsViewModel.settings.plugins.enclosure.rpi_inputs.remove(definition);
    };

    self.turnOffHeater = function (item) {
      console.log(item);
      // $.ajax({
      //   url: self.buildPluginUrl("/setEnclosureTemperature"),
      //   type: "GET",
      //   dataType: "json",
      //   data: {
      //     "enclosureSetTemp": 0
      //   },
      //   success: function (data) {
      //     $("#enclosureSetTemp").val('');
      //     $("#enclosureSetTemp").attr("placeholder", self.getCleanTemperature(data.enclosureSetTemperature));
      //   }
      // });
    };

    self.clearGPIOMode = function () {
      $.ajax({
        url: self.buildPluginUrl("/clearGPIOMode"),
        type: "GET",
        dataType: "json",
        success: function (data) {
          new PNotify({
            title: "Enclosure",
            text: "GPIO Mode cleared successfully",
            type: "success"
          });
        }
      });
    };

    self.getUpdateBtnStatus = function () {

      $.ajax({
        url: self.buildPluginUrl("/getUpdateBtnStatus"),
        type: "GET"
      });
    };

    self.requestEnclosureTemperature = function () {
      return $.ajax({
        type: "GET",
        url: self.buildPluginUrl("/getEnclosureTemperature"),
        async: false
      }).responseText;
    };

    self.requestEnclosureSetTemperature = function () {
      return $.ajax({
        type: "GET",
        url: self.buildPluginUrl("/getEnclosureSetTemperature"),
        async: false
      }).responseText;
    };

    self.handleIO = function (data, event) {
      $.ajax({
        type: "GET",
        dataType: "json",
        data: {
          "io": data[0],
          "status": data[1]
        },
        url: self.buildPluginUrl("/setIO"),
        async: false
      });
    };

    self.handlePWM = function (data, event) {
      io = parseInt(data[0]);
      pwmVal = parseInt($("#duty_cycle_" + io).val());
      if (pwmVal < 0 || pwmVal > 100 || isNaN(pwmVal)) {
        $("#duty_cycle_" + io).val('')
        new PNotify({
          title: "Enclosure",
          text: "Duty Cycle value needs to be between 0 and 100!",
          type: "error"
        });
      } else {
        // console.log(pwmVal);
        $("#duty_cycle_" + io).val('')
        $("#duty_cycle_" + io).attr("placeholder", pwmVal);
        $.ajax({
          type: "GET",
          dataType: "json",
          data: {
            "io": io,
            "pwmVal": pwmVal
          },
          url: self.buildPluginUrl("/setPWM"),
        });
      }
    };

    self.handleNeopixel = function (data, event) {
      io = parseInt(data[0]);
      tempStr = ($("#color_" + io).val()).replace("rgb(", "");

      r = parseInt(tempStr.substring(0, tempStr.indexOf(",")));
      tempStr = tempStr.slice(tempStr.indexOf(",") + 1);
      g = parseInt(tempStr.substring(0, tempStr.indexOf(",")));
      tempStr = tempStr.slice(tempStr.indexOf(",") + 1);
      b = parseInt(tempStr.substring(0, tempStr.indexOf(")")));

      if (r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255 || isNaN(r) || isNaN(g) || isNaN(b)) {
        new PNotify({
          title: "Enclosure",
          text: "Color needs to follow the format rgb(value_red,value_green,value_blue)!",
          type: "error"
        });
      } else {
        $.ajax({
          type: "GET",
          dataType: "json",
          data: {
            "io": io,
            "red": r,
            "green": g,
            "blue": b
          },
          url: self.buildPluginUrl("/setNeopixel"),
        });
      }
    };

    self.isNumeric = function (n) {
      return !isNaN(parseFloat(n)) && isFinite(n);
    };

    self.buildPluginUrl = function (path) {
      return window.PLUGIN_BASEURL + self.pluginName + path;
    };
  }

  OCTOPRINT_VIEWMODELS.push({
    construct: EnclosureViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
    dependencies: ["settingsViewModel", "connectionViewModel", "printerStateViewModel"],
    // Elements to bind to, e.g. #settings_plugin_tasmota-mqtt, #tab_plugin_tasmota-mqtt, ...
    elements: ["#tab_plugin_enclosure", "#settings_plugin_enclosure", "#navbar_plugin_enclosure"]
  });

});