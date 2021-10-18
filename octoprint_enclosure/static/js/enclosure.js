
$(function () {
  function EnclosureViewModel(parameters) {
    var self = this;

    self.settingsViewModel = parameters[0];
    self.connectionViewModel = parameters[1];
    self.printerStateViewModel = parameters[2];

    self.enclosureOutputs = ko.observableArray();
    self.enclosureInputs = ko.observableArray();

    self.settings_unsaved = ko.observable(false);

    self.onBeforeBinding = function () {

    };

    self.onSettingsBeforeSave = function () {
    };

    self.onEventSettingsUpdated = function () {

    };


    
    self.print_data = function () {

    };

  };



  OCTOPRINT_VIEWMODELS.push({
    construct: EnclosureViewModel,
    dependencies: ["settingsViewModel", "connectionViewModel", "printerStateViewModel"],
    elements: ["#settings_plugin_enclosure"]
  });

})