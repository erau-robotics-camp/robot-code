import smbus
import time
import commands
import RPi.GPIO as GPIO
import socket
GPIO.setmode(GPIO.BCM)

def HLS(red,green,blue):
    #Hue Saturation Lightness
         red = float(red)/1310
         green = float(green)/1310
         blue = float(blue)/1310
         low = min(red,green,blue)
         high = max(red,green,blue)
         delt = high - low
         if high == red:       
              H = (60*((green-blue)/delt))
              if H < 0:
                   H = H+360
         elif high == green:
              H = (60*(2+((blue-red)/delt)))
         elif high == blue:
              H = (60*(4+((red-green)/delt)))
         L = (high+low)/2
         if L < .5:
              S = delt/(high +low)
         elif L >= .5:
              S = delt/(2-delt)
         H=int(H)     
         L = int(L*10000)
         S = int(S*100)
         return H,L,S

def numcolor(H):
         if H <= 9:
               num_color = 2
         elif (H >= 15 and  H <= 20):
               num_color = 5
         elif (H >= 50 and H <= 70):
               num_color = 3
         elif (H >= 80 and H<= 140):
               num_color = 1
         elif (H >= 280 and H <= 341):
               num_color = 4
         else:
               num_color = 0
         return num_color 

laptop_ip = '192.168.1.21'
pi_ip = commands.getoutput("ifconfig").split("\n")[10].split()[1][5:]
send_port = 54322

bus = smbus.SMBus(1)
bus.write_byte(0x70,0x00)

bus.write_byte(0x70,0x01)
bus.write_byte(0x29,0x80|0x12)
ver = bus.read_byte(0x29)
if ver == 0x44:
     bus.write_byte(0x29, 0x80|0x00) # 0x00 = ENABLE register
     bus.write_byte(0x29, 0x01|0x02) # 0x01 = Power on, 0x02 RGB sensors enabled
     bus.write_byte(0x29, 0x80|0x14) # Reading results start register 14, LSB then MSB

bus.write_byte(0x70,0x02)
bus.write_byte(0x29,0x80|0x12)
ver = bus.read_byte(0x29)
if ver == 0x44:
     bus.write_byte(0x29, 0x80|0x00) # 0x00 = ENABLE register
     bus.write_byte(0x29, 0x01|0x02) # 0x01 = Power on, 0x02 RGB sensors enabled
     bus.write_byte(0x29, 0x80|0x14) # Reading results start register 14, LSB then MSB     


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
bus.write_byte(0x70,0x01)
data = bus.read_i2c_block_data(0x29, 0)
time.sleep(3)

x=0
int(x)

H = 0
int(H)
S=0
L=0
HSL = [0,0,0,0,0,0,0,0,0]

num_color = 0
int(num_color)

check_point_order = [2,3,1]
check_point_count = 0

current_check = 0
int(current_check)

tot_checkpoint = 0
int(tot_checkpoint)

t_start = time.time()
t_dif = 0

data = 0

red = 0
float(red)
green = 0
float(green)
blue = 0
float(blue)

print "working"
while True:
           
         data = bus.read_i2c_block_data(0x29, 0)
         red =  (data[3] << 8 | data[2])
         green =  (data[5] << 8 | data[4])
         blue =  (data[7] << 8 | data[6])

         
         [H,L,S] = HLS(red,green,blue) 
         num_color = numcolor(H)
         
         
         if (current_check == 0 and num_color == check_point_order[0]):
               check_point_count += 1
               current_check = 1
         elif (current_check == 1 and num_color == check_point_order[1]):
               check_point_count += 1
               current_check = 2
         elif (current_check == 2 and num_color == check_point_order[2]):
               check_point_count += 1
               current_check = 0
         

         tot_checkpoint = check_point_count
          
         
         
         #HSL = [x,H,S,L,red/257,green/257,blue/257, num_color,tot_checkpoint]
         HSL = "%.1s,%.5s,%.5s,%.5s,%.5s,%.5s,%.5s,%.1s,%.1s" % (x,H,S,L,red,green,blue,num_color,tot_checkpoint)
         print HSL
         
         s.sendto(HSL,(laptop_ip,send_port)) 
             
         
         if x == 0:
             x = 1
             bus.write_byte(0x70,0x02)
         elif x ==1:
             x = 0
             bus.write_byte(0x70,0x01)
         time.sleep(.01)
 

    
bus.write_byte(0x70,0x00)     
    
