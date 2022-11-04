from picamera import PiCamera
from time import sleep
from datetime import datetime
import boto3
import RPi.GPIO as GPIO
import os
import curses
import pyaudio
import wave
import getpass
import sys
import ST7789 as ST7789
from PIL import Image
from PIL import ImageColor
from PIL import ImageDraw

swPin=14

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(swPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

ACCESS_KEY = 'Access Key ID'
SECRET_KEY = 'Access Key Password'

oldSw=0
newSw=0

FORMAT=pyaudio.paInt16

RATE=44100
CHUNK=262144
SAMPLE_SIZE=1
RECORD_SECONDS=7
CHANNELS=1

screen = curses.initscr()
curses.noecho()
curses.cbreak()
curses.halfdelay(3)

screen.keypad(True)

camera = PiCamera()
camera.resolution = (2592, 1944)
camera.rotation = 85

image_file1 = "manual-text.jpg"
image_file2 = "complete upload.jpg"
display_type="square"

dc=24
rst=25
bl=27

disp=ST7789.ST7789(port=0, cs=ST7789.BG_SPI_CS_FRONT, dc=dc, rst=rst, 
                   backlight=bl, mode=3,
                   spi_speed_hz=80*1000*1000)

WIDTH=disp.width
HEIGHT=disp.height

def manual():
    #upload manual
    disp.begin()
    
    print('Loading image...'.format(image_file1))
    
    image1=Image.open(image_file1)
    image1=image1.resize((WIDTH, HEIGHT))
    
    print('Showing manual...')
    
    disp.display(image1)


def detectusus():
    username=getpass.getuser()
    curtime = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    #take picture
    camera.start_preview()
    sleep(0.2)
    savephotofile = '/home/cth/cth_python/'+ username + '-' + curtime + '.jpg'
    camera.capture(savephotofile) 
    camera.stop_preview()
    
    #record location
    p=pyaudio.PyAudio()
    
    stream=p.open(format=FORMAT,
                         channels=CHANNELS,
                         rate=RATE, 
                         input=True,
                         frames_per_buffer=CHUNK)
    
    print("Start to record the audio." )

    frames=[]
    
    now=datetime.now()
    
    for i in range(0, int(RATE/CHUNK*RECORD_SECONDS)):
        data=stream.read(CHUNK)
        frames.append(data)
        
    print("Recording is finished. ")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    savaudiofile='/home/cth/cth_python/' + username + '-' + curtime + '.wav'
    
    wf=wave.open(savaudiofile, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b' ' .join(frames))
    wf.close()
    
    cliname= username+ '-' + curtime
    
    #upload success message
    disp.begin()
    image2=Image.open(image_file2)
    image2=image2.resize((WIDTH, HEIGHT))
    disp.display(image2)
    
    sleep(3)
    
    #upload picture
    image3=Image.open(savephotofile)
    image3=image3.resize((WIDTH, HEIGHT))
    disp.display(image3)
    
    sleep(4)
    
    #upload to AWS S3
    client = boto3.client('s3',
                      aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)
    client.upload_file(savephotofile,'detectus-image', cliname +'.jpg')
    client.upload_file(savaudiofile,'detectus', cliname +'.wav')
 
    print('Done')

try:
    while True:
        newSw=GPIO.input(swPin)
        if newSw !=oldSw:
            manual()
            oldSw=newSw
            
            
            if newSw==1:
                now=datetime.now()
                detectusus()
            sleep(0.2)

except KeyboardInterrupt:
    pass

    GPIO.cleanup()
    camera.close()
    curses.nocbreak()
    screen.keypad(0)
    curses.echo()
    curses.endwin()
