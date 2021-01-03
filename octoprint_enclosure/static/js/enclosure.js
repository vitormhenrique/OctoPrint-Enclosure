$(function () {

  var cleanOutput = function (index_id) {
    return {
      index_id: index_id,
      label: "",
      output_type: "regular",
      gpio: {
        pin_name: ""
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
    // led strip output
    self.led_trip_gpio_clk = ko.observable()
    self.led_strip_gpio_data = ko.observable()
    self.default_led_strip_color = ko.observable()
    // schedule config
    self.toggle_timer =  ko.observable()
    self.toggle_timer_on =  ko.observable()
    self.toggle_timer_off =  ko.observable()
    self.startup_with_server =  ko.observable()
    self.auto_startup =  ko.observable()
    self.startup_time_delay =  ko.observable()
    self.auto_shutdown =  ko.observable()
    self.shutdown_on_failed =  ko.observable()
    self.shutdown_time_delay =  ko.observable()
    // shell script output
    self.shell_script =  ko.observable()
    // temp alarm output
    self.alarm_linked_temp_sensor =  ko.observable()
    self.alarm_set_temp =  ko.observable()
    self.controlled_io =  ko.observable()
    self.controlled_io_set_value =  ko.observable()
    // temp control output
    self.temp_ctr_linked_sensor =  ko.observable()
    self.temp_ctr_type =  ko.observable()
    self.temp_ctr_type =  ko.observable()
    self.temp_ctr_type =  ko.observable()
    self.temp_ctr_default_value =  ko.observable()
    self.temp_ctr_deadband =  ko.observable()
    self.temp_ctr_max_temp =  ko.observable()




    self.enclosureOutputs = undefined;

    self.fromOutputData = function (data) {

      self.isNew(data === undefined);

      if (data === undefined) {
        var arrRelaysLength = self.enclosureOutputs().length;
        var nextIndex = arrRelaysLength == 0 ? 1 : self.enclosureOutputs()[arrRelaysLength - 1].index_id + 1;
        data = cleanOutput(nextIndex);
      }


      self.index_id(data.index_id);
      self.label(data.label);
      self.output_type(data.output_type);
      self.gpio_pin(data.gpio.pin_name);

    };

    self.toOutputData = function () {
      var output_data = {
        index_id: "",
        label: self.label(),
        output_type: self.output_type(),
        gpio: {
          pin_name: self.gpio_pin()
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
          return -($(this).width() / 2);
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