# Energy Monitoring System (ESP32 + RS-485 + Modbus + UDP)

This project implements a real-time energy monitoring system using an ESP32 device with RS-485 (Modbus RTU) communication. The system reads electrical parameters from an Elmeasure 8400N energy meter and sends the data to a Python server over Wi-Fi using UDP protocol. The received data is processed and displayed on a web dashboard, allowing remote monitoring and analysis.

The hardware setup consists of an ESP32 connected to an RS-485 to TTL converter module. The RS-485 module is connected to the energy meter using A and B lines. On the ESP32 side, RO is connected to RX, DI to TX, and DE/RE to a GPIO pin for direction control. Proper grounding and correct Modbus configuration such as baud rate, parity, and slave ID must be ensured.

The ESP32 firmware (main.ino) is responsible for connecting to Wi-Fi, communicating with the energy meter using Modbus RTU, reading register values, converting them into meaningful parameters, and sending the data to the server using UDP. The Wi-Fi credentials and server IP address must be configured inside the firmware.

On the server side, a Python application (app.py) listens for incoming UDP data packets. Once received, the data is processed and displayed on a web-based dashboard for real-time monitoring.

To run this project, first clone the repository using:
git clone https://github.com/krishna99-tech/energy-meter.git
cd <repo-folder>

Then install the required Python dependencies:
pip install -r requirements.txt

Run the server using:
python app.py

After starting the server, open a browser and navigate to:
http://<server-ip>:<port>

The system works as follows: the ESP32 sends Modbus requests to the energy meter, the meter responds with register values, the ESP32 processes the data and sends it via UDP to the server, and the server updates the dashboard with the received values.

The parameters monitored include voltage, current, active power, reactive power, apparent power, energy consumption, frequency, and power factor.

An example of the UDP data format sent from the ESP32 is:
{
  "voltage": 230.5,
  "current": 5.2,
  "power": 1.2,
  "energy": 15.6,
  "frequency": 50,
  "pf": 0.98
}

The project uses ESP32 hardware, RS-485 communication with Modbus RTU protocol, UDP for data transmission, and a Python backend with a web dashboard built using HTML, CSS, and JavaScript.

For accurate register mapping and parameter extraction, refer to the Elmeasure 8400N datasheet.

This system can be used for industrial energy monitoring, smart energy systems, remote diagnostics, and IoT-based power analysis. Future improvements may include MQTT integration, cloud deployment, database storage, alerts, and mobile app support.

This project is licensed under the MIT License.
