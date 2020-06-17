from flask import *
import json
import numpy as np
import argparse
import os
import time
import cv2
import ConfigParser
import urllib                                                        
import thread
import logging
import requests
import boto3
from botocore.exceptions import NoCredentialsError



app = Flask(__name__)

@app.route('/motion', methods=['POST'])
def motion():
    global motionStatus
    if motionStatus == 0:
        print("Motion is detected")
        content = request.json
        motionStatus = 1
    return 'Success' 


def flaskThread():
    global dockerPort
    app.run(host= '0.0.0.0',port=dockerPort)
    
def upload_to_aws(local_file, bucket, s3_file):

    session = boto3.Session(
    aws_access_key_id=accessKey,
    aws_secret_access_key=secretKey,
    aws_session_token=sessionKey,)
    s3 = session.client('s3')
    
    try:
        s3.upload_file(local_file, bucket, s3_file)
        return True
    except Exception as e:
        return False


def checkWithRelay(objectList):
    relay_pin = int(config.get('birdRepellent', 'relay_pin'))
    #print objectList
    global frameCounter
    global detectorFlag
    global serviceIP
    global servicePort
    print objectList
    if ("bird" in objectList):
        print ("Detect : Bird")
        print ("Activate : Repeller")
        url = "http://"+serviceIP+":"+str(servicePort)+"/gpioAc"
        data = {'repeller': relay_pin}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        r = requests.post(url, data=json.dumps(data), headers=headers)
        #time.sleep(int(config.get('birdRepellent', 'actuator_runtime')))
        frameCounter = 0
        return 1
    else:
        frameCounter = frameCounter+1
        return 0

def startCamera():
    # initialize the camera and grab a reference to the raw camera capture
    # capture streams from the camera
    
    global detectorCount
    global serviceIP
    global servicePort
    
    print("Activate : Camera")
    
    while True:
        start = time.time()
        # grab the raw NumPy array representing the image, then initialize the timestamp
        # and occupied/unoccupied text
        objectList = [];
        
        url = "http://"+serviceIP+":"+str(servicePort)+"/camera"
        print(url)
        url_response = urllib.urlopen(url)
    
        img_array = np.array(bytearray(url_response.read()), dtype=np.uint8)
    
        frame = cv2.imdecode(img_array, -1)
    

        # grab the frame dimensions and convert it to a blob
        (h, w) = frame.shape[:2]

        
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (int(config.get('birdRepellent', 'blob_width')), int(config.get('birdRepellent', 'blob_hight')))),
            0.007843, (int(config.get('birdRepellent', 'blob_width')), int(config.get('birdRepellent', 'blob_hight'))), 127.5)

        # pass the blob through the network and obtain the detections and
        # predictions
        net.setInput(blob)
        
        
        detections = net.forward()
        

        # loop over the detections
        for i in np.arange(0, detections.shape[2]):
            # extract the confidence (i.e., probability) associated with
            # the prediction
            confidence = detections[0, 0, i, 2]

            # filter out weak detections by ensuring the `confidence` is
            # greater than the minimum confidence
            if confidence > 0.2:
                # extract the index of the class label from the
                # `detections`, then compute the (x, y)-coordinates of
                # the bounding box for the object
                idx = int(detections[0, 0, i, 1])
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                # draw the prediction on the frame
                label = "{}: {:.2f}%".format(CLASSES[idx],
                    confidence * 100)

                objectList.append(CLASSES[idx])
                
                cv2.rectangle(frame, (startX, startY), (endX, endY),
                    COLORS[idx], 2)
                y = startY - 15 if startY - 15 > 15 else startY + 15
                cv2.putText(frame, label, (startX, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)

        end = time.time()

        
        print("[INFO] Capture and Analysis took {:.6f} seconds".format(end - start))
        
        detectorFlag = checkWithRelay(objectList)
        
        if detectorFlag == 1:
            outpath = str(detectorCount)+".jpg"
            cv2.imwrite(outpath, frame)
            detectorCount = detectorCount + 1
            if bucketName!="x":
                destName = str(int(time.time()))+".jpg"
                upload_to_aws(outpath, bucketName, destName)
        
        
        # if the `q` key was pressed, break from the loop
        
        if frameCounter == int(config.get('birdRepellent', 'camera_runtime')):
            #cv2.destroyWindow("Stream")
            print("Close : Camera")
            break
        
        #if key == ord("q"):
            #break




if __name__ == "__main__":
    
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    motionStatus = 0;
    
    dockerIP = os.environ['dockerIP']
    dockerPort = os.environ['dockerPort']
    serviceIP = os.environ['serviceIP']
    servicePort = os.environ['servicePort']
    accessKey = os.environ['accessKey']
    secretKey = os.environ['secretKey']
    sessionKey = os.environ['sessionKey']
    bucketName = os.environ['bucketName']


    thread.start_new_thread(flaskThread,())

    frameCounter = 0
    detectorCount = 0
    
    

    #reading configuration files

    config = ConfigParser.ConfigParser()
    config.readfp(open(r'appConfig.txt'))

# initialize the list of class labels MobileNet SSD was trained to
# detect, then generate a set of bounding box colors for each class

    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
        "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
        "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
        "sofa", "train", "tvmonitor"]
    COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))

    # load our serialized model from disk
    #print("[INFO] loading model...")
    net = cv2.dnn.readNetFromCaffe('MobileNetSSD_deploy.prototxt.txt', 'MobileNetSSD_deploy.caffemodel')
    
    time.sleep(2)
    
    
    while True:
        if motionStatus == 1:
            startCamera()
            motionStatus = 0
            frameCounter = 0
        if detectorCount > int(config.get('birdRepellent', 'saved_image_number')) :
            detectorCount = 0



