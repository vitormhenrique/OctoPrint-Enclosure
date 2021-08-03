# API Reference v2.0

The API is located at \<OctoPrintURL>/plugin/enclosure. This needs to be added before each endpoint in order for the API to function properly. The API either returns a `application/json` body or an empty body for a successful request.

A failed request will return an error code as well as a short error description.

## List all inputs

Endpoint: **GET** `/inputs`

Response (200):

```
[
    {
        "index_id": number,
        "label": string
    }
]
```

Error Responses:
 - none

## List a specific input

Endpoint: **GET** `/inputs/<id>`

*Note: id needs to be int (index_id)*

Response (200):
```
{
    "controlled_io": null,
    "filament_sensor_timeout": number,
    "filament_sensor_enabled": boolean,
    "temp_sensor_address": string,
    "printer_action": string,
    "controlled_io_set_value": string,
    "temp_sensor_type": string,
    "temp_sensor_navbar": boolean,
    "temp_sensor_humidity": number,
    "edge": string,
    "ds18b20_serial": string,
    "action_type": string,
    "input_pull_resistor": string,
    "input_type": string,
    "temp_sensor_temp": number,
    "label": string,
    "index_id": number,
    "use_fahrenheit": boolean,
    "gpio_pin": string
}
```

Error Responses:
 - 404 if specified id cannot be found

## List all outputs

Endpoint: **GET** `/outputs`

Response (200):
```
[
    {
        "index_id": number,
        "label": string
    }
]
```

Error Responses:
 - none

## List a specific output

Endpoint: **GET** `/outputs/<id>`

*Note: id needs to be int (index_id)*


Response (200):
```
{
    "linked_temp_sensor": string,
    "ledstrip_gpio_dat": string,
    "startup_time": number,
    "temp_ctr_deadband": number,
    "neopixel_brightness": number,
    "new_duty_cycle": string,
    "gpio_pin": number,
    "default_duty_cycle": number,
    "neopixel_color": string,
    "hide_btn_ui": boolean,
    "temp_ctr_set_value": number,
    "temp_ctr_default_value": number,
    "default_neopixel_color": string,
    "controlled_io_set_value": string,
    "auto_shutdown": boolean,
    "shell_script": string,
    "label": string,
    "default_ledstrip_color": string,
    "duty_a": number,
    "toggle_timer_off": number,
    "alarm_set_temp": number,
    "ledstrip_gpio_clk": string,
    "auto_startup": boolean,
    "controlled_io": number,
    "shutdown_time": number,
    "temp_ctr_type": string,
    "gcode": string,
    "current_value": boolean,
    "shutdown_on_failed": boolean,
    "temperature_b": number,
    "ledstrip_color": string,
    "temperature_a": number,
    "neopixel_count": number,
    "duty_cycle": number,
    "toggle_timer_on": number,
    "show_on_navbar": boolean,
    "duty_b": number,
    "toggle_timer": boolean,
    "pwm_status": number,
    "gpio_status": boolean,
    "pwm_frequency": number,
    "new_ledstrip_color": string,
    "startup_with_server": boolean,
    "active_low": boolean,
    "temp_ctr_max_temp": number,
    "pwm_temperature_linked": boolean,
    "temp_ctr_new_set_value": string,
    "output_type": string,
    "microcontroller_address": number,
    "index_id": number,
    "new_neopixel_color": string
}
```

Error Responses:
 - 404 if specified id cannot be found

## Control specific output

Endpoint: **PATCH** `/outputs/<id>`

*Note: id needs to be int (index_id), one-based index in octoprint settings' enclosure section's `rpi_outputs` list*

Body (Content-Type: `application/json`):
```
{
    "status": boolean
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Enable/Disable  Output auto-startup

Endpoint: **PATCH** `/outputs/<id>/auto-startup`

*Note: id needs to be int (index_id)*

Body (Content-Type: `application/json`):
```
{
    "status": boolean
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Control auto-shutdown for specific output

Endpoint: **PATCH** `/outputs/<id>/auto-shutdown`

*Note: id needs to be int (index_id)*

Body (Content-Type: `application/json`):
```
{
    "status": boolean
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Control temperature

Endpoint: **PATCH** `/temperature/<id>`

*Note: id needs to be int (index_id)*

Body (Content-Type: `application/json`):
```
{
    "temperature": number
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Control filament sensor

Endpoint: **PATCH** `/filament/<id>`

*Note: id needs to be int (index_id)*

Body (Content-Type: `application/json`):
```
{
    "status": boolean
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Set PWM value

Endpoint: **PATCH** `/pwm/<id>`

*Note: id needs to be int (index_id)*

Body (Content-Type: `application/json`):
```
{
    "duty_cycle": number
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Set RGB LED color

Endpoint: **PATCH** `/rgb-led/<id>`

*Note: id needs to be int (index_id)*

Body (Content-Type: `application/json`):
```
{
    "rgb": string (rgb(r,g,b))
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Set neopixel color

Endpoint: **PATCH** `/neopixel/<id>`

*Note: id needs to be int (index_id)*

Body (Content-Type: `application/json`):
```
{
    "red": number,
    "green": number,
    "blue": number
}
```

Response (204): No-Content

Error Responses:
- 400 - wrong Content-Type or malformed request
- 406 - missing information (missing attribute given in response body)

## Clear GPIO Pins

Endpoint: **POST** `/clear-gpio`

Body: empty

Response (204): No-Content

Error Responses:
- none

## Update UI

Endpoint: **POST** `/update`

Body: empty

Response (204): No-Content

Error Responses:
- none

## Send shell command

Endpoint: **POST** `/shell/<id>`

*Note: id needs to be int (index_id)*

Body: empty

Response (204): No-Content

Error Responses:
- none

## Send gcode command

Endpoint: **POST** `/gcode/<id>`

*Note: id needs to be int (index_id)*

Body: empty

Response (204): No-Content

Error Responses:
- none
