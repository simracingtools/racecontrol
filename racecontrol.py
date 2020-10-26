#!python3
""" Daemon that can publishes iRacing telemetry values at MQTT topics.

Configure what telemery values from iRacing you would like to publish at which
MQTT topic.
Calculate the geographical and astronomical correct light situation on track. 
Send pit service flags and refuel amount to and receive pit commands from
a buttonbox using a serial connection.
 
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""
from distutils.log import info
from _ast import Not

__author__ = "Robert Bausdorf"
__contact__ = "rbausdorf@gmail.com"
__copyright__ = "2019, bausdorf engineering"
#__credits__ = ["One developer", "And another one", "etc"]
__date__ = "2019/06/01"
__deprecated__ = False
__email__ =  "rbausdorf@gmail.com"
__license__ = "GPLv3"
#__maintainer__ = "developer"
__status__ = "Beta"
__version__ = "0.90"

import sys
import configparser
import irsdk
import os
import time
import json
import logging
import requests

# this is our State class, with some helpful variables
class State:
    ir_connected = False
    tick = 0
    lap = 0
    eventCount = 0
    sessionId = -1
    subSessionId = -1
    sessionNum = -1
    sessionState = 0

    def fromDict(self, dic):
        self.lap = dic['Lap']
        self.tick = dic['Tick']
        self.eventCount = dic['EventCount']

    def toDict(self):
        dic = {}
        dic['Lap'] = self.lap
        dic['Tick'] = self.tick
        dic['EventCount'] = self.eventCount
        return dic

class Connector:
    postUrl = ''
    headers = {'x-teamtactics-token': 'None'}
    
    def __init__(self, config):
        print('Initializing connector')
        if config.has_option('connect', 'postUrl'):
            self.postUrl = str(config['connect']['postUrl'])
    
        if self.postUrl == '':
            print('No Url configured, only logging events')
        elif self.postUrl != '':
            print('Using Url ' + self.postUrl + ' to publish events')
            if config.has_option('connect', 'clientAccessToken'):
                self.headers = { 'x-teamtactics-token': config['connect']['clientAccessToken'], 'Content-Type': 'application/json'}

        if config.has_option('global', 'logfile'):
            logging.basicConfig(filename=str(config['global']['logfile']),level=logging.INFO,format='%(asctime)s$%(message)s')

    def publish(self, jsonData):
        try:
            logging.info(jsonData)
            if self.postUrl != '':
                response = requests.post(self.postUrl, data=jsonData, headers=self.headers, timeout=10.0)
                return response

        except Exception as ex:
            print('Unable to publish data: ' + str(ex))

# here we check if we are connected to iracing
# so we can retrieve some data
def check_iracing():        
    
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        # don't forget to reset all your in State variables
        state.tick = 0
        state.lap = 0
        state.sessionId = -1
        state.subSessionId = -1
        state.sessionNum = -1
        state.eventCount = 0
        state.sessionState = 0

        # we are shut down ir library (clear all internal variables)
        ir.shutdown()
        print('irsdk disconnected')

    elif not state.ir_connected:
        # Check if a dump file should be used to startup IRSDK
        if config.has_option('global', 'simulate'):
            is_startup = ir.startup(test_file=config['global']['simulate'])
            print('starting up using dump file: ' + str(config['global']['simulate']))
        else:
            is_startup = ir.startup()
            if debug:
                print('DEBUG: starting up with simulation')

        if is_startup and ir.is_initialized and ir.is_connected:
            state.ir_connected = True
            # Check need and open serial connection

            print('irsdk connected')

            checkSessionChange()
            try:
                __msgStr = json.dumps(toMessage(ir['DriverInfo']['Drivers'][0], 'sessionInfo', generateSessionEvent(ir)))
                connector.publish(__msgStr)
                print(__msgStr)
            except Exception as ex:
                print('Unable to publish initial session: ' + str(ex))
            
def getCollectionName():

    trackName = ir['WeekendInfo']['TrackName']
    return str(trackName) + '@' + state.sessionId + '#' + state.subSessionId + '#' + str(state.sessionNum)

def checkSessionChange():
    sessionChange = False
    
    if state.sessionId != str(ir['WeekendInfo']['SessionID']):
        state.sessionId = str(ir['WeekendInfo']['SessionID'])
        sessionChange = True
                
    if state.subSessionId != str(ir['WeekendInfo']['SubSessionID']):
        state.subSessionId = str(ir['WeekendInfo']['SubSessionID'])
        sessionChange = True

    if state.sessionNum != ir['SessionNum']:
        state.sessionNum = ir['SessionNum']
        sessionChange = True

    if state.sessionState != ir['SessionState']:
        state.sessionState = ir['SessionState']
        sessionChange = True

    if sessionChange:
        print('SessionId  : ' + getCollectionName())

    return sessionChange

def generateEvent(driver, driverIdx):
    trackEvent = {}
    state.eventCount += 1
    trackEvent['IncNo'] = state.eventCount
    trackEvent['CurrentDriver'] = driver['UserName']
    trackEvent['IRating'] = driver['IRating']
    trackEvent['TeamName'] = driver['TeamName']
    trackEvent['CarNumber'] = driver['CarNumber']
    trackEvent['CarName'] = driver['CarScreenName']
    trackEvent['CarClass'] = driver['CarClassShortName']
    trackEvent['CarClassId'] = driver['CarClassID']
    trackEvent['CarClassColor'] = driver['CarClassColor']
    trackEvent['CarLap'] = ir['CarIdxLap'][driverIdx]
    trackEvent['LapPct'] = ir['CarIdxLapDistPct'][driverIdx]
    trackEvent['SessionTime'] = ir['SessionTime'] / 86400
    
    return trackEvent

def generateSessionEvent(ir):
    sessionEvent = {}
    sessionEvent['TrackName'] = ir['WeekendInfo']['TrackDisplayName']
    if ir['WeekendInfo']['TrackConfigName']:
        sessionEvent['TrackName'] += ' - ' + ir['WeekendInfo']['TrackConfigName']
    sessionEvent['SessionDuration'] = ir['SessionInfo']['Sessions'][state.sessionNum]['SessionTime']
    sessionEvent['SessionType'] = ir['SessionInfo']['Sessions'][state.sessionNum]['SessionType']
    sessionEvent['SessionState'] = ir['SessionState']
    sessionEvent['SessionTime'] = ir['SessionTime'] / 86400

    return sessionEvent

def toMessage(driver, eventType, event):
    _dict = {}
    _dict['Version'] = __version__
    _dict['Type'] = eventType
    _dict['SessionId'] = getCollectionName()
    _dict['ClientId'] = driver['UserID']
    _dict['TeamId'] = driver['TeamID']
    _dict['Lap'] = state.lap
    _dict['Payload'] = event

    return _dict

# our main loop, where we retrieve data
# and do something useful with it
def loop():
    # on each tick we freeze buffer with live telemetry
    # it is optional, useful if you use vars like CarIdxXXX
    # in this way you will have consistent data from this vars inside one tick
    # because sometimes while you retrieve one CarIdxXXX variable
    # another one in next line of code can be changed
    # to the next iracing internal tick_count
    ir.freeze_var_buffer_latest()

    state.tick += 1
    collectionName = getCollectionName()
    
    # check for pit enter/exit
    #checkPitRoad()

    driverList = ir['DriverInfo']['Drivers']
    positions = ir['SessionInfo']['Sessions'][state.sessionNum]['ResultsPositions']
    state.lap = ir['SessionInfo']['Sessions'][state.sessionNum]['ResultsLapsComplete']

    if positions == None:
        return
    
    position = 0
    while position < len(positions):
        driverIdx = positions[position]['CarIdx'] -1
#        print(driverIdx)
#        print(len(driverList))
        try:
            driver = driverList[driverIdx]
        except IndexError:
            print('Driver index ' + str(driverIdx) + ' is invalid')
            continue

        teamId = driver['TeamID']
        if teamId < 1 and driver['UserID'] > 0:
            teamId = driver['UserID']

        dict = {}

        dict['teamName'] = driver['TeamName']
        dict['currentDriver'] = driver['UserName']
        dict['overallPosition'] = position
        dict['classPosition'] = positions[position]['ClassPosition']
        dict['lapsComplete'] = positions[position]['LapsComplete']
        dict['lastLapTime'] = positions[position]['LastTime'] / 86400
        dict['SessionTime'] = ir['SessionTime'] / 86400

        dict['onPitRoad'] = ir['CarIdxOnPitRoad'][driverIdx]
        dict['trackLoc'] = ir['CarIdxTrackSurface'][driverIdx]

        dataChanged = False
        
        if teamId in teams:
            teams[teamId]['teamName'] = driver['TeamName']
            teams[teamId]['overallPosition'] = position
            teams[teamId]['CarNumber'] = driver['CarNumberRaw']
            teams[teamId]['classPosition'] = positions[position]['ClassPosition']
            teams[teamId]['lap'] = ir['CarIdxLap'][driverIdx]
            teams[teamId]['SessionTime'] = ir['SessionTime'] / 86400
            if teams[teamId]['lastLapTime'] != dict['lastLapTime']:
                teams[teamId]['lastLapTime'] = positions[position]['LastTime'] / 86400
                dataChanged = True

            if teams[teamId]['currentDriver'] != driver['UserName']: 
            #and dict['trackLoc'] == 3:
                trackEvent = generateEvent(driver, driverIdx)
                trackEvent['Type'] = 'DriverChange'

                teams[teamId]['currentDriver'] = driver['UserName']
                
                print(json.dumps(trackEvent))
                
                try:
                    connector.publish(json.dumps(toMessage(driver, 'event', trackEvent)))
                except Exception as ex:
                    print('Unable to publish event: ' + str(ex))

            if teams[teamId]['onPitRoad'] != dict['onPitRoad']:
                trackEvent = generateEvent(driver, driverIdx)
                if dict['onPitRoad']:
                    trackEvent['Type'] = 'PitEnter'
                else:
                    trackEvent['Type'] = 'PitExit'

                teams[teamId]['onPitRoad'] = dict['onPitRoad']

                print(json.dumps(trackEvent))
                
                try:
                    connector.publish(json.dumps(toMessage(driver, 'event', trackEvent)))
                except Exception as ex:
                    print('Unable to publish session: ' + str(ex))

            if teams[teamId]['trackLoc'] != dict['trackLoc']:
                trackEvent = generateEvent(driver, driverIdx)
                #irsdk_NotInWorld       -1
                #irsdk_OffTrack          0
                #irsdk_InPitStall        1
                #irsdk_AproachingPits    2
                #irsdk_OnTrack           3
                if dict['trackLoc'] == -1:
                    trackEvent['Type'] = 'OffWorld'
                if dict['trackLoc'] == 0:
                    trackEvent['Type'] = 'OffTrack'
                elif dict['trackLoc'] == 1:
                    trackEvent['Type'] = 'InPitStall'
                elif dict['trackLoc'] == 2:
                    trackEvent['Type'] = 'AproachingPits'
                elif dict['trackLoc'] == 3 and teams[teamId]['trackLoc'] != -1:
                    trackEvent['Type'] = 'OnTrack'
                elif dict['trackLoc'] == 3 and state.sessionState == 1:
                    trackEvent['Type'] = 'OnTrack'
                else:
                    trackEvent['Type'] = 'None'

                teams[teamId]['trackLoc'] = dict['trackLoc']
                if dict['trackLoc'] != -1 and trackEvent['Type'] != 'None':
                    print(json.dumps(trackEvent))
                    try:
                        connector.publish(json.dumps(toMessage(driver, 'event', trackEvent)))
                    except Exception as ex:
                        print('Unable to publish event: ' + str(ex))

        else:
            teams[teamId] = dict
            dataChanged = True

        position += 1

    if checkSessionChange():
        try:
            sessionEvent = generateSessionEvent(ir)
            print(json.dumps(sessionEvent))
            connector.publish(json.dumps(toMessage(ir['DriverInfo']['Drivers'][0], 'sessionInfo', sessionEvent)))
        except Exception as ex:
            print('Unable to publish event: ' + str(ex))



def banner():
    print("=============================")
    print("|   iRacing Race Control    |")
    print("|           " + str(__version__) + "            |")
    print("=============================")


# Here is our main program entry
if __name__ == '__main__':
    # Read configuration file
    config = configparser.ConfigParser()    
    try: 
        config.read('racecontrol.ini')
    except Exception as ex:
        print('unable to read configuration: ' + str(ex))
        sys.exit(1)

    # Print banner an debug output status
    banner()
    if config.has_option('global', 'debug'):
        debug = config.getboolean('global', 'debug')
    else:
        debug = False
    
    if debug:
        print('Debug output enabled')

    if config.has_option('global', 'proxy'):
        proxyUrl = str(config['global']['proxy'])
        os.environ['http_proxy'] = proxyUrl
        os.environ['https_proxy'] = proxyUrl

    try:
        connector = Connector(config)
    except Exception as ex:
        print('Unable to initialize Connector: ' + str(ex))
        sys.exit(1)

    if config.has_option('global', 'logfile'):
        logging.basicConfig(filename=str(config['global']['logfile']),level=logging.INFO)

    # initializing ir and state
    ir = irsdk.IRSDK()
    state = State()
    teams = {}
    # Project ID is determined by the GCLOUD_PROJECT environment variable

    try:
        # infinite loop
        while True:
            # check if we are connected to iracing
            check_iracing()
                
            # if we are, then process data
            if state.ir_connected:
                loop()

            # sleep for half a second
            # maximum you can use is 1/60
            # cause iracing update data with 60 fps
            time.sleep(0.5)
    except KeyboardInterrupt:
        # press ctrl+c to exit
        print('exiting')
        time.sleep(1)
        pass