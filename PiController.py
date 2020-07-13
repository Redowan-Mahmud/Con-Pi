import netifaces as ni
import nmap
import ipaddress
import urllib.request
import requests
import json
import subprocess
import threading
from flask import *
import os
import time
import logging
import docker
import configparser


app = Flask(__name__)

@app.route('/test')
def test():
    return 'controller is working'

@app.route('/stopDocker', methods=['POST'])
def stopDocker():
    global ipDockerNameBind
    global ipDockerPortBind
    global client
    global logger
    
    content = request.json
    serviceIP = content['serviceIP']
    containerName = ipDockerNameBind[serviceIP]
    container = client.containers.get(containerName)
    container.kill()
    container = client.containers.get(containerName)
    
    ni.ifaddresses('wlan0')
    dockerExternalIP = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    
    logger.info('StopDocker: docker address='+str(dockerExternalIP)+':'+str(ipDockerPortBind[serviceIP])+', service address='+str(serviceIP)+':'+str(servicePort))
    
    if container.status == "removing":
        url = "http://"+serviceIP+":"+str(servicePort)+"/unsubscribe"
        data = {'dockerIP':dockerExternalIP,'dockerPort':ipDockerPortBind[serviceIP]}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        r = requests.post(url, data=json.dumps(data), headers=headers)
        return 'Success'
    else:
        return 'Fail'
        
    
    
    

@app.route('/startDocker', methods=['POST'])
def startDocker():
    global startingPortforDocker
    global offsetOfDockerPort
    global ipDockerNameBind
    global ipDockerPortBind
    global logger
    
    global client
    
    content = request.json
    dockerPort = -1 
    
    if offsetOfDockerPort==0:
        dockerPort = startingPortforDocker
        offsetOfDockerPort = offsetOfDockerPort+1
    else:
        dockerPort = startingPortforDocker+offsetOfDockerPort
        
    ni.ifaddresses('wlan0')
    dockerExternalIP = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    
    serviceIP = content['serviceIP']
    servicePort = content['servicePort']
    imageName = content['image']
    requestedServices = content['piServices']
    
    envVariables={"dockerIP":dockerExternalIP,"dockerPort":dockerPort,"serviceIP":serviceIP,"servicePort":servicePort,"accessKey":config.get('default', 'aws_access_key_id'),"secretKey":config.get('default', 'aws_secret_access_key'),"sessionKey":config.get('default', 'aws_session_token'),"bucketName":'disnetlab-bird'}
    
    containerName = str(int(time.time())) 
    
    container = None
    
    try:
        container = client.containers.run(image=imageName,network='host',detach=True, remove=True,environment=envVariables,name=containerName)
    except:
        logger.info('StartDocker:'+ str(docker.errors.ContainerError))

    logger.info('StartDocker: docker address='+str(dockerExternalIP)+':'+str(dockerPort)+', service address='+str(serviceIP)+':'+str(servicePort))
    
    if container.status == "created":
        if "motion" in requestedServices:
            url = "http://"+serviceIP+":"+str(servicePort)+"/subscribe"
            data = {'dockerIP':dockerExternalIP,'dockerPort':dockerPort}
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            r = requests.post(url, data=json.dumps(data), headers=headers)
            ipDockerNameBind[serviceIP] = containerName
            ipDockerPortBind[serviceIP] = dockerPort 
            return 'Success'
        else:
            return 'Fail'
    else:
        return 'Fail'
        

    


def flaskThread():
    global controllerPort
    app.run(host= '0.0.0.0',port=controllerPort)
    
def getBatteryOfPIs(IpAddress,ServicePort):
    print("Battery Check "+IpAddress)
    batteryLevel = None
    for x in range(3):
        try:
            batteryServiceAddress = "http://"+IpAddress+":"+str(ServicePort)+"/battery"
            batteryData = urllib.request.urlopen(batteryServiceAddress)
            batteryLevel = batteryData.read()
            if batteryLevel != None:
                break
            time.sleep(3)
        except requests.exceptions.RequestException as e:
            print("Not found battery level")
    return batteryLevel

