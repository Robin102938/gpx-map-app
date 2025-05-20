import io
import gpxpy
import requests
import streamlit as st
from staticmap import StaticMap, Line
from PIL import Image, ImageDraw, ImageFont

# Öffentlicher OSRM-Endpoint
OSRM_URL = (
    "http://router.project-osrm.org/"
    "match/v1/driving/{coords}"
    "?geometries=geojson&overview=full"
)

# Maximalpunkte fürs Matching (URL-Limit vermeiden)
MAX_MATCH_POINTS = 100

st.title("🏃 GPX-Map Generator")

# Formular
gpx_file = st.file_uploader("GPX-Datei hochladen", type="gpx")
runner = st.text_input("Dein Name")
event = st.text_input("Name des Laufs")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Karte generieren") and gpx_file and runner and event and duration:
    # 1) GPX parsen
    gpx = gpxpy.parse(gpx_file)
    pts = [
        (pt.longitude, pt.latitude)
        for track in gpx.tracks
        for seg in track.segments
        for pt in seg.points
    ]

    # 2) extrem sampeln, falls zu viele Punkte
    if len(pts) > MAX_MATCH_POINTS:
        step = len(pts) // MAX_MATCH_POINTS + 1
        pts = pts[::step]

    # 3) Map-Matching versuchen
    coord_str = ";".join(f"{lon},{lat}" for lon, lat in pts)
    try:
        res = requests.get(OSRM_URL.format(coords=coord_str))
        res.raise_for_status()
        matched = res.json()["matchings"][0]["geometry"]["coordinates"]
    except Exception as e:
        st.warning("⚠️ Map-Matching fehlgeschlagen – verwende Roh-Daten.")
        matched = pts

    # 4) Karte rendern
    m = StaticMap(800, 1200)
    m.add_line(Line(matched, width=2))
    img = m.render()

    # 5) Footer-Text darunter zeichnen
    canvas = Image.new("RGB", (img.width, img.height + 80), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, text in enumerate([event, runner, duration]):
        w, h = draw.textsize(text, font=font)
        y = img.height + 5 + 25 * i
        draw.text(((canvas.width - w) / 2, y), text, fill="black", font=font)

    # 6) Bild anzeigen und Download anbieten
    bio = io.BytesIO()
    canvas.save(bio, format="PNG")
    st.image(canvas, use_column_width=True)
    st.download_button(
        "📥 Download PNG",
        data=bio.getvalue(),
        file_name="route.png",
        mime="image/png"
    )
