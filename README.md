# Raspberry Pi HVAC

HVAC model on a Raspberry Pi.

This program tests many different electronic components.

Features include:
- movement detection
- thermometer (with humidity from CIMIS API)
- LCD status window
- mini HVAC system

# How to Install

1. Connect Raspberry Pi and modules to pins (follow board schematics in images, make sure to use resistors).

<pre>

  Green LED      | Pin = 7   GPIO = 4

  Blue LED       | Pin = 15  GPIO = 22

  Red LED        | Pin = 18  GPIO = 24

  Blue Button    | Pin = 13  GPIO = 27

  Red Button     | Pin = 16  GPIO = 23

  Green Button   | Pin = 40  GPIO = 21

  DHT Sensor     | Pin = 11  GPIO = 17

  Infared Sensor | Pin = 29  GPIO = 5

</pre>

2. Download code and change directory to src

3. Run main.py

# How to Use

To turn on the Green LED, have movement in front of the infared sensor. The LED will stay on for 10 seconds since the last movement.

To turn on the AC, use the blue button to lower the desired temperature to at least 3 less than the actual temperature. (LCD displays actual temperature / desired temperature on the top left)

To turn on the HEAT, use the red button to raise the desired temperature to at least 3 above than the actual temperature.

HEAT and AC will turn off / on automatically whenever the desired temperature has more than 3 temperature difference than the actual temperature.

The green button will close / open the door. If the door is open, the HVAC will be turned off no matter the changes in temperature.

