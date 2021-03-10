function isInteger(value) {
  return /^\d+$/.test(value);
}

$(function () {

  var cleanInput = function (index_id) {
    return {
      index_id: index_id,
      label: "",
      input_type: "regular_gpio",
      action_type: "output_control",
      gpio: {
        pin_name: "",
        pull_resistor: "input_pull_up",
        linked_action: "output_control",
        edge_detection: "fall",
      },
      linked_printer_action: {
        action: "filament",
        filament_sensor_enabled: false,
        filament_sensor_timeout: 120,
      },
      linked_output_action: {
        output_index_id: "",
        output_set_value: "low",
      },
      temperature_sensor: {
        type: "si7021",
        address: "",
        unit: "celsius",
      }
    }
  };

  var cleanOutput = function (index_id) {
    return {
      index_id: index_id,
      label: "",
      output_type: "regular_gpio",
      gpio: {
        pin_name: "",
        active_low: false,
      },
      gcode: {
        gcode: "",
      },
      neopixel: {
        count: "",
        brightness: "",
        default_color: "",
      },
      other_config: {
        hide_on_tab: false,
        show_on_navbar: false,
      },
      pwm: {
        linked_to_temperature: false,
        duty_a: "",
        temperature_a: "",
        duty_b: "",
        temperature_b: "",
        frequency: "",
        default_duty_cycle: "",
        linked_temp_sensor: "",
      },
      led_strip: {
        clock_pin: "",
        data_pin: "",
        default_color: "",
      },
      schedule: {
        toggle_timer: false,
        time_on: "",
        time_off: "",
        startup_with_server: false,
        auto_startup: false,
        startup_time_delay: "",
        auto_shutdown: false,
        shutdown_on_failed: false,
        shutdown_time_delay: "",
      },
      shell_script: {
        shell_script: "",
      },
      temperature_alarm: {
        linked_temp_sensor: "",
        set_temp: "",
        controlled_io: "",
        controlled_io_set_value: "high",
      },
      temperature_control: {
        linked_temp_sensor: "",
        control_type: "heater",
        default_value: "",
        deadband: "",
        max_temperature: "",
      }
    }
  };

  function EnclosureInputEditorViewModel(parameters) {
    var self = this;

    self.isNew = ko.observable(false);
    // general info
    self.index_id = ko.observable();
    self.label = ko.observable();
    self.input_type = ko.observable();
    self.action_type = ko.observable();
    // gpio output
    self.gpio_pin = ko.observable();
    self.pull_resistor = ko.observable();
    self.linked_action = ko.observable();
    self.edge_detection = ko.observable();
    // output on linked action
    self.controlled_output = ko.observable();
    self.controlled_output_set_value = ko.observable();
    // printer action on linked action
    self.printer_action = ko.observable();
    self.filament_sensor_enabled = ko.observable();
    self.filament_sensor_timeout = ko.observable();
    // temperature sensor
    self.temperature_sensor_type = ko.observable();
    self.temperature_sensor_address = ko.observable();
    self.temperature_sensor_unit = ko.observable();

    self.enclosureInputs = undefined;

    self.validInput = ko.pureComputed(function () {

      if (self.input_type() == "regular_gpio") {
        if (self.label() != "") {
          return true;
        }
      }

      return false

    });

    self.fromInputEnclosureData = function (data) {

      self.isNew(data === undefined);

      if (data === undefined) {
        var arrRelaysLength = self.enclosureInputs().length;
        var nextIndex = arrRelaysLength == 0 ? 1 : self.enclosureInputs()[arrRelaysLength - 1].index_id() + 1;
        data = cleanInput(nextIndex);
      } else {
        objIndex = self.enclosureInputs().findIndex((obj => obj.index_id == data.index_id));
        data = ko.mapping.toJS(self.enclosureInputs()[objIndex]);
      }

      // general info
      self.index_id(data.index_id);
      self.label(data.label);
      self.input_type(data.input_type);
      self.action_type(data.action_type);
      // gpio output
      self.gpio_pin(data.gpio.pin_name);
      self.pull_resistor(data.gpio.pull_resistor);
      self.linked_action(data.gpio.linked_action);
      self.edge_detection(data.gpio.edge_detection);
      // output on linked action
      self.controlled_output(data.linked_output_action.output_index_id);
      self.controlled_output_set_value(data.linked_output_action.output_set_value);
      // printer action on linked action
      self.printer_action(data.linked_printer_action.action);
      self.filament_sensor_enabled(data.linked_printer_action.filament_sensor_enabled);
      self.filament_sensor_timeout(data.linked_printer_action.filament_sensor_timeout);
      // temperature sensor
      self.temperature_sensor_type(data.type);
      self.temperature_sensor_address(data.address);
      self.temperature_sensor_unit(data.unit);

    };

    self.toInputEnclosureData = function (data) {
      var output_data = {
        index_id: self.index_id(),
        label: self.label(),
        input_type: self.input_type(),
        action_type: self.action_type(),
        gpio: {
          pin_name: self.gpio_pin(),
          pull_resistor: self.pull_resistor(),
          linked_action: self.linked_action(),
          edge_detection: self.edge_detection(),
        },
        linked_printer_action: {
          action: self.printer_action(),
          filament_sensor_enabled: self.filament_sensor_enabled(),
          filament_sensor_timeout: self.filament_sensor_timeout(),
        },
        linked_output_action: {
          output_index_id: self.controlled_output(),
          output_set_value: self.controlled_output_set_value(),
        },
        temperature_sensor: {
          type: self.temperature_sensor_type(),
          address: self.temperature_sensor_address(),
          unit: self.temperature_sensor_unit(),
        }
      }

      return output_data;
    };


    // end of EnclosureInputEditorViewModel
  };

  function EnclosureOutputEditorViewModel(parameters) {
    var self = this;

    self.isNew = ko.observable(false);
    // general info
    self.index_id = ko.observable();
    self.label = ko.observable();
    self.output_type = ko.observable();
    // gpio output
    self.gpio_pin = ko.observable();
    self.active_low = ko.observable();
    // gcode output
    self.gcode = ko.observable();
    // neopixel output
    self.neopixel_count = ko.observable();
    self.neopixel_brightness = ko.observable();
    self.default_neopixel_color = ko.observable();
    // other output configurations
    self.hide_btn_ui = ko.observable();
    self.show_on_navbar = ko.observable();
    // pwm output
    self.pwm_temperature_linked = ko.observable();
    self.duty_a = ko.observable();
    self.temperature_a = ko.observable();
    self.duty_b = ko.observable();
    self.temperature_b = ko.observable();
    self.pwm_frequency = ko.observable();
    self.default_duty_cycle = ko.observable();
    self.pwm_linked_temp_sensor = ko.observable();
    // led strip output
    self.led_trip_gpio_clk = ko.observable();
    self.led_strip_gpio_data = ko.observable();
    self.default_led_strip_color = ko.observable();
    // schedule config
    self.toggle_timer = ko.observable();
    self.toggle_time_on = ko.observable();
    self.toggle_time_off = ko.observable();
    self.startup_with_server = ko.observable();
    self.auto_startup = ko.observable();
    self.startup_time_delay = ko.observable();
    self.auto_shutdown = ko.observable();
    self.shutdown_on_failed = ko.observable();
    self.shutdown_time_delay = ko.observable();
    // shell script output
    self.shell_script = ko.observable();
    // temp alarm output
    self.alarm_linked_temp_sensor = ko.observable();
    self.alarm_set_temp = ko.observable();
    self.controlled_io = ko.observable();
    self.controlled_io_set_value = ko.observable();
    // temp control output
    self.temp_ctr_linked_sensor = ko.observable();
    self.temp_ctr_type = ko.observable();
    self.temp_ctr_default_value = ko.observable();
    self.temp_ctr_deadband = ko.observable();
    self.temp_ctr_max_temp = ko.observable();

    self.enclosureOutputs = undefined;

    self.validOutput = ko.pureComputed(function () {

      if (self.output_type() == "regular_gpio") {
        if (self.label() != "" && self.gpio_pin() != "" && isInteger(self.gpio_pin())) {
          return true;
        }
      }
      return false;
    });

    self.fromOutputEnclosureData = function (data) {

      self.isNew(data === undefined);

      if (data === undefined) {
        var arrRelaysLength = self.enclosureOutputs().length;
        var nextIndex = arrRelaysLength == 0 ? 1 : self.enclosureOutputs()[arrRelaysLength - 1].index_id() + 1;
        data = cleanOutput(nextIndex);
      } else {
        objIndex = self.enclosureOutputs().findIndex((obj => obj.index_id == data.index_id));
        data = ko.mapping.toJS(self.enclosureOutputs()[objIndex]);
      }

      // general info
      self.index_id(data.index_id);
      self.label(data.label);
      self.output_type(data.output_type);
      // gpio output
      self.gpio_pin(data.gpio.pin_name);
      self.active_low(data.gpio.active_low);
      // gcode output
      self.gcode(data.gcode.gcode);
      // neopixel output
      self.neopixel_count(data.neopixel.count);
      self.neopixel_brightness(data.neopixel.brightness);
      self.default_neopixel_color(data.neopixel.default_color);
      // other output configurations
      self.hide_btn_ui(data.other_config.hide_on_tab);
      self.show_on_navbar(data.other_config.show_on_navbar);
      // pwm output
      self.pwm_temperature_linked(data.pwm.linked_to_temperature);
      self.duty_a(data.pwm.duty_a);
      self.temperature_a(data.pwm.temperature_a);
      self.duty_b(data.pwm.duty_b);
      self.temperature_b(data.pwm.temperature_b);
      self.pwm_frequency(data.pwm.frequency);
      self.default_duty_cycle(data.pwm.default_duty_cycle);
      self.pwm_linked_temp_sensor(data.pwm.linked_temp_sensor);
      // led strip output
      self.led_trip_gpio_clk(data.led_strip.clock_pin);
      self.led_strip_gpio_data(data.led_strip.data_pin);
      self.default_led_strip_color(data.led_strip.default_color);
      // schedule config
      self.toggle_timer(data.schedule.toggle_timer);
      self.toggle_time_on(data.schedule.time_on);
      self.toggle_time_off(data.schedule.time_off);
      self.startup_with_server(data.schedule.startup_with_server);
      self.auto_startup(data.schedule.auto_startup);
      self.startup_time_delay(data.schedule.startup_time_delay);
      self.auto_shutdown(data.schedule.auto_shutdown);
      self.shutdown_on_failed(data.schedule.shutdown_on_failed);
      self.shutdown_time_delay(data.schedule.shutdown_time_delay);
      // shell script output
      self.shell_script(data.shell_script.shell_script);
      // temp alarm output
      self.alarm_linked_temp_sensor(data.temperature_alarm.linked_temp_sensor);
      self.alarm_set_temp(data.temperature_alarm.set_temp);
      self.controlled_io(data.temperature_alarm.controlled_io);
      self.controlled_io_set_value(data.temperature_alarm.controlled_io_set_value);
      // temp control output
      self.temp_ctr_linked_sensor(data.temperature_control.linked_temp_sensor);
      self.temp_ctr_type(data.temperature_control.control_type);
      self.temp_ctr_default_value(data.temperature_control.default_value);
      self.temp_ctr_deadband(data.temperature_control.deadband);
      self.temp_ctr_max_temp(data.temperature_control.max_temperature);
    };

    self.showColorPicker = function () {

    };

    self.toOutputEnclosureData = function () {
      var output_data = {
        index_id: self.index_id(),
        label: self.label(),
        output_type: self.output_type(),
        gpio: {
          pin_name: self.gpio_pin(),
          active_low: self.active_low(),
        },
        gcode: {
          gcode: self.gcode(),
        },
        neopixel: {
          count: self.neopixel_count(),
          brightness: self.neopixel_brightness(),
          default_color: self.default_neopixel_color(),
        },
        other_config: {
          hide_on_tab: self.hide_btn_ui(),
          show_on_navbar: self.show_on_navbar(),
        },
        pwm: {
          linked_to_temperature: self.pwm_temperature_linked(),
          duty_a: self.duty_a(),
          temperature_a: self.temperature_a(),
          duty_b: self.duty_b(),
          temperature_b: self.temperature_b(),
          frequency: self.pwm_frequency(),
          default_duty_cycle: self.default_duty_cycle(),
          linked_temp_sensor: self.pwm_linked_temp_sensor(),
        },
        led_strip: {
          clock_pin: self.led_trip_gpio_clk(),
          data_pin: self.led_strip_gpio_data(),
          default_color: self.default_led_strip_color(),
        },
        schedule: {
          toggle_timer: self.toggle_timer(),
          time_on: self.toggle_time_on(),
          time_off: self.toggle_time_off(),
          startup_with_server: self.startup_with_server(),
          auto_startup: self.auto_startup(),
          startup_time_delay: self.startup_time_delay(),
          auto_shutdown: self.auto_shutdown(),
          shutdown_on_failed: self.shutdown_on_failed(),
          shutdown_time_delay: self.shutdown_time_delay(),
        },
        shell_script: {
          shell_script: self.shell_script(),
        },
        temperature_alarm: {
          linked_temp_sensor: self.alarm_linked_temp_sensor(),
          set_temp: self.alarm_set_temp(),
          controlled_io: self.controlled_io(),
          controlled_io_set_value: self.controlled_io_set_value(),
        },
        temperature_control: {
          linked_temp_sensor: self.temp_ctr_linked_sensor(),
          control_type: self.temp_ctr_type(),
          default_value: self.temp_ctr_default_value(),
          deadband: self.temp_ctr_deadband(),
          max_temperature: self.temp_ctr_max_temp(),
        }
      }
      return output_data
    };

    // end of EnclosureOutputEditorViewModel
  };

  function EnclosureViewModel(parameters) {
    var self = this;

    self.settingsViewModel = parameters[0];
    self.connectionViewModel = parameters[1];
    self.printerStateViewModel = parameters[2];

    self.enclosureOutputs = ko.observableArray();
    self.enclosureInputs = ko.observableArray();

    self.settings_unsaved = ko.observable(false);

    self.onBeforeBinding = function () {
      self.enclosureOutputs(self.settingsViewModel.settings.plugins.enclosure.enclosureOutputs())
      self.enclosureInputs(self.settingsViewModel.settings.plugins.enclosure.enclosureInputs())
      // self.settings_unsaved(false);
    };

    self.onSettingsBeforeSave = function () {
      // self.enclosureOutputs(self.settingsViewModel.settings.plugins.enclosure.enclosureOutputs());
    };

    self.onEventSettingsUpdated = function () {
      self.settingsViewModel.settings.plugins.enclosure.enclosureOutputs(self.enclosureOutputs());
      self.settingsViewModel.settings.plugins.enclosure.enclosureInputs(self.enclosureInputs());
      self.settings_unsaved(false);
    };


    self.syncSettings = function () {
      // self.settingsViewModel.settings.plugins.enclosure.enclosureOutputs(self.enclosureOutputs());
      // self.settingsViewModel.settings.plugins.enclosure.enclosureInputs(self.enclosureInputs());
      // self.settings_unsaved(false);
    };

    self.createOutputEditor = function (data) {
      var outputEditor = new EnclosureOutputEditorViewModel();
      return outputEditor;
    };

    self.createInputEditor = function (data) {
      var inputEditor = new EnclosureInputEditorViewModel();
      return inputEditor;
    };

    self.outputEditor = self.createOutputEditor();
    self.outputEditor.enclosureOutputs = self.enclosureOutputs;

    self.inputEditor = self.createInputEditor();
    self.inputEditor.enclosureInputs = self.enclosureInputs;


    self.removeOutput = function (data) {
      self.enclosureOutputs.remove(data);
      self.settings_unsaved(true);
    };

    self.removeInput = function(data){
      self.enclosureInputs.remove(data);
      self.settings_unsaved(true);
    }

    self.showOutputEditorDialog = function (data) {

      self.outputEditor.fromOutputEnclosureData(data);

      var editDialog = $("#settings_outputs_edit_dialog");

      $('ul.nav-pills a[data-toggle="tab"]:first', editDialog).tab("show");
      editDialog.modal({
        minHeight: function () {
          return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
        }
      }).css({
        width: 'auto',
        'margin-left': function () {
          return -($(this).width());
        }
      });
    };

    self.showInputEditorDialog = function (data) {

      self.inputEditor.fromInputEnclosureData(data);

      var editDialog = $("#settings_inputs_edit_dialog");

      $('ul.nav-pills a[data-toggle="tab"]:first', editDialog).tab("show");
      editDialog.modal({
        minHeight: function () {
          return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
        }
      }).css({
        width: 'auto',
        'margin-left': function () {
          return -($(this).width());
        }
      });
    };

    self.confirmEditOutput = function () {

      if (self.outputEditor.validOutput()) {
        var callback = function () {
          $("#settings_outputs_edit_dialog").modal("hide");
        };

        self.addOutputs(callback);

        // self.syncSettings();
      }
    };

    self.confirmEditInput = function () {

      if (self.inputEditor.validInput()) {
        var callback = function () {
          $("#settings_inputs_edit_dialog").modal("hide");
        };

        self.addInputs(callback);

        // self.syncSettings();
      }
    };


    self.addOutputs = function (callback) {
      var isNew = self.outputEditor.isNew();

      self.settings_unsaved(true);

      var output = ko.mapping.fromJS(self.outputEditor.toOutputEnclosureData());

      if (isNew) {
        self.enclosureOutputs.push(output);
      } else {
        objIndex = self.enclosureOutputs().findIndex((obj => obj.index_id() == output.index_id()));
        var _old_output = self.enclosureOutputs()[objIndex];
        self.enclosureOutputs.replace(_old_output, output);
      }

      if (callback !== undefined) {
        callback();
      }
    };

    self.addInputs = function (callback) {
      var isNew = self.inputEditor.isNew();

      self.settings_unsaved(true);

      var input = ko.mapping.fromJS(self.inputEditor.toInputEnclosureData());

      if (isNew) {
        self.enclosureInputs.push(input);
      } else {
        objIndex = self.enclosureInputs().findIndex((obj => obj.index_id() == input.index_id()));
        var _old_input = self.enclosureInputs()[objIndex];
        self.enclosureInputs.replace(_old_input, input);
      }

      if (callback !== undefined) {
        callback();
      }
    };

    self.print_data = function () {
      console.log(self);
    };

    // end of EnclosureViewModel
  };



  OCTOPRINT_VIEWMODELS.push({
    construct: EnclosureViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
    dependencies: ["settingsViewModel", "connectionViewModel", "printerStateViewModel"],
    elements: ["#settings_plugin_enclosure"]
  });

})