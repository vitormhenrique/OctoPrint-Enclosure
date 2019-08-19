import bme680
import time


try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except IOError:
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

# These calibration data can safely be commented
# out, if desired.


# These oversampling settings can be tweaked to
# change the balance between accuracy and noise in
# the data.

hum_weighting = float(0.25)   # so hum effect is 25% of the total air quality score
gas_weighting = float(0.75)   # so gas effect is 75% of the total air quality score

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_2X)
sensor.set_temperature_oversample(bme680.OS_2X)
sensor.set_filter(bme680.FILTER_SIZE_3)

sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

gas_reference = float(250000)
hum_reference = float(40)
getgasreference_count = int(0)


def GetGasReference(gas_reference):
  # Now run the sensor for a burn-in period, then use combination of relative humidity and gas resistance to estimate indoor air quality as a percentage.
  # print("Getting a new gas reference value")
  readings = int(10)
  while True:
    sensor.get_sensor_data()
    if sensor.data.heat_stable:
      for i in range(1, readings):  # // read gas for 10 x 0.150mS = 1.5secs
        sensor.get_sensor_data()
        gas_reference = gas_reference + sensor.data.gas_resistance
        # print(sensor.data.gas_resistance)
      gas_reference = gas_reference / readings
      return




  # for i in range(1, readings):  # // read gas for 10 x 0.150mS = 1.5secs
  #   gas_reference = gas_reference + sensor.data.gas_resistance
  #   print(sensor.data.gas_resistance)
  # gas_reference = gas_reference / readings


def CalculateIAQ(score):
  IAQ_text = "Air quality is "
  score = float((100 - score) * 5)
  if score >= 301:
    IAQ_text = IAQ_text + "Hazardous"
  elif score >= 201 and score <= 300:
    IAQ_text = IAQ_text + "Very Unhealthy"
  elif score >= 176 and score <= 200:
    IAQ_text = IAQ_text + "Unhealthy"
  elif score >= 151 and score <= 175:
    IAQ_text = IAQ_text + "Unhealthy for Sensitive Groups"
  elif score >= 51 and score <= 150:
    IAQ_text = IAQ_text + "Moderate"
  elif score >= 00 and score <= 50:
    IAQ_text = IAQ_text + "Good"
  return IAQ_text



#Calculate humidity contribution to IAQ index
current_humidity = float(sensor.data.humidity)
if (current_humidity >= 38 and current_humidity <= 42):
	hum_score = float(0.25*100)  # Humidity +/-5% around optimum 
else:
  #sub-optimal
  if (current_humidity < 38):
    hum_score = float(0.25/hum_reference*current_humidity*100)
  else:
    hum_score = ((-0.25/(100-hum_reference)*current_humidity)+0.416666)*100


#Calculate gas contribution to IAQ index
gas_lower_limit = float(5000)   # Bad air quality limit
gas_upper_limit = float(50000)  # Good air quality limit

if (gas_reference > gas_upper_limit):  
  gas_reference = gas_upper_limit   #gas_reference = 250000 see above
if (gas_reference < gas_lower_limit): 
  gas_reference = gas_lower_limit

gas_score = float((0.75/(gas_upper_limit-gas_lower_limit)*gas_reference -(gas_lower_limit*(0.75/(gas_upper_limit-gas_lower_limit))))*100)

# print('gas_upper_limit--------')
# print(gas_upper_limit)
#
# print('gas_lower_limit--------')
# print(gas_lower_limit)
#
#
# print('gas score---------')
# print(gas_score)
#Combine results for the final IAQ index value (0-100% where 100% is good quality air)
air_quality_score = float(hum_score + gas_score)

# print('Air Quality = {0:.2f} % derived from 25% of Humidity reading and 75% of Gas reading - 100% is good quality air'.format( air_quality_score))

# print('Humidity element was : {0:.2f} of 0.25'.format( hum_score/100))
# print('     Gas element was : {0:.2f} of 0.25'.format( gas_score/100))




# if (sensor.data.gas_resistance < 120000):
# 	print('Poor air qulity *****')

GetGasReference(gas_reference)

# print(CalculateIAQ(air_quality_score))
# print("------------------------------------------------")
# time.sleep(2)
print('{0:0.1f}'.format(air_quality_score))

