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
            alert(data[1]);
            // $.ajax({
            //         type: "GET",
            //         dataType: "json",
            //         data: {"io": data.pin, "status": data.value},
            //         url: "/plugin/enclosure/handleIO",
            //         async: false
            // });
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