def requestDockerStart(ControllerIP,ControllerPort,RequesterIp,RequesterServPort,DockerImageName,ReqestedPiService):
    global logger
    
    logger.info('RequestStartDocker: '+str(RequesterIp)+' is requesting '+str(ControllerIP)+' to start a docker')
    dockerStartUrl = "http://"+ControllerIP+":"+str(ControllerPort)+"/startDocker"
    dockerStartData = {'serviceIP':RequesterIp,'servicePort':RequesterServPort,'image':DockerImageName,'piServices':ReqestedPiService}
    dockerStartHeaders = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    responseDockerStart = requests.post(dockerStartUrl, data=json.dumps(dockerStartData), headers=dockerStartHeaders)
    if responseDockerStart.text=='Success':
        return True
    else:
        return False

def checkRemoteExecutions(IpAddress,ServicePort):
    checkingAddress = "http://"+IpAddress+":"+str(ServicePort)+"/check"
    checkData = urllib.request.urlopen(checkingAddress)
    isRemoteExecutionWorking = checkData.read()
    return str(isRemoteExecutionWorking)

def requestDockerStop(ControllerIP,ControllerPort,RequesterIp):
    global logger
    
    logger.info('RequestStartDocker: '+str(RequesterIp)+' is requesting '+str(ControllerIP)+' to stop a docker')
    
    dockerStopUrl = "http://"+ControllerIP+":"+str(ControllerPort)+"/stopDocker"
    dockerStopData = {'serviceIP':RequesterIp}
    dockerStopHeaders = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    responseDockerStop = requests.post(dockerStopUrl, data=json.dumps(dockerStopData), headers=dockerStopHeaders)
    if responseDockerStop.text=='Success':
        return True
    else:
        return False
    

def checkNeighbours():

    global servicePort
    global logger
    
    neighbours = set()
    ni.ifaddresses('wlan0')
    ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    netmask = ni.ifaddresses('wlan0')[ni.AF_INET][0]['netmask']
    gateway = ni.gateways()['default'][ni.AF_INET][0]
    #print("IP            "+ip)
    #print("Netaask       "+netmask)
    #print("Gateway IP    "+gateway)
    
    # cidr e.g. 192.168.43.0/24
    net = str(ipaddress.ip_network(ip+"/"+netmask,strict=False))
    #print("Subnet        "+net)

    # getting all ip addresses in the subnet
    nm = nmap.PortScanner()
    nm.scan(hosts=net, arguments='-sn -sP -PE -PA21,23,80,3389')
    hosts_list = [(x, nm[x]['status']['state']) for x in nm.all_hosts()]
    for host, status in hosts_list:
        if status=='up' and host!=gateway and host!=ip:
            #print("Other IPs     "+host)
            try:
                if urllib.request.urlopen("http://"+host+":"+str(servicePort)+"/battery").getcode()==200:
                    logger.info('Neighbour:'+ str(host)+' is active')
                    neighbours.add(host)
            except:
                logger.info('Neighbour:'+ str(host)+' is down')
                
    return neighbours


