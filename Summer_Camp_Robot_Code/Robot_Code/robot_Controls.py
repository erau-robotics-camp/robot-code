#!/usr/bin/env python

# 2017-2-15
# Senior Design Summer Camp Robot Control Python

import urllib2
import re
import time
import sys
import commands
import socket
import fcntl, os
import errno
import pigpio
import read_PWM
import RPi.GPIO as GPIO  
import logging
import logging.handlers
import argparse

# Deafults
LOG_FILENAME = "/tmp/robot_Controls.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

# Define and parse command line arguments
parser = argparse.ArgumentParser(description="Robot Controls Python service")
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
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="h", interval = 1, backupCount=5)
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

#define PCB pins
LeftMotorPin    = 24 # pwm broadcom pin 18 (switch pin with Servo)
RightMotorPin   = 23 # pwm broadcom pin 23
ServoPin        = 18 # pwm broadcom pin 24 (servo - note: need to use 50hz - range is 1 to 10)
RCJoyXPin       = 10 # RC Channel 1 (left/right)
RCJoyYPin       = 19 # RC channel 2 (forward/back)
ServoControlPin = 26 # RC channel 3 (forward/back)
KillSwitchPin   = 16 # RC channel 5 (robot kill switch)
RCSwitchPin     = 20 # RC channel 6 (RC/Autonomous switch)
EStopPin        = 4  # EStop GPIO Pin

#define PWM frequency
freq = 50

#server interaction
bot_number = int(commands.getoutput("ifconfig").split("\n")[18].split()[1][16:])
server_ip = '192.168.1.10'

#items
itemTime = 0
lightning = 0
oil = 0
item = 0

#moon delay variables
delay_time = []
motor_right = []
motor_left = []
motor_servo = []
rc_delay = 0
purge_delay = 0

#motor variables
motorCenter = 7.3
motorDeadzone = 0.2
motorMax = 11
motorMin = 3.5
controllerOffset = -0.95
controllerCenter = 8.15
rc_sens = 1
last_Servo = 0

#UDP
laptop_ip = '192.168.1.21'
pi_ip = commands.getoutput("ifconfig").split("\n")[18].split()[1][5:] #look in ifconfig for pi IP
rec_port = 54320
send_port = 54322

#set up UDP
UDPreciever = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
UDPreciever.bind((pi_ip, rec_port))
fcntl.fcntl(UDPreciever, fcntl.F_SETFL, os.O_NONBLOCK)

#pin set up
GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme

