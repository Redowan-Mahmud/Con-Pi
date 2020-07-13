from flask import *
import json
#PiJuice
from pijuice import PiJuice
#PiCamera
from picamera import PiCamera
from picamera.array import PiRGBArray
#thread
import requests
import threading
#GPIO
import RPi.GPIO as GPIO

import logging
import time

app = Flask(__name__)

@app.route('/battery')
def batteryFunc():
    global logger
    logger.info('Battery: service requested')
    pijuice = PiJuice(1,0x14)
    charge = pijuice.status.GetChargeLevel()
    return str(charge['data'])

@app.route('/check')
def remoteCheckFunc():
    global addressSet
    global lock
    with lock:
        remoteConnections = addressSet.copy()
    return str(remoteConnections)
    
@app.route('/camera')
def cameraFunc():
    global logger
    logger.info('Camera: service requested')
    global lock
    with lock:
        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.capture("/home/pi/image.jpg")
        camera.close()
    return send_file("/home/pi/image.jpg")
    
@app.route('/gpioAc', methods=['POST'])
def gpioAcFunc():
    
    logger.info('Actuation: service requested')
    
    content = request.json
    GPIO.setup(int(content['repeller']), GPIO.OUT)
    time.sleep(15)
    GPIO.setup(int(content['repeller']), GPIO.IN)
    return 'success'

@app.route('/subscribe', methods=['POST'])
def subscribeFunc():

    global addressSet
    global lock
    global logger
    content = request.json
    address = content['dockerIP']+":"+str(content['dockerPort'])
    
    logger.info('Subscribe: request from '+str(address))
    
    with lock:
        addressSet.add(address)
        
    return 'success'

@app.route('/unsubscribe', methods=['POST'])
def unsubscribeFunc():

    global addressSet
    global lock
    global logger
    content = request.json
    address = content['dockerIP']+":"+str(content['dockerPort'])
    
    logger.info('Unsubscribe: request from '+str(address))
    
    with lock:
        addressSet.discard(address)
        
    return 'success'
    
def MOTION(pir):
    global lock
    global logger
    print("Motion Detected")

    with lock:
        logger.info('Motion: copying addresses')
        tempAddressSet = addressSet.copy()
    for address in tempAddressSet:
        try:
            url = 'http://'+address+'/motion'
            data = {'motion': 'True'}
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            r = requests.post(url, data=json.dumps(data), headers=headers,timeout=1)
            logger.info('Motion: sending motion data to '+str(address))
            time.sleep(0.7)
        except requests.exceptions.RequestException as e:
            print("error")
            logger.info('Motion: error occured '+str(e))

def checkWithMotion(pir):
    global logger
    logger.info('Motion: service started')
    print("Motion Called")
    try:
        GPIO.add_event_detect(pir, GPIO.RISING, callback=MOTION)
        while 1:
            print("Motion: Called inside loop")
            time.sleep(100)
    except KeyboardInterrupt:
        logger.info('Motion: Quit')

            

if __name__ == '__main__':
    
    # logger modue
    
    logger = logging.getLogger('dev')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    fileHandler = logging.FileHandler('PiService.log')
    fileHandler.setFormatter(formatter)
    fileHandler.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    consoleHandler.setLevel(logging.INFO)

    logger.addHandler(fileHandler)
    logger.addHandler(consoleHandler)

    addressSet = set()
    
    GPIO.setmode(GPIO.BCM)
    pir = 16
    GPIO.setup(pir, GPIO.IN)
    
    lock = threading.Lock()

    thread1 = threading.Thread(target = checkWithMotion, args = (pir,))
    thread1.start()
    
    app.run(host= '0.0.0.0',port='5000')
