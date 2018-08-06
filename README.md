# WROOM_Flash
A tool for flashing ESP32 and ESP8266 chips

## Installation
### Using git clone
```
$ git clone https://github.com/rdslade/WROOM_Flash
$ cd WROOM_Flash
```
### Using downloads
1. Download WROOM_Flash.zip
2. Unzip or open the file in the desired location

## How to use
This program relies on the Espressif [esptool](https://github.com/espressif/esptool) command line interface for working with ESP chips in bootloader mode. If there are any questions about the module itself or the configuration of the bootloader circuit, reference the link above.

This program requires the chip to be placed into bootloader mode as specified by [this section](https://github.com/espressif/esptool#entering-the-bootloader) in the Espressif documentation.

### Layout of the Firmware directory
All firmware that needs to be loaded is located in seperate directories within the `Firmware` directory. In each folder, each individual binary file needs to be placed along with a text file named `map.txt`. This text file specifies where in flash each binary file should be loaded and the format of the file is crucial to the flash working. Below is an example of a `map.txt` file.
> ESP8266-v1.6.1 Firmware map.txt
```
0x0 boot_v1.7.bin
0x1000 user1.2048.new.5.bin
0x1fc000 esp_init_data_default_v08.bin
0xfe000 blank.bin
```

### Layout of prodCfg directory and the main function
There are multiple text files in the ```prodCfg/``` directory which speicify which COM ports are used for programming. For production purposes, there are two such text files each specifying 4 COM ports. The `main` function in `main.py` instantiates two different windows using the two seperate text files for initialization. This `main` function can be edited to only open one window or whatever configuration is needed.

### Run program
There are two modes in which this program can run: production and normal.

#### Production Mode

In production mode, many of the options are removed from the user such as the firmware choice. This is meant to reduce accidental selection of unwanted configurations. In order to run in production mode, perform the following with the correct set up described in the `prodCfg` directory.

```
py main.py prod
```

This will initialize two windows with minimal options. Each 'station' should be populated with the COM ports listed in the `prodCfg` directory.

#### Normal mode

Normal mode has a similar set up to production mode, except the graphics window will have more configuration options available at run time. The configuration comes from the same location as listed above. 

```
py main.py
```

Notice that no command line arguments are needed to run in normal mode.

### Start the flash
Starting the programming of the module is done with the use of an external COM port. In this case, the COM port is connected to the button on the Espressif fixture. The button press (lowering handle on fixture) signals the start of the program.

This feature can be easily changed and will be configurable by the user in the next release. For the time being, if manual START button is wanted/needed, please contact the creator.
