import smbus
import time

try:
	import struct
except ImportError:
	import ustruct as struct

class AM2320Exception(Exception):
	""" Base class for exception """

class AM2320DeviceNotFound(AM2320Exception, ValueError):
	""" Device not found """

class AM2320ReadError(AM2320Exception, RuntimeError):
	""" Read error or CRC mismatch """

def _crc16(data):
	crc = 0xFFFF
	for byte in data:
		crc ^= byte
		for _ in range(8):
			if crc & 0x0001:
				crc >>= 1
				crc ^= 0xA001
			else:
				crc >>= 1
	return crc


sensor = smbus.SMBus(1)

def getTemp(bus):
	for _ in range(3):
		try:
			bus.write_byte(0x5C, 0x00)
		except:
			pass

	bus.write_i2c_block_data(0x5C, 0x03, [0x02, 2])
	time.sleep(0.001)
	result = bytearray(bus.read_i2c_block_data(0x5C, 0x00, 6))
	if result[0] != 0x3 or result[1] != 2:
		raise AM2320ReadError("Command does not match returned data")
	temp = struct.unpack(">H", result[2:-2])[0]
	crc1 = struct.unpack("<H", bytes(result[-2:]))[0]
	crc2 = _crc16(result[0:-2])
	if crc1 != crc2:
			raise AM2320ReadError("CRC Mismatch")
	if temp >= 32768:
		temp = 32768 - temp
	return (temp / 10.0)

def getHumi(bus):
	for _ in range(3):
		try:
			bus.write_byte(0x5C, 0x00)
		except:
			pass

	bus.write_i2c_block_data(0x5C, 0x03, [0x00, 2])
	time.sleep(0.001)
	result = bytearray(bus.read_i2c_block_data(0x5C, 0x00, 6))
	if result[0] != 0x3 or result[1] != 2:
		raise AM2320ReadError("Command does not match returned data")
	humi = struct.unpack(">H", result[2:-2])[0]
	crc1 = struct.unpack("<H", bytes(result[-2:]))[0]
	crc2 = _crc16(result[0:-2])
	if crc1 != crc2:
			raise AM2320ReadError("CRC Mismatch")
	return (humi / 10.0)

def main():
	try:
		temperature = getTemp(sensor)
		humidity = getHumi(sensor)
		print('{0:0.1f} | {1:0.1f}'.format(temperature, humidity))
	except:
		print('-1 | -1')

if __name__ == "__main__":
	main()
