import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import random
import time
from datetime import datetime
import math
import serial
import requests

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IoT Sensor Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Session State ────────────────────────────────────────────────────────────
if "temp_history" not in st.session_state:
    st.session_state.temp_history = []
if "hum_history" not in st.session_state:
    st.session_state.hum_history = []
if "time_history" not in st.session_state:
    st.session_state.time_history = []
if "tick" not in st.session_state:
    st.session_state.tick = 0

# ─── ESP32 Connection Configuration ──────────────────────────────────────────
ESP32_IP = "192.168.1.100"    # ← Change to your ESP32's IP address
SERIAL_PORT = "COM11"         # ← Your ESP32 COM port
SERIAL_BAUD = 115200
WIFI_TIMEOUT = 2              # seconds

# ─── Helper: Parse "temperature,humidity" line ────────────────────────────────
def _parse_sensor_line(line):
    """Parse a 'temp,humidity' string. Returns (float, float) or (None, None)."""
    try:
        line = line.strip()
        if not line or "," not in line:
            return None, None
        parts = line.split(",")
        temperature = round(float(parts[0]), 1)
        humidity = round(float(parts[1]), 1)
        return temperature, humidity
    except (ValueError, IndexError):
        return None, None

# ─── Helper: Read via WiFi (HTTP) ─────────────────────────────────────────────
def _read_wifi():
    """HTTP GET to ESP32 root. Returns (temp, hum) or (None, None)."""
    try:
        resp = requests.get(f"http://{ESP32_IP}", timeout=WIFI_TIMEOUT)
        if resp.status_code == 200:
            return _parse_sensor_line(resp.text)
    except (requests.ConnectionError, requests.Timeout, requests.RequestException):
        pass
    return None, None

# ─── Helper: Init Serial (cached in session_state) ───────────────────────────
def _init_serial():
    """Open the serial port once and cache in session_state."""
    if "ser" not in st.session_state or st.session_state.ser is None:
        try:
            ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            st.session_state.ser = ser
        except serial.SerialException:
            st.session_state.ser = None

# ─── Helper: Read via Serial (USB) ────────────────────────────────────────────
def _read_serial():
    """Read one line from cached serial port. Returns (temp, hum) or (None, None)."""
    _init_serial()
    ser = st.session_state.get("ser")
    if ser is None:
        return None, None
    try:
        if not ser.is_open:
            ser.open()
        raw = ser.readline().decode("utf-8", errors="ignore")
        return _parse_sensor_line(raw)
    except (serial.SerialException, OSError):
        st.session_state.ser = None
        return None, None

# ─── Read Sensor Data (WiFi first → Serial fallback) ─────────────────────────
def get_sensor_data():
    # 1) Try WiFi
    temp, hum = _read_wifi()
    if temp is not None and hum is not None:
        return temp, hum
    # 2) Fallback to Serial
    temp, hum = _read_serial()
    if temp is not None and hum is not None:
        return temp, hum
    # 3) Both failed
    return None, None

# ─── Theme Helper ─────────────────────────────────────────────────────────────
def get_theme(temp):
    if temp < 22:
        return "cold"
    elif temp > 35:
        return "hot"
    return "normal"

