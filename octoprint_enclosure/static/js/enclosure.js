$(function () {
  function EnclosureViewModel(parameters) {

    self.showAddOutputDialog = function (data) {
      var editDialog = $("#settings_outputs_editDialog");

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
    }


  };


  OCTOPRINT_VIEWMODELS.push({
    construct: EnclosureViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
    dependencies: ["settingsViewModel", "connectionViewModel", "printerStateViewModel"],
    // Elements to bind to, e.g. #settings_plugin_tasmota-mqtt, #tab_plugin_tasmota-mqtt, ...
    elements: ["#settings_plugin_enclosure"]
  });

});