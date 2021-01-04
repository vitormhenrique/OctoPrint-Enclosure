$(function () {

  var cleanOutput = function (index_id) {
    return {
      index_id: index_id,
      label: "",
      output_type: "regular",
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

    self.fromOutputData = function (data) {

      self.isNew(data === undefined);

      if (data === undefined) {
        var arrRelaysLength = self.enclosureOutputs().length;
        var nextIndex = arrRelaysLength == 0 ? 1 : self.enclosureOutputs()[arrRelaysLength - 1].index_id + 1;
        data = cleanOutput(nextIndex);
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

    self.toOutputData = function () {
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

    self.onBeforeBinding = function () {
      self.enclosureOutputs(self.settingsViewModel.settings.plugins.enclosure.enclosureOutputs());
      // console.log(self.settingsViewModel.settings.plugins.enclosure)
    };

    self.onEventSettingsUpdated = function () {
      self.enclosureOutputs(self.settingsViewModel.settings.plugins.enclosure.enclosureOutputs());
    };

    self.createOutputEditor = function (data) {
      var outputEditor = new EnclosureOutputEditorViewModel();

      return outputEditor;
    };

    self.outputEditor = self.createOutputEditor();
    self.outputEditor.enclosureOutputs = self.enclosureOutputs;

    self.showOutputEditorDialog = function (data) {

      self.outputEditor.fromOutputData(data);

      var editDialog = $("#settings_outputs_edit_dialog");

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


    self.addOutputs = function () {
      var output = self.outputEditor.toOutputData();

      self.settingsViewModel.settings.plugins.enclosure.enclosureOutputs.push(output);
    };

    self.print_data = function () {
      console.log(self.enclosureOutputs.root);
      // console.log(self);
    };

    // end of EnclosureViewModel
  };



  OCTOPRINT_VIEWMODELS.push({
    construct: EnclosureViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
    dependencies: ["settingsViewModel", "connectionViewModel", "printerStateViewModel"],
    // Elements to bind to, e.g. #settings_plugin_tasmota-mqtt, #tab_plugin_tasmota-mqtt, ...
    elements: ["#settings_plugin_enclosure"]
  });

})