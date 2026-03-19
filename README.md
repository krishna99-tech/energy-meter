⚡ Energy Monitoring System (ESP32 + RS-485 + Modbus + UDP)
📌 Overview
This project implements a real-time Energy Monitoring System using an ESP32-based embedded device integrated with RS-485 (Modbus RTU) communication.
The system reads electrical parameters from an Elmeasure 8400N Energy Meter and transmits the data to a remote server via Wi-Fi using UDP protocol, enabling live monitoring, visualization, and analysis through a web dashboard.
🚀 Features
📡 Modbus RTU (RS-485) communication with energy meter
📶 Wi-Fi enabled ESP32 device for wireless data transmission
⚡ Real-time acquisition of electrical parameters:
Voltage
Current
Power
Energy
Frequency
Power Factor
🌐 UDP-based data transfer to server
📊 Web dashboard for:
Live monitoring
Historical data analysis
🔧 Scalable backend using Python
🏗️ System Architecture

[ Energy Meter (Elmeasure 8400N) ]
                │
           (RS-485 / Modbus RTU)
                │
        [ ESP32 + RS-485 Module ]
                │
            (Wi-Fi / UDP)
                │
          [ Python Server ]
                │
           [ Web Dashboard ]
🧰 Hardware Requirements
ESP32 Development Board
RS-485 to TTL Converter Module
Elmeasure 8400N Energy Meter
Connecting wires
Power supply
🔌 Hardware Setup
Connect RS-485 module to ESP32:
RO → RX
DI → TX
DE/RE → GPIO (control pin)
Connect RS-485 lines:
A → A (Energy meter)
B → B (Energy meter)
Ensure:
Proper grounding
Correct baud rate and Modbus settings
💻 Software Setup
1️⃣ Clone the Repository
Bash
git clone <your-repo-url>
cd <repo-folder>
2️⃣ Install Python Dependencies
Bash
pip install -r requirements.txt
3️⃣ Run the Server
Bash
python app.py
4️⃣ Access Dashboard
After running the server, open the link shown in the terminal:

http://<server-ip>:<port>
📡 ESP32 Firmware
Firmware file: main.ino
Developed using Arduino IDE
Key Responsibilities:
Connect to Wi-Fi
Communicate with energy meter using Modbus RTU
Read register values from Elmeasure 8400N
Send data via UDP to server
📊 Data Flow
ESP32 sends Modbus request via RS-485
Energy meter responds with parameter values
ESP32 parses and formats the data
Data is sent to server using UDP
Server processes and displays it on dashboard
📘 Reference
For accurate register mapping and parameter extraction, refer to:
👉 Elmeasure 8400N Datasheet (Modbus Register Map)
⚙️ Configuration
ESP32
Update Wi-Fi credentials:
C++
const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
Set server IP and port for UDP communication
Server
Configure UDP port in app.py
Ensure firewall allows UDP traffic
🛠️ Technologies Used
Hardware: ESP32, RS-485
Protocol: Modbus RTU, UDP
Backend: Python (Flask / Socket handling)
Frontend: HTML, CSS, JS (Dashboard)
📈 Use Cases
Industrial energy monitoring
Smart grid systems
Remote power analysis
IoT-based energy management