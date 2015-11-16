$(function() {
    function EnclosureViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.connection = parameters[1];

        self.enclosureTemp = ko.observable();
        self.enclosureSetTemperature = ko.observable();
        self.enclosureHumidity = ko.observable();

        self.onBeforeBinding = function () {
            
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
             if (plugin != "enclosure") {
                return;
            }
            self.enclosureTemp(data.enclosuretemp);
            self.enclosureHumidity(data.enclosureHumidity);
        };

        self.isConnected = ko.computed(function() {
            //return self.connection.isOperational();
            return true;
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
                        $("#enclosureSetTemp").attr("placeholder", self.getStatusHeater());
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
                    $("#enclosureSetTemp").attr("placeholder", self.getStatusHeater());
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

        self.getStatusHeater = function(){
            setTemp = self.requestEnclosureSetTemperature();
            currentTemp = self.requestEnclosureTemperature();
            if (parseFloat(setTemp)>parseFloat(currentTemp)){
                return cleanTemperature(setTemp);
            }
            return "off";
        }
		
		self.turnFanOn = function(isON){
            $.ajax({
                    type: "GET",
					dataType: "json",
					data: {"status": isON ? "on" : "off"},
                    url: "/plugin/enclosure/getEnclosureTemperature",
                    async: false
            });
        }
		
		self.turnLightOn = function(isON){
            $.ajax({
                    type: "GET",
					dataType: "json",
					data: {"status": isON ? "on" : "off"},
                    url: "/plugin/enclosure/getEnclosureTemperature",
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
