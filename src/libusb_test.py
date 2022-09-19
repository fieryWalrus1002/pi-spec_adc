
import usb.core
import usb.backend.libusb1
import serial.tools.list_ports

for port in serial.tools.list_ports.comports():
    print(f"port:{port}, device: {port.device}, vid:{port.vid}, pid:{port.pid}")
    


VENDOR_ID = 10374 # Seediuino
#PRODUCT_ID = 32815 # XIAO
PRODUCT_ID  = GARBAGE
device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

if device is None:
    raise ValueError('ADU Device not found. Please ensure it is connected to the tablet.')
    sys.exit(1)

# Claim interface 0 - this interface provides IN and OUT endpoints to write to and read from
usb.util.claim_interface(device, 0)

# Write commands to ADU
bytes_written = write_to_adu(device, 'SK0') # set relay 0
bytes_written = write_to_adu(device, 'RK0') # reset relay 0

# Read from the ADU
bytes_written = write_to_adu(device, 'RPA') # request the value of PORT A in binary 

data = read_from_adu(device, 200) # read from device with a 200 millisecond timeout

if data != None:
    print("Received string: {}".format(data))
    print("Received data as int: {}".format(int(data))) # the returned value is a string - we can convert it to a number (int) if we wish


def write_to_adu(dev, msg_str):
    print('Writing command: {}'.format(msg_str))

    # message structure:
    #   message is an ASCII string containing the command
    #   8 bytes in length
    #   0th byte must always be 0x01 (decimal 1)
    #   bytes 1 to 7 are ASCII character values representing the command
    #   remainder of message is padded to 8 bytes with character code 0

    byte_str = chr(0x01) + msg_str + chr(0) * max(7 - len(msg_str), 0)

    num_bytes_written = 0

    try:
        # 0x01 is the OUT endpoint
        num_bytes_written = dev.write(0x01, byte_str)
    except usb.core.USBError as e:
        print (e.args)

    return num_bytes_written

def read_from_adu(dev, timeout):
    try:
		# try to read a maximum of 64 bytes from 0x81 (IN endpoint)
        data = dev.read(0x81, 64, timeout)
    except usb.core.USBError as e:
        print ("Error reading response: {}".format(e.args))
        return None

    byte_str = ''.join(chr(n) for n in data[1:]) # construct a string out of the read values, starting from the 2nd byte
    result_str = byte_str.split('\x00',1)[0] # remove the trailing null '\x00' characters

    if len(result_str) == 0:
        return None

    return result_str