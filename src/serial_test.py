import serial
import time
import serial.tools.list_ports

ser = None

for port in serial.tools.list_ports.comports():
    if port.vid == 1027:
        device = port.device
        print(device)

while ser is None:
    print(f"connecting to tcdev at {device}...")
    ser = serial.Serial(device, 9600)

    if ser is None:
        time.sleep(1)
print(f"connecting...")
time.sleep(12)
print("connected")
# ser = serial.Serial(baudrate=9600, port="/dev/ttyUSB0")
# time.sleep(12)

ser.write(b"d;")

print(ser.read_until().decode())
