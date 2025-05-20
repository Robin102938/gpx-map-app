import io
import gpxpy
import streamlit as st
from staticmap import StaticMap, Line
from PIL import Image, ImageDraw, ImageFont

# Wir verwenden ab jetzt **kein** OSRM-Matching mehr,
# sondern zeichnen die rohe GPX-Strecke.
# Und holen uns Schwarz-Weiß-Tiles:
TILE_URL = "https://a.tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png"

# Wie viele Punkte maximal aufs Bild?
MAX_PTS = 2000

st.title("🏃 GPX-Map Generator – Rohspur")

# Formular
gpx_file = st.file_uploader("GPX-Datei hochladen", type="gpx")
runner   = st.text_input("Dein Name")
event    = st.text_input("Name des Laufs")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Karte generieren") and gpx_file and runner and event and duration:
    # 1) GPX einlesen
    gpx = gpxpy.parse(gpx_file)
    pts = [
        (pt.longitude, pt.latitude)
        for tr in gpx.tracks
        for seg in tr.segments
        for pt  in seg.points
    ]

    # 2) ggf. Sampling, damit es nicht zu viele sind
    if len(pts) > MAX_PTS:
        step = len(pts) // MAX_PTS + 1
        pts = pts[::step]

    # 3) Karte rendern (BW-Tiles)
    m = StaticMap(800, 1200, url_template=TILE_URL)
    m.add_line(Line(pts, color="black", width=2))
    img = m.render()

    # 4) Footer-Beschriftung
    canvas = Image.new("RGB", (img.width, img.height + 80), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, text in enumerate([event, runner, duration]):
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        y = img.height + 5 + 25 * i
        draw.text(((canvas.width - w) / 2, y), text, fill="black", font=font)

    # 5) Ausgabe & Download
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    st.image(canvas, use_column_width=True)
    st.download_button(
        "📥 Download als PNG",
        data=buf.getvalue(),
        file_name="route.png",
        mime="image/png"
    )
