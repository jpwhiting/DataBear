'''
DataBear command line utility

Use:
databear <cmd> <option>

'''
import socket
import json
import os
import sys
import yaml

#Setup socket for communication with databear
ipaddress = 'localhost'
udp_port = 62000
sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.settimeout(5)

#------------- Functions --------------
def runDataBear(yamlfile=None):
    '''
    Run databear with optional yaml configuration
    file
    '''
    import subprocess

    #Parse YAML file and load to database
    if yamlfile:
        loadYAML(yamlfile)
        
    #Check to see if logger is already running
    #If so, shutdown for restart
    statusrsp = sendCommand('status')
    print(statusrsp)
    if statusrsp:
        shtdwnrsp = sendCommand('shutdown')
        print(shtdwnrsp)
    
    #Run logger in the background
    print('Running databear with python -m databear.logger')
    subprocess.Popen(
        [sys.executable,'-m','databear.logger'],
        stdout=open('databear_error.log','a'),
        stderr=subprocess.STDOUT)
    '''
    my_env = os.environ.copy()
    subprocess.Popen([sys.executable,'-m','databear.logger'],
            cwd=os.getcwd(), 
            env=my_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    '''
    
def updateAvailableSensors():
    '''
    Return a list of available sensor classes from
    databear.sensors
    '''
    pass

def sendCommand(command,argument=None):
    '''
    Send a command to DataBear
    '''
    msg = {'command':command}
    if argument: msg['arg'] = argument

    #Send and receive message
    print('Sending message: {}'.format(msg))

    try:
        sock.sendto(json.dumps(msg).encode('utf-8'),(ipaddress,udp_port))
        response = sock.recv(1024)
    except:
        response = None

    return response

def findSensors():
    '''
    Load all sensors from DBSENSORPATH and DBSENSORS to sensors available
    '''
    from databear import databearDB
    import pkgutil

    #Connect or create database
    db = databearDB.DataBearDB()

    #Parse list of sensor modules from DBSENSORS
    if 'DBSENSORS' in os.environ:
        dbsensors = os.environ['DBSENSORS']
        sensorlist = dbsensors.split(',')

        for sensor_module in sensorlist:
            db.load_sensor(sensor_module)

    #Find all modules in DBSENSORPATH
    if 'DBSENSORPATH' in os.environ:
        for modinfo in pkgutil.iter_modules([os.environ['DBSENSORPATH']]):
            db.load_sensor(modinfo[1])


def loadYAML(yamlfile):
    '''
    parse a YAML configuration file and input
    in database
    '''
    from databear import databearDB

    with open(yamlfile,'rt') as yin:
        configyaml = yin.read()

    config = yaml.safe_load(configyaml)

    #Connect or create database
    db = databearDB.DataBearDB()

    #Set all prior configurations as in-active
    for activeConfig in db.getConfigIDs('sensor',activeonly=True):
        db.setConfigStatus('sensor',activeConfig,'deactivate')
    for activeConfig in db.getConfigIDs('logging',activeonly=True):
        db.setConfigStatus('logging',activeConfig,'deactivate')
        
    #Load sensor configuration to database
    for sensorconfig in config['sensors']:
        #Check if sensor already in database
        oldsensorid = db.getSensorID(
            sensorconfig['name'],
            sensorconfig['serialnumber'],
            sensorconfig['address'],
            sensorconfig['virtualport'],
            sensorconfig['sensortype']
        )
        
        if not oldsensorid:
            #Load to sensors available
            db.load_sensor(sensorconfig['sensortype'])

            #Add sensor config to database
            sensorid = db.addSensor(
                    sensorconfig['sensortype'],
                    sensorconfig['name'],
                    sensorconfig['serialnumber'],
                    sensorconfig['address'],
                    sensorconfig['virtualport']
                )
        else:
            sensorid = oldsensorid

        #Check if configuration already in database
        oldsensorconfig = db.getSensorConfigID(
            sensorid,
            sensorconfig['measure_interval']
        )

        if not oldsensorconfig:
            db.addSensorConfig(
                sensorid,
                sensorconfig['measure_interval']
            )
        else:
            db.setConfigStatus('sensor',oldsensorconfig,'activate')
            
    #Load logging configuration
    active_sensor_ids = db.active_sensor_ids
    process_ids = db.process_ids
    sensor_modules = db.sensor_modules
    for logsetting in config['datalogger']['settings']:
            measureid = db.getMeasurementID(
                logsetting['store'],
                sensor_modules[logsetting['sensor']])
            
            #Check for existing logging config
            oldloggingconfig = db.getLoggingConfigID(
                measureid,
                active_sensor_ids[logsetting['sensor']],
                logsetting['storage_interval'],
                process_ids[logsetting['process']]
            )

            if not oldloggingconfig:
                db.addLoggingConfig(
                    measureid,
                    active_sensor_ids[logsetting['sensor']],
                    logsetting['storage_interval'],
                    process_ids[logsetting['process']],
                    1
                )
            else:
                db.setConfigStatus('logging',oldloggingconfig,'activate')


#---------------  Main ----------------
def main_cli():
    '''
    Entry point for command line execution
    '''
    #Read in command line args
    if len(sys.argv) < 2:
            print('Arguments: <cmd> <options>')
            return

    cmd = sys.argv[1]
    if len(sys.argv) > 2:
        option = sys.argv[2]
    else:
        option = None

    if cmd=='run':
        runDataBear(option)
    elif cmd=='initialize':
        findSensors()
    else:
        rsp = sendCommand(cmd,option)
        print(rsp)

if __name__ == "__main__":
    main_cli()
    
