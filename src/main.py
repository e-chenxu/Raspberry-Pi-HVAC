#!/usr/bin/python

### modules ###
import threading
import RPi.GPIO as GPIO
import time     # for time delay and threshold
from datetime import datetime, date
import requests

# lcd and dht files
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
import Freenove_DHT as DHT

# using board number system
GPIO.setmode(GPIO.BOARD)

# PIN DECLARATIONS #
LED_G = 7     # green led            GPIO 4
LED_B = 15    # blue led             GPIO 22
LED_R = 18    # red led              GPIO 24

BTN_B = 13    # blue button          GPIO 27
BTN_R = 16    # red bytton           GPIO 23
BTN_G = 40    # green led            GPIO 21

DHT_IN = 11   # DHT                  GPIO 17
INFAR = 29    # infared sensor       GPIO 5

# to disable warnings
GPIO.setwarnings(False) 


# PIN SETUPS
GPIO.setup(BTN_G, GPIO.IN, pull_up_down=GPIO.PUD_UP) # input of green button
GPIO.setup(BTN_R, GPIO.IN, pull_up_down=GPIO.PUD_UP) # input of red button
GPIO.setup(BTN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP) # input of blue button

GPIO.setup(LED_G, GPIO.OUT, initial=GPIO.LOW) # output of greens
GPIO.setup(LED_R, GPIO.OUT, initial=GPIO.LOW) # output of reds
GPIO.setup(LED_B, GPIO.OUT, initial=GPIO.LOW) # output of blues

GPIO.setup(INFAR, GPIO.IN, pull_up_down=GPIO.PUD_UP) # set INFAR to INPUT mode


# GLOBAL FLAGS
GREEN_LCDFLAG = 0       # tells if the green led is on
door_flag = 0           # open = 1, closed = 0
door_alert = 0          # alerts when door is opened/ closed
hvac_setting = 0        # 0 = off, 1 = AC, 2 = HEAT
prev_hvac_setting = 0   # holds previous setting to compare
desired_temp = 0        # desired temperature
feels_like_temp = 0     # temperature that feels like

# energy bill in k
CONST_AC = 18
CONST_HEAT = 36
CONST_kW = .50


def sensor_light():
    ''' takes care of movemnt light, 
    makes a thread that lasts for 10 seconds 
    each time there is movement 
    '''
    
    global GREEN_LCDFLAG     # global green lcdflag is an increment to tell how many threads are waiting for the green light
    GPIO.output(LED_G, GPIO.HIGH)
    GREEN_LCDFLAG += 1
    time.sleep(10)
    GREEN_LCDFLAG -= 1
    if (GREEN_LCDFLAG == 0): # if all the threads are gone, then lcd goes low
        GPIO.output(LED_G, GPIO.LOW)


def get_humidity():
    # retrieves web data using API key

    today = date.today()
    count = 0
    humidity = 0
    todaysdate = today.strftime("%Y-%m-%d")
    webstring = "https://et.water.ca.gov/api/data?appKey=30df55a6-1b4b-4320-926a-949b89e08a95&targets=75&startDate=" + todaysdate + "&endDate=" + todaysdate + "&dataItems=hly-rel-hum"
    response = requests.get(webstring).json()
    if response:
        print('Retrieved Web Data!')
        # parse through, and break if you find a none value
        for i in response['Data']['Providers'][0]['Records']:
            if (i['HlyRelHum']['Value'] == None):
                break
            count+=1
        # if none recieved, humidity is just the dht humidity
        humidity = response['Data']['Providers'][0]['Records'][count-1]['HlyRelHum']['Value'] 
    else:
        print('Error occurred. Using DHT11 humidity value... ')
        humidity = dht.humidity
    return int(humidity)


