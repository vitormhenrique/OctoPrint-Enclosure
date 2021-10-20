$(function () {

    var cleanIFTTT = function (index_id) {
        return {
            index_id: index_id,
            trigger_type: "io_trigger",
            linked_input_id: "",
            input_logic: "equals",
            input_value: "",
            action_type: "set_output_value",
            linked_output: "",
            output_set_value: ""
        }
    };

    function generate_random_uuid() {
        return ([1e2] + 1e2).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }

    function IFTTTEditorViewModel(parameters) {
        var self = this;

        self.isNew = ko.observable(false);
        self.index_id = ko.observable();
        self.trigger_type = ko.observable();
        self.action_type = ko.observable();
        self.linked_input_id = ko.observable();
        self.linked_output = ko.observable();
        self.output_set_value = ko.observable();

        self.ifttt_logic = undefined;
        self.enclosureOutputs = undefined;
        self.enclosureInputs = undefined;


        self.validInput = ko.pureComputed(function () {
            return true;
        });

        self.linked_input = ko.pureComputed(function () {
            if (self.trigger_type() == 'io_trigger') {
                var _linked_input = ko.utils.arrayFilter(self.enclosureInputs(), function (item) {
                    return (self.linked_input_id() == item.index_id());
                }).pop();
                if(_linked_input){
                    return _linked_input
                }
            }
            return undefined
        });

        // self.linked_input_type = ko.pureComputed(function () {
        //     if (self.linked_input()) {
        //         return  self.linked_input.category;
        //     }
        //     return ko.observable("none");
        // });

        self.fromIFTTTData = function (data) {

            self.isNew(data === undefined);

            if (data === undefined) {
                var arrRelaysLength = self.ifttt_logic().length;
                var nextIndex = arrRelaysLength == 0 ? 1 : self.ifttt_logic()[arrRelaysLength - 1].index_id() + 1;
                data = cleanIFTTT(nextIndex);
            } else {
                objIndex = self.ifttt_logic().findIndex((obj => obj.index_id == data.index_id));
                data = ko.mapping.toJS(self.ifttt_logic()[objIndex]);
            }

            self.index_id(data.index_id);
            self.trigger_type(data.trigger_type)
            self.action_type(data.action_type)
            self.linked_input_id(data.linked_input_id)
            self.linked_output(data.linked_output)
            self.output_set_value(data.output_set_value)

        };

        self.toIFTTTData = function (data) {
            var output_data = {
                index_id: self.index_id(),
                trigger_type: self.trigger_type(),
                action_type: self.action_type(),
                linked_input_id: self.linked_input_id(),
                linked_output: self.linked_output(),
                output_set_value: self.output_set_value(),
            }

            return output_data;
        };
        // end of IFTTTEditorViewModel
    };


    function EnclosureViewModel(parameters) {
        var self = this;

        self.pluginName = "enclosure";

        self.settingsViewModel = parameters[0];
        self.connectionViewModel = parameters[1];
        self.printerStateViewModel = parameters[2];

        self.settings_unsaved = ko.observable(false);

        self.ifttt_logic = ko.observableArray();
        self.enclosureOutputs = ko.observableArray();
        self.enclosureInputs = ko.observableArray();
        self.settings_unsaved = ko.observable(false);

        // self.settings_outputs_regular = ko.pureComputed(function () {
        //     return ko.utils.arrayFilter(self.settingsViewModel.settings.plugins.enclosure.rpi_outputs(), function (item) {
        //       return (item.output_type() === "regular_gpio" && !item.toggle_timer());
        //     });
        //   });

        self.createIFTTTEditor = function (data) {
            var inputEditor = new IFTTTEditorViewModel();
            return inputEditor;
        };

        self.inputEditor = self.createIFTTTEditor();
        self.inputEditor.ifttt_logic = self.ifttt_logic;
        self.inputEditor.enclosureOutputs = self.enclosureOutputs;
        self.inputEditor.enclosureInputs = self.enclosureInputs;

        self.removeLogic = function (data) {
            self.ifttt_logic.remove(data);
            self.settings_unsaved(true);
        }

        self.buildPluginUrl = function (path) {
            return window.PLUGIN_BASEURL + self.pluginName + path;
        };

        self.get_uuid = function () {

            while (true) {
                uuid_test = generate_random_uuid();
                var used_id_output = ko.utils.arrayFilter(self.enclosureOutputs(), function (item) {
                    return (uuid_test == item.index_id());
                }).pop();

                var used_id_input = ko.utils.arrayFilter(self.enclosureInputs(), function (item) {
                    return (uuid_test == item.index_id());
                }).pop();

                if (!used_id_output && !used_id_input) {
                    return uuid_test
                }
            }

            // response = $.ajax({
            //     type: "GET",
            //     url: self.buildPluginUrl("/uuid"),
            //     async: false
            // }).responseText;

            // return JSON.parse(response);
        }

        self.addLogic = function (callback) {
            var isNew = self.inputEditor.isNew();

            self.settings_unsaved(true);

            var input = ko.mapping.fromJS(self.inputEditor.toIFTTTData());

            if (isNew) {
                self.ifttt_logic.push(input);
            } else {
                objIndex = self.ifttt_logic().findIndex((obj => obj.index_id() == input.index_id()));
                var _old_input = self.ifttt_logic()[objIndex];
                self.ifttt_logic.replace(_old_input, input);
            }

            if (callback !== undefined) {
                callback();
            }
        };

        self.confirmEditLogic = function () {

            if (self.inputEditor.validInput()) {
                var callback = function () {
                    $("#settings_ifttt_edit_dialog").modal("hide");
                };

                self.addLogic(callback);
            }
        };

        self.showIFTTTDialog = function (data) {

            self.inputEditor.fromIFTTTData(data);

            var editDialog = $("#settings_ifttt_edit_dialog");

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

        self.onBeforeBinding = function () {

        };

        self.onSettingsBeforeSave = function () {};

        self.onEventSettingsUpdated = function () {

        };

    };



    OCTOPRINT_VIEWMODELS.push({
        construct: EnclosureViewModel,
        dependencies: ["settingsViewModel", "connectionViewModel", "printerStateViewModel"],
        elements: ["#settings_plugin_enclosure"]
    });

})