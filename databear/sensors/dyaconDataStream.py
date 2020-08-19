'''
Dyacon DataStream
A testing module for reading streaming data from simDataStream.py

Setup:
- Windows: loopback USB-RS485 and run both simDataStream and DataBear
- Other: Connect PC to device and run simDataStream

'''
#Import any libraries needed for sensor operation. Also
#import error classes to alert users to problems.
import datetime
from databear.errors import MeasureError, SensorConfigError
import serial
import re

class dyaconDataStream:
    interface_version = '0.2'
    def __init__(self,name,settings):
        '''
        Create a new sensor
        Inputs
        - name: string - name for sensor
        - settings: dictionary
            settings['serialnum'] = Serial Number 
            settings['measurement'] = Sensor measurement interval sec 
            settings['port'] = Serial port
            settings['baud'] = Baud rate
        '''
        #Load settings to instance attributes
        try:
            self.name = name
            self.sn = settings['serialnumber']
            self.frequency = settings['measurement']
            self.port = settings['port']
            self.baud = settings['baud']
            
        except KeyError as ke:
            raise SensorConfigError('YAML missing required sensor setting')
        
        #Other settings
        self.maxfrequency = 0  #Maximum sample rate
        self.timeout = 0

        #Serial settings for MDL
        self.rs = 'RS485'
        self.duplex = 'half'
        self.resistors = 1
        self.bias = 1

        #Set up connection
        self.comm = serial.Serial(self.port,self.baud,timeout=self.timeout)
        self.comm.reset_input_buffer()

        #Initialize data structure
        self.data = {'raw':[]}
        
    def measure(self):
        '''
        Read in data from port and parse to measurements
        '''
        dt = datetime.datetime.now()

        #Read in bytes from port
        dbytes = self.comm.in_waiting

        if dbytes > 0:
            rawdata = self.comm.read(dbytes).decode('utf-8')
            self.data['raw'].append((dt,rawdata))

    def getcurrentdata(self):
        '''
        Return most recent data from sensor
        Output:
            {'name':(dt,val),'name2'...}
        Return None if no data for particular measurement
        '''
        currentdata = {}
        for key,val in self.data.items():
            try:
                currentdata[key]=val[-1]
            except IndexError:
                #Assign none if there is nothing in list
                currentdata[key]=None

        return currentdata
    
    def getdata(self,name,startdt,enddt):
            '''
            Return a list of values such that
            startdt <= timestamps < enddt
            - Inputs: datetime objects
            '''
            output = []
            data = self.data[name]
            for val in data:
                if (val[0]>=startdt) and (val[0]<enddt):
                    output.append(val)
            return output
        
    def cleardata(self,name,startdt,enddt):
        '''
        Clear data values for a particular measurement
        Loop through values and remove. Note: This is probably
        inefficient if the data structure is large.
        '''
        savedata = []
        data = self.data[name]
        for val in data:
            if (val[0]<startdt) or (val[0]>=enddt):
                savedata.append(val)

        self.data[name] = savedata
