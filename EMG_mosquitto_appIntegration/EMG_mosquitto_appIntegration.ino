#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h> 
#include <Adafruit_Sensor.h>  
#include <ArduinoJson.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>

// Web server and DNS for captive portal
WebServer server(80);
DNSServer dnsServer;
Preferences preferences;

// Configuration structure
struct Config {
  char ssid[32] = "";
  char password[32] = "";
  char mqtt_server[32] = "192.168.88.1";
  int mqtt_port = 1883;
};

Config config;

// Operation modes
enum OperationMode { CONFIG_MODE, DATA_MODE };
OperationMode currentMode = CONFIG_MODE;
unsigned long modeStartTime;
const unsigned long CONFIG_TIMEOUT = 90000; 
bool shouldRestart = false;
bool shouldSwitchToData = false;

// Access Point credentials
const char* AP_SSID = "ESP32-EMG-Sensor";
const char* AP_PASSWORD = "configure123";

// Network Clients
WiFiClient espClient;
PubSubClient client(espClient);

// Sensors
Adafruit_MPU6050 mpu; 
const int sensorPin = 34;
const int sensorPin2 = 32;
unsigned long startMillis;

// I2C Pins
#define I2C_SDA 21 
#define I2C_SCL 22 

void loadConfiguration() {
  preferences.begin("wifi-config", true);
  String savedSSID = preferences.getString("ssid", "");
  String savedPASS = preferences.getString("password", "");
  String savedMQTT = preferences.getString("mqtt_server", "192.168.88.1");
  config.mqtt_port = preferences.getInt("mqtt_port", 1883);
  preferences.end();

  if (savedSSID != "") {
    strlcpy(config.ssid, savedSSID.c_str(), sizeof(config.ssid));
    strlcpy(config.password, savedPASS.c_str(), sizeof(config.password));
    strlcpy(config.mqtt_server, savedMQTT.c_str(), sizeof(config.mqtt_server));
    Serial.println("Loaded saved configuration");
    Serial.println("SSID: " + savedSSID);
    Serial.println("Pass: " + savedPASS);
  } else {
    Serial.println("No saved configuration found");
  }
}

void saveConfiguration() {
  preferences.begin("wifi-config", false);
  preferences.putString("ssid", config.ssid);
  preferences.putString("password", config.password);
  preferences.putString("mqtt_server", config.mqtt_server);
  preferences.putInt("mqtt_port", config.mqtt_port);
  preferences.end();
  Serial.println("Configuration saved to flash!");
}

void startConfigMode() {
  currentMode = CONFIG_MODE;
  modeStartTime = millis();
  Serial.println("=== Starting Configuration Mode ===");
  
  if (client.connected()) client.disconnect();
  WiFi.disconnect();
  delay(100);

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD);
  
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());

  dnsServer.start(53, "*", WiFi.softAPIP());
  setupWebServer();
  server.begin();
  Serial.println("Web server started");
}

void setup_wifi() {
  if (strlen(config.ssid) == 0) {
    Serial.println("No WiFi configuration saved.");
    // Fallback to Config Mode if there is no saved config
    startConfigMode();
    return;
  }
  
  Serial.print("Connecting to WiFi: ");
  Serial.println(config.ssid);
  
  WiFi.begin(config.ssid, config.password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 50) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi!");
    // Fallback to Config Mode if connection fails
    startConfigMode();
  }
}

void startDataMode() {
  currentMode = DATA_MODE;
  Serial.println("=== Starting Data Mode ===");
  
  server.stop();
  dnsServer.stop();
  
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_STA);
  delay(100);
  
  setup_wifi();
  
  // Only proceed with MQTT setup if WiFi connected successfully
  if (WiFi.status() == WL_CONNECTED) {
      client.setServer(config.mqtt_server, config.mqtt_port);
      startMillis = millis();
      Serial.println("Data mode initialized");
  }
}

