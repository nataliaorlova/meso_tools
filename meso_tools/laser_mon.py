import pyvisa as visa
import sys
import numpy as np
import matplotlib.pylab as pl

class RigolAPI():
    """
    Class with simple commands to RIGOL DS7034 oscilloscope via PyVisa interface 
    """
    def __init__(self):
        """
        Here we will configure the backend, find Rigol device, get it's address and open it for communication
        Make sure only one Rigol Oscilloscope is connected to given host 
        """
        rm = visa.ResourceManager()
        instruments = rm.list_resources()
        # find rigol device - should be on USB0:
        usb = list(filter(lambda x: 'USB' in x, instruments))
        if len(usb) != 1:
            print('Bad instrument list', instruments)
            sys.exit(-1)
        
        self.scope = rm.open_resource(usb[0]) # bigger timeout for long mem  , 

        # Get the timescale
        self.timescale = float(self.scope.query(":TIM:SCAL?"))
        # Get the timescale offset
        self.timeoffset = float(self.scope.query(":TIM:OFFS?"))
        self.voltscale = float(self.scope.query(':CHAN1:SCAL?'))
        # And the voltage offset
        self.voltoffset = float(self.scope.query(":CHAN1:OFFS?"))


    def get_trace(self, channel : str) -> np.array:
        """
            Function to get data fomr the oscillsocope's memory
        Args:
            channel (str): channel to connect to, CHAN1 or CHAN2

        Returns:
            np.array: array of datapoint
        """
        self.scope.write(":WAV:MODE MAX")
        self.scope.write(":STOP")
        self.scope.write(":WAV:FORM ASCii")
        self.scope.write(f":WAV:SOUR {channel}")
        self.scope.write(":WAV:POIN 10000")
        rawdata = self.scope.query(":WAV:DATA?")
        params = self.scope.query(":WAV:PRE?")
        self.scope.write(":RUN")
        self.sample_rate = float(self.scope.query(':ACQ:SRAT?'))
        params = params.split(',')
        rawdata=rawdata[11:]
        data_string = rawdata.split(",")
        del data_string[-1] # removing new line character
        self.data = [float(item) for item in data_string]


    def plot_data(self) -> pl.figure:
        """
            Function to generate a figure visualizing the data
        Args:
            data (np.array): array of datapoints, units = volts

        Returns:
            pl.figure: handle to a matplotlib figure
        """
        data = np.array(self.data)
        total_time = len(data)/self.sample_rate / self.timescale  
        time = np.linspace(0,total_time,num=len(data))
        # Plot the data
        fig = pl.figure(figsize=[10, 2])
        pl.plot(time, data)
        pl.title("Oscilloscope Channel 1")
        pl.ylabel("Voltage (V)")
        pl.xlabel("Time ( ns )")
        pl.show()