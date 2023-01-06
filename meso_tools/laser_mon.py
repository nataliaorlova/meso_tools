import pyvisa as visa
import logging

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
        addresses = rm.list_opened_resources()
        # find rigol device - should be on USB0:
        for address in addresses:
            if 'USB' in address:
                device = rm.open_resource(address)
                name = device.query("*IDN?")
                if 'RIGOL' in name:
                    self.rigol = device
                    print(f"Found Rigol as {name}\nAt address {address}")
                    break
            else:
                print(f"No USB devices are present")
        if not self.rigol:
             print(f"Rigol is not present on your system, check connection. It should be plugged in to one of the USB ports.")
                