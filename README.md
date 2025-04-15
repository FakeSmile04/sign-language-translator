# sign-language-translator
AI-based Sign Language Translator Using Electromyography

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
