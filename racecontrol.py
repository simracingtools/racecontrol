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

__author__ = "Robert Bausdorf"
__contact__ = "rbausdorf@gmail.com"
__copyright__ = "2019-2022, bausdorf engineering"
__date__ = "2019/06/01"
__deprecated__ = False
__email__ = "rbausdorf@gmail.com"
__license__ = "GPLv3"
__status__ = "Beta"
__version__ = "1.1.0"

import configparser
import json
import logging
import os
import sys
import time
import pickle

import irsdk
from connector import Connector

# this is our State class, with some helpful variables
UNABLE_TO_PUBLISH_EVENT = "Unable to publish event: "


class State:
    ir_connected = False
    tick = 0
    lap = 0
    event_count = 0
    session_id = -1
    sub_session_id = -1
    session_num = -1
    session_state = 0

    def from_dict(self, dic):
        self.lap = dic['Lap']
        self.tick = dic['Tick']
        self.event_count = dic['EventCount']


def to_dict(self):
    _dic = {'Lap': self.lap, 'Tick': self.tick, 'EventCount': self.event_count}
    return _dic


# here we check if we are connected to iracing,
# so we can retrieve some data
def check_iracing():
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        # don't forget to reset all your in State variables
        state.tick = 0
        state.lap = 0
        state.session_id = -1
        state.sub_session_id = -1
        state.session_num = -1
        state.event_count = 0
        state.session_state = 0

        # we are shut down ir library (clear all internal variables)
        ir.shutdown()
        print('irsdk disconnected')

    elif not state.ir_connected:
        # Check if a dump file should be used to startup IRSDK
        if config.has_option('global', 'simulate'):
            is_startup = ir.startup(test_file=config['global']['simulate'])
            print('starting up using dump file: ' + str(
                config['global']['simulate']))
        else:
            is_startup = ir.startup()
            if debug:
                print('DEBUG: starting up with simulation')

        if is_startup and ir.is_initialized and ir.is_connected:
            state.ir_connected = True
            # Check need and open serial connection

            print('irsdk connected')

            check_session_change()
            read_session_event_count()
            publish_for_event_no(to_message(ir['DriverInfo']['Drivers'][0], 'sessionInfo', generate_session_event()))


def get_collection_name():
    track_name = ir['WeekendInfo']['TrackName']
    return str(
        track_name) + '@' + str(state.session_id) \
           + '#' + str(state.sub_session_id) \
           + '#' + str(state.session_num)


def check_session_change():
    session_change = False

    if state.session_id != str(ir['WeekendInfo']['SessionID']):
        state.session_id = str(ir['WeekendInfo']['SessionID'])
        session_change = True

    if state.sub_session_id != str(ir['WeekendInfo']['SubSessionID']):
        state.sub_session_id = str(ir['WeekendInfo']['SubSessionID'])
        session_change = True

    if state.session_num != ir['SessionNum']:
        state.session_num = ir['SessionNum']
        session_change = True

    if state.session_state != ir['SessionState']:
        state.session_state = ir['SessionState']
        session_change = True

    if session_change:
        print('SessionId  : ' + get_collection_name())

    return session_change


def read_session_event_count():
    try:
        f = open(get_collection_name(), "rb")
        state.event_count = pickle.load(f)
        print("Event count for session: " + str(state.event_count))
        f.close()
    except Exception as fileException:
        print(str(fileException))


def generate_event(driver, driver_idx):
    track_event = {}
    state.event_count += 1
    track_event['IncNo'] = state.event_count
    track_event['CurrentDriver'] = driver['UserName']
    track_event['IRating'] = driver['IRating']
    track_event['TeamName'] = driver['TeamName']
    track_event['CarNumber'] = driver['CarNumber']
    track_event['CarName'] = driver['CarScreenName']
    track_event['CarClass'] = driver['CarClassShortName']
    track_event['CarClassId'] = driver['CarClassID']
    track_event['CarClassColor'] = driver['CarClassColor']
    track_event['CarLap'] = ir['CarIdxLap'][driver_idx]
    track_event['LapPct'] = ir['CarIdxLapDistPct'][driver_idx]
    track_event['SessionTime'] = ir['SessionTime'] / 86400

    pickle.dump(state.event_count, open(get_collection_name(), "wb"))

    return track_event


