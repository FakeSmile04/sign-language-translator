# sign-language-translator
AI-based Sign Language Translator Using Electromyography

## Version 0.5
- Now uses Mosquitto as the MQTT broker (Mosquitto is required to run the program)
- Uploaded latest version of the Arduino Sketch that now has config mode using simple webpage in AP
- Uploaded Flutter Project Directory pertaining to mobile interface
- Uploaded stable release .apk file of the mobile interface for Android phones

Notes:
- Python backend isn't finalised yet
- PCB sketch project files and other related files aren't uploaded yet

## Version 0.2
- Implemented MQTT as the method of sending data from ESP32 to app.py
- Removed codes related to serial method
- Uploaded an updated version of Arduino sketch installed in ESP32 for EMG data collection
- Added basic stylings for the webpage to make it looks nicer
- Cleaned out the file strcture of the whole repository

Notes:
- WiFi credentials are in the sketch and has to be reuploaded to ESP32 each time it is used
- ESP32 and the PC doesn't need to be in same network in theory, not tried yet

Future Plans:
- Implement a better ML model for sign prediction
- Test the program with new sensor circuit setup

## Version 0.1.2
- Added AI prediction model and TTS capability on the Websocket version
- Recommended to use Chrome to run index.html

Issues and Future Plans:
- Implement port fowarding so it can be used online (to port 8000)
- Look into possibility on making the output as close to real-time as possible
- Test the program with proper EMG sensors once worked

## Version 0.1.1

- Added another version of the program that doesn't use XAMPP, instead serves the webpage directly from Python due to issues implementing WebSocket in XAMPP environment
- Tested out some basic TTS functionalities to read out the page's **header**

Issues and Future Plans:
- The values presented on the webpage aren't still in real time
- Implement AI model to read the signals and translate it into words
- Expand TTS functionality to read the words

## Version 0.1

Developed on XAMPP Local Web Server

Notes:
- data.json and homepage.php has to be put inside the htdocs folder in XAMPP's directory
- The ESP32 Microcontroller is connected to the PC on port COM9 with appropiate driver (port used can be changed in bridge.py)

Current Progress:
The program is now able to read signals from the EMG sensor, process it and sends it to a webpage to display the result

Current Issues:
The display values aren't in real-time

Future Plans:
- Move to WebSocket Server for real-time value display
- Add AI TTS to read what's on the webpage
- Implement AI model to read the signals and translate it into words
