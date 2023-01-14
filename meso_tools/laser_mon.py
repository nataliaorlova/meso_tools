import pyvisa as visa
import sys
import numpy as np
import matplotlib.pylab as pl
import time


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
        self.usb_device = usb[0]
        self.scope = rm.open_resource(self.usb_device, open_timeout=20) # bigger timeout for long calls to memory
    

    def open_scope(self, timeout=20):
        """
        open_scope reopen a communication session with the scope 

        Parameters
        ----------
        timeout : int, optional
            timeout, by default 20
        """
        rm = visa.ResourceManager()
        self.scope = rm.open_resource(self.usb_device, open_timeout=timeout) # bigger timeout for long mem 
        return 


    def get_timescale(self) -> float:
        """
        get_timescale send query to retrieve timescale 

        Returns
        -------
        float
            timescale
        """
        try :
            # if session to the scope is active - send query to retrieve timescale
            self.scope.session
            # Get the timescale
            timescale = float(self.scope.query(":TIM:SCAL?"))
        except visa.errors.InvalidSession : 
            # if session is gone, reopen and retry
            self.open_scope()
            timescale = self.get_timescale()
        return timescale

    @property
    def timescale(self) -> float:
        """
        timescale property getter for timescale

        Returns
        -------
        float
            timescale
            
        """
        return self.get_timescale()

    
    def get_time_offset(self) -> float:
        """
        get_timescale sends query to retrieve time offset (horisontal shift)

        Returns
        -------
        float
            time offset
            
        """
        try :
            # if session tot he scope is active - send query to retrieve timescale
            self.scope.session
            # Get the timescale
            timeoffset = float(self.scope.query(":TIM:OFFS?"))
        except visa.errors.InvalidSession : 
            # if session is gone, reopen and retry
            self.open_scope()
            timeoffset = self.get_time_offset()
        return timeoffset

    @property 
    def time_offset(self) -> float : 
        """
        time_offset property for get_time_offset

        Returns
        -------
        float
            time offset
        """
        return self.get_time_offset()



    def get_voltage_scale(self, channel : str = "CHAN1") -> float:
        """
        get_voltage_scale  - send query to the scope to get the voltage scale 

        Parameters
        ----------
        channel : str
            channel which we're reading vlaues for, one of ["CHAN1", "CHAN2", "CHAN3" "CHAN4"] 
            default "CHAN1"

        Returns
        -------
        float
            voltage scale
        """
        try :
            # if session tot he scope is active - send query to retrieve data
            self.scope.session
            # Get the timescale
            voltage_scale = float(self.scope.query(f':{channel}:SCAL?'))
        except visa.errors.InvalidSession : 
            # if session is gone, reopen and retry
            self.open_scope()
            voltage_scale = self.get_voltage_scale()
        return voltage_scale

    @property
    def volts_scale_channel1(self) -> float:
        """ Getter for voltage scale channel 1
        """
        return self.get_voltage_scale('CHAN1')


    @property
    def volts_scale_channel2(self) -> float:
        """ Getter for voltage scale channel 2
        """
        return self.get_voltage_scale('CHAN2')

    def get_voltage_offset(self, channel : str = "CHAN1") -> float:
        """
        get_voltage_scale  - send query to the scope to get the voltage offset 

        Parameters
        ----------
        channel : str
            channel which we're reading values for, one of ["CHAN1", "CHAN2", "CHAN3" "CHAN4"] 
            default "CHAN1"

        Returns
        -------
        float
            voltage offset
        """
        try :
            # if session to the scope is active - send query to retrieve data
            self.scope.session
            # Get the timescale
            voltage_offset = float(self.scope.query(f':{channel}:OFFS?'))
        except visa.errors.InvalidSession :
            # if session is gone, reopen and retry
            self.open_scope()
            voltage_offset = self.get_voltage_scale()
        return voltage_offset

    @property
    def volts_offset_channel1(self) -> float:
        """ Getter for voltage scale channel 1
        """
        return self.get_voltage_offset('CHAN1')


    @property
    def volts_offset_channel2(self) -> float:
        """ Getter for voltage scale channel 2
        """
        return self.get_voltage_offset('CHAN2')


    def get_sample_rate(self) -> float:
        """
        get_smaple_rate _summary_

        Returns
        -------
        float
            _description_
        """
        try :
            # if session to the scope is active - send query to retrieve data
            self.scope.session
            sample_rate = float(self.scope.query(':ACQ:SRAT?'))
        except visa.errors.InvalidSession :
            self.open_scope()
            sample_rate = self.get_sample_rate()
        return sample_rate

    @property 
    def sample_rate(self) -> float:
        """
        sample_rate property for the get sample rate

        Returns
        -------
        float
            sample rate
        """
        return self.get_sample_rate()

        

    def get_trace(self, channel : str) -> np.array:
        """
            Function to get trace values from the oscillsocope's memory
        Args:
            channel (str): channel to connect to, CHAN1 or CHAN2

        Returns:
            np.array: array of datapoint
        """
        try :
            self.scope.session
            self.scope.write(":WAV:MODE MAX")
            time.sleep(0.1)
            self.scope.write(":STOP")
            time.sleep(0.1)
            self.scope.write(":WAV:FORM ASCii")
            time.sleep(0.1)
            self.scope.write(f":WAV:SOUR {channel}")
            time.sleep(0.1)
            self.scope.write(":WAV:POIN 10000")
            time.sleep(0.1)
            rawdata = self.scope.query(":WAV:DATA?")
            time.sleep(1)
            rawdata=rawdata[11:]
            data_string = rawdata.split(",")
            del data_string[-1] # removing new line character
            data  = np.array([float(item) for item in data_string])
            self.scope.write(":RUN")
        except visa.errors.InvalidSession:
            self.open_scope()
            data = self.get_trace(channel)
        return data

    @property
    def trace_channel1(self) -> np.array:
        """ Trace from channel 1

        Returns:
        --------
        np.array
            array of voltage values
        """
        while True:
            data = self.get_trace('CHAN1')
            if len(data) != 0:
                break
        return data

    @property
    def trace_channel2(self) -> np.array:
        """
        Trace from channel 2

        Returns
        -------
        np.array
             array of voltage values
        """
        while True:
            data = self.get_trace('CHAN2')
            if len(data) != 0:
                break
        return data


    def plot_data(self, channel : str) -> None:
        """
            Function to generate a figure visualizing the data
        Args:
            channel (str): channel from which we get data 'CHAN1' or 'CHAN2'

        Returns:
            pl.figure: handle to a matplotlib figure
        """
        if channel == 1:
            data = self.trace_channel1
            color = 'orange'
        elif channel == 2:
            data = self.trace_channel2
            color = 'blue'
        
        total_time = len(data)/self.sample_rate
        time = np.linspace(0,500,num=len(data))
        # Plot the data
        fig = pl.figure(figsize=[10, 2])
        pl.plot(time, data, color)
        pl.title(f"Oscilloscope Channel {channel}")
        pl.ylabel("Voltage (V)")
        pl.xlabel("Time ( ns )")
        pl.show()
        return

    def get_trace_frequency(self, channel : int = 1) -> float:
        """Get frequency on teh trace, assuming sinewave or close to it

        Args:
            channel (int): channel from which we get data, 1,2,3 or 4, default 1

        Returns:
            float: frequency in Hz
        """
        try :
            self.scope.session
            frequency = self.scope.query(f"MEAS:ITEM? FREQ,CHAN{channel}")
        except visa.errors.InvalidSession:
            self.open_scope()
            frequency = self.get_trace_frequency(channel)
        return frequency


    @property
    def trace_frequency_channel1(self):
        return self.get_trace_frequency(1)

    @property
    def trace_frequency_channel2(self):
        return self.get_trace_frequency(2)
