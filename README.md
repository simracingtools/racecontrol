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
	# Proxy configuration. The given URL will be used as Proxy on both http and 
	# https protocol
	;proxy = <Proxy URL>

	## The following options are for development/debugging only. 
	# Generates additional debug output. Comment out or set to yes/True to enable
	;debug = yes

	# Logfile to which data is written in debug mode 
	logfile = racecontrol.log

	# Uncomment to start the application using a data dump file from irsdk for 
	# testing/development purposes. The dump file can be created by issuing the 
	# command 'irsdk --dump data.dmp'
	;simulate = data/monzasunset.dump

	[connect]
	# URL to which all events are posted as json data. 
	# If postUrl value is empty data is only written to the logfile.
	postUrl = http://localhost:8080/clientmessage


To start a session recording:

	python racecontrol.py
	
## Data collections

All session data is intended to be sent to an instance of a [racecontrol-server](https://github.com/simracingtools/racecontrol-server). 


## Developer info

### Requirements

To install all required packages, run

	pip install -r requirements.txt
### Build

Run

    pyinstaller --clean -F racecontrol.py
