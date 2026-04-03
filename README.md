# Tempreatre_humidity_iot_dashboard
A dynamic Streamlit dashboard that visualizes real-time IoT sensor data with animations, smart alerts, and an adaptive user experience.
Note - This dashboard uses simulated values...but can be integrated with ESP32 or Ardiuno.
# 🌡️ Smart IoT Dashboard

An interactive and visually engaging dashboard built using Streamlit to monitor real-time temperature and humidity data from an ESP32-based sensor system.

---

## ✨ Features

- 📊 Real-time visualization of temperature & humidity  
- 🎨 Dynamic UI that adapts to environmental conditions  
- 🧍 Animated human figure reacting to temperature changes  
- 🚨 Smart alerts for extreme conditions  
- 🌙 Modern, animation-rich dashboard design  

---

## 🛠️ Tech Stack

- Python  
- Streamlit  
- Plotly  
- Requests / PySerial  

---

## 🚀 How to Run

1. Make sure ESP32 is running and connected to WiFi  
2. Note the ESP32 IP address from Serial Monitor  
3. Update the IP in `app.py`  
4. Run the dashboard:

```bash
streamlit run app.py
