$(function () {

  var cleanOutput = function () {
    return {
      index_id: "",
      label: "",
      output_type: "Regular",
      gpio: {
        pin_name: ""
      }
    }
  };

  function EnclosureOutputEditorViewModel(parameters) {
    var self = this;

    self.isNew = ko.observable(false);
    self.label = ko.observable();
    self.output_type = ko.observable();
    self.gpio_pin = ko.observable();

    self.fromOutputData = function (data) {

      self.isNew(data === undefined);

      if (data === undefined) {
        data = cleanOutput();
      }

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

    self.createOutputEditor = function (data) {
      var outputEditor = new EnclosureOutputEditorViewModel();

      return outputEditor;
    };

    self.outputEditor = self.createOutputEditor();

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

    };

    self.print = function () {
      console.log(self);
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