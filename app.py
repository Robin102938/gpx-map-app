import io, math
import gpxpy, streamlit as st
from staticmap import StaticMap, Line
from PIL import Image, ImageDraw, ImageFont

# ——— Parameter ———
MAX_SPEED_M_S    = 10       # >36 km/h filtern
MIN_DT_S         = 1        # min. Sekunden-Diff
MAX_PTS_DISPLAY  = 2000     # Sampling-Limit
# Druck-Qualität: A4 bei 300 dpi ~ 2480×3508px
MAP_W, MAP_H     = 2480, 3508
FOOTER_H         = 250      # Platz für Footer-Text

st.title("🏃‍ GPX-Map Generator – Print-Ready")

# ——— Formular ———
gpx_file = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
runner   = st.text_input("Dein Name")
event    = st.text_input("Name des Laufs")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Karte generieren") and gpx_file and runner and event and duration:
    # 1) GPX parse & Timestamp sammeln
    gpx = gpxpy.parse(gpx_file)
    raw = [(pt.longitude, pt.latitude, pt.time)
           for tr in gpx.tracks for seg in tr.segments
           for pt in seg.points if pt.time]
    if len(raw) < 2:
        st.error("Nicht genug GPX-Punkte mit Zeitstempel.")
        st.stop()

    # 2) Outlier-Filter per Haversine-Speed
    def haversine(a,b):
        lon1,lat1,lon2,lat2 = map(math.radians,(a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(h))

    clean = [raw[0]]
    for prev,curr in zip(raw, raw[1:]):
        dist = haversine(prev,curr)
        dt   = (curr[2]-prev[2]).total_seconds()
        if dtMAX_SPEED_M_S:
            continue
        clean.append(curr)
    if len(clean)<2:
        st.error("Zu viele Ausreißer – keine Punkte übrig.")
        st.stop()

    # 3) Sampling
    pts = [(lon,lat) for lon,lat,_ in clean]
    if len(pts)>MAX_PTS_DISPLAY:
        step = len(pts)//MAX_PTS_DISPLAY + 1
        pts = pts[::step]

    # 4) Basemap & Route rendern
    TILE_URL = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    m = StaticMap(MAP_W, MAP_H, url_template=TILE_URL)
    # Route als Linienzug mit Schatten
    m.add_line(Line(pts, color="#CCCCCC", width=12))  # Schatten
    m.add_line(Line(pts, color="#000000", width=6))   # Hauptroute
    try:
        img = m.render(zoom=None)
    except Exception:
        # Fallback: nur weiße Fläche & Linie
        img = Image.new("RGB", (MAP_W, MAP_H), "white")
        d = ImageDraw.Draw(img)
        # einfache Umrechnung in Pixels:
        lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
        min_lon, max_lon = min(lons), max(lons); span_lon = max_lon-min_lon or 1e-6
        min_lat, max_lat = min(lats), max(lats); span_lat = max_lat-min_lat or 1e-6
        scale = min(MAP_W/span_lon, MAP_H/span_lat)
        pixel = [((lon-min_lon)*scale, (max_lat-lat)*scale) for lon,lat in pts]
        d.line(pixel, fill="black", width=6)

    # 5) Footer mit schicker Typo
    canvas = Image.new("RGB", (MAP_W, MAP_H+FOOTER_H), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    # bitte prüfe Pfad zu deinen TTF-Fonts!
    font_event = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  fifty) if False else ImageFont.load_default()
    # Fallback auf Default-Font:
    font_event = ImageFont.load_default()
    font_meta  = ImageFont.load_default()
    texts = [event.upper(), runner, duration]
    sizes = [60,  Forty,  Forty] = [40, 30, 30]  # alternativ feste Pixelgrößen
    yc = MAP_H + 20
    for txt, size in zip(texts, sizes):
        # hier könntest du mit truetype-Fonts arbeiten
        w,h = draw.textbbox((0,0), txt, font=font_event)[2:]
        draw.text(((MAP_W-w)/2, yc), txt, fill="black", font=font_event)
        yc += h + 10

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
