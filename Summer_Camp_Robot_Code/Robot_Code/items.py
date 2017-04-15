
import time

class item:
  def wheelie
  #everyone wheelies except user
  LeftMotor.ChangeDutyCycle(7.3)
  RightMotor.ChangeDutyCycle(7.3)
  LeftMotor.ChangeDutyCycle(3.5)
  RightMotor.ChangeDutyCycle(3.5)
  time.sleep(.5)
  LeftMotor.ChangeDutyCycle(3.5)
  RightMotor.ChangeDutyCycle(3.5)
  time.sleep(.5)
  LeftMotor.ChangeDutyCycle(3.5)
  RightMotor.ChangeDutyCycle(3.5)

  def BananaPeal
  #everyone spins out except user
  LeftMotor.ChangeDutyCycle(7.3)
  RightMotor.ChangeDutyCycle(7.3)
  LeftMotor.ChangeDutyCycle(12)
  RightMotor.ChangeDutyCycle(12)
  time.sleep(.5)

  def LightningStrike
  #lowers everyones speed by 50%
  #assume some input from labview
  LeftMotorSpeed = int(GETMOTOR1SPEED)
  RightMotorSpeed = int(GETMOTOR2SPEED)
  LeftMotor.ChangeDutyCycle(LeftMotorspeed/2)
  RightMotor.ChangeDutyCycle(RightMotorspeed/27.3)

  def OilSlick
  
