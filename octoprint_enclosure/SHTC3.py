import sys
import time

from smbus2 import SMBus, i2c_msg

try:
	import struct
except ImportError:
	import ustruct as struct

from crc import CrcCalculator, Configuration
width = 8
poly = 0x31
init_value = 0xFF
final_xor_value = 0x00
reverse_input = False
reverse_output = False
configuration = Configuration(width, poly, init_value, final_xor_value, reverse_input, reverse_output)

use_table = True
crc_calculator = CrcCalculator(configuration, use_table)


class SHTC3Exception(Exception):
	""" Base class for exception """


class SHTC3DeviceNotFound(SHTC3Exception, ValueError):
	""" Device not found """


class SHTC3ReadError(SHTC3Exception, RuntimeError):
	""" Read error or CRC mismatch """


CMD_SLEEP = 0xB098
CMD_WAKE = 0x3517  # 240µs
CMD_RESET = 0x805D  # 240µs

CMD_READ_ID = 0xEFC8

# Normal sample time 12ms
# Low sample time 0.8ms
CMD_NORMAL_T = 0x7866
CMD_NORMAL_RH = 0x58E0
CMD_LOW_T = 0x609C
CMD_LOW_RH = 0x401A

CMD_NORMAL_STRETCH_T = 0x7CA2
CMD_NORMAL_STRETCH_RH = 0x5C24
CMD_LOW_STRETCH_T = 0x6458
CMD_LOW_STRETCH_RH = 0x44DE

SHTC3_I2CADDR_DEFAULT = 0x70


def send_command(bus, address, cmd):
	"""Write the command bytes to the bus."""
	byte_array = cmd.to_bytes(2, 'big')
	for b in byte_array:
		bus.write_byte_data(address, 0, b)
		time.sleep(0.001)


def write_then_read(bus, address, cmd, read_length):
	"""In a single transaction write a cmd, then read the result."""
	cmd_bytes = cmd.to_bytes(2, 'big')
	write = i2c_msg.write(address, cmd_bytes)
	read = i2c_msg.read(address, read_length)

	bus.i2c_rdwr(write, read)

	return bytes(read)


def to_relative_humidity(raw_data):
	"""Convert the linearized 16 bit values into Relative humidity (result in %RH)

	Source: https://sensirion.com/media/documents/643F9C8E/6164081E/Sensirion_Humidity_Sensors_SHTC3_Datasheet.pdf
	"""
	return 100.0 * (raw_data / 2 ** 16)


def to_temperature(raw_data):
	"""Convert the linearized 16 bit values into Temperature (result in °C)

	Source: https://sensirion.com/media/documents/643F9C8E/6164081E/Sensirion_Humidity_Sensors_SHTC3_Datasheet.pdf
	"""
	return -45 + 175 * (raw_data / 2 ** 16)


def sample_temperature(bus, address):

	send_command(bus, address, CMD_RESET)
	time.sleep(0.001)
	send_command(bus, address, CMD_WAKE)
	time.sleep(0.001)

	try:
		result = write_then_read(bus, address, CMD_NORMAL_STRETCH_T, 3)

		if not crc_calculator.verify_checksum(result[0:2], result[2]):
			raise SHTC3ReadError('CRC Mismatch')

		raw_temp, crc = struct.unpack(">HB", result)
		return to_temperature(raw_temp)

	finally:
		send_command(bus, address, CMD_SLEEP)


def sample_humidity(bus, address):
	send_command(bus, address, CMD_RESET)
	time.sleep(0.001)
	send_command(bus, address, CMD_WAKE)
	time.sleep(0.001)

	try:
		result = write_then_read(bus, address, CMD_NORMAL_STRETCH_RH, 3)

		if not crc_calculator.verify_checksum(result[0:2], result[2]):
			raise SHTC3ReadError('CRC Mismatch')

		raw_rh, crc = struct.unpack(">HB", result)
		return to_relative_humidity(raw_rh)

	finally:
		send_command(bus, address, CMD_SLEEP)


def sample_both(bus, address):
	"""Sample of temperature and humidity."""

	send_command(bus, address, CMD_RESET)
	send_command(bus, address, CMD_WAKE)

	try:
		result = write_then_read(bus, address, CMD_NORMAL_STRETCH_T, 6)

		if not crc_calculator.verify_checksum(result[0:2], result[2]):
			raise SHTC3ReadError('CRC Mismatch')

		if not crc_calculator.verify_checksum(result[3:5], result[5]):
			raise SHTC3ReadError('CRC Mismatch')

		raw_temp, crc_temp, raw_rh, crc_rh = struct.unpack(">HBHB", result)
		temperature = to_temperature(raw_temp)
		humidity = to_relative_humidity(raw_rh)

		return temperature, humidity

	finally:
		# Sleep
		send_command(bus, address, CMD_SLEEP)


def main():
	# get i2c bus and bus address if provided or use defaults
	address = SHTC3_I2CADDR_DEFAULT
	bus = SMBus(1)
	if len(sys.argv) > 1:
		bus = SMBus(int(sys.argv[1]))
		address = int(sys.argv[2], 16)

	try:
		temperature, humidity = sample_both(bus, address)
		print('{0:0.1f} | {1:0.1f}'.format(temperature, humidity))

	except Exception:
		print('-1 | -1')


if __name__ == "__main__":
	main()
