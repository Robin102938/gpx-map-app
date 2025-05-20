import io
import gpxpy, requests
from staticmap import StaticMap, Line
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# OSRM-Public-Endpoint
OSRM_URL = (
    "http://router.project-osrm.org/"
    "match/v1/driving/{coords}"
    "?geometries=geojson&overview=full"
)

st.title("🏃 GPX-Map Generator")

# ——— Eingabe-Form ———
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
        for segment in track.segments
        for pt in segment.points
    ]

    # — Sampling: max. 500 Punkte behalten, um URL-Limit zu umgehen
    MAX_MATCH_POINTS = 500
    if len(pts) > MAX_MATCH_POINTS:
        step = len(pts) // MAX_MATCH_POINTS + 1
        pts = pts[::step]

    # 2) Map-Matching mit Fehlerbehandlung
    coord_str = ";".join(f"{lon},{lat}" for lon, lat in pts)
    try:
        r = requests.get(OSRM_URL.format(coords=coord_str))
        r.raise_for_status()
        matched = r.json()["matchings"][0]["geometry"]["coordinates"]
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Map-Matching fehlgeschlagen:\n{e}")
        st.stop()

    # 3) Karte rendern
    m = StaticMap(800, 1200)
    m.add_line(Line(matched, width=2))
    img = m.render()

    # 4) Footer-Text zeichnen
    canvas = Image.new("RGB", (img.width, img.height + 80), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, text in enumerate([event, runner, duration]):
        w, h = draw.textsize(text, font=font)
        y = img.height + 5 + 25 * i
        draw.text(((canvas.width - w) / 2, y), text, fill="black", font=font)

    # 5) Anzeige & Download
    bio = io.BytesIO()
    canvas.save(bio, format="PNG")
    st.image(canvas, use_column_width=True)
    st.download_button(
        "📥 Download PNG",
        data=bio.getvalue(),
        file_name="route.png",
        mime="image/png"
    )
