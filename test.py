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
device = "GC-CAN-USB-COM"
flash_map = [['0' for x in range(2)] for y in range(6)]
### class which details the specifics of each individual station programming
### threaded such that multiple Station instances can run simultaneously
arduino = serial.Serial("COM18", 9600, timeout = .1)
sleep(3)
class Station():
    def __init__(self, parent, com_, stat_num):
        self.thread = threading.Thread(target = self.process)
        self.station_num = stat_num
        self.parent = parent

        self.com = StringVar() #programming port
        self.com.set(com_[0])

        self.side = com_[1]

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
        mac_cmd = 'py -m esptool --port '+ self.com.get() +' read_mac'
        try:
            check_mac = subprocess.check_output(mac_cmd, shell=True, stderr=subprocess.STDOUT)
            check_mac = check_mac.decode("utf-8")
            for line in check_mac.split("\n"):
                if "MAC: " in line:
                    self.mac = line.split("MAC: ")[1]
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
                return 0
            else:
                addTextToLabel(self.explanation, "\nFailed Load")
                return 1
        except subprocess.CalledProcessError as check_load_error:
            check_load = str(check_load_error.output)
            return 1

    ### Organize and log status of each Station instance
    # TODO: log errors correctly with serial number for identification
    def log_run(self, flash, verify, comm):
        # Only log is some sort of upload was attempted
        if not flash:
            full_date = str(datetime.datetime.now())
            log_str = full_date + " " + self.sernum + " " + self.version + " " + device + " "
            # No Failures
            if(not flash and not verify and not comm):
                log_str += str(self.program.get()) + " " + str(self.verify.get()) + " " + str(self.communicate.get())
                log_filename = r"Log\success.txt"
            # Some form of failure
            else:
                log_str += "ERROR- "
                if flash:
                    log_str = ""
                if verify:
                    log_str += "Verification "
                if comm:
                    log_str += "Communication "
                log_filename = r"Log\fail.txt"
            log_str += "\n"
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
        self.mac_fail = self.runMACCommand()
        # Send message to arduino saying done
        arduino.write(self.side.encode())
        if not self.mac_fail:
            self.flash_fail = self.runFlashCommand()
        # stat.log_run(stat.flash_fail, stat.verify_fail, stat.test_fail)
        overallFail = self.flash_fail + self.mac_fail
        self.stopProgressBar(overallFail)
        # Update successful iterations
        if not overallFail:
            lock.acquire()
            loaded.set(loaded.get() + 1)
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
            p = line.split()
            # Add all COM ports associated with one device
            if "COM" in p[0]:
                port.append(p[0])
                port.append(p[1])
                devices.append(port)
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
        global loaded, devicesLoaded
        # self.communicationThread = threading.Thread(target = self.testMessages)
        # completeIndSend = IntVar()
        # completeIndSend.set(0)
        # completeIndSend.trace('w', self.updateComVar)

        loaded = IntVar()
        loaded.set(getNumDevicesLoaded())
        loaded.trace("w", updateDevicesLoaded)
        s = ttk.Style()
        s.theme_use('default')
        s.configure("red.Horizontal.TProgressbar", foreground='red', background='red')
        s.configure("green.Horizontal.TProgressbar", foreground='green', background='green')
        self.parent = parent
        self.parent.title("CAN-232 Programmer")
        self.stations = []
        # stations_with_com = []
        self.frame = tk.Frame(self.parent)
        self.configureMenu()
        self.titleLabel = tk.Label(self.frame, text = 'Details/Instructions', font = 10)
        self.instructions = tk.Label(self.frame, text = '- Programming stations \
are labelled with both COM ports listed in config.txt\n \
            - Click START to begin the upload', pady = 5)
        devices = getCOMPorts()
        # Size of window based on how many stations are present
        root_width = max(700, (len(devices) - 1) * 205)
        self.parent.geometry(str(root_width) + "x900+0+0")
        devicesLoaded = tk.Label(self.frame, text = ("Devices Loaded: " + str(loaded.get())).ljust(10), pady = 10)
        self.buttonFrame = tk.Frame(self.frame)
        self.clearCounter = tk.Button(self.buttonFrame, text = "Clear Counter", width = 15, bg = gridColor, height = 2, command = clearDevCounter)
        self.start = tk.Button(self.buttonFrame, text = "START", width = 22, bg = gridColor, height = 3, command = self.startUpload)
        # self.changePermissions = tk.Button(self.buttonFrame, text = "Switch Advanced/Production", command = changePermissions, width = 22, bg = gridColor, height = 2)
        # self.configureModeOptions()
        # self.configureDeviceOptions()
        self.configureFirmwareSelection()
        self.packObjects()
        # d[0] is common port; begin Station initalization at 1, passing in unique station id
        for d in range(0, len(devices)):
            self.stations.append(Station(root, devices[d], d))

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
        self.firmwareBox.select_set(0)
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
        self.setupFirmwareMap()
        for stat in self.stations:
            if not stat.thread.is_alive():
                stat.createNewThread()

### Instantiate the root window and start the Application
if __name__ == "__main__":
    root = tk.Tk()
    a1 = Application(root)
    root.mainloop()
