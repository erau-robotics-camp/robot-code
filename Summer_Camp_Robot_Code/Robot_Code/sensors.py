import smbus
import time
import commands
import RPi.GPIO as GPIO
import socket
import sys
import logging
import logging.handlers
import argparse
import array
from array import *
GPIO.setmode(GPIO.BCM)

def HLS(red,green,blue): #function to convert RGB to HSL
	#RGB 0-65535, must scale to 0-1 
         red = float(red)/1310
         green = float(green)/1310
         blue = float(blue)/1310
	 
	#lowest, highest, and difference between the two out of R,G,and B
         low = min(red,green,blue)
         high = max(red,green,blue)
         delt = high - low

	#Hue Calculation
         if high == red:       
              H = (60*((green-blue)/delt))
              if H < 0:
                   H = H+360
         elif high == green:
              H = (60*(2+((blue-red)/delt)))
         elif high == blue:
              H = (60*(4+((red-green)/delt)))
	#Lightness Calculation
         L = (high+low)/2
	#Saturation Calculation
         if L < .5:
              S = delt/(high +low)
         elif L >= .5:
              S = delt/(2-delt)
         H=int(H)
	#lessening decimals for smaller data transfer     
         L = int(L*10000)
         S = int(S*100)
         return H,L,S

def numcolor(H,S): #function to determine color from Hue and Saturation
         if H <= 25:
               num_color = 2#red
         elif (H >= 1000 and  H <= 2000):
               num_color = 5#orange
         elif (H >= 40 and H <= 65 and S>50):
               num_color = 3#yellow
         elif (H >= 80 and H<= 140):
               num_color = 1#green
         elif (H >= 180 and H <= 220):
               num_color = 4#blue
         else:
               num_color = 0
         return num_color 

# Deafults
LOG_FILENAME = "/tmp/sensors.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

# Define and parse command line arguments
parser = argparse.ArgumentParser(description="Sensors Python service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")

# If the log file is specified on the command line then override the default
args = parser.parse_args()
if args.log:
        LOG_FILENAME = args.log

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="h", interval=1, backupCount=5)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
        def __init__(self, logger, level):
                """Needs a logger and a logger level."""
                self.logger = logger
                self.level = level

        def write(self, message):
                # Only log if there is a message (not just a new line)
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

laptop_ip = '192.168.1.21'
pi_ip = commands.getoutput("ifconfig").split("\n")[10].split()[1][5:]
send_port = 54322

bus = smbus.SMBus(1)#initialize serial commands using serial bus 1
bus.write_byte(0x70,0x00)#turns MUL (address byte 0x70) on using command (0x00)

bus.write_byte(0x70,0x01)#activates only port 1 on MUL
bus.write_byte(0x29,0x80|0x12)#writes to sensors address (0x29) to initialize first sensor
ver = bus.read_byte(0x29)#variable to ensure sensor 1 is on
if ver == 0x44:
     bus.write_byte(0x29, 0x80|0x00) # 0x00 = ENABLE register
     bus.write_byte(0x29, 0x01|0x02) # 0x01 = Power on, 0x02 RGB sensors enabled
     bus.write_byte(0x29, 0x80|0x14) # Reading results start register 14, LSB then MSB

bus.write_byte(0x70,0x02)#activates only port 2 on MUL
bus.write_byte(0x29,0x80|0x12)#initializes sensor 2
ver = bus.read_byte(0x29)#variable to ensure sensor 2 is on
if ver == 0x44:
     bus.write_byte(0x29, 0x80|0x00) # 0x00 = ENABLE register
     bus.write_byte(0x29, 0x01|0x02) # 0x01 = Power on, 0x02 RGB sensors enabled
     bus.write_byte(0x29, 0x80|0x14) # Reading results start register 14, LSB then MSB     


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#defining socket/packet as UDP via internet

bus.write_byte(0x70,0x01)#set MUL to first Port
data = bus.read_i2c_block_data(0x29, 0)#begin read sequence
time.sleep(3)#sleep for 3 seconds to allow sensors to start recording data

#initializing Variables
x=0
H = 0
S=0
L=0
HSL = [0,0,0,0,0,0,0,0,0]
num_color = 0
check_point_order = [2,1,4]
check_point_count = 0
current_check = 0
prev_check = 0
tot_checkpoint = 0
t_start = time.time()
t_dif = 0
data = 0
red = 0
green = 0
blue = 0

print "working"
while True:
         #data retrieval from sensors  
         data = bus.read_i2c_block_data(0x29, 0)
         red =  (data[3] << 8 | data[2])
         green =  (data[5] << 8 | data[4])
         blue =  (data[7] << 8 | data[6])

         
         [H,L,S] = HLS(red,green,blue)#converts RGB to HSL 
         num_color = numcolor(H,S)#uses Hue values to determine color 
		#Red = 2
		#Green = 1
		#Yellow = 3
		#Orange = 5
		#Blue = 4
	 
         #Check point counting function: if-statments(1-3) forward coutning (4-6) backwards counting
         if (current_check == 0 and num_color == check_point_order[0]):
               check_point_count = check_point_count + 1
               current_check = 1
	       prev_check = 0
         elif (current_check == 1 and num_color == check_point_order[1]):
               check_point_count += 1
               current_check = 2
               prev_check = 1
         elif (current_check == 2 and num_color == check_point_order[2]):
               check_point_count += 1
               current_check = 0
               prev_check = 2
	 elif (current_check == 1 and num_color == check_point_order[2] and prev_check == 0):
	       check_point_count -=1
	       current_check =0
	       prev_check = 2
	 elif (current_check == 0 and num_color == check_point_order[1] and prev_check == 2):
	       check_point_count -= 1
	       current_check = 2
	       prev_check = 1
	 elif (current_check == 2 and num_color == check_point_order[0] and prev_check == 1):
               check_point_count -= 1
               current_check = 1
	       prev_check = 0	
	       	
          

         
         #HSL = [x,H,S,L,red/257,green/257,blue/257, num_color,tot_checkpoint]
         HSL = "%.1s,%.5s,%.5s,%.5s,%.5s,%.5s,%.5s,%.5s,%.5s,%.5s" % (x,H,S,L,red,green,blue,num_color,check_point_count,current_check)
         print HSL
         
         s.sendto(HSL,(laptop_ip,send_port))#send packet via UDP 
             
         #Multiplexer changing function
         if x == 0:
             x = 1
             bus.write_byte(0x70,0x02)#change MUL to second port
         elif x ==1:
             x = 0
             bus.write_byte(0x70,0x01)#change MUL to first Port

         time.sleep(.01)#slight delay to prevent buffering with labview
 

    
bus.write_byte(0x70,0x00)#change all ports off at end of program <-- just for "good" programming     
    
