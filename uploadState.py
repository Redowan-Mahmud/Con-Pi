#pip3 install boto3
#pip3 install configparser
import urllib.request
import time
from datetime import datetime
import psutil
import os
import boto3
from botocore.exceptions import NoCredentialsError
import configparser
import docker
import logging



def upload_to_aws(local_file):

    session = boto3.Session(
    aws_access_key_id=accessKey,
    aws_secret_access_key=secretKey,
    aws_session_token=sessionKey,)
    s3 = session.client('s3')
    
    try:
        s3.upload_file(local_file, bucketName, local_file)
        return True
    except Exception as e:
        logger.info(e)
        return False

global logger
logger = logging.getLogger('dev')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

fileHandler = logging.FileHandler('uploadState.log')
fileHandler.setFormatter(formatter)
fileHandler.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
consoleHandler.setLevel(logging.INFO)

logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)

try:
    logger.info('UploadState: Started')
    link = "http://127.0.0.1:5000/battery"
    config = configparser.ConfigParser()
    logger.info('UploadState: Reading AWS Key file')
    config.read_file(open(r'AWS_Keys.txt'))
    accessKey = config.get('default', 'aws_access_key_id')
    secretKey = config.get('default', 'aws_secret_access_key')
    sessionKey = config.get('default', 'aws_session_token')
    bucketName = 'disnetlab-bird'
    client = docker.from_env()

    while True:
        #logger.info('UploadState: Loop')
        try:
            urlData = urllib.request.urlopen(link)
            batteryLevel = int(urlData.read())
            cpuLevel = str(psutil.cpu_percent());
            psutil.virtual_memory()
            ip = os.popen('ip addr show wlan0').read().split("inet ")[1].split("/")[0]
            now = datetime.now()
            current_time = now.strftime("%d%m%Y-%H%M%S")
            fileExtension = ".csv"
            fileName = "Data-"+ip+fileExtension
            file = open(fileName, "a")
            dockerCount = len(client.containers.list(all=True))
            file.write(current_time+",B-"+str(batteryLevel)+",C-"+str(cpuLevel)+",M-"+str(psutil.virtual_memory()[2])+",D-"+str(dockerCount)+'\n')
            file.close()
    
            success = upload_to_aws(fileName)
            logger.info('UploadState: '+ fileName+' is uploaded to s3 successfully.')
            time.sleep(120)
            #if(batteryLevel<15):
                #    break
            #if success:
                #os.remove(fileName)
            #time.sleep(60)
        except KeyboardInterrupt:
            raise
            break
        except Exception as e:
            logger.info(e)
            time.sleep(120)
except KeyboardInterrupt:
    logger.info('Terminated by keyboard intrupt')        
except Exception as e:
    logger.info(e)
    logger.info('UploadState: terminated.')
            
