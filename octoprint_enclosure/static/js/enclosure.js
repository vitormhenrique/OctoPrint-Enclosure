$(function() {
    function EnclosureViewModel(parameters) {
        var self = this;

        self.global_settings = parameters[0];
        self.connection = parameters[1];
        self.printerStateViewModel = parameters[2];

        self.temperature_reading = ko.observableArray();
        self.temperature_control = ko.observableArray();
        self.rpi_outputs = ko.observableArray();
        self.rpi_inputs = ko.observableArray();
        self.filamentSensorGcode = ko.observable();

        self.enclosureTemp = ko.observable();
        self.enclosureSetTemperature = ko.observable();
        self.enclosureHumidity = ko.observable();


        self.previousGpioStatus;

        self.onDataUpdaterPluginMessage = function(plugin, data) {
             if (plugin != "enclosure") {
                return;
            }

            if (data.hasOwnProperty("enclosuretemp")) {
                self.enclosureTemp(data.enclosuretemp);
            }
            if (data.hasOwnProperty("enclosureHumidity")) {
                self.enclosureHumidity(data.enclosureHumidity);
            }

            if (data.hasOwnProperty("enclosureSetTemp")){
                if (parseFloat(data.enclosureSetTemp)>0.0){
                  $("#enclosureSetTemp").attr("placeholder", data.enclosureSetTemp);
                }else{
                  $("#enclosureSetTemp").attr("placeholder", "off");
                }
            }

            if(!data.rpi_output){
              data.rpi_output = self.previousGpioStatus;
            }

            if(data.rpi_output){
              data.rpi_output.forEach(function(gpio) {
                  key = Object.keys(gpio)[0];
                  if(gpio[key]){
                    $("#btn_off_"+key).removeClass('active');
                    $("#btn_on_"+key).addClass('active');
                  }else{
                    $("#btn_off_"+key).addClass('active');
                    $("#btn_on_"+key).removeClass('active');
                  }
              });
              self.previousGpioStatus = data.rpi_output;
            }

            if (data.isMsg) {
                new PNotify({title:"Enclosure", text:data.msg, type: "error"});
            }
        };

        self.enableBtn = ko.computed(function() {
            // return self.connection.loginState.isUser() && self.printerStateViewModel.isOperational();
            return self.connection.loginState.isUser();
        });

        self.onBeforeBinding = function () {
            self.settings = self.global_settings.settings.plugins.enclosure;
            self.temperature_reading(self.settings.temperature_reading());
            // self.temperature_control(self.settings.temperature_control.slice(0));
            self.rpi_outputs(self.settings.rpi_outputs());
            self.rpi_inputs(self.settings.rpi_inputs());
            self.filamentSensorGcode(self.settings.filamentSensorGcode());
        };

        self.onStartupComplete = function () {
          self.getUpdateBtnStatus();
        };

        self.onSettingsShown = function(){
          self.fixUI();
        }

        self.save = function(){
          $.ajax({
              url: "/plugin/enclosure/save",
              type: "GET"
          });
        }


        self.setTemperature = function(){
            if(self.isNumeric($("#enclosureSetTemp").val())){
                $.ajax({
                    url: "/plugin/enclosure/setEnclosureTemperature",
                    type: "GET",
                    dataType: "json",
                    data: {"enclosureSetTemp": Number($("#enclosureSetTemp").val())},
                     success: function(data) {
                        $("#enclosureSetTemp").val('');
                        $("#enclosureSetTemp").attr("placeholder", self.getStatusHeater(data.enclosureSetTemperature,data.enclosureCurrentTemperature));
                    }
                });
            }else{
                alert("Temperature is not a number");
            }
        };

        self.addRpiOutput = function(){
          self.global_settings.settings.plugins.enclosure.rpi_outputs.push({label: ko.observable("Ouput "+
            (self.global_settings.settings.plugins.enclosure.rpi_outputs().length+1)) ,
            gpioPin: 0,activeLow: true,
            autoStartup:false, startupTimeDelay:0, autoShutdown:false,shutdownTimeDelay:0,active:false});
        };

        self.removeRpiOutput = function(definition) {
          self.global_settings.settings.plugins.enclosure.rpi_outputs.remove(definition);
        };

        self.addRpiInput = function(){
          self.global_settings.settings.plugins.enclosure.rpi_inputs.push({label:ko.observable( "Input "+
          (self.global_settings.settings.plugins.enclosure.rpi_inputs().length+1)), gpioPin: 0,inputPull: "inputPullUp",
          eventType:ko.observable("temperature"),setTemp:100,controlledIO:ko.observable(""),setControlledIO:"low",
          edge:"fall",printerAction:"filament"});
        };

        self.removeRpiInput = function(definition) {
          self.global_settings.settings.plugins.enclosure.rpi_inputs.remove(definition);
        };

        self.turnOffHeater = function(){
            $.ajax({
                url: "/plugin/enclosure/setEnclosureTemperature",
                type: "GET",
                dataType: "json",
                data: {"enclosureSetTemp":0},
                 success: function(data) {
                    $("#enclosureSetTemp").val('');
                    $("#enclosureSetTemp").attr("placeholder", self.getStatusHeater(data.enclosureSetTemperature,data.enclosureCurrentTemperature));
                }
            });
        };

        self.clearGPIOMode = function(){
            $.ajax({
                url: "/plugin/enclosure/clearGPIOMode",
                type: "GET",
                dataType: "json",
                 success: function(data) {
                   new PNotify({title:"Enclosure", text:"GPIO Mode cleared successfully", type: "success"});
                }
            });
        };

        self.getUpdateBtnStatus = function(){
            $.ajax({
                url: "/plugin/enclosure/getUpdateBtnStatus",
                type: "GET"
            });
        };

        self.requestEnclosureTemperature = function(){
            return $.ajax({
                    type: "GET",
                    url: "/plugin/enclosure/getEnclosureTemperature",
                    async: false
                }).responseText;
        };

        self.requestEnclosureSetTemperature = function(){
            return $.ajax({
                    type: "GET",
                    url: "/plugin/enclosure/getEnclosureSetTemperature",
                    async: false
                }).responseText;
        };

        self.getStatusHeater = function(setTemp,currentTemp){
            if (parseFloat(setTemp)>0.0){
                return cleanTemperature(setTemp);
            }
            return "off";
        };

        self.handleIO = function(data, event){
            $.ajax({
                    type: "GET",
                    dataType: "json",
                    data: {"io": data[0], "status": data[1]},
                    url: "/plugin/enclosure/setIO",
                    async: false
            });
        };

        self.fixUI = function(){
          if($('#enableTemperatureReading').is(':checked')){
            $('#enableHeater').prop('disabled', false);
            $('#temperature_reading_content').show("blind");
            // $('#temperature_control_content').show("blind");
          }else{
            $('#enableHeater').prop('disabled', true);
            $('#enableHeater').prop('checked', false);
            $('#temperature_reading_content').hide("blind");
            // $('#temperature_control_content').hide("blind");
          }

          if($('#enableHeater').is(':checked')){
            $('#temperature_control_content').show("blind");
          }else{
            $('#temperature_control_content').hide("blind");
          }

        };

        // self.fixEventTypeUI = function(){
        //   $('[name^="eventType_"]').each(function() {
        //     if($( this ).is(':checked')){
        //       selectedType = $( this ).val();
        //       idNumber = $( this ).attr('name').replace("eventType_", "");
        //       self.eventTypeUI(idNumber,selectedType);
        //     }
        //   });
        // };
        //
        // self.eventTypeUI = function(idNumber,selectedType){
        //
        //   $('#input_io_'+idNumber).hide();
        //   $('#temp_controlled_'+idNumber).hide();
        //   $('#filament_controlled_'+idNumber).hide();
        //   $('#gpio_controlled_'+idNumber).hide();
        //
        //   if(selectedType=='temperature'){
        //     $('#temp_controlled_'+idNumber).show();
        //     console.log("temperature");
        //   }else if(selectedType=='filament'){
        //     $('#filament_controlled_'+idNumber).show();
        //     $('#input_io_'+idNumber).show();
        //     console.log("filament");
        //   }else if(selectedType=='gpio'){
        //     $('#gpio_controlled_'+idNumber).show();
        //     $('#input_io_'+idNumber).show();
        //     console.log("gpio");
        //   }
        // };


        self.fixAutoStartupUI = function(idNumber){
          if($('#autoStartup_'+idNumber).is(':checked')){
            $('#autoStartupField_'+idNumber).show("blind");
          }else{
            $('#autoStartupField_'+idNumber).hide("blind");
          }
        };

        self.fixAutoShutdownUI = function(idNumber){
          if($('#autoShutdown_'+idNumber).is(':checked')){
            $('#autoShutdownField_'+idNumber).show("blind");
          }else{
            $('#autoShutdownField_'+idNumber).hide("blind");
          }
        };

        self.isNumeric = function(n){
          return !isNaN(parseFloat(n)) && isFinite(n);
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        EnclosureViewModel,
        ["settingsViewModel","connectionViewModel","printerStateViewModel"],
        ["#tab_plugin_enclosure","#settings_plugin_enclosure"]
    ]);
});