def send_track_event(_dict, driver_idx, driver, team_id):
    track_event = generate_event(driver, driver_idx)
    # irsdk_NotInWorld       -1
    # irsdk_OffTrack          0
    # irsdk_InPitStall        1
    # irsdk_AproachingPits    2
    # irsdk_OnTrack           3
    if _dict['trackLoc'] == -1:
        track_event['Type'] = 'OffWorld'
    if _dict['trackLoc'] == 0:
        track_event['Type'] = 'OffTrack'
    elif _dict['trackLoc'] == 1:
        track_event['Type'] = 'InPitStall'
    elif _dict['trackLoc'] == 2:
        track_event['Type'] = 'AproachingPits'
    elif _dict['trackLoc'] == 3 and teams[team_id]['trackLoc'] != -1:
        track_event['Type'] = 'OnTrack'
    elif _dict['trackLoc'] == 3 and state.session_state == 1:
        track_event['Type'] = 'OnTrack'
    else:
        track_event['Type'] = 'None'

    if _dict['trackLoc'] != -1 and track_event['Type'] != 'None':
        print(json.dumps(track_event))
        publish_for_event_no(to_message(driver, 'event', track_event))


def generate_session_event():
    session_event = {'TrackName': ir['WeekendInfo']['TrackDisplayName']}
    if ir['WeekendInfo']['TrackConfigName']:
        session_event['TrackName'] += ' - ' + ir['WeekendInfo'][
            'TrackConfigName']
    session_event['SessionDuration'] = \
        ir['SessionInfo']['Sessions'][state.session_num]['SessionTime']
    session_event['SessionType'] = \
        ir['SessionInfo']['Sessions'][state.session_num][
            'SessionType']
    session_event['SessionState'] = ir['SessionState']
    session_event['SessionTime'] = ir['SessionTime'] / 86400

    return session_event


def publish_for_event_no(event_message):
    try:
        _event_no = connector.publish(json.dumps(event_message))
        try:
            _event_count = int(_event_no)
            if _event_count > -1:
                state.event_count = _event_count
            else:
                print("Event count -1 (invalid)")
        except ValueError as vr:
            print("Server returned: " + str(vr))

    except Exception as send_exception:
        print(UNABLE_TO_PUBLISH_EVENT + str(send_exception))


def to_message(driver, event_type, event):
    _dict = {'version': __version__,
             'type': event_type,
             'sessionId': get_collection_name(),
             'clientId': driver['UserID'],
             'teamId': driver['TeamID'],
             'lap': state.lap,
             'payload': event}

    if _dict['teamId'] == 0:
        _dict['teamId'] = driver['UserID']

    return _dict


def get_position_data(car_idx, positions):
    if not positions:
        return

    position = 0
    _dict = {}
    while position < len(positions):
        if positions[position]['CarIdx'] == car_idx:
            _dict['overallPosition'] = positions[position]['Position']
            _dict['classPosition'] = positions[position]['ClassPosition']
            _dict['lapsComplete'] = positions[position]['LapsComplete']
            _dict['lastLapTime'] = positions[position]['LastTime'] / 86400
            return _dict

        position += 1

    return None


def send_pit_event(team_id, driver, driver_idx, _dict):
    track_event = generate_event(driver, driver_idx)
    if _dict['onPitRoad']:
        track_event['Type'] = 'PitEnter'
    else:
        track_event['Type'] = 'PitExit'

    teams[team_id]['onPitRoad'] = _dict['onPitRoad']

    print(json.dumps(track_event))

    publish_for_event_no(to_message(driver, 'event', track_event))


def send_driver_change(team_id, driver, driver_idx):
    track_event = generate_event(driver, driver_idx)
    track_event['Type'] = 'DriverChange'

    teams[team_id]['currentDriver'] = driver['UserName']

    print(json.dumps(track_event))
    publish_for_event_no(to_message(driver, 'event', track_event))


