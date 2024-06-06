from time import sleep
import datetime
from picamera import PiCamera

camera = PiCamera()
camera.resolution=(1024,768)
camera.start_preview()
sleep(2)

while True:
  camera.capture("picture_test.jpg" + str(datetime.time))
  sleep(3)
