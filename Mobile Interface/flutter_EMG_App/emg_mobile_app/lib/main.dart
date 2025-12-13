import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_tts/flutter_tts.dart';

void main() {
  runApp(const EmgApp());
}

class EmgApp extends StatelessWidget {
  const EmgApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EMG Sign Language Translator',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.indigo,
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}

// ============================================================================
// 1. HOME SCREEN
// ============================================================================
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("EMG Sign Language Translator")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.touch_app_rounded, size: 80, color: Colors.indigo),
            const SizedBox(height: 40),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
              ),
              onPressed: () {
                print("Navigating to Configuration Screen");
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const ConfigScreen()),
                );
              },
              icon: const Icon(Icons.settings),
              label: const Text("Configure Hand Glove"),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                backgroundColor: Colors.green.shade600,
                foregroundColor: Colors.white,
              ),
              onPressed: () {
                print("Navigating to Data Display Screen");
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const DataScreen()),
                );
              },
              icon: const Icon(Icons.translate),
              label: const Text("View Translations"),
            ),
            const SizedBox(height: 40),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 40),
              child: Text(
                "Note: Connect to 'ESP32-EMG-Sensor' WiFi for Config Mode.\nConnect to Home WiFi for Data Mode.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey, fontStyle: FontStyle.italic),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ============================================================================
// 2. CONFIGURATION SCREEN
// ============================================================================
class ConfigScreen extends StatefulWidget {
  const ConfigScreen({super.key});

  @override
  State<ConfigScreen> createState() => _ConfigScreenState();
}

class _ConfigScreenState extends State<ConfigScreen> {
  // Default values mimicking the ESP defaults
  final TextEditingController _ssidController = TextEditingController();
  final TextEditingController _passController = TextEditingController();
  final TextEditingController _mqttIpController = TextEditingController(text: "192.168.88.1");
  final TextEditingController _mqttPortController = TextEditingController(text: "1883");

  // The default IP of the ESP32 in AP Mode
  final String espIp = "http://192.168.4.1";

  Future<void> _saveAndRestart() async {
    print("Attempting to Save & Restart...");
    
    // Construct the payload required by the ESP32
    final Map<String, dynamic> data = {
      "ssid": _ssidController.text,
      "password": _passController.text,
      "mqtt_server": _mqttIpController.text,
      "mqtt_port": int.tryParse(_mqttPortController.text) ?? 1883
    };

    try {
      print("Sending payload to $espIp/save: $data");
      
      // Send POST request
      final response = await http.post(
        Uri.parse('$espIp/save'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(data),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        print("Success: ESP is saving and restarting.");
        _showSnack("Saved! ESP is restarting...");
      } else {
        print("Error: Server responded with ${response.statusCode}");
        _showSnack("Error: ${response.statusCode}");
      }
    } catch (e) {
      print("Connection Failed: $e");
      _showSnack("Failed to connect to ESP. Are you on the right WiFi?");
    }
  }

  Future<void> _switchToDataMode() async {
    print("Attempting to Switch to Data Mode (No Save)...");
    try {
      print("Sending request to $espIp/exit-config");
      final response = await http.post(
        Uri.parse('$espIp/exit-config'),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        print("Success: ESP switching to Data Mode.");
        _showSnack("Switching to Data Mode...");
      } else {
         print("Error: Server responded with ${response.statusCode}");
        _showSnack("Error: ${response.statusCode}");
      }
    } catch (e) {
      print("Connection Failed: $e");
      _showSnack("Failed to connect to ESP.");
    }
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
        ),
        backgroundColor: Colors.indigo.shade600,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("ESP Configuration")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              "Ensure you are connected to ESP32 WiFi (AP)",
              style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _ssidController,
              decoration: const InputDecoration(labelText: "WiFi SSID", border: OutlineInputBorder()),
            ),
            const SizedBox(height: 15),
            TextField(
              controller: _passController,
              decoration: const InputDecoration(labelText: "WiFi Password", border: OutlineInputBorder()),
              obscureText: true,
            ),
            const SizedBox(height: 15),
            TextField(
              controller: _mqttIpController,
              decoration: const InputDecoration(labelText: "MQTT Broker IP", border: OutlineInputBorder()),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 15),
            TextField(
              controller: _mqttPortController,
              decoration: const InputDecoration(labelText: "MQTT Port", border: OutlineInputBorder()),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 30),
            ElevatedButton(
              onPressed: _saveAndRestart,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Colors.indigo,
                foregroundColor: Colors.white,
              ),
              child: const Text("Save & Restart"),
            ),
            const SizedBox(height: 10),
            TextButton(
              onPressed: _switchToDataMode,
              child: const Text("Switch to Data Mode (No Save)"),
            ),
          ],
        ),
      ),
    );
  }
}