# ─── Hex to RGBA ──────────────────────────────────────────────────────────────
def hex_to_rgba(hex_color, alpha=0.09):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ─── Animated Human Figure (rendered via components.html) ─────────────────────
def render_human_figure(theme, accent, card_bg, glow):
    """Render an animated SVG human figure using st.components.v1.html
    so the SVG and CSS animations are NOT stripped by Streamlit sanitizer."""

    if theme == "cold":
        svg_body = """
        <!-- Shivering cold figure -->
        <g class="shiver-body">
          <circle cx="80" cy="42" r="26" fill="url(#grad)" stroke="#4db8ff" stroke-width="1.5"/>
          <!-- Eyes (worried) -->
          <circle cx="72" cy="38" r="3.5" fill="#0d2b4e"/>
          <circle cx="88" cy="38" r="3.5" fill="#0d2b4e"/>
          <!-- Eyebrows raised -->
          <path d="M66 30 Q72 25 78 30" stroke="#0d2b4e" stroke-width="2" fill="none" stroke-linecap="round"/>
          <path d="M82 30 Q88 25 94 30" stroke="#0d2b4e" stroke-width="2" fill="none" stroke-linecap="round"/>
          <!-- Mouth (chattering) -->
          <path d="M69 52 Q80 46 91 52" stroke="#0d2b4e" stroke-width="2.5" fill="none" stroke-linecap="round"/>
          <rect x="73" y="50" width="14" height="5" rx="2" fill="white" opacity="0.8" class="teeth"/>
          <!-- Neck -->
          <rect x="74" y="66" width="12" height="12" rx="3" fill="#2979b8"/>
          <!-- Scarf -->
          <path d="M56 78 Q80 88 104 78" stroke="#ff6b6b" stroke-width="7" fill="none" stroke-linecap="round"/>
          <path d="M104 78 Q110 96 100 108" stroke="#ff6b6b" stroke-width="7" fill="none" stroke-linecap="round"/>
          <!-- Torso (hunched coat) -->
          <ellipse cx="80" cy="128" rx="30" ry="38" fill="#1a4a8a" stroke="#4db8ff" stroke-width="1"/>
          <line x1="80" y1="88" x2="80" y2="162" stroke="#4db8ff" stroke-width="1.2" opacity="0.4"/>
          <!-- Arms wrapped around body -->
          <path d="M50 100 Q38 128 44 150" stroke="#1a4a8a" stroke-width="16" fill="none" stroke-linecap="round"/>
          <path d="M110 100 Q122 128 116 150" stroke="#1a4a8a" stroke-width="16" fill="none" stroke-linecap="round"/>
          <circle cx="44" cy="152" r="8" fill="#2979b8"/>
          <circle cx="116" cy="152" r="8" fill="#2979b8"/>
          <!-- Legs -->
          <rect x="62" y="162" width="16" height="55" rx="7" fill="#0f2d5c"/>
          <rect x="82" y="162" width="16" height="55" rx="7" fill="#0f2d5c"/>
          <ellipse cx="70" cy="220" rx="13" ry="7" fill="#0a1f3d"/>
          <ellipse cx="90" cy="220" rx="13" ry="7" fill="#0a1f3d"/>
        </g>
        <!-- Snowflakes -->
        <text x="15"  y="55"  class="sf s1" font-size="14">❄</text>
        <text x="130" y="75"  class="sf s2" font-size="12">❄</text>
        <text x="25"  y="140" class="sf s3" font-size="10">❄</text>
        <text x="125" y="165" class="sf s4" font-size="13">❄</text>
        <text x="8"   y="195" class="sf s5" font-size="11">❄</text>
        <text x="140" y="125" class="sf s6" font-size="9">❄</text>
        <!-- Cold breath puffs -->
        <ellipse cx="55" cy="60" class="bp b1" rx="7" ry="4" fill="rgba(168,216,255,0.35)"/>
        <ellipse cx="50" cy="48" class="bp b2" rx="5" ry="3" fill="rgba(168,216,255,0.22)"/>
        """
        gradient = '<radialGradient id="grad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#a8d8ff"/><stop offset="100%" stop-color="#2979b8"/></radialGradient>'
        label = "🥶 FREEZING"
        label_color = "#4db8ff"
        extra_css = """
        @keyframes shiver {
          0%,100% { transform:translateX(0) rotate(0deg); }
          15%     { transform:translateX(-4px) rotate(-1.5deg); }
          30%     { transform:translateX(4px) rotate(1.5deg); }
          45%     { transform:translateX(-3px) rotate(-1deg); }
          60%     { transform:translateX(3px) rotate(1deg); }
          75%     { transform:translateX(-2px) rotate(-0.8deg); }
        }
        @keyframes snowfall {
          0%   { transform:translateY(0) rotate(0deg); opacity:1; }
          100% { transform:translateY(35px) rotate(360deg); opacity:0; }
        }
        @keyframes breathPuff {
          0%   { opacity:0; transform:scale(0.6) translateX(0); }
          30%  { opacity:0.7; transform:scale(1.2) translateX(-8px); }
          100% { opacity:0; transform:scale(1.6) translateX(-20px); }
        }
        @keyframes teethChatter {
          0%,100% { transform:translateY(0); }
          50%     { transform:translateY(2px); }
        }
        .shiver-body { animation:shiver 0.3s ease-in-out infinite; transform-origin:80px 130px; }
        .sf { fill:#a8d8ff; animation:snowfall 2.5s ease-in infinite; }
        .s1 { animation-delay:0s; animation-duration:2.8s; }
        .s2 { animation-delay:0.5s; animation-duration:3.1s; }
        .s3 { animation-delay:1.0s; animation-duration:2.6s; }
        .s4 { animation-delay:1.4s; animation-duration:3.3s; }
        .s5 { animation-delay:0.3s; animation-duration:3.5s; }
        .s6 { animation-delay:1.8s; animation-duration:2.7s; }
        .bp { animation:breathPuff 2.4s ease-out infinite; }
        .b1 { animation-delay:0s; }
        .b2 { animation-delay:0.3s; }
        .teeth { animation:teethChatter 0.2s ease-in-out infinite; }
        """

    elif theme == "hot":
        svg_body = """
        <!-- Heat haze -->
        <ellipse cx="80" cy="16" rx="45" ry="7" fill="none" stroke="rgba(255,100,0,0.2)" stroke-width="2" class="hz h1"/>
        <ellipse cx="80" cy="6"  rx="32" ry="5" fill="none" stroke="rgba(255,60,0,0.15)" stroke-width="2" class="hz h2"/>
        <!-- Sweating hot figure -->
        <g class="hot-sway">
          <circle cx="80" cy="42" r="26" fill="url(#grad)" stroke="#ff4500" stroke-width="2"/>
          <!-- Flushed cheeks -->
          <circle cx="65" cy="46" r="8" fill="rgba(255,60,0,0.3)"/>
          <circle cx="95" cy="46" r="8" fill="rgba(255,60,0,0.3)"/>
          <!-- Eyes (tired/drooping) -->
          <path d="M67 36 Q72 32 77 36" stroke="#3d0a00" stroke-width="2.5" fill="none" stroke-linecap="round"/>
          <path d="M83 36 Q88 32 93 36" stroke="#3d0a00" stroke-width="2.5" fill="none" stroke-linecap="round"/>
          <circle cx="72" cy="38" r="2.5" fill="#3d0a00"/>
          <circle cx="88" cy="38" r="2.5" fill="#3d0a00"/>
          <!-- Open mouth (panting) -->
          <path d="M69 52 Q80 62 91 52" stroke="#3d0a00" stroke-width="2.5" fill="rgba(200,0,0,0.5)" stroke-linecap="round"/>
          <ellipse cx="80" cy="57" rx="6" ry="4" fill="#ff6666"/>
          <!-- Neck -->
          <rect x="74" y="66" width="12" height="12" rx="3" fill="#cc2200"/>
          <!-- Torso -->
          <ellipse cx="80" cy="126" rx="28" ry="38" fill="#b52000" stroke="#ff4500" stroke-width="1.5"/>
          <path d="M66 88 L80 103 L94 88" stroke="#ff6b35" stroke-width="2" fill="none"/>
          <!-- Arms -->
          <path d="M52 100 Q32 130 28 155" stroke="#b52000" stroke-width="16" fill="none" stroke-linecap="round"/>
          <path d="M108 100 Q130 118 136 142" stroke="#b52000" stroke-width="16" fill="none" stroke-linecap="round" class="fan-arm"/>
          <circle cx="28" cy="157" r="8" fill="#cc2200"/>
          <circle cx="136" cy="144" r="8" fill="#cc2200"/>
          <!-- Fan -->
          <path d="M136 134 Q148 118 144 106 Q140 94 132 100 Q124 106 130 118 Z" fill="#ffd700" opacity="0.8" class="fan-blade"/>
          <path d="M136 134 Q150 122 150 108 Q150 94 142 94 Q134 94 136 108 Z" fill="#ffb347" opacity="0.6" class="fan-blade"/>
          <!-- Legs -->
          <rect x="62" y="160" width="16" height="55" rx="7" fill="#8b1500"/>
          <rect x="82" y="160" width="16" height="55" rx="7" fill="#8b1500"/>
          <ellipse cx="70" cy="218" rx="13" ry="6" fill="#6b0f00"/>
          <ellipse cx="90" cy="218" rx="13" ry="6" fill="#6b0f00"/>
        </g>
        <!-- Sweat drops -->
        <ellipse cx="52" cy="62" rx="3" ry="5" fill="#4dc3ff" class="sw w1"/>
        <ellipse cx="108" cy="62" rx="3" ry="5" fill="#4dc3ff" class="sw w2"/>
        <ellipse cx="66" cy="78" rx="2.5" ry="4" fill="#4dc3ff" class="sw w3"/>
        <ellipse cx="96" cy="76" rx="2.5" ry="4" fill="#4dc3ff" class="sw w4"/>
        <!-- Fire emoji -->
        <text x="62" y="20" font-size="18" class="flame">🔥</text>
        """
        gradient = '<radialGradient id="grad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#ffb347"/><stop offset="100%" stop-color="#cc2200"/></radialGradient>'
        label = "🔥 OVERHEATING"
        label_color = "#ff6b35"
        extra_css = """
        @keyframes sway {
          0%,100% { transform:rotate(-2deg) translateX(-2px); }
          50%     { transform:rotate(2deg)  translateX(2px); }
        }
        @keyframes sweatDrop {
          0%   { opacity:0; transform:translateY(0); }
          25%  { opacity:1; }
          100% { opacity:0; transform:translateY(25px); }
        }
        @keyframes fanSpin {
          0%   { transform:rotate(0deg); }
          100% { transform:rotate(360deg); }
        }
        @keyframes flamePulse {
          0%,100% { transform:scale(1) translateY(0); opacity:0.85; }
          50%     { transform:scale(1.2) translateY(-5px); opacity:1; }
        }
        @keyframes hazeRise {
          0%   { transform:scaleX(1) translateY(0); opacity:0.55; }
          100% { transform:scaleX(0.4) translateY(-20px); opacity:0; }
        }
        .hot-sway { animation:sway 1.5s ease-in-out infinite; transform-origin:80px 130px; }
        .sw { animation:sweatDrop 1.3s ease-in infinite; }
        .w1 { animation-delay:0s; }
        .w2 { animation-delay:0.4s; }
        .w3 { animation-delay:0.8s; }
        .w4 { animation-delay:1.1s; }
        .fan-arm { animation:sway 0.5s ease-in-out infinite; transform-origin:108px 100px; }
        .fan-blade { animation:fanSpin 0.4s linear infinite; transform-origin:136px 134px; }
        .flame { animation:flamePulse 0.9s ease-in-out infinite; }
        .hz { animation:hazeRise 2.2s ease-out infinite; }
        .h1 { animation-delay:0s; }
        .h2 { animation-delay:0.7s; }
        """

    else:  # normal
        svg_body = """
        <!-- Aura rings -->
        <ellipse cx="80" cy="130" rx="55" ry="110" fill="none" stroke="rgba(77,255,145,0.07)" stroke-width="3" class="aura a1"/>
        <ellipse cx="80" cy="130" rx="68" ry="124" fill="none" stroke="rgba(77,255,145,0.04)" stroke-width="2" class="aura a2"/>
        <!-- Happy relaxed figure -->
        <g class="breathe-body">
          <circle cx="80" cy="42" r="26" fill="url(#grad)" stroke="#4dff91" stroke-width="1.5"/>
          <!-- Hair -->
          <path d="M54 30 Q57 12 80 14 Q103 12 106 30" fill="#0a3d1a" stroke="none"/>
          <!-- Happy closed eyes -->
          <path d="M66 37 Q72 32 78 37" stroke="#0a3d1a" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M82 37 Q88 32 94 37" stroke="#0a3d1a" stroke-width="3" fill="none" stroke-linecap="round"/>
          <!-- Big smile -->
          <path d="M67 51 Q80 63 93 51" stroke="#0a3d1a" stroke-width="2.5" fill="rgba(255,255,255,0.15)" stroke-linecap="round"/>
          <!-- Rosy cheeks -->
          <circle cx="64" cy="48" r="6" fill="rgba(255,180,180,0.3)"/>
          <circle cx="96" cy="48" r="6" fill="rgba(255,180,180,0.3)"/>
          <!-- Neck -->
          <rect x="74" y="66" width="12" height="12" rx="3" fill="#1a7a40"/>
          <!-- Torso -->
          <ellipse cx="80" cy="126" rx="28" ry="38" fill="#155e30" stroke="#4dff91" stroke-width="1.2"/>
          <path d="M66 88 Q80 96 94 88" stroke="#4dff91" stroke-width="1" fill="none" opacity="0.5"/>
          <!-- Arms relaxed at sides -->
          <path d="M52 100 Q36 134 40 160" stroke="#155e30" stroke-width="16" fill="none" stroke-linecap="round"/>
          <path d="M108 100 Q124 134 120 160" stroke="#155e30" stroke-width="16" fill="none" stroke-linecap="round"/>
          <circle cx="40" cy="162" r="8" fill="#1a7a40"/>
          <circle cx="120" cy="162" r="8" fill="#1a7a40"/>
          <!-- Legs -->
          <rect x="62" y="160" width="16" height="55" rx="7" fill="#0f4a20"/>
          <rect x="82" y="160" width="16" height="55" rx="7" fill="#0f4a20"/>
          <ellipse cx="70" cy="218" rx="13" ry="7" fill="#093318"/>
          <ellipse cx="90" cy="218" rx="13" ry="7" fill="#093318"/>
        </g>
        <!-- Floating notes -->
        <text x="18"  y="85"  class="fn n1" font-size="14" fill="#4dff91" opacity="0.7">♪</text>
        <text x="132" y="95"  class="fn n2" font-size="14" fill="#4dff91" opacity="0.7">♫</text>
        <text x="12"  y="170" class="fn n3" font-size="12" fill="#4dff91" opacity="0.5">✦</text>
        <text x="138" y="175" class="fn n4" font-size="12" fill="#4dff91" opacity="0.5">✦</text>
        <text x="22"  y="50"  class="fn n5" font-size="14" fill="#80ffaa">🌿</text>
        """
        gradient = '<radialGradient id="grad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#b8ffce"/><stop offset="100%" stop-color="#1a7a40"/></radialGradient>'
        label = "😊 COMFORTABLE"
        label_color = "#4dff91"
        extra_css = """
        @keyframes breathe {
          0%,100% { transform:scaleY(1) scaleX(1); }
          50%     { transform:scaleY(1.025) scaleX(1.01); }
        }
        @keyframes floatNote {
          0%,100% { transform:translateY(0) rotate(0deg); opacity:0.6; }
          50%     { transform:translateY(-14px) rotate(10deg); opacity:1; }
        }
        @keyframes auraGlow {
          0%,100% { opacity:0.1; transform:scale(1); }
          50%     { opacity:0.25; transform:scale(1.03); }
        }
        .breathe-body { animation:breathe 3.5s ease-in-out infinite; transform-origin:80px 130px; }
        .fn { animation:floatNote 3s ease-in-out infinite; }
        .n1 { animation-delay:0s; }
        .n2 { animation-delay:0.7s; }
        .n3 { animation-delay:1.4s; }
        .n4 { animation-delay:2.0s; }
        .n5 { animation-delay:0.4s; }
        .aura { animation:auraGlow 4s ease-in-out infinite; }
        .a1 { animation-delay:0s; }
        .a2 { animation-delay:1s; }
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      body {{ margin:0; padding:0; background:transparent; overflow:hidden;
             display:flex; flex-direction:column; align-items:center;
             justify-content:center; height:100%; }}
      .card-container {{
        background:{card_bg};
        border:1px solid {accent}44;
        border-radius:18px;
        padding:18px 8px;
        text-align:center;
        box-shadow:0 8px 32px rgba(0,0,0,0.5),inset 0 1px 0 rgba(255,255,255,0.05);
        backdrop-filter:blur(14px);
        min-height:280px;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        width:100%;
        box-sizing:border-box;
      }}
      svg  {{ width:100%; max-width:180px; height:auto; }}
      .label {{ font-family:'Segoe UI',Arial,sans-serif; font-size:12px;
               letter-spacing:3px; text-transform:uppercase; font-weight:700;
               color:{label_color}; text-shadow:0 0 12px {label_color}88;
               margin-top:8px; text-align:center; }}
      {extra_css}
    </style>
    </head>
    <body>
      <div class="card-container">
        <svg viewBox="0 0 160 240" xmlns="http://www.w3.org/2000/svg">
          <defs>{gradient}</defs>
          {svg_body}
        </svg>
        <div class="label">{label}</div>
      </div>
    </body>
    </html>
    """
    # Use components.html so SVG renders without sanitization
    components.html(html_content, height=340)


