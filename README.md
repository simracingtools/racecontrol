# Racecontrol

This application is intended to collect driver events from iRacing team
members during a team event.

## Problem

If you try to do appropriate live race control in iRacing then you are likely
to miss important events like pitstops or driver changes.

## Solution

If racecontrol runs this script the following events of each driver are
recorded along with a timestamp:

* Approaching pits
* Enter pitlane
* In pit stalls
* Driver change
* Exit pitlane

## Configuration and usage

	[DEFAULT]
	
	[global]
	# Firebase access credentials. This file has to be provided
	# by the Google Firestore owner. It has to placed in the same
	# directory as teamtactics.exe
	firebase = <firestoreCedentials.json>

	# Proxy configuration. The given URL will be used as Proxy on both http and 
	# https protocol
	;proxy = <Proxy URL>

	## The following options are for development/debugging only. 
	# Generates additional debug output. Comment out or set to yes/True to enable
	;debug = yes

	# Logfile to which data is written in debug mode 
	logfile = irtactics.log

	# Uncomment to start the application using a data dump file from irsdk for 
	# testing/development purposes. The dump file can be created by issuing the 
	# command 'irsdk --dump data.dmp'
	;simulate = data/monzasunset.dump

To start a session recording:

	python racecontrol.py
	
## Data collections

All session data is gathered within a Firestore collection. The collection name will be

	<teamName>@<sessionId>#<subsessionId>#<sessionNumber>
	

Each collection maintains a 'state' document containing synchronization information to enable restarting
the script during an ongoing event without information loss. 

The telemetry data mentioned above is collected in one document per event - so document
'1' contains data for event #1.


## Developer info
### Build

Follow instructions at 
https://stackoverflow.com/questions/55848884/google-cloud-firestore-distribution-doesnt-get-added-to-pyinstaller-build

Run

    pyinstaller --clean -F racecontrol.py