// ============================================================================
// 3. DATA DISPLAY SCREEN
// ============================================================================
class DataScreen extends StatefulWidget {
  const DataScreen({super.key});

  @override
  State<DataScreen> createState() => _DataScreenState();
}

class _DataScreenState extends State<DataScreen> {
  // Default points to localhost emulator IP for Android (10.0.2.2) 
  // or a common local IP. User should change this to their Python PC IP.
  final TextEditingController _wsUrlController = TextEditingController(text: "192.168.215.1:8765");
  
  WebSocketChannel? _channel;
  bool _isConnected = false;
  String _currentLabel = "Waiting...";
  
  // TTS
  final FlutterTts flutterTts = FlutterTts();
  bool _isTtsEnabled = false;
  String? _lastSpokenLabel; // To track the last spoken word for deduplication

  @override
  void initState() {
    super.initState();
    _initTts();
  }

  void _initTts() async {
    await flutterTts.setLanguage("en-US");
    await flutterTts.setPitch(1.0);
  }

  void _toggleConnection() {
    if (_isConnected) {
      // Disconnect
      print("Disconnecting from WebSocket...");
      _channel?.sink.close();
      setState(() {
        _isConnected = false;
        _currentLabel = "Disconnected";
        _lastSpokenLabel = null; // Reset spoken history
      });
    } else {
      // Connect
      final url = "ws://${_wsUrlController.text}";
      print("Connecting to WebSocket at $url...");
      
      try {
        _channel = WebSocketChannel.connect(Uri.parse(url));
        setState(() {
          _isConnected = true;
          _currentLabel = "Connected. Waiting for data...";
        });
        print("WebSocket connection initiated.");
      } catch (e) {
        print("WebSocket Error: $e");
        setState(() {
          _currentLabel = "Connection Error";
        });
      }
    }
  }

  void _processData(dynamic data) {
    print("Raw Data Received: $data");
    
    try {
      // Python sends: {"predicted_label": "rock"}
      final parsed = jsonDecode(data);
      if (parsed.containsKey('predicted_label')) {
        String label = parsed['predicted_label'];
        
        setState(() {
          _currentLabel = label.toUpperCase();
        });

        // TTS LOGIC:
        // 1. Must be enabled
        // 2. Must be different from the last word spoken (to avoid repetition)
        if (_isTtsEnabled && label != _lastSpokenLabel) {
          print("TTS Speaking: $label");
          flutterTts.speak(label);
          _lastSpokenLabel = label; // Update history
        }
      }
    } catch (e) {
      print("JSON Parse Error: $e");
    }
  }

  @override
  void dispose() {
    _channel?.sink.close();
    _wsUrlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Translation Display")),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            // Connection Input
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _wsUrlController,
                    decoration: const InputDecoration(
                      labelText: "WebSocket IP:Port",
                      hintText: "192.168.1.X:8765",
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 0),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: _toggleConnection,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _isConnected ? Colors.red : Colors.green,
                    foregroundColor: Colors.white,
                  ),
                  child: Text(_isConnected ? "Stop" : "Connect"),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text("The WebSocket IP is the same as MQTT Broker IP set in Config. Default port is 8765.",
              style: TextStyle(fontSize: 12, color: Colors.grey)),
            const Divider(height: 20),
            
            // Display Area
            Expanded(
              child: Center(
                child: _isConnected
                    ? StreamBuilder(
                        stream: _channel?.stream,
                        builder: (context, snapshot) {
                          if (snapshot.hasError) {
                            return Text("Error: ${snapshot.error}", style: const TextStyle(color: Colors.red));
                          }
                          if (snapshot.hasData) {
                            // Data processing happens here
                            WidgetsBinding.instance.addPostFrameCallback((_) {
                              _processData(snapshot.data);
                            });
                            
                            return _buildBigLabel(_currentLabel);
                          }
                          return const CircularProgressIndicator();
                        },
                      )
                    : _buildBigLabel("Offline"),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          setState(() {
            _isTtsEnabled = !_isTtsEnabled;
            // Optional: If you enable it, you might want it to reset history
            // so it speaks the current gesture immediately.
            _lastSpokenLabel = null; 
          });
          print("TTS Toggled: $_isTtsEnabled");
        },
        backgroundColor: _isTtsEnabled ? Colors.indigo : Colors.grey,
        foregroundColor: Colors.white,
        icon: Icon(_isTtsEnabled ? Icons.volume_up : Icons.volume_off),
        label: Text(_isTtsEnabled ? "TTS ON" : "TTS OFF"),
      ),
    );
  }

  Widget _buildBigLabel(String text) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          text,
          style: const TextStyle(fontSize: 48, fontWeight: FontWeight.bold, color: Colors.indigo),
        ),
        const Text("PREDICTED GESTURE", style: TextStyle(letterSpacing: 2, color: Colors.grey)),
      ],
    );
  }
}