def hvac_loop():
    ''' loop that updates temperature variables
    by getting the past 3 temperatures 
    '''
    
    global desired_temp
    global feels_like_temp
    global hvac_setting
    dht = DHT.DHT(DHT_IN)
    count = 0 # Measurement counts
    avg_temp = 0
    start = 0    #first 3 are on
    threelist = [] # lists the last 3
    while(True):
        for i in range(0,11):            
            check = dht.readDHT11()
            if (check is dht.DHTLIB_OK):
                break
            time.sleep(0.1)
        if (count >= 3):
            threelist.pop(0)
            threelist.append(dht.temperature*1.8+32) # convert to F
            avg_temp = sum(threelist) / 3
        else:
            threelist.append(dht.temperature*1.8+32)
            avg_temp = dht.temperature*1.8+32
        humidity = get_humidity()
        # set initial desired temp to whatever temp it is now
        feels_like_temp = avg_temp + 0.05*humidity
        if (count == 0):
            desired_temp = feels_like_temp
        count += 1
        time.sleep(1)

        
def loop():
    ''' LCD update loop,
    will wait for door close / open
    and temperature updates
    '''
    
    global door_alert
    global door_flag
    global GREEN_LCDFLAG
    global hvac_setting
    global prev_hvac_setting
    total_energy = 0    # this is in kWh
    total_cost = 0      # money
    mcp.output(3,1)     # turn on LCD backlight
    lcd.begin(16,2)     # set number of LCD lines and column
    while(True):
        # check for door / window update
        if (door_alert == 1):
            time.sleep(0.1) # wait for variable to update
            if (door_flag == 1):
                lcd.setCursor(0,0)
                lcd.message("DOOR/WINDOW OPEN\n")
                lcd.message("  HVAC HALTED   ")
                GPIO.output(LED_B, GPIO.LOW)
                GPIO.output(LED_R, GPIO.LOW)
                prev_hvac_setting = hvac_setting
                hvac_setting = 0
            else:
                lcd.setCursor(0,0)
                lcd.message("DOOR/WINDOW SHUT\n")
                lcd.message("  HVAC RESUMED  ")
                # resumes the hvac
                hvac_setting = prev_hvac_setting
            time.sleep(3)
            door_alert = 0
        # do hvac stuff
        if (door_flag == 0):
            prev_hvac_setting = hvac_setting
            # want hotter
            if (desired_temp - feels_like_temp >= 3):
                hvac_setting = 2
                GPIO.output(LED_B, GPIO.LOW)
                GPIO.output(LED_R, GPIO.HIGH)
                if (hvac_setting != prev_hvac_setting):
                    lcd.setCursor(0, 0)  # set cursor position
                    lcd.message("  HVAC HEAT ON  \n")
                    lcd.message("                \n")
                    time.sleep(3)
                    # then show cost report
                    lcd.setCursor(0, 0)  # set cursor position
                    lcd.message("Energy: %.2fKWh   \nCost: $%.2f    "%(total_energy,total_cost))  # display CPU temperature
                    time.sleep(1.5)
            # want cooler
            elif (desired_temp - feels_like_temp <= -3):
                hvac_setting = 1
                GPIO.output(LED_B, GPIO.HIGH)
                GPIO.output(LED_R, GPIO.LOW)
                if (hvac_setting != prev_hvac_setting):
                    lcd.setCursor(0, 0)  # set cursor position
                    lcd.message("   HVAC AC ON   \n")
                    lcd.message("                \n")
                    time.sleep(3)
                    # then show cost report
                    lcd.setCursor(0, 0)  # set cursor position
                    lcd.message("Energy: %.2fKWh   \nCost: $%.2f    "%(total_energy,total_cost))  # display CPU temperature
                    time.sleep(1.5)
            # right temp
            else:
                hvac_setting = 0
                GPIO.output(LED_B, GPIO.LOW)
                GPIO.output(LED_R, GPIO.LOW)
                if (hvac_setting != prev_hvac_setting):
                    lcd.setCursor(0, 0)  # set cursor position
                    lcd.message("    HVAC OFF    \n") 
                    lcd.message("                \n")
                    time.sleep(3)
                    # then show cost report
                    lcd.setCursor(0, 0)  # set cursor position
                    lcd.message("Energy: %.2fKWh \nCost: $%.2f   "%(total_energy,total_cost))  # display CPU temperature
                    time.sleep(1.5)
        # determine the cost
        # adjust lights
        if (hvac_setting == 0):
            GPIO.output(LED_B, GPIO.LOW)
            GPIO.output(LED_R, GPIO.LOW)
        elif (hvac_setting == 1):
            GPIO.output(LED_B, GPIO.HIGH)
            GPIO.output(LED_R, GPIO.LOW)
            # ac cost, 18k / 3600 ( seconds in an hour) * 0.1 seconds (cuz time sleep)
            total_energy += (CONST_AC / 3600 * 0.1)
            total_cost = total_energy * CONST_kW
        elif (hvac_setting == 2):
            GPIO.output(LED_B, GPIO.LOW)
            GPIO.output(LED_R, GPIO.HIGH)
            total_energy += (CONST_HEAT / 3600 * 0.1)
            total_cost = total_energy * CONST_kW
        # check for lcd update
        if (GREEN_LCDFLAG > 0):
            led = "ON "
        if (GREEN_LCDFLAG == 0):
            led = "OFF"
            
        # check door status
        if (door_flag == 1):
            door = "OPEN"
            
        else:
            door = "SAFE"
        
        # check hvac status
        if (hvac_setting == 0):
            hvac = "OFF "
        elif (hvac_setting == 1):
            hvac = "AC  "
        else:
            hvac = "HEAT"
        
        # hvac settings
        lcd.setCursor(0,0)  # set cursor position
        lcd.message("%02d/%02d"%(feels_like_temp,desired_temp) + "     " + "D:" + door + '\n')# display CPU temperature
        lcd.message("H:" + hvac + "     " + "L:" + led + '\n')# display CPU temperature
        time.sleep(0.1)
        
        
