'''
DataBear database manager class

- init: Connect to database (databear.db) or create if none
- load_sensor: Loads measurements to database from sensor_class
- Various get/set methods

'''

import os
import sys
import sqlite3
import importlib

#-------- Database Initialization and Setup ------
class DataBearDB:
    '''
    The sqlite database for databear
    '''

    def __init__(self):
        '''
        Initialize the database manager
        - Connect to database in path DBDRIVER
            -- If none, create
            -- If not set check CWD or create in CWD
        - Create connection to database
        '''
        try:
            self.dbpath = os.environ['DBDATABASE']
        except KeyError:
            #DBDATABASE not set, assume databear.db in CWD
            self.dbpath = 'databear.db'

        # Add SENSORSPATH to pythonpath for importing alternative sensors
        if 'DBSENSORPATH' in os.environ:
            sys.path.append(os.environ['DBSENSORPATH'])

        #Set an attribute for config_id related functions
        self.configtables = {
            'sensor':['sensor_config_id','sensor_configuration'],
            'logging':['logging_config_id','logging_configuration']
            }

        # Check if database exists
        exists = os.path.isfile(self.dbpath)

        # Initialize database sqlite connection object
        # This will create the file if it doesn't exist, hence the check first
        self.conn = sqlite3.connect(self.dbpath, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()
        self.path = os.path.dirname(__file__)

        # Only initialize if the database didn't already exist
        if not exists:
            with open(self.path + '/databearDB.sql', 'r') as sql_init_file:
                sql_script = sql_init_file.read()

            self.curs.executescript(sql_script)
        
    @property
    def sensors_available(self):
        '''
        A list of sensors from the sensors table
        '''
        sensorlist = []
        self.curs.execute('SELECT * FROM sensors_available')
        for row in self.curs.fetchall():
            sensorlist.append(row['sensor_module'])
        return sensorlist

    @property
    def active_sensor_ids(self):
        '''
        Return a dictionary mapping sensor name to id for active sensors
        '''
        sensorids = {}
        self.curs.execute('SELECT sensors.sensor_id AS sensor_id, name '
                          'FROM sensors JOIN '
                          'sensor_configuration ON '
                          'sensors.sensor_id = sensor_configuration.sensor_id '
                          'WHERE status=1')
        for row in self.curs.fetchall():
            sensorids[row['name']] = row['sensor_id']
        return sensorids

    @property
    def sensor_modules(self):
        '''
        Return a dictionary mapping sensor names to classes
        '''
        sensormodules = {}
        self.curs.execute('SELECT name, module_name FROM sensors')
        for row in self.curs.fetchall():
            sensormodules[row['name']] = row['module_name']
        return sensormodules

    @property
    def process_ids(self):
        '''
        A dictionary mapping process names to ids
        '''
        processids = {}
        self.curs.execute('SELECT process_id, name FROM processes')
        for row in self.curs.fetchall():
            processids[row['name']] = row['process_id']
        return processids

    def load_sensor(self,module_name):
        '''
        Loads sensor module to the sensors_available table if not already there.
        Also load sensor measurements into database if not already there.
        '''
        #Check if sensor is already in sensors_available
        if module_name in self.sensors_available:
            return

        # Import sensor to load measurements to measurements table
        # DBSENSORPATH added to sys.path during init
        sensor_module = importlib.import_module(module_name)
        
        # Load class. Class name should be dbsensor
        sensor_class = getattr(sensor_module,'dbsensor')

        #Load sensor measurements to database
        for measurement_name in sensor_class.measurements:
            self.addMeasurement(
                module_name,
                measurement_name,
                sensor_class.units[measurement_name],
                sensor_class.measurement_description.get(measurement_name,None)
            )

        #Update sensors_available table
        #Do this last to ensure there is no failure loading measurements
        #prior to making the sensor available
        self.curs.execute('INSERT INTO sensors_available '
                          '(sensor_module) VALUES (?)',(module_name,))
        self.conn.commit()

    def addMeasurement(self,sensormodule,measurename,units,description=None):
        '''
        Add a measurement to the database
        Returns new rowid
        '''
        addqry = ('INSERT INTO measurements '
                  '(name,units,description,sensor_module) '
                  'VALUES (?,?,?,?)')
        qryparams = (measurename,units,description,sensormodule)

        self.curs.execute(addqry,qryparams)
        self.conn.commit()

        return self.curs.lastrowid

    def addSensor(self,modulename,sensorname,serialnumber,address,virtualport,description=None):
        '''
        Add a new sensor to the database
        '''
        addqry = ('INSERT INTO sensors '
                  '(name,serial_number,address,virtualport,module_name,description) '
                  'VALUES (?,?,?,?,?,?)')
        qryparams = (sensorname,serialnumber,address,virtualport,modulename,description)

        self.curs.execute(addqry,qryparams)
        self.conn.commit()

        return self.curs.lastrowid

    def addSensorConfig(self, sensor_id, measure_interval):
        '''
        Add a new sensor configuration to the system
        '''
        self.curs.execute('INSERT INTO sensor_configuration '
                  '(sensor_id,measure_interval,status) '
                  'VALUES (?,?,?)',(sensor_id,measure_interval,1))
        self.conn.commit()

        return self.curs.lastrowid

    def addLoggingConfig(self, measurement_id, sensor_id, storage_interval, process_id, status):
        '''
        Add a new logger configuration
        '''
        params = (measurement_id, sensor_id, storage_interval, process_id, status)
        self.curs.execute('INSERT INTO logging_configuration '
                  '(measurement_id, sensor_id, storage_interval, process_id, status) '
                  'VALUES (?,?,?,?,?)',params)
        self.conn.commit()

        return self.curs.lastrowid
    
    def getSensorIDs(self,activeonly=False):
        '''
        Return list of sensor ids.
        activeonly: true/false, to return only active sensorids
        '''
        sensor_ids = []
        if activeonly:
            qry = ('SELECT sensor_id FROM sensor_configuration '
                   'WHERE status=1')
        else:
            qry = 'SELECT sensor_id FROM sensors'
        
        self.curs.execute(qry)
            
        for row in self.curs.fetchall():
            sensor_ids.append(row["sensor_id"])

        return sensor_ids

    def getConfigIDs(self,configtype,activeonly=False):
        '''
        Return list of configuration IDs from either sensor config or logging config.
        configtype = 'sensor' or 'logging'
        activeonly = True/False, when true only active configs returned
        '''
        ids = []
        qry = 'SELECT {} from {}'.format(
                self.configtables[configtype][0],
                self.configtables[configtype][1])
        if activeonly:
            qry = qry + ' WHERE status=1'
        
        for row in self.curs.execute(qry):
            ids.append(row[self.configtables[configtype][0]])

        return ids
        
    def getMeasurementID(self,measurement_name,module_name):
        '''
        Get the measurement id for a given name and sensor class
        '''
        params = (measurement_name,module_name)
        self.curs.execute('SELECT measurement_id FROM measurements '
                          'WHERE name=? and sensor_module=?',params)
        
        row = self.curs.fetchone()

        if not row:
            return None

        return row['measurement_id']

    def getSensorID(self,sensorname,serialnumber,address,virtualport,modulename):
        '''
        Get sensor id associated with parameters
        Return sensor_id or none
        '''
        params = (sensorname,serialnumber,address,virtualport,modulename)
        self.curs.execute('SELECT sensor_id FROM sensors '
                          'WHERE name=? AND serial_number=? '
                          'AND address=? AND virtualport=? '
                          'AND module_name=?',params)
        
        row = self.curs.fetchone()

        if not row:
            return None

        return row['sensor_id']

    def getSensorConfigID(self,sensor_id,measure_interval):
        '''
        Get sensor configuration id associated with parameters
        Return sensor_config_id or none
        '''
        params = (sensor_id,measure_interval)
        self.curs.execute('SELECT sensor_config_id FROM sensor_configuration '
                          'WHERE sensor_id=? AND measure_interval=?',params)
        
        row = self.curs.fetchone()

        if not row:
            return None

        return row['sensor_config_id']

    def getLoggingConfigID(self,measurement_id,sensor_id,storage_interval,process_id):
        '''
        Get logging configuration id associated with parameters
        Return sensor_config_id or none
        '''
        params = (measurement_id,sensor_id,storage_interval,process_id)
        self.curs.execute('SELECT logging_config_id FROM logging_configuration '
                          'WHERE measurement_id=? AND sensor_id=? '
                          'AND storage_interval=? AND process_id=?',params)
        
        row = self.curs.fetchone()

        if not row:
            return None

        return row['logging_config_id']
    
    def getSensorConfig(self, sensor_id):
        '''
        Return the given sensor's object as a sensor object (name, serial_number, etc.) 
        or None if id is invalid
        '''
        sensor = {}
        sensor_id = (sensor_id,)
        self.curs.execute("Select * from sensors s inner join "
                          "sensor_configuration sc on s.sensor_id = sc.sensor_id "
                          "where s.sensor_id = ? and sc.status = 1", sensor_id)
        row = self.curs.fetchone()

        if not row:
            return None

        sensor["name"] = row["name"]
        sensor["serial_number"] = row["serial_number"]
        sensor["address"] = row["address"]
        sensor["virtualport"] = row["virtualport"]
        sensor["measure_interval"] = row["measure_interval"]
        sensor["module_name"] = row["module_name"]
        sensor["sensor_config_id"] = row["sensor_config_id"]

        return sensor

    def getLoggingConfig(self, logging_config_id):
        # Get a logging configuration by it's id
        # Logging configurations join with measurements, processes, and sensors to get all their details

        config = {}
        self.curs.execute(
            'SELECT m.name AS measurement_name, s.name AS sensor_name, '
            'p.name AS process_name, storage_interval FROM logging_configuration l '
            'INNER JOIN measurements m ON l.measurement_id = m.measurement_id '
            'INNER JOIN processes p ON l.process_id = p.process_id '
            'INNER JOIN sensors s on l.sensor_id = s.sensor_id '
            'WHERE l.logging_config_id = ?', (logging_config_id,))
        
        row = self.curs.fetchone()

        if not row:
            return None

        config["measurement_name"] = row["measurement_name"]
        config["sensor_name"] = row["sensor_name"]
        config["storage_interval"] = row["storage_interval"]
        config["process"] = row["process_name"]
        return config

    def setConfigStatus(self,configtype,config_id,status='activate'):
        '''
        Set a configuration to active or not active
        configtype = 'sensor' or 'logging'
        config_id
        toggle = 'activate' or 'deactivate'
        '''
        togglecode = {'activate':1,'deactivate':None}
        qry = 'UPDATE {} SET status=? WHERE {}=?'.format(
            self.configtables[configtype][1],
            self.configtables[configtype][0]
        )
        self.curs.execute(qry,(togglecode[status],config_id))
        self.conn.commit()
    
    def storeData(self, datetime, value, sensor_config_id, logging_config_id, qc_flag):
        '''
        Store data value in database
        Inputs:
            - datetime [string]
        Returns new rowid
        '''
        storeqry = ('INSERT INTO data '
                    '(dtstamp,value,sensor_configid,logging_configid,qc_flag) '
                    'VALUES (?,?,?,?,?)')
        qryparams = (datetime, float(value), sensor_config_id, logging_config_id, qc_flag)

        self.curs.execute(storeqry,qryparams)
        self.conn.commit()

        return self.curs.lastrowid

    def close(self):
        '''
        Close all connections
        '''
        self.curs.close()
        self.conn.close()













