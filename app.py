import io, math
import gpxpy, streamlit as st
from staticmap import StaticMap, Line
from PIL import Image, ImageDraw, ImageFont

# ——— Parameter ———
MAX_SPEED_M_S    = 10      # >36 km/h filtern
MIN_DT_S         = 1       # min. Sekunden-Diff
MAX_PTS_DISPLAY  = 2000    # Sampling-Limit
# A4 bei 300 dpi: 2480×3508 Pixel
MAP_W, MAP_H     = 2480, 3508
FOOTER_H         = 250     # Platz für Footer

st.title("🏃‍ GPX-Map Generator – Print-Ready")

# ——— Formular ———
gpx_file = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
runner   = st.text_input("Dein Name")
event    = st.text_input("Name des Laufs")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Karte generieren") and gpx_file and runner and event and duration:
    # 1) GPX parsen
    gpx = gpxpy.parse(gpx_file)
    raw = [
        (pt.longitude, pt.latitude, pt.time)
        for tr in gpx.tracks for seg in tr.segments
        for pt in seg.points if pt.time
    ]
    if len(raw) < 2:
        st.error("Zu wenige GPX-Punkte mit Zeitstempel.")
        st.stop()

    # 2) Outlier-Filter per Geschwindigkeit
    def haversine(a, b):
        lon1, lat1, lon2, lat2 = map(math.radians, (a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(h))

    clean = [raw[0]]
    for prev, curr in zip(raw, raw[1:]):
        dist = haversine(prev, curr)
        dt   = (curr[2] - prev[2]).total_seconds()
        if dt < MIN_DT_S or (dist/dt) > MAX_SPEED_M_S:
            continue
        clean.append(curr)
    if len(clean) < 2:
        st.error("Nach Filterung zu wenige Punkte übrig.")
        st.stop()

    # 3) Sampling bei vielen Punkten
    pts = [(lon, lat) for lon, lat, _ in clean]
    if len(pts) > MAX_PTS_DISPLAY:
        step = len(pts) // MAX_PTS_DISPLAY + 1
        pts = pts[::step]

    # 4) Karte rendern (CartoDB Positron Light-Tiles)
    TILE_URL = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    m = StaticMap(MAP_W, MAP_H, url_template=TILE_URL)
    # Schatten-Layer
    m.add_line(Line(pts, color="#CCCCCC", width=12))
    # Hauptroute
    m.add_line(Line(pts, color="#000000", width=6))
    try:
        img = m.render(zoom=None)
    except Exception:
        # Fallback: weißer Hintergrund + Linie
        img = Image.new("RGB", (MAP_W, MAP_H), "white")
        d = ImageDraw.Draw(img)
        # einfache Linearprojektion
        lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
        min_lon, max_lon = min(lons), max(lons); span_lon = max_lon - min_lon or 1e-6
        min_lat, max_lat = min(lats), max(lats); span_lat = max_lat - min_lat or 1e-6
        scale = min(MAP_W/span_lon, MAP_H/span_lat)
        pixel = [((lon-min_lon)*scale, (max_lat-lat)*scale) for lon, lat in pts]
        d.line(pixel, fill="black", width=6)

    # 5) Footer-Text
    canvas = Image.new("RGB", (MAP_W, MAP_H + FOOTER_H), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)

    # Versuche, einen TrueType-Font zu laden, sonst Default
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
    except:
        font_big = font_small = ImageFont.load_default()

    y = MAP_H + 20
    # Event in Großbuchstaben
    w, h = draw.textbbox((0,0), event.upper(), font=font_big)[2:]
    draw.text(((MAP_W-w)/2, y), event.upper(), fill="black", font=font_big)
    y += h + 10

    # Runner
    w, h = draw.textbbox((0,0), runner, font=font_small)[2:]
    draw.text(((MAP_W-w)/2, y), runner, fill="black", font=font_small)
    y += h + 5

    # Duration
    w, h = draw.textbbox((0,0), duration, font=font_small)[2:]
    draw.text(((MAP_W-w)/2, y), duration, fill="black", font=font_small)

    # 6) Ausgabe & Download
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    st.image(canvas, use_container_width=True)
    st.download_button(
        "📥 Druck-PNG herunterladen",
        data=buf.getvalue(),
        file_name="route_print.png",
        mime="image/png"
    )