def send_lap_change(driver, driver_idx):
    track_event = generate_event(driver, driver_idx)
    track_event['Type'] = 'Lap'

    print(json.dumps(track_event))
    publish_for_event_no(to_message(driver, 'event', track_event))


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
    #    print(("enter loop"))
    state.tick += 1

    driver_list = ir['DriverInfo']['Drivers']
    state.lap = ir['SessionInfo']['Sessions'][state.session_num][
        'ResultsLapsComplete']
    positions = ir['SessionInfo']['Sessions'][state.session_num][
        'ResultsPositions']

    position = 0
    while position < len(driver_list):
        driver_idx = driver_list[position]['CarIdx']
        #        print(driverIdx)
        #        print(len(driverList))
        try:
            driver = driver_list[driver_idx]
        except IndexError:
            position += 1
            #            print('Driver index ' + str(driverIdx) + ' is invalid')
            continue

        team_id = driver['TeamID']
        #        print("team id: " + str(teamId))
        if team_id < 1 and driver['UserID'] > 0:
            team_id = driver['UserID']

        _dict = {'teamName': driver['TeamName'],
                 'currentDriver': driver['UserName'],
                 'SessionTime': ir['SessionTime'] / 86400,
                 'onPitRoad': ir['CarIdxOnPitRoad'][driver_idx],
                 'trackLoc': ir['CarIdxTrackSurface'][driver_idx]}

        #        print(str(dict))
        pos_data = get_position_data(driver_idx, positions)
        if pos_data:
            _dict['overallPosition'] = pos_data['overallPosition']
            _dict['classPosition'] = pos_data['classPosition']
            _dict['lapsComplete'] = pos_data['lapsComplete']
            _dict['lastLapTime'] = pos_data['lastLapTime']

        #        print("Posdata: " + str(posData))

        if team_id in teams:
            #            print("known team id")
            teams[team_id]['teamName'] = driver['TeamName']
            teams[team_id]['CarNumber'] = driver['CarNumberRaw']
            teams[team_id]['SessionTime'] = ir['SessionTime'] / 86400
            if pos_data:
                teams[team_id]['overallPosition'] = pos_data['overallPosition']
                teams[team_id]['classPosition'] = pos_data['classPosition']
                try:
                    if teams[team_id]['lastLapTime'] != pos_data['lastLapTime']:
                        teams[team_id]['lastLapTime'] = pos_data['lastLapTime']
                except KeyError:
                    teams[team_id]['lastLapTime'] = pos_data['lastLapTime']

            if teams[team_id]['currentDriver'] != driver['UserName']:
                send_driver_change(team_id, driver, driver_idx)

            if teams[team_id]['LapPct'] > ir['CarIdxLapDistPct'][driver_idx] \
                    and _dict['trackLoc'] == 3 \
                    and ir['CarIdxLap'][driver_idx] > teams[team_id]['Lap']:
                #   print("Lap(" + str(team_id) + ") " + str(teams[team_id]['Lap']) + ", " + str(ir['CarIdxLap'][driver_idx]))
                #   print("LapPct(" + str(team_id) + ") " + str(teams[team_id]['LapPct']) + ", " + str(ir['CarIdxLapDistPct'][driver_idx]))
                send_lap_change(driver, driver_idx)

            teams[team_id]['Lap'] = ir['CarIdxLap'][driver_idx]
            teams[team_id]['LapPct'] = ir['CarIdxLapDistPct'][driver_idx]

            if teams[team_id]['onPitRoad'] != _dict['onPitRoad']:
                send_pit_event(team_id, driver, driver_idx, _dict)

            if teams[team_id]['trackLoc'] != _dict['trackLoc']:
                teams[team_id]['trackLoc'] = _dict['trackLoc']
                send_track_event(_dict, driver_idx, driver, team_id)

        else:
            #            print("new team: " + str(dict))
            if team_id > 0:
                _dict['LapPct'] = ir['CarIdxLapDistPct'][driver_idx]
                _dict['Lap'] = ir['CarIdxLap'][driver_idx]
                teams[team_id] = _dict
                send_track_event(_dict, driver_idx, driver, team_id)

        position += 1

    #    print("after while")
    if check_session_change():
        session_event = generate_session_event()
        print(json.dumps(session_event))
        publish_for_event_no(to_message(ir['DriverInfo']['Drivers'][0], 'sessionInfo', session_event))


def banner():
    print("=============================")
    print("|   iRacing Race Control    |")
    print("|           " + str(__version__) + "           |")
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
        logging.basicConfig(filename=str(config['global']['logfile']),
                            level=logging.INFO)

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
