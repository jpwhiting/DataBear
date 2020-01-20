'''
Data Logger

 - Components:
    -- Measure
        - Measure each configured sensor
        - Complete measurements at sample frequency
    -- Store
        - Process the measurements: max, min, avg
        - Store data in database at storage frequency
** Need more documentation here...

'''

import databear.schedule as schedule
import databear.sensor as sensor
import yaml
import time #For sleeping during execution
import csv
import sys #For command line args

#-------- Logger Initialization and Setup ------
class DataLogger:
    '''
    A data logger
    '''
    def __init__(self,configpath):
        '''
        Initialize a new data logger
        Input - path to configuration file
        '''
        #Import configuration ***Testing
        tphmeasures = [{'name':'airT','method':'modbus','port':'COM7','register':210,
                        'regtype':'float','timeout':0.1}]
        tph = {'name':'TPH1','serialnumber':6166,'measurements':tphmeasures}
        rmymeasures = [{'name':'bp','method':'stream','port':'COM8','baud':9600,
                        'timeout':0,'dataRE':r'\d\d\d\d.\d\d'}]
        rmy = {'name':'RMY','serialnumber':9999,'measurements':rmymeasures}
        sensors=[tph,rmy]
        loggersettings=[{'name':'airT','sensor':'TPH1','sample':5,'process':'sample','store':30},
                        {'name':'bp','sensor':'TPH1','sample':10,'process':'sample','store':60}]

        datalogger = {'name':'testlogger','settings':loggersettings}
        
        self.name = datalogger['name']
        
        #Initialize properties
        self.sensors = []
        self.loggersettings = [] #Form (<measurement>,<sensor>)
        self.logschedule = schedule.Scheduler()

        #Configure logger
        for sensor in sensors:
            self.addSensor(sensor['name'],sensor['serialnumber'],sensor['measurements'])

        for setting in loggersettings:
            self.scheduleMeasurement(setting['name'],setting['sensor'],setting['sample'])
            self.scheduleStorage(setting['name'],setting['process'],setting['store'])

        #Create output file
        self.csvfile = open(datalogger['name']+'.csv','w',newline='')
        self.csvwrite = csv.DictWriter(self.csvfile,['dt','measurement','value','sensor'])
        self.csvwrite.writeheader()

    def addSensor(self,name,sn,measurements):
        '''
        Add a sensor to the logger
        '''
        self.sensors[name] = sensor.Sensor(name,sn,measurements)

    def scheduleMeasurement(self,name,sensor,frequency):
        '''
        Schedule a measurement
        Frequency is seconds
        '''
        m = self.sensors[sensor].measure
        self.logschedule.every(frequency).do(m,name)
        
    def scheduleStorage(self,name,sensor,frequency):
        '''
        Schedule when storage takes place
        '''
        s = self.storeMeasurement
        self.logschedule.every(frequency).do(s,name,sensor,'sample')

    def storeMeasurement(self,name,sensor,process):
        '''
        Store measurement data according to process.
        - process is fixed at 'sample' for now.
        Deletes any unstored data.
        '''
        if not self.sensors[sensor].data[name]:
            #No data stored
            return

        if process=='sample':
            currentdata = self.sensors[sensor].data[name][-1]
            dt = currentdata[0].strftime('%Y-%m-%d %H:%M:%S:%f')
            val = currentdata[1]
            datadict = {
                    'dt':dt,
                    'measurement':name,
                    'value':val,
                    'sensor':sensor}

            #Output row to CSV
            self.csvwrite.writerow(datadict)

    def run(self):
        '''
        Run the logger
        ctrl-C to stop
        '''
        while True:
            try:
                self.logschedule.run_pending()
                sleeptime = self.logschedule.idle_seconds
                if sleeptime > 0:
                    time.sleep(sleeptime)
            except KeyboardInterrupt:
                break

        #Close CSV after stopping
        self.csvfile.close()
            

#-------- Run from command line -----
if __name__ == "__main__":

    #Process command line args
    #Still developing
    if len(sys.argv) > 1:
        cmdarg = sys.argv[1]
        print('Command line arg: {}'.format(cmdarg))

    datalogger = DataLogger('myLogger')

    #Load logger configuration
    '''
    Under development
    '''

    #Run logger
    datalogger.run()








