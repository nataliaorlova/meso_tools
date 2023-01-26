# Natalia Orlova | January 2023

# This script will connect to the laser monitoring device (Rigol DS7034)
# grab data from channel 1 every 10 seconds, calculare frequency 
# and send a log message to file reporting the frequency
# if the frequency is <79 Mhz and > 81 MHz, it will send a warning message to teh mpe log server http://eng-logtools:8080
# and a Teams message to Natalia
# All logs will write to this path: c:\projectdata\AIBS_MPE\ProjectName\logs\ProjectName.log


import logging
from meso_tools.laser_mon import *
from mpetk import mpeconfig
import time
from .. import __version__

if __name__ == "__main__":

    #seting up log file:
    mpeconfig.source_configuration("laser_monitoring", fetch_project_config=False, version=__version__)
    rigol = RigolAPI()

    while True:
        ch1_freq = rigol.trace_frequency_channel1
        
        if  abs( 79*(10**6) - ch1_freq ) > 0.1 or abs(ch1_freq - 81*(10**6) ) > 0.1 :
            logging.warning(f"Laser frequency reported is  {ch1_freq / (10**6)} MHz")
        else:
            logging.info(f"Laser frequency reported is  {ch1_freq / (10**6)} MHz")

        time.sleep(10)