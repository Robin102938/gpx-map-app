import io, math
import gpxpy, streamlit as st
from staticmap import StaticMap, Line
from PIL import Image, ImageDraw, ImageFont

# ——— Parameter ———
MAX_SPEED_M_S   = 10      # max. 36 km/h → Ausreißer-Filter
MIN_DT_S        = 1       # min. Zeitdiff in Sekunden
MAX_PTS_DISPLAY = 1500    # Sampling für zu viele Punkte
MAP_W, MAP_H    = 800, 1200
FOOTER_H        = 80

st.title("🏃‍ GPX-Map Generator mit OSM-Tiles")

# ——— Formular ———
gpx_file = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
runner   = st.text_input("Dein Name")
event    = st.text_input("Name des Laufs")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Karte generieren") and gpx_file and runner and event and duration:
    # 1) GPX parsen + Zeitstempel
    gpx        = gpxpy.parse(gpx_file)
    raw_pts_ts = [
        (pt.longitude, pt.latitude, pt.time)
        for tr in gpx.tracks for seg in tr.segments
        for pt in seg.points if pt.time
    ]
    if len(raw_pts_ts) < 2:
        st.error("Nicht genug GPX-Punkte mit Zeitstempel.")
        st.stop()

    # 2) Ausreißer rausfiltern (Haversine‐Geschwindigkeit)
    def haversine(p, q):
        lon1, lat1, lon2, lat2 = map(math.radians, (p[0],p[1],q[0],q[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(a))

    clean = [raw_pts_ts[0]]
    for prev, curr in zip(raw_pts_ts, raw_pts_ts[1:]):
        dist = haversine(prev, curr)
        dt   = (curr[2] - prev[2]).total_seconds()
        if dt < MIN_DT_S or (dist/dt) > MAX_SPEED_M_S:
            continue
        clean.append(curr)
    if len(clean) < 2:
        st.error("Nach Filterung zu wenige gültige Punkte.")
        st.stop()

    # 3) Sampling, wenn zu viele Punkte
    coords = [(lon, lat) for lon, lat, _ in clean]
    if len(coords) > MAX_PTS_DISPLAY:
        step = len(coords)//MAX_PTS_DISPLAY + 1
        coords = coords[::step]

    # 4) Karte rendern – OSM-Tiles
    TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    # Versuch 1: Auto-Zoom
    m = StaticMap(MAP_W, MAP_H, url_template=TILE_URL)
    m.add_line(Line(coords, color="black", width=2))
    try:
        img = m.render(zoom=None)
    except Exception:
        # wenn zu viele Tiles → niedrigere Zoom-Stufe
        img = m.render(zoom=12)

    # 5) Footer-Text zeichnen
    canvas = Image.new("RGB", (MAP_W, MAP_H + FOOTER_H), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, txt in enumerate([event, runner, duration]):
        bbox = draw.textbbox((0, 0), txt, font=font)
        w, h  = bbox[2]-bbox[0], bbox[3]-bbox[1]
        y_txt = MAP_H + 5 + 25*i
        draw.text(((MAP_W-w)/2, y_txt), txt, fill="black", font=font)

    # 6) Ausgeben & Download
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    st.image(canvas, use_container_width=True)
    st.download_button(
        "📥 Download PNG",
        data=buf.getvalue(),
        file_name="route.png",
        mime="image/png"
    )
