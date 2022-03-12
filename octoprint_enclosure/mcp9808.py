import sys
import smbus

# default I2C address for device.
MCP9808_I2CADDR_DEFAULT = 0x18

# register addresses.
MCP9808_REG_CONFIG = 0x01
MCP9808_REG_UPPER_TEMP = 0x02
MCP9808_REG_LOWER_TEMP = 0x03
MCP9808_REG_CRIT_TEMP = 0x04
MCP9808_REG_AMBIENT_TEMP = 0x05
MCP9808_REG_MANUF_ID = 0x06
MCP9808_REG_DEVICE_ID = 0x07
MCP9808_REG_RESOLUTION = 0x08

# configuration register values.
MCP9808_REG_CONFIG_CONTCONV = 0x0000
MCP9808_REG_CONFIG_SHUTDOWN = 0x0100
MCP9808_REG_CONFIG_CRITLOCKED = 0x0080
MCP9808_REG_CONFIG_WINLOCKED = 0x0040
MCP9808_REG_CONFIG_INTCLR = 0x0020
MCP9808_REG_CONFIG_ALERTSTAT = 0x0010
MCP9808_REG_CONFIG_ALERTCTRL = 0x0008
MCP9808_REG_CONFIG_ALERTSEL = 0x0002
MCP9808_REG_CONFIG_ALERTPOL = 0x0002
MCP9808_REG_CONFIG_ALERTMODE = 0x0001


def main():
	# get i2c bus and bus address if provided or use defaults
	address = MCP9808_I2CADDR_DEFAULT
	bus = smbus.SMBus(1)
	if len(sys.argv) > 1:
		bus = smbus.SMBus(int(sys.argv[1]))
		address = int(sys.argv[2], 16)

	# MCP9808 address, default 0x18(24)
	# configuration register, 0x01(1)
	# continuous conversion mode, power-up default
	config = [MCP9808_REG_CONFIG_CONTCONV, 0x00]
	bus.write_i2c_block_data(address, MCP9808_REG_CONFIG, config)

	# MCP9808 address, default 0x18(24)
	# select resolution rgister, 0x08(8)
	# resolution = +0.0625 / C, 0x03(03)
	bus.write_byte_data(address, MCP9808_REG_RESOLUTION, 0x03)

	# MCP9808 address, default 0x18(24)
	# read data back from 0x05(5), 2 bytes
	# temp MSB, TEMP LSB
	data = bus.read_i2c_block_data(address, MCP9808_REG_AMBIENT_TEMP, 2)

	# convert the data to 13-bits
	ctemp = ((data[0] & 0x1F) * 256) + data[1]
	if ctemp > 4095:
		ctemp -= 8192
	ctemp = ctemp * 0.0625
	# ftemp = ctemp * 1.8 + 32

	# output data
	print('{0:0.2f}'.format(ctemp))


if __name__ == "__main__":
	main()
