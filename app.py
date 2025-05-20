import io, math
import gpxpy
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ——— Parameter ———
MAX_SPEED_M_S   = 10      # max. 36 km/h; schneller sind Ausreißer
MIN_DT_S        = 1       # mind. 1 s Differenz
MAX_PTS_DISPLAY = 1_500   # max Punkte zum Darstellen (Sampling)
MAP_W, MAP_H    = 800, 1200
FOOTER_H        = 80

st.title("🏃‍ GPX-Map Generator — Offline-Modus")

# ——— Formular ———
gpx_file = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
runner   = st.text_input("Dein Name")
event    = st.text_input("Name des Laufs")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Karte generieren") and gpx_file and runner and event and duration:
    # 1) GPX parsen und Punkte+Timestamp sammeln
    gpx        = gpxpy.parse(gpx_file)
    raw_pts_ts = [(pt.longitude, pt.latitude, pt.time)
                  for tr in gpx.tracks
                  for seg in tr.segments
                  for pt  in seg.points
                  if pt.time]
    if len(raw_pts_ts) < 2:
        st.error("Zu wenige GPX-Punkte mit Zeitstempel.")
        st.stop()

    # 2) Ausreißer-Filter via Haversine-Geschwindigkeit
    def haversine(p, q):
        lon1, lat1, lon2, lat2 = map(math.radians, (p[0], p[1], q[0], q[1]))
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
        st.error("Nach Filterung zu wenige Punkte.")
        st.stop()

    # 3) Sampling für Darstellung
    coords = [(lon, lat) for lon, lat, _ in clean]
    if len(coords) > MAX_PTS_DISPLAY:
        step = len(coords) // MAX_PTS_DISPLAY + 1
        coords = coords[::step]

    # 4) Bounding-Box & Projektion auf Pixel-Raster
    lons = [c[0] for c in coords]; lats = [c[1] for c in coords]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    span_lon = max_lon - min_lon or 1e-6
    span_lat = max_lat - min_lat or 1e-6

    # Zoom-Fit: Ratio prüfen
    if span_lon/span_lat > MAP_W/MAP_H:
        scale = MAP_W / span_lon
    else:
        scale = MAP_H / span_lat

    pixel_pts = [
        (
            (lon - min_lon) * scale,
            (max_lat - lat) * scale
        )
        for lon, lat in coords
    ]

    # 5) Karte zeichnen
    # Weißer Map-Layer
    map_img = Image.new("RGB", (
        min(int(span_lon*scale), MAP_W),
        min(int(span_lat*scale), MAP_H)
    ), "white")
    draw = ImageDraw.Draw(map_img)
    draw.line(pixel_pts, fill="black", width=2)

    # 6) Canvas zusammenbauen (Map + Footer)
    canvas = Image.new("RGB", (MAP_W, MAP_H + FOOTER_H), "white")
    # Map zentriert einfügen
    x_off = (MAP_W - map_img.width) // 2
    y_off = (MAP_H - map_img.height) // 2
    canvas.paste(map_img, (x_off, y_off))

    # Footer-Text
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, txt in enumerate([event, runner, duration]):
        bbox = draw.textbbox((0, 0), txt, font=font)
        w, h  = bbox[2]-bbox[0], bbox[3]-bbox[1]
        ytxt  = MAP_H + 5 + 25*i
        draw.text(((MAP_W-w)/2, ytxt), txt, fill="black", font=font)

    # 7) Ausgabe
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    st.image(canvas, use_container_width=True)
    st.download_button(
        "📥 Download PNG",
        data=buf.getvalue(),
        file_name="route.png",
        mime="image/png"
    )