#pin set output
GPIO.setup(LeftMotorPin, GPIO.OUT)
GPIO.setup(RightMotorPin, GPIO.OUT)
#GPIO.setup(ServoPin, GPIO.OUT)
GPIO.setup(RCSwitchPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(RCJoyXPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(RCJoyYPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(ServoControlPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(EStopPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#pin set freq
LeftMotor = GPIO.PWM(LeftMotorPin,freq)
RightMotor = GPIO.PWM(RightMotorPin,freq)
#Servo = GPIO.PWM(ServoPin,freq)

#pin start
LeftMotor.start(100)
RightMotor.start(100)
#Servo.start(0)

#motor command pigpio
Servo = pigpio.pi()

#motor pigpio mode
Servo.set_mode(ServoPin, pigpio.OUTPUT)

#reciever pigpio
RCJoyXPigpio        = pigpio.pi() # RC Channel 1 (left/right)
RCJoyYPigpio        = pigpio.pi() # RC channel 2 (forward/back)
ServoControlPigpio  = pigpio.pi() # RC channel 3 (forward/back)
KillSwitchPigpio    = pigpio.pi() # RC channel 5 (robot kill switch)
RCSwitchPigpio      = pigpio.pi() # RC channel 6 (RC/Autonomous switch)

#start pigpio reader
RCJoyXReader        = read_PWM.reader(RCJoyXPigpio, RCJoyXPin) # RC Channel 1 (left/right)
RCJoyYReader        = read_PWM.reader(RCJoyYPigpio, RCJoyYPin) # RC channel 2 (forward/back)
ServoControlReader  = read_PWM.reader(ServoControlPigpio, ServoControlPin) # RC channel 3 (forward/back)
KillSwitchReader    = read_PWM.reader(KillSwitchPigpio, KillSwitchPin) # RC channel 5 (robot kill switch)
RCSwitchReader      = read_PWM.reader(RCSwitchPigpio, RCSwitchPin) # RC channel 6 (RC/Autonomous switch)

#Give time to initialize
time.sleep(1.0)

try:
   while True:
       LeftMotor.ChangeDutyCycle(100) 
       RightMotor.ChangeDutyCycle(100)
       while GPIO.input(EStopPin) == True:
            #print("RCX={:.2f}".format(RCJoyYReader.duty_cycle()))
            # check if killed
            while  KillSwitchReader.duty_cycle() < controllerCenter:
                #do nothing, its dead
                #print("DEAD")
                #print("Kill={:.2f}".format(KillSwitchReader.duty_cycle()))
                
                #De-energize the motors
                LeftMotor.ChangeDutyCycle(100)
                RightMotor.ChangeDutyCycle(100)

                #Open server and get bot settings
                rc_info_http = urllib2.urlopen("http://"+server_ip+"/rc_info.php").read()
                rc_info = re.findall(r"[-+]?\d*\.\d+|\d+",rc_info_http)
                rc_delay = float(rc_info[(bot_number-1)*3+1])
                rc_sens = float(rc_info[(bot_number-1)*3+2])
                sens = rc_sens
                purge_delay = 1
                #print rc_delay
                print ("100,100,5,0,{:.2f},{:.2f}".format(rc_sens,rc_delay))
                time.sleep(.1)
                
            # while loop to constantly check if RC or autonomous
            if RCSwitchReader.duty_cycle() > controllerCenter:
                #do autonomous stuff
                #print "AUTO"     
                try:
                  #UDPreciever.sendto("1",(laptop_ip,send_port))
                  rdata, addr = UDPreciever.recvfrom(2048)
                except socket.error, e:
                  err = e.args[0]
                  if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    print 'No data available'
                    continue
                  else:
                    print e
                else:
                  data = rdata.split(",")
                  LeftMotor.ChangeDutyCycle((float(data[0])*5)+5)
                  RightMotor.ChangeDutyCycle((float(data[1])*5)+5)
                  Servo.ChangeDutyCycle(float(data[2])*12)	  
                  print("left={:.2f} right={:.2f}".format((float(data[0])*5)+5, (float(data[1])*5)+5))

            else:
                currentTime = time.time()
            
                #Get and handle items
                request = "http://"+server_ip+"/ItemFX.php?robot_number="+str(bot_number)
                try:     
                    response = urllib2.urlopen(request, timeout=0.025)
                    item = int(response.read())
                except urllib2.URLError, e:
                    print e
                    continue
                except socket.timeout, e:
                    print e
                    continue
                except socket.error, e:
                    print e
                    continue
                #except:
                #    print sys.exc_info()[0]
                #    continue

                # get RC values
                ServoIn = int((ServoControlReader.duty_cycle()-5.4)*350+500)           
                JoyXIn = RCJoyXReader.duty_cycle() + controllerOffset 
                JoyYIn = RCJoyYReader.duty_cycle() + controllerOffset

                #convert joystick inputs to motor values
                #Calculate drive turn output  due to joystick X input
                if JoyYIn >= (motorCenter + motorDeadzone):
                    #forward
                    PremixMotorLeft = JoyXIn
                    PremixMotorRight = motorCenter-(JoyXIn-motorCenter)
                            
                elif JoyYIn <= (motorCenter - motorDeadzone):
                    #backward
                    PremixMotorLeft = JoyXIn
                    PremixMotorRight = motorCenter-(JoyXIn-motorCenter)

                else:
                    #stationary
                    PremixMotorLeft = JoyXIn
                    PremixMotorRight = motorCenter-(JoyXIn-motorCenter)

                #items
                if item == 0 or currentTime - itemTime < 10:
                    #print "NO ITEM"
                    item = 0
                elif item == 1: #Wheelies
                    #print "Wheelie"
                    itemTime = time.time()
                    LeftMotor.ChangeDutyCycle(7.3)
                    RightMotor.ChangeDutyCycle(7.3)
                    LeftMotor.ChangeDutyCycle(3.5)
                    RightMotor.ChangeDutyCycle(3.5)
                    time.sleep(.5)
                    LeftMotor.ChangeDutyCycle(11)
                    RightMotor.ChangeDutyCycle(11)
                    time.sleep(.5)
                    LeftMotor.ChangeDutyCycle(3.5)
                    RightMotor.ChangeDutyCycle(3.5)
                elif item == 2: #Banana Peal (spin out)
                    #print "Banana Peel"
                    itemTime = time.time()
                    LeftMotor.ChangeDutyCycle(7.3)
                    RightMotor.ChangeDutyCycle(7.3)
                    LeftMotor.ChangeDutyCycle(11)
                    RightMotor.ChangeDutyCycle(3.5)
                    time.sleep(.5)
                    LeftMotor.ChangeDutyCycle(7.3)
                    RightMotor.ChangeDutyCycle(7.3)
                elif item == 3: #Lightning Strike (reduce speed)
                    #print "Lightning Strike"
                    itemTime = time.time()
                    lightning = 1
                    motorMax = 8
                elif item == 4: #Oil Slick (Sensitivity is doubled)
                    #print "Oil Slick"
                    itemTime = time.time()
                    oil = 1
                    rc_sens = 2
                elif item == 5: #Blue Shell
                    #print "Blue Shell"
                    itemTime = time.time()
                    LeftMotor.ChangeDutyCycle(7.3)
                    RightMotor.ChangeDutyCycle(7.3)
                    time.sleep(3)
                elif item == 6: #InstaPass (git rected scrubs)
                    #print "InstaPass"
                    itemTime = time.time()
                    LeftMotor.ChangeDutyCycle(7.3)
                    RightMotor.ChangeDutyCycle(7.3)
                    time.sleep(5)

                if oil == 1 and currentTime-itemTime > 3:
                    oil = 0
                    rc_sens = sens

                if lightning == 1 and currentTime-itemTime > 10:
                    lightning = 0
                    motorMax = 11
                    
                #Scale drive output due to joystick Y input (throttle)
                PremixMotorLeft = PremixMotorLeft*(JoyYIn/motorCenter)
                PremixMotorRight = PremixMotorRight*(JoyYIn/motorCenter)

                MixMotorLeft = PremixMotorLeft*rc_sens+motorCenter*(1-rc_sens)
                MixMotorRight = PremixMotorRight*rc_sens+motorCenter*(1-rc_sens)

                #Limit inputs
                if MixMotorLeft > motorMax:
                   MixMotorLeft = motorMax
                elif MixMotorLeft < motorMin:
                   MixMotorLeft = motorMin

                if MixMotorRight > motorMax:
                   MixMotorRight = motorMax
                elif MixMotorRight < motorMin:
                   MixMotorRight = motorMin

                if ServoIn < 500:
                  ServoIn = 500
                elif ServoIn > 2500:
                  ServoIn = 2500
                   
                #Stop jitter
                if JoyXIn <= 7.4 and JoyXIn >= 7.1 and JoyYIn <= 7.4 and JoyYIn >= 7.1:
                   MixMotorLeft = motorCenter
                   MixMotorRight = motorCenter
                   
                #print("X={:.2f} Y={:.2f}".format(RCJoyXReader.duty_cycle(), RCJoyYReader.duty_cycle()))   
                #print("raw={:.2f} servo={:.2f}".format(ServoInRaw, ServoIn))
                #print("Left={:.2f} Right={:.2f}".format(MixMotorLeft, MixMotorRight))

                #clear delay lists if delay time has changed
                if purge_delay == 1:
                  delay_time[:] = []
                  motor_right[:] = []
                  motor_left[:] = []
                  motor_right[:] = []
                  motor_servo[:] = []
                  purge = 0

                #Add motor inputs into lists and associated time
                delay_time.append(currentTime)
                motor_right.append(MixMotorRight)
                motor_left.append(MixMotorLeft)
                motor_servo.append(ServoIn)
                
                if currentTime - delay_time[0] >= rc_delay:#else: # time - delay_time[0] >= rc_delay:
                  #output values to motors
                  #print len(delay_time)
                  LeftMotor.ChangeDutyCycle(motor_left[0])
                  RightMotor.ChangeDutyCycle(motor_right[0])
                  Servo.set_servo_pulsewidth(ServoPin, ServoIn)
                  #Servo.ChangeDutyCycle(motor_servo[0])
                  #print motor_servo[0]

                  #cycle delay lists
                  delay_time.pop(0)
                  motor_left.pop(0)
                  motor_right.pop(0)
                  motor_servo.pop(0)

                #Right Motor, Left Motor, Servo, Item, Sensitivity, Delay
                print ("{:.2f},{:.2f},{:.2f},{:d},{:.2f},{:.2f}".format(MixMotorRight,MixMotorLeft,ServoIn,item,rc_sens,rc_delay))
                  
                time.sleep(.1)
  
except:
  print sys.exc_info()[0]

  print 'Canceling PWM readers'
  RCJoyXReader.cancel()
  RCJoyYReader.cancel()
  ServoControlReader.cancel()
  KillSwitchReader.cancel()
  RCSwitchReader.cancel()

  print 'Stopping Pigpio'
  RCJoyXPigpio.stop()
  RCJoyYPigpio.stop()
  ServoControlPigpio.stop()
  KillSwitchPigpio.stop()
  RCSwitchPigpio.stop()   

  print 'Cleaning GPIO'
  GPIO.cleanup()

  print 'Close UDP'
  UDPreciever.close()

  sys.exit()
