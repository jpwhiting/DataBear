'''
Use timeit to test data reading speeds

Setup
- Always read in 50 bytes
- Have incoming data on the port using simDataStream
'''
from timeit import timeit
import serial
import time

comm = serial.Serial('COM7',19200,timeout=0)
data = []
tests = 50
time.sleep(10)

def measure():
    #Read in bytes from port
    rawdata = comm.read(50).decode('utf-8')
    data.append(rawdata)


tot = timeit('measure()',globals=globals(),number=tests)
print(tot/tests)

print(data)
'''
for i in range(5):
    measure()
'''