import pyvisa as visa

class RigolAPI():
    """
    Class with simple commands to RIGOL DS7034 oscilloscope via PyVisa interface 
    """
    def __init__(self):
        """
        """
        rm = visa.ResourceManager()
        devices = rm.list_opened_resources()

