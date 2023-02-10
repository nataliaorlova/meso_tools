# Natalia Orlova | January 2023

# This script will connect to the laser monitoring device (Rigol DS7034)
# grab data from channel 1 every 10 seconds, calculare frequency 
# and send a log message to file reporting the frequency
# if the frequency is <79 Mhz and > 81 MHz, it will send a warning message to teh mpe log server http://eng-logtools:8080
# and a Teams message to Natalia
# All logs will write to this path: c:\projectdata\AIBS_MPE\ProjectName\logs\ProjectName.log


import logging
import np_logging.handlers as handlers
from meso_tools.laser_mon import *
import time
import math
from meso_tools import __version__
import np_logging

if __name__ == "__main__":

    logger = logging.getLogger()
    logger.setLevel("INFO")
    logger.addHandler(handlers.FileHandler(logs_dir="C:\\Users\\nataliao\\Documents\\Logs\\", level=logging.WARNING))
    logger.addHandler(handlers.FileHandler(logs_dir="C:\\Users\\nataliao\\Documents\\Logs\\", level=logging.INFO))
    logger.addHandler(handlers.ConsoleHandler())
    
    #seting up log file:
    weblogger = np_logging.web("laser_monitoring")
    email_logger = np_logging.email("nataliao@alleninstitute.org", subject="Laser frequency logging info")
    rigol = RigolAPI()

    while True:
        ch1_freq = rigol.trace_frequency_channel1  
        if  math.isclose(ch1_freq, 80*(10**6), abs_tol=5*10**6) :
            logger.info(f"Laser frequency reported is  {ch1_freq / (10**6)} MHz")  
        else:
            logger.warning(f"Laser frequency reported is  {ch1_freq / (10**6)} MHz")
            weblogger.warning(f"Laser frequency reported is  {ch1_freq / (10**6)} MHz") 
            # email_logger.warning(f"Laser frequency reported is  {ch1_freq / (10**6)} MHz")
        time.sleep(10)