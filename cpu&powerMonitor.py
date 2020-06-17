import urllib.request
import time
from datetime import datetime
import psutil

link = "http://127.0.0.1:5000/battery"
timeCounter = 0;

while True:
    
    urlData = urllib.request.urlopen(link)
    batteryLevel = int(urlData.read())
    cpuLevel = str(psutil.cpu_percent());
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    file = open("cpu&powerStatus.txt", "a")
    file.write(current_time+" B-"+str(batteryLevel)+" C-"+cpuLevel+'\n')
    file.close()
    timeCounter = timeCounter+10;
    print(current_time+" B-"+str(batteryLevel)+" C-"+cpuLevel+'\n')
    if(batteryLevel<15):
        break
    time.sleep(5)





