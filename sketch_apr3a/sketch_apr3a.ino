#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "FaKe";
const char* password = "diesofcringe";
const char* mqtt_server = "broker.hivemq.com";

WiFiClient espClient;
PubSubClient client(espClient);

const int sensorPin = 34;  // Adjust if using a different pin

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected.");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  int sensorValue = analogRead(sensorPin);
  
  // Create a clean JSON payload
  String payload = "{\"value\":" + String(sensorValue) + "}";
  client.publish("esp32/emg", payload.c_str());
  Serial.print("Data sent.");
  delay(500);
}