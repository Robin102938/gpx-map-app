import io
import math
import gpxpy
import streamlit as st
from staticmap import StaticMap, Line
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# 1) Schwar-Weiß-Tiles von Stamen (Fastly CDN, https)
TILE_URL = "https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png"

# 2) Parameter fürs Outlier-Filtering
MAX_SPEED_M_S = 10 # wenn zwischen zwei Punkten >10 m/s, ist’s vermutlich ein Ausreißer
MIN_TIME_S = 1 # Zeitdifferenz mindestens 1 s
MAX_PTS = 1500 # für die Darstellung sampeln, wenn’s zu viele sind

st.title("🏃 GPX-Map Generator mit Outlier-Filter")

# Eingabe
gpx_file = st.file_uploader("GPX-Datei hochladen", type="gpx")
runner = st.text_input("Dein Name")
event = st.text_input("Name des Laufs")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Karte generieren") and gpx_file and runner and event and duration:
    # --- 1) GPX einlesen und timestamp und coords extrahieren
    gpx = gpxpy.parse(gpx_file)
    raw_pts = []
    for tr in gpx.tracks:
        for seg in tr.segments:
            for pt in seg.points:
                if pt.time:
                    raw_pts.append((pt.longitude, pt.latitude, pt.time))
    if len(raw_pts) < 2:
        st.error("Nicht genug gültige GPX-Punkte mit Zeitstempel.")
        st.stop()

    # --- 2) Outlier rausfiltern nach Speed
    def haversine(a, b):
        # Abstand in Metern
        lon1, lat1 = math.radians(a[0]), math.radians(a[1])
        lon2, lat2 = math.radians(b[0]), math.radians(b[1])
        dlon, dlat = lon2 - lon1, lat2 - lat1
        r = 6371000
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2 * r * math.asin(math.sqrt(h))

    clean_pts = [raw_pts[0]]
    for prev, curr in zip(raw_pts, raw_pts[1:]):
        dist = haversine(prev, curr)
        dt = (curr[2] - prev[2]).total_seconds()
        if dt < MIN_TIME_S or (dist/dt) > MAX_SPEED_M_S:
            # überspringen
            continue
        clean_pts.append(curr)
    if len(clean_pts) < 2:
        st.error("Nach Filterung sind zu wenige Punkte übrig.")
        st.stop()

    # 3) Für die Darstellung nur Koordinaten extrahieren und ggf. sampeln
    coords = [(lon, lat) for lon, lat, _ in clean_pts]
    if len(coords) > MAX_PTS:
        step = len(coords) // MAX_PTS + 1
        coords = coords[::step]

    # 4) Karte rendern mit Stamen-Tiles
    try:
        m = StaticMap(800, 1200, url_template=TILE_URL)
        m.add_line(Line(coords, color="black", width=2))
        img = m.render(zoom=None) # auto-zoom
    except Exception as e:
        st.warning(f"Tile-Download fehlgeschlagen ({e}), zeichne weiße Fläche.")
        # Fallback: nur weiße Fläche
        img = Image.new("RGB", (800, 1200), "white")
        draw = ImageDraw.Draw(img)
        draw.line(coords, fill="black", width=2)

    # 5) Footer-Beschriftung
    canvas = Image.new("RGB", (img.width, img.height + 80), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, text in enumerate([event, runner, duration]):
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        y = img.height + 5 + 25 * i
        draw.text(((canvas.width - w)/2, y), text, fill="black", font=font)

    # 6) Ausgabe & Download
    bio = io.BytesIO()
    canvas.save(bio, format="PNG")
    st.image(canvas, use_column_width=True)
    st.download_button(
        "📥 Download PNG",
        data=bio.getvalue(),
        file_name="route.png",
        mime="image/png"
    )
