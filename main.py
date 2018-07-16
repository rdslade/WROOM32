import subprocess
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import IntVar, StringVar
from time import sleep
import serial
import sys
import os
import time
import datetime
import threading
from multiprocessing import Queue, Process
import re
from tkinter.filedialog import askopenfilename

### Helper function for reading serial words
def readSerialWord(ser_port):
    char = '0'
    response = ""
    # Continue reading word until not more chars
    while char != '':
        char = ser_port.read().decode()
        response += char
    return response

gridColor = "#20c0bb"
entryWidth = 8
num_coms = 1
baudrate = 115200
lock = threading.Lock()
flash_map = [['0' for x in range(2)] for y in range(6)]
### class which details the specifics of each individual station programming
### threaded such that multiple Station instances can run simultaneously
#arduino = serial.Serial("COM18", 9600, timeout = .1)
sleep(.5)
class Station():
    def __init__(self, parent, com_, stat_num):
        self.thread = threading.Thread(target = self.process)
        self.station_num = stat_num
        self.parent = parent

        self.com = StringVar() #programming port
        self.com.set(com_)

        self.frame = tk.Frame(self.parent)
        self.initComponents()
        self.packObjects()

    ### Creates the components associated with a single Station instance
    def initComponents(self):
        self.setup = tk.Frame(self.frame)
        self.prog = tk.Frame(self.setup)
        self.out = tk.Frame(self.setup)
        self.station_label = tk.Label(self.setup, text = self.com.get())

        self.statusSpace = tk.LabelFrame(self.frame, width = 200, height = 250)
        self.currentStatus = tk.Label(self.statusSpace, text = "", width = 25, pady = 10)
        self.progressBar = ttk.Progressbar(self.statusSpace, mode = 'determinate', length = 125)
        self.explanation = tk.Label(self.statusSpace, text = "", width = 25, pady = 10)
        self.startTime = 0;

    ### Loads objects into correct places
    def packObjects(self):
        self.prog.pack(pady = 5)
        self.out.pack()

        self.station_label.pack()

        self.setup.pack()
        self.statusSpace.pack()
        self.currentStatus.pack()
        self.progressBar.pack()
        self.explanation.pack()
        self.frame.pack(side = tk.LEFT, padx = 10)

    ### Checks device is accessible and retrieves MAC
    def runMACCommand(self):
        self.currentStatus.configure(text = "Checking MAC")
        mac_cmd = 'py -m esptool --port '+ self.com.get() +' --after no_reset --no-stub read_mac'
        try:
            check_mac = subprocess.check_output(mac_cmd, shell=True, stderr=subprocess.STDOUT)
            check_mac = check_mac.decode("utf-8")
            for line in check_mac.split("\n"):
                if "MAC: " in line:
                    self.mac = line.split("MAC: ")[1][:-1]
                    addTextToLabel(self.explanation, line)
                    return 0
        except subprocess.CalledProcessError as check_mac_error:
            addTextToLabel(self.explanation, "Unable to retrieve MAC")
            self.mac = ''
            return 1
    ## Get magic flash commands ready
    def runFlashCommand(self):
        global flash_map
        self.currentStatus.configure(text = "Loading firmware")
        flash_cmd = 'py -m esptool --port '+ self.com.get() +' --baud 1500000 write_flash --verify'
        for x in range(0,6):
            if flash_map[x][0] != 0:
                if flash_map[x][1] != 0:
                    flash_cmd = flash_cmd + ' ' + flash_map[x][0] + ' \"' + flash_map[x][1] + '\"'
        if flash_cmd == 'py -m esptool --port '+ self.com.get() +' --baud 1500000 write_flash  --verify':
            addTextToLabel(self.explanation, processID+'cfg.txt', 'Error With Firmware Map File')
            return
        try:
            check_load = subprocess.check_output(flash_cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
            numFilesToWrite = 0
            for file in flash_map:
                if file[1]:
                    numFilesToWrite += 1
            if check_load.count("OK") == 4:
                addTextToLabel(self.explanation, "\nSuccessful Load")
                addTextToLabel(self.explanation, "\nFinished in " + str(round((time.time() - self.startTime), 2)) + " sec")
                return 0
            else:
                addTextToLabel(self.explanation, "\nFailed Load")
                return 1
        except subprocess.CalledProcessError as check_load_error:
            check_load = str(check_load_error.output)
            return 1

    ### Organize and log status of each Station instance
    # TODO: log errors correctly with serial number for identification
    def log_run(self):
        # Only log is some sort of upload was attempted
        log_str = "|" + str(datetime.datetime.now()) + " " + str(self.mac) + " " + str(device.get())
        if self.flash_fail:
            log_str += "  FAIL  |\n"
            #log_filename = r"Log\fail.txt"
        else:
            log_str += " SUCCESS|\n"
            #log_filename = r"Log\success.txt"
        log_filename = r"Log\log.txt"
        with open(log_filename, 'a+',encoding='utf-8') as log:
            log.write(log_str)
            log.close()

    ### Stops and configures progress bar to correct style
    def stopProgressBar(self, fail):
        self.progressBar.stop()
        if not fail:
            self.progressBar.configure(value = 100, style = "green.Horizontal.TProgressbar")
        else:
            self.progressBar.configure(value = 100, style = "red.Horizontal.TProgressbar")

    ### Resets styles and progress of progress bar
    def restartProgressBar(self):
        self.progressBar.configure(value = 0, style = "Horizontal.TProgressbar")
        self.progressBar.start()

    ### Initiates each step of the entire programming process
    def process(self):
        self.restartProgressBar()
        self.explanation.configure(text = "")
        self.mac_fail = self.flash_fail = 0
        # Configre text files signifying programming ports
        # test = serial.Serial(self.com.get())
        # test.close()
        self.mac_fail = self.runMACCommand()
        # Send message to arduino saying done
        #arduino.write(self.side.encode())
        if not self.mac_fail:
            self.flash_fail = self.runFlashCommand()
            self.log_run()
        overallFail = self.flash_fail + self.mac_fail
        self.stopProgressBar(overallFail)
        # Update successful iterations
        if not overallFail:
            lock.acquire()
            loaded.set(getNumDevicesLoaded() + 1)
            lock.release()
            self.currentStatus.configure(text = "SUCCESS")
        else:
            self.currentStatus.configure(text = "FAIL")

    ### Restarts thread with new instantiation
    def createNewThread(self):
        self.thread = threading.Thread(target = self.process)
        self.thread.start()

### Reconfigures parameter label to append input text
def addTextToLabel(label, textToAdd):
    label.configure(text = label.cget("text") + textToAdd);

### Read COM ports from config file and returned organized lists of ports
def getCOMPorts():
    devices = []
    with open("cfg.txt", 'r+', encoding = 'utf-8') as cfg:
        cfg.readline()
        port = []
        for line in cfg.readlines():
            # Add all COM ports associated with one device
            if "COM" in line:
                devices.append(line.split('\n')[0])
    return devices

### Reads counter file and returns value in the file
def getNumDevicesLoaded():
    try:
        with open("device_counter.txt", 'r+', encoding = 'utf-8') as dev:
            ret = int(dev.readline())
            dev.close()
            return ret
    except IOError:
        with open("device_counter.txt", "w", encoding = 'utf-8') as file:
            file.write('0')
            file.close()
            return 0

### Resets device counter
def clearDevCounter():
    with open("device_counter.txt", 'w+', encoding = 'utf-8') as dev:
        dev.write('0')
        dev.close()
    loaded.set(0)

### Callback for updating IntVar variable represeting successful device programmings
def updateDevicesLoaded(*args):
    devicesLoaded.configure(text = ("Devices Loaded: " + str(loaded.get())).ljust(20))
    with open("device_counter.txt", 'w+', encoding = 'utf-8') as dev:
        dev.write(str(loaded.get()))
        dev.close()

### Read the issue COM port and display status of that port
def getCOMProblem(e, stat):
     #RegEx to find all instances between '...' e.g. for COM port
    com_problem = re.findall(r'(?<=\').*?(?=\')', str(e))[0]
    addTextToLabel(stat.explanation, "\nCould not open " + com_problem)
    return 1

### High level applications which includes all relevant pieces and instances of
### Station class and other widgets
class Application:
    def __init__(self, parent):
        global loaded, devicesLoaded, device
        # self.communicationThread = threading.Thread(target = self.testMessages)
        # completeIndSend = IntVar()
        # completeIndSend.set(0)
        # completeIndSend.trace('w', self.updateComVar)

        loaded = IntVar()
        loaded.set(getNumDevicesLoaded())
        loaded.trace("w", updateDevicesLoaded)
        device = StringVar()
        device.set(None)
        s = ttk.Style()
        s.theme_use('default')
        s.configure("red.Horizontal.TProgressbar", foreground='red', background='red')
        s.configure("green.Horizontal.TProgressbar", foreground='green', background='green')
        self.parent = parent
        self.parent.title("WROOM-xx Programmer")
        self.stations = []
        self.frame = tk.Frame(self.parent)
        self.configureMenu()
        self.titleLabel = tk.Label(self.frame, text = 'Details/Instructions', font = 10)
        self.instructions = tk.Label(self.frame, text = '- Programming stations \
are labelled with both COM ports listed in cfg.txt\n \
            - Click START to begin the upload', pady = 5)
        devices = getCOMPorts()
        semaphore = open("semaphore.txt", "w+", encoding = "utf-8")
        semaphore.write("write")
        semaphore.close()
        # Size of window based on how many stations are present
        root_width = max(300, (len(devices)) * 205)
        self.parent.geometry(str(root_width) + "x900+0+0")
        devicesLoaded = tk.Label(self.frame, text = ("Devices Loaded: " + str(loaded.get())).ljust(10), pady = 10)
        self.buttonFrame = tk.Frame(self.frame)
        self.clearCounter = tk.Button(self.buttonFrame, text = "Clear Counter", width = 15, bg = gridColor, height = 2, command = clearDevCounter)
        self.start = tk.Button(self.buttonFrame, text = "START", width = 22, bg = gridColor, height = 3, command = self.startUpload)
        # self.changePermissions = tk.Button(self.buttonFrame, text = "Switch Advanced/Production", command = changePermissions, width = 22, bg = gridColor, height = 2)
        # self.configureModeOptions()
        # self.configureDeviceOptions()
        self.configureFirmwareSelection()
        self.createDeviceOptions()
        self.packObjects()
        # d[0] is common port; begin Station initalization at 1, passing in unique station id
        for d in range(0, len(devices)):
            self.stations.append(Station(root, devices[d], d))

    def createDeviceOptions(self):
        self.deviceFrame = tk.Frame(self.frame)
        w02 = tk.Radiobutton(self.deviceFrame, text = "WROOM-02", variable = device, value = "WROOM-02")
        w32 = tk.Radiobutton(self.deviceFrame, text = "WROOM-32", variable = device, value = "WROOM-32")
        w02.pack()
        w32.pack()

    ### Places objects on screen in correct format
    def packObjects(self):
        self.frame.pack(side = tk.TOP)
        self.titleLabel.pack()
        self.instructions.pack()
        self.firmwareFrame.pack(side = tk.LEFT)
        self.clearCounter.pack(pady = 5)
        self.start.pack()
        self.buttonFrame.pack(side = tk.LEFT, padx = 20)
        devicesLoaded.pack(side = tk.RIGHT)
        self.deviceFrame.pack(side = tk.RIGHT, padx = 20)

    def configureFirmwareSelection(self):
        self.firmwareFrame = tk.Frame(self.frame)
        self.firmwareLabel = tk.Label(self.firmwareFrame, text = "Please select a firmware file: ")
        self.firmwareBox = tk.Listbox(self.firmwareFrame)
        firmware_directory_gone = 0
        try:
            check_firmware = subprocess.check_output('dir Firmware /b', shell=True)
            check_firmware = check_firmware.decode("utf-8")
            for line in check_firmware.split('\n'):
                if line != '':
                    if not 'template' in line:
                        self.firmwareBox.insert(tk.END,line)
        except subprocess.CalledProcessError as check_firmware_error:
            firmware_directory_make = subprocess.check_output("mkdir Firmware\\template", shell=True)
            with open('Firmware\\template\\map.txt', 'w',encoding='utf-8' ) as mapfile:
                mapfile.write('0x0 boot_v1.5.bin\n0x1000 user1.bin\n0x81000 user2.bin\n0x7e000 master_device_key.bin\n0x3fc000 esp_init_data_default.bin\n0x3fe000 blank.bin' )
            with open('Firmware\\template\\boot_v1.5.bin', 'w',encoding='utf-8' ) as boot:
                boot.close()
            with open('Firmware\\template\\user1.bin', 'w',encoding='utf-8' ) as u1:
                u1.close()
            with open('Firmware\\template\\user2.bin', 'w',encoding='utf-8' ) as u2:
                u2.close()
            with open('Firmware\\template\\master_device_key.bin', 'w',encoding='utf-8' ) as dk:
                dk.close()
            with open('Firmware\\template\\esp_init_data_default.bin', 'w',encoding='utf-8' ) as ind:
                ind.close()
            with open('Firmware\\template\\blank.bin', 'w',encoding='utf-8' ) as bln:
                bln.close()
            firmware_directory_gone = 1
        self.firmwareBox.selection_clear(0)
        self.firmwareLabel.pack()
        self.firmwareBox.pack()

    ### Create and "pack" menu for main root window
    def configureMenu(self):
        menubar = tk.Menu(self.parent)

        filemenu = tk.Menu(menubar, tearoff = 0)
        filemenu.add_command(label = "Open")
        filemenu.add_command(label = "Print")

        editmenu = tk.Menu(menubar, tearoff = 0)
        editmenu.add_command(label = "Undo")
        editmenu.add_command(label = "Redo")

        menubar.add_cascade(label = "File", menu = filemenu)
        menubar.add_cascade(label = "Edit", menu = editmenu)
        self.parent.configure(menu = menubar)

    def setupFirmwareMap(self):
        lbindex = self.firmwareBox.curselection()
        try:
            lbmessage = self.firmwareBox.get(lbindex)
        except TclError:
            print('TCL Error')
            return
        lbmessage=lbmessage[:-1]
        for y in range(0,2):
            for x in range (0,6):
                flash_map[x][y] = 0

        firmware_directory = 'Firmware/' + lbmessage + '/'
        map_file = 'Firmware/' + lbmessage + '/map.txt'
        try:
            with open(map_file, 'r',encoding='utf-8' ) as mp:
                linenum = 0
                for line in mp.readlines():
                    if '0x' in line:
                        if linenum < 6:
                            splitline = line.split(' ')
                            flash_map[linenum][0] = splitline[0]
                            flash_map[linenum][1] = 'Firmware/' + lbmessage + '/' + splitline[1]
                            flash_map[linenum][0] = flash_map[linenum][0].rstrip()
                            flash_map[linenum][1] = flash_map[linenum][1].rstrip()
                            linenum=linenum+1
        except IOError:
            messagebox.showinfo('map.txt', 'Can\'t Read Firmware Map File')
            return

    ### Trigger function for START button which begins/continues each Station thread
    def startUpload(self):
        if self.checkSelections():
            self.setupFirmwareMap()
            #arduino.write("N".encode())
            for stat in self.stations:
                stat.startTime = time.time()
                if not stat.thread.is_alive():
                    stat.createNewThread()

    ### Function to make sure all necessary selections are made
    def checkSelections(self):
        firmwareMessage = "\nPlease select firmware to be loaded"
        deviceMessage = "\nPlease select a device type"
        firmwareSuccess = len(self.firmwareBox.curselection())
        deviceSuccess = device.get() != "None"
        if firmwareSuccess and deviceSuccess:
            return True
        else:
            message = ""
            if not firmwareSuccess:
                message += firmwareMessage
            if not deviceSuccess:
                message += deviceMessage
            messagebox.showinfo("Error", message)


### Instantiate the root window and start the Application
if __name__ == "__main__":
    root = tk.Tk()
    a1 = Application(root)
    root.mainloop()