def handle(pin):
    ''' catches interrupt and spawns the 
    blink_thread() thread to handle interrupt
    '''
    
    global GREEN_LCDFLAG
    global door_alert
    global door_flag
    global hvac_setting
    global desired_temp
    # handle the events
    t = None
    # if the infared is moved, we create a thread for each blink so the light wont flicker
    if (pin == INFAR):
        # entering thread
        t = threading.Thread(target=sensor_light)
        t.daemon = True
        t.start()
    # alert the door and change the door state
    if (pin == BTN_G):
        door_alert = 1
        if (door_flag == 1):
            door_flag = 0
        else:
            door_flag = 1
            hvac_setting = 0
    # just set desired temp
    if (pin == BTN_R):
        desired_temp += 1
    if (pin == BTN_B):
        desired_temp -= 1
 
# lcd template used
# chip addresses
PCF8574_address = 0x27
PCF8574A_address = 0x3F
# create gpio adapter
try:
    mcp = PCF8574_GPIO(PCF8574_address)
except:
    try:
        mcp = PCF8574_GPIO(PCF8574A_address)
    except:
        print ('I2C address error.')
        exit(1)
        
# lcd to the gpio adapter pins
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp)

# event functions
GPIO.add_event_detect(BTN_G,GPIO.RISING,callback=handle, bouncetime=50) # detect green press
GPIO.add_event_detect(BTN_R,GPIO.RISING,callback=handle, bouncetime=50) # detect red press
GPIO.add_event_detect(BTN_B,GPIO.RISING,callback=handle, bouncetime=50) # detect blue press
GPIO.add_event_detect(INFAR,GPIO.RISING,callback=handle, bouncetime=50) # detect infared movement

# main thread
if __name__ == '__main__':
    print ('Program is starting ... ')
    try:
        t = None
        # create a thread for the other loop
        t = threading.Thread(target=hvac_loop)
        t.daemon = True
        t.start()   # start threading
        time.sleep(0.5) # wait a bit for variables
        loop()
    except KeyboardInterrupt:
        lcd.clear()
        GPIO.cleanup()
        exit()

