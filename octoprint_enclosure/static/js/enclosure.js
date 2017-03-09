$(function() {
    function EnclosureViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.connection = parameters[1];

        self.enclosureTemp = ko.observable();
        self.enclosureSetTemperature = ko.observable();
        self.enclosureHumidity = ko.observable();

        self.onStartupComplete = function () {
          fixUI();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
             if (plugin != "enclosure") {
                return;
            }
            self.enclosureTemp(data.enclosuretemp);
            self.enclosureHumidity(data.enclosureHumidity);
        };

        self.isConnected = ko.computed(function() {
            return self.connection.loginState.isUser();
        });

        self.setTemperature = function(){
            if(isNumeric($("#enclosureSetTemp").val())){
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
        }

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
        }

        self.requestEnclosureTemperature = function(){
            return $.ajax({
                    type: "GET",
                    url: "/plugin/enclosure/getEnclosureTemperature",
                    async: false
                }).responseText;
        }

        self.requestEnclosureSetTemperature = function(){
            return $.ajax({
                    type: "GET",
                    url: "/plugin/enclosure/getEnclosureSetTemperature",
                    async: false
                }).responseText;
        }

        self.getStatusHeater = function(setTemp,currentTemp){
            if (parseFloat(setTemp)>parseFloat(currentTemp)){
                return cleanTemperature(setTemp);
            }
            return "off";
        }

        self.handleIO = function(data, event){
            $.ajax({
                    type: "GET",
                    dataType: "json",
                    data: {"io": data[0], "status": data[1]},
                    url: "/plugin/enclosure/setIO",
                    async: false
            });
        }
    }

    ADDITIONAL_VIEWMODELS.push([
        EnclosureViewModel,
        ["settingsViewModel","connectionViewModel"],
        [document.getElementById("tab_plugin_enclosure")]
    ]);
});

function isNumeric(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

function fixUI() {
  if($('#enableTemperatureReading').is(':checked')){
    $('#enableHeater').prop('disabled', false);
    $('#temperature_reading_content').show("blind");
  }else{
    $('#enableHeater').prop('disabled', true);
    $('#enableHeater').prop('checked', false);
    $('#temperature_reading_content').hide("blind");
  }

  if($('#enableHeater').is(':checked')){
    $('#heater_content').show("blind");
  }else{
    $('#heater_content').hide("blind");
  }

  if($('#io1_enabled').is(':checked')){
    $('#io1_content').show("blind");
  }else{
    $('#io1_content').hide("blind");
  }

  if($('#io2_enabled').is(':checked')){
    $('#io2_content').show("blind");
  }else{
    $('#io2_content').hide("blind");
  }

  if($('#io3_enabled').is(':checked')){
    $('#io3_content').show("blind");
  }else{
    $('#io3_content').hide("blind");
  }

  if($('#io4_enabled').is(':checked')){
    $('#io4_content').show("blind");
  }else{
    $('#io4_content').hide("blind");
  }

  if($('#filament_sensor_enable').is(':checked')){
    $('#filament_sensor_content').show("blind");
  }else{
    $('#filament_sensor_content').hide("blind");
  }
}