void setupWebServer() {
  server.on("/", HTTP_GET, []() {
    String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 EMG Sensor Configuration</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            max-width: 500px; margin: 0 auto; background: white; 
            padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 { color: #333; text-align: center; margin-bottom: 30px; font-size: 24px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; }
        input { 
            width: 100%; padding: 12px; border: 2px solid #ddd; 
            border-radius: 8px; box-sizing: border-box; font-size: 16px;
        }
        input:focus { border-color: #667eea; outline: none; }
        button { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 15px; border: none; border-radius: 8px; 
            cursor: pointer; width: 100%; font-size: 16px; font-weight: bold; margin-bottom: 10px;
        }
        button.secondary { background: #6c757d; }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .status { margin-top: 20px; padding: 15px; border-radius: 8px; text-align: center; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .logo { text-align: center; font-size: 48px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🖐️</div>
        <h1>EMG Sensor Setup</h1>
        <div id="status"></div>
        <form id="config-form">
            <div class="form-group">
                <label for="ssid">WiFi Network (SSID):</label>
                <input type="text" id="ssid" name="ssid" placeholder="WiFi Name" value="%SSID%" required>
            </div>
            <div class="form-group">
                <label for="password">WiFi Password:</label>
                <input type="password" id="password" name="password" placeholder="Password" value="%PASSWORD%">
            </div>
            <div class="form-group">
                <label for="mqtt_server">MQTT Server IP:</label>
                <input type="text" id="mqtt_server" name="mqtt_server" value="%MQTT_SERVER%" required>
            </div>
            <div class="form-group">
                <label for="mqtt_port">MQTT Port:</label>
                <input type="number" id="mqtt_port" name="mqtt_port" value="%MQTT_PORT%" required>
            </div>
            <button type="submit">Save & Restart</button>
            <button type="button" id="exit-btn" class="secondary">Switch to Data Mode (No Save)</button>
        </form>
    </div>
    <script>
        // Function to attempt closing the captive portal
        function closePortal() {
            setTimeout(function() {
                // Try standard close
                window.close();
                // Fallback for some browsers to clear the screen
                window.location.href = 'about:blank';
            }, 2000);
        }

        document.getElementById('config-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const btn = this.querySelector('button[type="submit"]');
            btn.disabled = true; btn.textContent = 'Saving...';
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            fetch('/save', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(d => {
                const s = document.getElementById('status');
                if(d.success) {
                    s.innerHTML = '<div class="status success">' + d.message + '</div>';
                    btn.textContent = 'Success! Restarting...';
                    btn.style.background = '#28a745';
                    // Attempt to close window after save
                    closePortal();
                } else {
                    s.innerHTML = '<div class="status error">' + d.message + '</div>';
                    btn.disabled = false; btn.textContent = 'Save & Restart';
                }
            })
            .catch(e => {
                 document.getElementById('status').innerHTML = '<div class="status error">Error: ' + e + '</div>';
                 btn.disabled = false; btn.textContent = 'Save & Restart';
            });
        });

        document.getElementById('exit-btn').addEventListener('click', function(e) {
            const btn = this; btn.disabled = true; btn.textContent = 'Switching...';
            fetch('/exit-config', { method: 'POST' })
            .then(r => r.json())
            .then(d => {
                 document.getElementById('status').innerHTML = '<div class="status success">Switching to Data Mode...</div>';
                 // Attempt to close window after switching
                 closePortal();
            });
        });
    </script>
</body>
</html>
)rawliteral";
    
    // Pre-fill inputs with current config
    html.replace("%SSID%", config.ssid);
    html.replace("%PASSWORD%", config.password);
    html.replace("%MQTT_SERVER%", config.mqtt_server);
    html.replace("%MQTT_PORT%", String(config.mqtt_port));
    
    server.send(200, "text/html", html);
  });

  server.on("/save", HTTP_POST, []() {
    String body = server.arg("plain");
    DynamicJsonDocument doc(512);
    deserializeJson(doc, body);
    
    if (doc.containsKey("ssid")) strlcpy(config.ssid, doc["ssid"], sizeof(config.ssid));
    if (doc.containsKey("password")) strlcpy(config.password, doc["password"], sizeof(config.password));
    if (doc.containsKey("mqtt_server")) strlcpy(config.mqtt_server, doc["mqtt_server"], sizeof(config.mqtt_server));
    if (doc.containsKey("mqtt_port")) config.mqtt_port = doc["mqtt_port"];
    
    saveConfiguration();
    server.send(200, "application/json", "{\"success\":true, \"message\":\"Saved. Restarting...\"}");
    shouldRestart = true;
  });

  server.on("/exit-config", HTTP_POST, []() {
    server.send(200, "application/json", "{\"success\":true}");
    shouldSwitchToData = true;
  });

  server.onNotFound([]() {
    server.sendHeader("Location", "http://" + WiFi.softAPIP().toString(), true);
    server.send(302, "text/plain", "");
  });
}

void reconnect() {
  if (!client.connected()) {
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("MQTT connected");
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  
  
  // MPU6050 Initialization
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    // We do not halt here (while(1)) so the device can still function as an EMG sensor
  } else {
    Serial.println("MPU6050 Found!");
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }
  

  loadConfiguration();

  // Boot Logic: Try Data Mode first if SSID exists
  if (strlen(config.ssid) > 0) {
    startDataMode();
  } else {
    startConfigMode();
  }
  
  Serial.println("\nSetup complete!");
}

void loop() {
  if (shouldRestart) { delay(2000); ESP.restart(); }
  if (shouldSwitchToData) { delay(500); startDataMode(); shouldSwitchToData = false; }
  
  if (currentMode == CONFIG_MODE) {
    dnsServer.processNextRequest();
    server.handleClient();
    if (millis() - modeStartTime > CONFIG_TIMEOUT) startDataMode();
  } 
  else { // DATA_MODE
    //Check for WiFi connection loss
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[ERROR] WiFi connection lost! Restarting ESP32...");
      delay(1000); // Allow time for Serial message to send
      ESP.restart();
    }

    if (!client.connected()) reconnect();
    client.loop();

    int emg1 = analogRead(sensorPin);
    int emg2 = analogRead(sensorPin2);
    
    // MPU Reading
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    float acc_x = a.acceleration.x;
    float acc_y = a.acceleration.y;
    float acc_z = a.acceleration.z;
  
    float gyro_x = g.gyro.x;
    float gyro_y = g.gyro.y;
    float gyro_z = g.gyro.z;

    StaticJsonDocument<512> doc;
    JsonObject value = doc.createNestedObject("value");
    value["time"] = millis() - startMillis;
    value["emg1"] = emg1;
    value["emg2"] = emg2;
    value["acc_x"] = acc_x;
    value["acc_y"] = acc_y;  
    value["acc_z"] = acc_z;
    value["gyro_x"] = gyro_x;
    value["gyro_y"] = gyro_y;
    value["gyro_z"] = gyro_z;

    char payload[512];
    serializeJson(doc, payload);

    if (client.connected()){
      client.publish("esp32/emg", payload);
      Serial.printf("Data sent to MQTT Broker.\n");
    } else {
      Serial.printf("Failed to send data to MQTT broker. ");
    }
    Serial.printf("EMG1: %d | EMG2: %d\n", emg1, emg2);
    delay(100);
  }
}