if __name__ == "__main__":
    
    # logger modue
    
    logger = logging.getLogger('dev')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    fileHandler = logging.FileHandler('PiController.log')
    fileHandler.setFormatter(formatter)
    fileHandler.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    consoleHandler.setLevel(logging.INFO)

    logger.addHandler(fileHandler)
    logger.addHandler(consoleHandler)
    
    time.sleep(2)
    
    
    config = configparser.ConfigParser()
    config.readfp(open(r'AWS_Keys.txt'))
    
    controllerPort=8000
    servicePort=5000
    startingPortforDocker=7000
    offsetOfDockerPort=0
    imageName="bird_v02"
    
    ipDockerNameBind = {}
    ipDockerPortBind = {}
    
    client = docker.from_env()
    
    ni.ifaddresses('wlan0')
    externalIP = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
    #localIP = "127.0.0.1"

    
    localDockerStatus=0
    remoteDockerStatus=0
    selectedRemotePi=None
    
    
    time.sleep(3)
    thread1 = threading.Thread(target = flaskThread, args = ())
    thread1.start()
    time.sleep(5)
    logger.info('Controller: Initializing')
        
    while True:
        
        offload = os.getenv('OFFLOAD')
        if offload == None or offload=='0': #offload is not set or set as False 
            if localDockerStatus==0: #local docker is not executing
                serviceList=["motion"]
                responseData = requestDockerStart(externalIP,controllerPort,externalIP,servicePort,imageName,serviceList) #creating docker locally
                if responseData==True:
                    logger.info('Controller: docker is running')
                    localDockerStatus=1
                else:
                    logger.info('Controller: docker creation in failed')
            else: #local docker is executing
                logger.info('Controller: docker is running locally')
        
        
        else: #offload is set 
            localBatteryLevel=getBatteryOfPIs(externalIP,servicePort)
            if localBatteryLevel != None: # Service is responding
                if int(localBatteryLevel) > 50: # Battery is high
                    if localDockerStatus==0 and remoteDockerStatus==0: # no local and remote docker has been running
                        serviceList=["motion"]
                        responseData = requestDockerStart(externalIP,controllerPort,externalIP,servicePort,imageName,serviceList) #creating local docker
                        if responseData==True:
                            logger.info('Controller: local docker is running')
                            localDockerStatus=1 #local docker is running
                        else:
                            logger.info('Controller: local docker creation failed')
                    elif localDockerStatus==0 and remoteDockerStatus==1 and int(localBatteryLevel) > 60: # no local docker, but remote docker and battery gets higher
                        responseData1 = requestDockerStop(selectedRemotePi,controllerPort,externalIP)
                        responseData = requestDockerStart(externalIP,controllerPort,externalIP,servicePort,imageName,serviceList)
                        remoteDockerStatus==0 # stop remote docker. 
                        localDockerStatus=1 #local docker is running
            
                else: # Battery is low
                    if remoteDockerStatus==0: # No remote docker, want to create
                        neighbourPIs = checkNeighbours() 
                        for PI in neighbourPIs:
                            print(PI)
                            remoteBatteryLevel = getBatteryOfPIs(PI,servicePort)
                            if remoteBatteryLevel != None and int(remoteBatteryLevel)>70: # trying to find a RPi with even higher battery level
                                selectedRemotePi = PI # selecteing as a offloading destination
                                logger.info('Controller: '+str(selectedRemotePi)+' is selected for docker exectuion')
                                break
                        if selectedRemotePi == None and localDockerStatus==0: # not found offloading destination and local docker is not running
                            serviceList=["motion"]
                            responseData = requestDockerStart(externalIP,controllerPort,externalIP,servicePort,imageName,serviceList) # creating the docker locally. 
                            if responseData==True:
                                logger.info('Controller: local docker is running')
                                localDockerStatus=1 # local docker is running. 
                       
                        elif selectedRemotePi != None: # suitable doffloading estination has been found
                                
                            serviceList=["motion"]
                            responseData = requestDockerStart(selectedRemotePi,controllerPort,externalIP,servicePort,imageName,serviceList) #create local remotely
                            if responseData==True:
                                logger.info('Controller: remote docker is running')
                                remoteDockerStatus=1 # remote docker running
                                for key in ipDockerNameBind:
                                    print(key)
                                    responseData1 = requestDockerStop(externalIP,controllerPort,key) # stop all local docker. 
                                    localDockerStatus==0 # local docker is not running
                                logger.info('Controller: terminated all locally run docker')
                            else:
                                logger.info('Controller: remote docker creation failed')
                            time.sleep(30)     
            
                if remoteDockerStatus==1:
                    responseData2 = checkRemoteExecutions(externalIP,servicePort)
                    if str(selectedRemotePi) in responseData2:
                        logger.info('Controller: '+str(selectedRemotePi)+' is running the docker remotely')
                    else:
                        remoteDockerStatus=0
                    
            else: #service is not responding
               logger.info('Controller: PiService is not responding')
               logger.info('Controller: Program finishing...')
               break
                
        
        
        time.sleep(30)
