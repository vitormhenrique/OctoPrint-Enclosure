# API Reference v2.0

## List all Inputs.

Method: GET

http://<host>/plugin/enclosure/inputs?apikey=<APIKEY>

Response:

```
[
    {
        "index_id": 1,
        "label": "Input 1"
    }
]
```


## List a specific input.

Method: GET

http://<host>/plugin/enclosure/inputs/1?apikey=<APIKEY>

Response:
```
{
    "controlled_io": null,
    "filament_sensor_timeout": 120,
    "filament_sensor_enabled": true,
    "temp_sensor_address": "",
    "printer_action": "filament",
    "controlled_io_set_value": "low",
    "temp_sensor_type": "11",
    "temp_sensor_navbar": true,
    "temp_sensor_humidity": 19,
    "edge": "fall",
    "ds18b20_serial": "",
    "action_type": "output_control",
    "input_pull_resistor": "input_pull_up",
    "input_type": "temperature_sensor",
    "temp_sensor_temp": 33,
    "label": "Input 1",
    "index_id": 1,
    "use_fahrenheit": false,
    "gpio_pin": "4"
}
```

## List all outputs

Method: GET

http://<host>/plugin/enclosure/outputs?apikey=<APIKEY>

Response:
```
[
    {
        "index_id": 1,
        "label": "Ouput 1"
    }
]
```

## List a specific output

Method: GET

http://<host>/plugin/enclosure/outputs/1?apikey=<APIKEY>

Response: 
```
{
    "linked_temp_sensor": "",
    "ledstrip_gpio_dat": "",
    "startup_time": 0,
    "temp_ctr_deadband": 0,
    "neopixel_brightness": 255,
    "new_duty_cycle": "",
    "gpio_pin": 0,
    "default_duty_cycle": 0,
    "neopixel_color": "rgb(0,0,0)",
    "hide_btn_ui": false,
    "temp_ctr_set_value": 0,
    "temp_ctr_default_value": 0,
    "default_neopixel_color": "",
    "controlled_io_set_value": "Low",
    "auto_shutdown": false,
    "shell_script": "",
    "label": "Ouput 1",
    "default_ledstrip_color": "",
    "duty_a": 0,
    "toggle_timer_off": 0,
    "alarm_set_temp": 0,
    "ledstrip_gpio_clk": "",
    "auto_startup": false,
    "controlled_io": 0,
    "shutdown_time": 0,
    "temp_ctr_type": "heater",
    "gcode": "M117 Test",
    "shutdown_on_failed": false,
    "temperature_b": 0,
    "ledstrip_color": "rgb(0,0,0)",
    "temperature_a": 0,
    "neopixel_count": 0,
    "duty_cycle": 0,
    "toggle_timer_on": 0,
    "show_on_navbar": false,
    "duty_b": 0,
    "toggle_timer": false,
    "pwm_status": 50,
    "gpio_status": false,
    "pwm_frequency": 50,
    "new_ledstrip_color": "",
    "startup_with_server": true,
    "active_low": true,
    "temp_ctr_max_temp": 0,
    "pwm_temperature_linked": false,
    "temp_ctr_new_set_value": "",
    "output_type": "regular",
    "microcontroller_address": 0,
    "index_id": 1,
    "new_neopixel_color": ""
}
```

## Enable/Disable  Output:

http://<host>/plugin/enclosure/outputs/1?apikey=<APIKEY>

Method: PATCH
Content-Type: application/json
Body:  { "status": boolean }

example:  
```
{ "status": true }
```


## Enable/Disable  Output auto-shutdown:

http://<host>/plugin/enclosure/outputs/1/auto-shutdown?apikey=<APIKEY>

Method: PATCH
Content-Type: application/json
Body:  { "status": boolean }

example:  
```
{ "status": true }
```


## Enable/Disable  Output auto-shutdown:

http://<host>/plugin/enclosure/outputs/1/auto-startup?apikey=<APIKEY>

Method: PATCH
Content-Type: application/json
Body:  { "status": boolean }

example:  
```
{ "status": true }
```
