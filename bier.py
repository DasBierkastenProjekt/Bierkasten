#! /usr/bin/env python

# bier.py (c) 2016 by Karsten Lehmann

###############################################################################
#                                                                             #
#    This file is a part of Das Bierkastenprojekt                             #
#                                                                             #
#    Das Bierkastenprojekt is free software: you can redistribute it and/or   #
#    modify it under the terms of the GNU General Public License as published #
#    by the Free Software Foundation, either version 3 of the License, or any #
#    later version.                                      		      #
#                                                                             #
#    This program is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#    GNU General Public License for more details.                             #
#                                                                             #
#    You should have received a copy of the GNU General Public License        #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
###############################################################################

import os
import sys
import smbus
import RPi.GPIO as gpio

__author__ = "Karsten Lehmann"
__copyright__ = "Copyright (c) 2016, Karsten Lehmann"
__credits__ = ["Karsten Lehmann"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Karsten Lehmann"
__email__ = "ka.lehmann@yahoo.com"
__status__ = "Development"

W1_PATH = "/sys/bus/w1/devices/"
EXPANDER_ADDRESS = [0x20, 0x21]	 # I2C addresses of the 2 mcp23017 portexpanders
GPIO_MAP = {  1 :  2,
              2 : 29,		 #
              3 : 14,		 #  #####################
              4 :  4,		 #  # 1 # 2 # 3 # 4 # 5 #
              5 : 15,		 #  #####################   
              6 : 17,		 #  # 6 # 7 # 8 # 9 #10 #   <- Bierkasten
              7 : 18,		 #  #####################
              8 : 27,		 #  #11 #12 #13 #14 #15 #
              9 : 22,		 #  #####################
             10 : 23,		 #  #16 #17 #18 #19 #20 #
             11 : 24,		 #  #####################
             12 : 10,		 #		# RPi #
             13 :  9,		 # 
             14 : 25,		 # This dict shows, which GPIO is connected to
             15 : 28,            # which bottle.
             16 :  8,            #
             17 : 11,
             18 :  7,
             19 : 30,
             20 : 31 }

def get_ds18b20():
    """Return a thermalsensor if avaible"""
    if os.path.isdir(W1_PATH):
        for i in os.walk(W1_PATH):
            for device in i[1]:
                if device.startswith("10-"):
                    return DS18B20(W1_PATH + device)
    return None

def is_mcp23017(bus):
    """Check if there are 2 mcp23017 portexpanders connected to the I2C-bus"""
    try:
        for addr in EXPANDER_ADDRESS:
            bus.read_byte_data(addr, 0x00)
        return True
    except IOError as err:
        print err
        return False

def get_bierkasten():
    """Check which Bierkasten is avaible and return a Bierkasten-object"""
    if os.getuid() != 0:
        print("Error, you must run this as root!")
        sys.exit()
    try:
        bus = smbus.SMBus(1)
        ds18b20 = get_ds18b20()
        if ds18b20 != 0 and is_mcp23017(bus):
            print("Having a portexpander based Bierkasten...")
            return PortExpanderBasedBierkasten(bus, ds18b20)
    except IOError:
        print("Error while connecting to I2C-Adapter")

    print("Having a GPIO based Bierkasten...")
    return GPIObasedBierkasten(GPIO_MAP)

class BierData(object):
    """This class represends all bottles in a Bierkasten.
       It has 20 virtual attributes of type string named bottle01 to bottle20.
       "1"represends a full bottle and "0" an empty bottle."""

    repr_str = \
"""
---------------------
| %s | %s | %s | %s | %s |
---------------------
| %s | %s | %s | %s | %s |
---------------------
| %s | %s | %s | %s | %s |
---------------------
| %s | %s | %s | %s | %s |
---------------------
"""

    def __init__(self, data):
        self.data = data

    def __getattr__(self, name):
        if name.startswith("bottle"):
            bottle_number = int(name.replace("bottle", ""))
        elif name.toLower().startswith("flasche"):
            bottle_number = int(name.toLower().replace("flasche", ""))
        else:
            raise AttributeError

        if not 1 <= bottle_number <= 20:
            raise AttributeError
        return True if self.data[bottle_number-1] == "1" else False

    def __repr__(self):
        return BierData.repr_str % tuple(self.data)

class DS18B20(object):
    """This class provides access to the ds18b20 thermal sensor.

       It takes the path to the sensor as only argument.
       (/sys/bus/w1/devices/10-xxxxx/)
    """
    def __init__(self, path):
        self.path = path

    def get_temperature(self):
        """This method returns the current temperature of the Sensor"""
        temp_file = open(self.path + "/w1_slave", "r")
        temp = temp_file.readlines()[1]
        temp = temp.split("t=")[1].replace("\n", "")
        temp = temp[:len(temp)-2]
        temp = float(temp) / 10
        temp_file.close()
        return temp

class Bierkasten(object):
    """This is the base class represending a Bierkasten

       It provides informations about the temperature/bottles/type of the
       Bierkasten with the methods get_temperature/get_bier_data/get_type.

       To check if there is information about temperature/bottles use
       has_temperature/has_bier_data methods.

       Every class that inherits from Bierkasten should register one ore more
       callbacks to provide information about it in its constructor:
        - register_temperature_call(<function>)
        - register_bier_data_call(<function>)

       The temperature callback should return a float value and the bier data
       callback a string, where a "0" represents an empty bottle and a "1" a
       full bottle. The numeration for the bottles always starts at the top left
       corner of the Bierkasten, where the Raspberry Pi is alway at the bottom
       of the Bierkasten.

       You could also register a cleanup callback, for example to cleanup all
       used gpios:
        - register_cleanup(<function>)  
    """
    def __init__(self):
        self.__temperature = None
        self.__bier_access = None
        self.__cleanup = lambda: None

    def register_temperature_call(self, func):
        self.__temperature = func

    def register_bier_data_call(self, func):
        self.__bier_access = func

    def register_cleanup(self, func):
        self.__cleanup = func

    def has_temperature(self):
        if self.__temperature:
            return True
        else:
            return False

    def has_bier_data(self):
        if self.__bier_access:
            return True
        else:
            return False

    def get_temperature(self):
        return self.__temperature()

    def get_bier_data(self):
        return self.__bier_access()

    def get_type(self):
        return self.__class__.__name__

    def cleanup(self):
        self.__cleanup()

class PortExpanderBasedBierkasten(Bierkasten):
    """This is the Bierkasten class.

       It connects to two I2C Portexpanders (MCP23017) and a digital thermometer
       (ds18b20).
    """
    def __init__(self, bus, ds18b20):
        Bierkasten.__init__(self)
        self.bus = bus
        self.ds18b20 = ds18b20
        # setup portexpanders
        # deklare all ports as inputs
        self.bus.write_byte_data(EXPANDER_ADDRESS[0], 0x00, 0xff)
        self.bus.write_byte_data(EXPANDER_ADDRESS[0], 0x01, 0xff)
        self.bus.write_byte_data(EXPANDER_ADDRESS[1], 0x00, 0xff)
        self.bus.write_byte_data(EXPANDER_ADDRESS[1], 0x01, 0xff)

        # set A7-A3 PullUps
        self.bus.write_byte_data(EXPANDER_ADDRESS[0], 0x0C, 0b11111000)
        # set B0-B4 PullUps
        self.bus.write_byte_data(EXPANDER_ADDRESS[0], 0x0D, 0b00011111)
        self.bus.write_byte_data(EXPANDER_ADDRESS[1], 0x0C, 0b11111000)
        self.bus.write_byte_data(EXPANDER_ADDRESS[1], 0x0D, 0b00011111)

        self.register_temperature_call(self.get_temperature)
        self.register_bier_data_call(self.get_bottle_state)

    def get_temperature(self):
        """This method returns the current temperature of the Bierkasten"""
        return self.ds18b20.get_temperature()

    def get_bottle_state(self):
        """This method returns a Bierdata object, which contains information
           about the number of empty and full bottles in the Bierkasten."""
        data = ""
        for i in range(2):
            for j in range(2):
                dat = format(
                    self.bus.read_byte_data(EXPANDER_ADDRESS[i], 0x12+j),
                    '#010b')
                if j == 0:
                    data += dat[2:7]
                else:
                    data += dat[5:10]

        data = data.replace("0", "2")
        data = data.replace("1", "0")
        data = data.replace("2", "1")

        return BierData(data)

class GPIObasedBierkasten(Bierkasten):
    """This is the class for the "traditional" Bierkasten.

       That Bierkasten has 20 buttons - one under every bottle - which are wired
       to a GPIO and GND. Therefore pullup resistors are needed at every GPIO
       and if a full bottle stands on a button, the state of the button is 0
       (GPIO connected to GND) and 1 for an empty bottle.

       It has now way to provide temperature data.
    """
    def __init__(self, gpio_map):
        Bierkasten.__init__(self)
        self.gpio_map = gpio_map
        # gpio.BOARD is not an option here, because gpio.BOARD does not include
        # the P5-header.
        gpio.setmode(gpio.BCM)

	# Disable the warnings for 
        #  1) gpios, which already have a physical pullup resistors
        #  2) gpios, which are already in use (the Bierkasten uses all gpios,
        #     so there could be no other use for the gpios)
        gpio.setwarnings(False)
        for bottle in self.gpio_map:
            # setup all pins with internal pullup resistor
            # some may have a physical pullup resistor, but warnings are already
            # disabled ;-)
            gpio.setup(self.gpio_map[bottle], gpio.IN, pull_up_down=gpio.PUD_UP)
        self.register_bier_data_call(self.get_bottle_state)
        self.register_cleanup(gpio.cleanup)

    def get_bottle_state(self):
        data = ""
        for i in range(1, 21):
            pin = self.gpio_map[i]
            # Switch states, because the get_bier_data function of the
            # Bierkasten class uses 1 for full bottles, not empty ones.
            data += "0" if gpio.input(pin) else "1"
        return BierData(data)