# ─── Dynamic CSS ──────────────────────────────────────────────────────────────
def get_styles(theme):
    """Return (css_string, theme_display_name, accent_color, card_bg, glow)."""
    if theme == "cold":
        bg       = "linear-gradient(135deg,#020d1f 0%,#071e3d 45%,#0a3060 80%,#071e3d 100%)"
        accent   = "#4db8ff"
        card_bg  = "rgba(10,30,65,0.75)"
        glow     = "0 0 22px rgba(77,184,255,0.45)"
        name     = "❄️ Cold Zone"
        p_color  = "rgba(120,190,255,0.55)"
        p_dx     = "(Math.random()-0.5)*0.5"
        p_dy     = "(Math.random()-0.5)*0.4"
        p_cnt    = "50"
    elif theme == "hot":
        bg       = "linear-gradient(135deg,#150202 0%,#3d0800 45%,#6b1200 80%,#3d0800 100%)"
        accent   = "#ff6b35"
        card_bg  = "rgba(60,10,0,0.75)"
        glow     = "0 0 28px rgba(255,90,0,0.65),0 0 55px rgba(255,40,0,0.3)"
        name     = "🔥 Heat Alert"
        p_color  = "rgba(255,110,40,0.6)"
        p_dx     = "(Math.random()-0.5)*1.0"
        p_dy     = "-(Math.random()*1.2+0.3)"
        p_cnt    = "60"
    else:
        bg       = "linear-gradient(135deg,#020f05 0%,#082b12 45%,#0e4220 80%,#082b12 100%)"
        accent   = "#4dff91"
        card_bg  = "rgba(8,40,18,0.75)"
        glow     = "0 0 20px rgba(77,255,145,0.35)"
        name     = "🌿 Comfortable"
        p_color  = "rgba(80,220,130,0.45)"
        p_dx     = "(Math.random()-0.5)*0.6"
        p_dy     = "(Math.random()-0.5)*0.5"
        p_cnt    = "40"

    hot_extra = ""
    if theme == "hot":
        hot_extra = """
        @keyframes flashRed {
          0%,100% { background:rgba(180,20,0,0.22); border-color:rgba(255,80,0,0.85);
                    box-shadow:0 0 18px rgba(255,60,0,0.4); }
          50%     { background:rgba(255,50,0,0.42); border-color:rgba(255,130,0,1);
                    box-shadow:0 0 42px rgba(255,80,0,0.9); }
        }
        @keyframes shake {
          0%,100%             { transform:translateX(0); }
          10%,30%,50%,70%,90% { transform:translateX(-6px); }
          20%,40%,60%,80%     { transform:translateX(6px); }
        }
        @keyframes pulseGlow {
          0%,100% { text-shadow:0 0 10px #ff4500,0 0 20px #ff4500; }
          50%     { text-shadow:0 0 26px #ff6b35,0 0 55px #ff6b35,0 0 85px #ff2200; }
        }
        @keyframes heatWave {
          0%,100% { filter:blur(0px) brightness(1); transform:scaleY(1); }
          50%     { filter:blur(1px) brightness(1.04); transform:scaleY(1.001); }
        }
        .flash-banner { animation:flashRed 1s ease-in-out infinite; }
        .shake-text   { animation:shake 0.55s ease-in-out infinite; display:inline-block; }
        .pulse-temp   { animation:pulseGlow 1.1s ease-in-out infinite; }
        .heat-shimmer { animation:heatWave 2.5s ease-in-out infinite; }
        """

    particle_js = f"""
    <script>
    (function(){{
      var c=document.getElementById('pc');
      if(!c)return;
      var x=c.getContext('2d');
      c.width=window.innerWidth;c.height=window.innerHeight;
      var P=[],N={p_cnt};
      for(var i=0;i<N;i++)P.push({{
        x:Math.random()*c.width,y:Math.random()*c.height,
        r:Math.random()*3+1,dx:{p_dx},dy:{p_dy},
        a:Math.random()*0.5+0.2
      }});
      function d(){{
        x.clearRect(0,0,c.width,c.height);
        for(var i=0;i<P.length;i++){{
          var p=P[i];x.beginPath();x.arc(p.x,p.y,p.r,0,Math.PI*2);
          x.fillStyle='{p_color}';x.globalAlpha=p.a;x.fill();x.globalAlpha=1;
          p.x+=p.dx;p.y+=p.dy;
          if(p.x<0||p.x>c.width)p.dx*=-1;
          if(p.y<0)p.y=c.height;if(p.y>c.height)p.y=0;
        }}
        requestAnimationFrame(d);
      }}
      d();
    }})();
    </script>"""

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Rajdhani:wght@300;400;500;600&display=swap');

    html,body,[data-testid="stAppViewContainer"] {{
      background:{bg} !important; background-attachment:fixed !important;
      font-family:'Rajdhani',sans-serif; color:#e8f4fd; min-height:100vh;
    }}
    [data-testid="stHeader"]  {{ background:transparent !important; }}
    [data-testid="stToolbar"] {{ display:none; }}
    section[data-testid="stSidebar"] {{ display:none; }}

    #pc {{ position:fixed;top:0;left:0;width:100vw;height:100vh;
           pointer-events:none;z-index:0;opacity:0.55; }}

    .main .block-container {{
      position:relative;z-index:1;padding:1.2rem 2rem 3rem 2rem;max-width:1440px;
    }}

    .dashboard-title {{
      font-family:'Orbitron',monospace;font-size:2.1rem;font-weight:900;
      letter-spacing:5px;text-align:center;color:{accent};
      text-shadow:0 0 18px {accent}88;margin-bottom:0.15rem;padding-top:0.4rem;
    }}
    .dashboard-subtitle {{
      text-align:center;font-size:0.88rem;letter-spacing:3px;
      color:rgba(200,220,255,0.45);margin-bottom:1.2rem;text-transform:uppercase;
    }}

    .theme-badge {{ text-align:center;margin-bottom:1rem; }}
    .theme-pill {{
      display:inline-block;padding:5px 22px;border-radius:30px;
      border:1px solid {accent}55;background:{accent}15;color:{accent};
      font-family:'Orbitron',monospace;font-size:0.76rem;letter-spacing:2px;font-weight:600;
    }}

    .status-row {{
      display:flex;justify-content:center;gap:28px;margin:0.5rem 0 1rem 0;flex-wrap:wrap;
    }}
    .status-item {{
      display:flex;align-items:center;gap:8px;font-size:0.8rem;
      color:rgba(200,220,255,0.55);letter-spacing:1px;
    }}
    .status-dot {{
      width:8px;height:8px;border-radius:50%;background:{accent};
      box-shadow:0 0 7px {accent};animation:blink 2s ease-in-out infinite;
    }}
    @keyframes blink {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.25;}} }}

    .alert-banner {{
      border-radius:12px;padding:13px 24px;margin-bottom:1rem;border:2px solid;
      text-align:center;font-family:'Orbitron',monospace;font-size:0.82rem;
      letter-spacing:2px;font-weight:600;
    }}
    .alert-normal {{
      background:rgba(30,90,50,0.28);border-color:{accent}55;color:{accent};
    }}

    .sensor-card {{
      background:{card_bg};border:1px solid {accent}44;border-radius:18px;
      padding:26px 20px 20px 20px;text-align:center;
      box-shadow:0 8px 32px rgba(0,0,0,0.5),inset 0 1px 0 rgba(255,255,255,0.05);
      backdrop-filter:blur(14px);transition:transform 0.3s ease,box-shadow 0.3s ease;
      min-height:300px;
    }}
    .sensor-card:hover {{
      transform:translateY(-5px);
      box-shadow:0 18px 50px rgba(0,0,0,0.6),{glow};
    }}
    .sensor-label {{
      font-family:'Orbitron',monospace;font-size:0.68rem;letter-spacing:4px;
      color:{accent}bb;text-transform:uppercase;margin-bottom:10px;
    }}
    .sensor-value {{
      font-family:'Orbitron',monospace;font-size:3.4rem;font-weight:700;
      color:#ffffff;line-height:1;text-shadow:{glow};margin-bottom:6px;
      transition:color 0.8s ease,text-shadow 0.8s ease;
    }}
    .sensor-unit {{ font-size:0.88rem;color:{accent}99;letter-spacing:2px; }}
    .sensor-icon {{ font-size:2.2rem;margin-bottom:8px;opacity:0.88; }}

    .gauge-track {{
      width:80%;margin:14px auto 0 auto;height:8px;
      background:rgba(255,255,255,0.08);border-radius:4px;overflow:hidden;
    }}
    .gauge-fill {{
      height:100%;border-radius:4px;
      background:linear-gradient(90deg,{accent}88,{accent});
      box-shadow:0 0 8px {accent}66;transition:width 0.8s ease;
    }}

    .char-card {{
      background:{card_bg};border:1px solid {accent}44;border-radius:18px;
      padding:10px 8px;text-align:center;
      box-shadow:0 8px 32px rgba(0,0,0,0.5),inset 0 1px 0 rgba(255,255,255,0.05);
      backdrop-filter:blur(14px);min-height:300px;
      display:flex;flex-direction:column;align-items:center;justify-content:center;
    }}

    .mini-stat {{
      background:{accent}0f;border:1px solid {accent}2e;border-radius:10px;
      padding:10px 12px;text-align:center;margin:4px;transition:transform 0.2s ease;
    }}
    .mini-stat:hover {{ transform:translateY(-3px); }}
    .mini-stat-label {{
      font-size:0.63rem;letter-spacing:2px;color:{accent}77;text-transform:uppercase;
    }}
    .mini-stat-value {{
      font-family:'Orbitron',monospace;font-size:1.05rem;font-weight:600;color:{accent};
    }}

    .chart-card {{
      background:{card_bg};border:1px solid {accent}30;border-radius:18px;
      padding:20px;box-shadow:0 8px 32px rgba(0,0,0,0.42);
      backdrop-filter:blur(14px);margin-bottom:1rem;
    }}
    .chart-title {{
      font-family:'Orbitron',monospace;font-size:0.7rem;letter-spacing:3px;
      color:{accent}99;text-transform:uppercase;margin-bottom:10px;
    }}

    hr {{ border:none;border-top:1px solid {accent}20;margin:1rem 0; }}
    ::-webkit-scrollbar {{ width:5px; }}
    ::-webkit-scrollbar-track {{ background:transparent; }}
    ::-webkit-scrollbar-thumb {{ background:{accent}33;border-radius:3px; }}

    /* Hide iframe borders from components.html */
    iframe {{ border:none !important; }}

    {hot_extra}
    </style>

    <canvas id="pc"></canvas>
    {particle_js}
    """
    return css, name, accent, card_bg, glow


# ─── Build Plotly Chart ───────────────────────────────────────────────────────
def build_chart(times, temps, hums, accent):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=temps, name="Temperature (°C)",
        line=dict(color=accent, width=2.5, shape="spline"),
        mode="lines", fill="tozeroy",
        fillcolor=hex_to_rgba(accent, 0.1),
    ))
    fig.add_trace(go.Scatter(
        x=times, y=hums, name="Humidity (%)",
        line=dict(color="#a78bfa", width=2, shape="spline"),
        mode="lines", yaxis="y2", fill="tozeroy",
        fillcolor="rgba(167,139,250,0.08)",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Rajdhani, sans-serif", color="#c8d8f0", size=12),
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=1.08,
            bgcolor="rgba(0,0,0,0)", font=dict(size=11),
        ),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(
            showgrid=False, zeroline=False, tickfont=dict(size=10),
            linecolor="rgba(255,255,255,0.07)",
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.03)", zeroline=False,
            tickfont=dict(size=10), title="Temp (°C)",
            title_font=dict(size=10, color=accent),
        ),
        yaxis2=dict(
            showgrid=False, zeroline=False, overlaying="y", side="right",
            tickfont=dict(size=10), title="Humidity (%)",
            title_font=dict(size=10, color="#a78bfa"),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0d1b2a", font_color="#e8f4fd",
            bordercolor="rgba(255,255,255,0.12)",
        ),
    )
    return fig


# ─── Main App ─────────────────────────────────────────────────────────────────
def main():
    st.session_state.tick += 1
    temperature, humidity = get_sensor_data()

    # If ESP32 data not available yet, show warning and retry
    if temperature is None or humidity is None:
        st.warning("⏳ Waiting for ESP32 data… Make sure the sensor is connected.")
        time.sleep(1)
        st.rerun()
        return

    now = datetime.now()
    st.session_state.temp_history.append(temperature)
    st.session_state.hum_history.append(humidity)
    st.session_state.time_history.append(now)

    MAX_POINTS = 60
    if len(st.session_state.temp_history) > MAX_POINTS:
        st.session_state.temp_history = st.session_state.temp_history[-MAX_POINTS:]
        st.session_state.hum_history  = st.session_state.hum_history[-MAX_POINTS:]
        st.session_state.time_history = st.session_state.time_history[-MAX_POINTS:]

    theme = get_theme(temperature)
    css, theme_name, accent, card_bg, glow = get_styles(theme)

    # ── Inject CSS + Particles ──
    st.markdown(css, unsafe_allow_html=True)

    # ── Title ──
    heat_cls = "heat-shimmer" if theme == "hot" else ""
    st.markdown(f"""
    <div class="{heat_cls}">
      <div class="dashboard-title">⚡ IOT SENSOR HUB</div>
      <div class="dashboard-subtitle">Real-Time Environmental Monitor</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Theme Badge + Status ──
    st.markdown(f"""
    <div class="theme-badge"><span class="theme-pill">{theme_name}</span></div>
    <div class="status-row">
      <div class="status-item"><div class="status-dot"></div> SENSOR ONLINE</div>
      <div class="status-item">📡 MQTT CONNECTED</div>
      <div class="status-item">🕒 {now.strftime('%H:%M:%S')}</div>
      <div class="status-item">📊 TICK #{st.session_state.tick}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Alert Banner ──
    if temperature > 35:
        st.markdown("""
        <div class="alert-banner flash-banner" style="border-color:#ff4500;color:#ff6b35;">
          <span class="shake-text">⚠️ CRITICAL HEAT ALERT — TEMPERATURE EXCEEDS 35°C ⚠️</span>
        </div>
        """, unsafe_allow_html=True)
    elif temperature < 22:
        st.markdown("""
        <div class="alert-banner" style="background:rgba(10,40,90,0.32);
             border-color:#4db8ff55;color:#4db8ff;">
          ❄️ LOW TEMPERATURE WARNING — ENVIRONMENT IS COLD
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-banner alert-normal">
          ✅ ALL SYSTEMS NOMINAL — COMFORTABLE ENVIRONMENT
        </div>
        """, unsafe_allow_html=True)

    # ── 3-Column Layout: Temp | Humidity | Animated Figure ──
    col1, col2, col3 = st.columns(3, gap="large")

    temp_pct  = max(0, min(100, int(temperature / 50 * 100)))
    hum_pct   = max(0, min(100, int(humidity)))
    pulse_cls = "pulse-temp" if temperature > 35 else ""

    with col1:
        st.markdown(f"""
        <div class="sensor-card">
          <div class="sensor-icon">🌡️</div>
          <div class="sensor-label">Temperature</div>
          <div class="sensor-value {pulse_cls}">{temperature}</div>
          <div class="sensor-unit">°C — CELSIUS</div>
          <div class="gauge-track"><div class="gauge-fill" style="width:{temp_pct}%"></div></div>
          <div style="margin-top:16px;font-size:0.73rem;letter-spacing:1px;
               color:rgba(220,235,255,0.35);">RANGE: 0°C – 50°C</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        hum_icon = "💧" if humidity > 70 else "🌬️" if humidity < 40 else "💦"
        st.markdown(f"""
        <div class="sensor-card">
          <div class="sensor-icon">{hum_icon}</div>
          <div class="sensor-label">Humidity</div>
          <div class="sensor-value">{humidity}</div>
          <div class="sensor-unit">% — RELATIVE</div>
          <div class="gauge-track"><div class="gauge-fill" style="width:{hum_pct}%"></div></div>
          <div style="margin-top:16px;font-size:0.73rem;letter-spacing:1px;
               color:rgba(220,235,255,0.35);">RANGE: 0% – 100%</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # Try GIF first; fall back to animated SVG
        import os
        gif_map = {"cold": "cold.gif", "normal": "normal.gif", "hot": "hot.gif"}
        gif_path = gif_map[theme]
        if os.path.exists(gif_path):
            import base64
            with open(gif_path, "rb") as f:
                gif_b64 = base64.b64encode(f.read()).decode()
            gif_html = f"""
            <div style="background:{card_bg};border:1px solid {accent}44;border-radius:18px;
                        padding:18px 8px;text-align:center;
                        box-shadow:0 8px 32px rgba(0,0,0,0.5),inset 0 1px 0 rgba(255,255,255,0.05);
                        backdrop-filter:blur(14px);min-height:280px;
                        display:flex;flex-direction:column;align-items:center;justify-content:center;">
              <img src="data:image/gif;base64,{gif_b64}" style="max-width:100%;height:auto;" />
            </div>
            """
            components.html(gif_html, height=340)
        else:
            render_human_figure(theme, accent, card_bg, glow)

    # ── Mini Stats ──
    if len(st.session_state.temp_history) > 1:
        t_min = min(st.session_state.temp_history)
        t_max = max(st.session_state.temp_history)
        t_avg = round(sum(st.session_state.temp_history) / len(st.session_state.temp_history), 1)
        h_avg = round(sum(st.session_state.hum_history)  / len(st.session_state.hum_history),  1)

        s1, s2, s3, s4 = st.columns(4)
        for col, lbl, val in zip(
            [s1, s2, s3, s4],
            ["TEMP MIN", "TEMP MAX", "TEMP AVG", "HUM AVG"],
            [f"{t_min}°C", f"{t_max}°C", f"{t_avg}°C", f"{h_avg}%"],
        ):
            with col:
                st.markdown(f"""
                <div class="mini-stat">
                  <div class="mini-stat-label">{lbl}</div>
                  <div class="mini-stat-value">{val}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Live Chart ──
    st.markdown(
        '<div class="chart-card"><div class="chart-title">'
        '📈 Live Sensor History — Last 60 Readings</div>',
        unsafe_allow_html=True,
    )
    fig = build_chart(
        st.session_state.time_history,
        st.session_state.temp_history,
        st.session_state.hum_history,
        accent,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Footer ──
    st.markdown(f"""
    <div style="text-align:center;margin-top:2rem;color:rgba(200,220,255,0.22);
                font-size:0.68rem;letter-spacing:2px;font-family:'Orbitron',monospace;">
      IOT SENSOR HUB v3.0 &nbsp;·&nbsp; AUTO-REFRESH EVERY 1s
      &nbsp;·&nbsp; {now.strftime('%Y-%m-%d')}
    </div>
    """, unsafe_allow_html=True)

    # ── Auto-refresh ──
    time.sleep(1)
    st.rerun()


if __name__ == "__main__":
    main()