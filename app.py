import io, math
import gpxpy, streamlit as st
from datetime import datetime
from staticmap import StaticMap, Line, CircleMarker
from PIL import Image, ImageDraw, ImageFont

# ——— Konfiguration ———
MAX_SPEED_M_S = 10 # >36 km/h filtern
MIN_DT_S = 1 # mind. 1 s
MAX_PTS_DISPLAY = 2000 # Sampling-Limit
# Karte etwas kleiner für mehr Footer
MAP_W, MAP_H = 2480, 3000 # A4-Breite, reduzierte Höhe
PAD_HORIZ = 200 # horizontaler Seitenrand
PAD_VERT = 40 # vertikaler Abstand
BOTTOM_EXTRA = 300 # zusätzlicher Unterkante-Puffer für Footer mehr Platz # zusätzlicher Unterkante-Puffer

st.title("🏃‍ GPX-Map Generator – Print-Ready")

# ——— Eingaben ———
gpx_file = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
event_name = st.text_input("Name des Laufs / Events")
run_date = st.date_input("Datum des Laufs")
distance_opt = st.selectbox(
    "Distanz auswählen",
    ["5 km", "10 km", "21,0975 km", "42,195 km", "Andere…"]
)
if distance_opt == "Andere…":
    custom_dist = st.text_input("Eigene Distanz (z.B. '15 km')")
    distance = (custom_dist.strip() or distance_opt)
else:
    distance = distance_opt

city = st.text_input("Stadt")
bib_no = st.text_input("Startnummer (ohne #)")
runner = st.text_input("Dein Name")
duration = st.text_input("Zeit (HH:MM:SS)")

if st.button("Poster erzeugen") and gpx_file and event_name and runner and duration:
    # 1) GPX-Daten einlesen
    gpx = gpxpy.parse(gpx_file)
    raw = [(pt.longitude, pt.latitude, pt.elevation, pt.time)
           for tr in gpx.tracks for seg in tr.segments for pt in seg.points
           if pt.time and pt.elevation is not None]
    if len(raw) < 2:
        st.error("Zu wenige valide GPX-Daten.")
        st.stop()

    # 2) Ausreißer filtern (Haversine-Speed)
    def hav(a, b):
        lon1, lat1, lon2, lat2 = map(math.radians, (a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2 * 6371000 * math.asin(math.sqrt(h))

    clean = [raw[0]]
    for prev, curr in zip(raw, raw[1:]):
        dist = hav(prev, curr)
        dt = (curr[3] - prev[3]).total_seconds()
        if dt < MIN_DT_S or (dist / dt) > MAX_SPEED_M_S:
            continue
        clean.append(curr)
    if len(clean) < 2:
        st.error("Kein gültiger Track nach Filter.")
        st.stop()

    # 3) Sampling
    pts = [(lon, lat) for lon, lat, _, _ in clean]
    if len(pts) > MAX_PTS_DISPLAY:
        step = len(pts) // MAX_PTS_DISPLAY + 1
        pts = pts[::step]

    # 4) Karte rendern (leicht gezoomt)
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    m = StaticMap(MAP_W, MAP_H, url_template=TILE)
    m.add_line(Line(pts, color="#CCCCCC", width=18))
    m.add_line(Line(pts, color="#000000", width=10))
    m.add_marker(CircleMarker(pts[0], "#00b300", 30))
    m.add_marker(CircleMarker(pts[-1], "#e60000", 30))
    # Fixer Zoom-Level für etwas nähere Ansicht
    map_img = m.render(zoom=14)
    st.image(map_img, use_container_width=True)

    # 5) Footer-Bereich berechnen
    try:
        f_event = ImageFont.truetype("DejaVuSans-Bold.ttf", 160)
        f_info = ImageFont.truetype("DejaVuSans.ttf", 100)
        f_meta = ImageFont.truetype("DejaVuSans.ttf", 100)
    except:
        f_event = f_info = f_meta = ImageFont.load_default()

    ev = event_name.upper()
    date_str = run_date.strftime('%d %B %Y')
    center = f"{distance} – {city}"
    bib_str = f"#{bib_no.strip()} {runner}"
    time_str = duration

    tmp = Image.new('RGB', (1,1))
    dtmp = ImageDraw.Draw(tmp)
    be = dtmp.textbbox((0,0), ev, font=f_event)
    bd = dtmp.textbbox((0,0), date_str, font=f_info)
    bc = dtmp.textbbox((0,0), center, font=f_info)
    bb = dtmp.textbbox((0,0), bib_str, font=f_meta)
    bt = dtmp.textbbox((0,0), time_str, font=f_meta)

    # Gesamt-Footer-Höhe
    footer_h = (be[3]-be[1]) + PAD_VERT + (bd[3]-bd[1]) + PAD_VERT + 3 + PAD_VERT + \
               max(bc[3]-bc[1], bb[3]-bb[1], bt[3]-bt[1]) + BOTTOM_EXTRA

    # 6) Poster-Canvas
    poster = Image.new("RGB", (MAP_W, MAP_H + footer_h), "white")
    poster.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(poster)

    y = MAP_H + PAD_VERT
    # Event-Name
    w_e, h_e = be[2]-be[0], be[3]-be[1]
    draw.text(((MAP_W-w_e)/2, y), ev, font=f_event, fill="#000000")
    y += h_e + PAD_VERT

    # Stadt-Name unter Titel
    bcity = dtmp.textbbox((0,0), city, font=f_info)
    w_city, h_city = bcity[2]-bcity[0], bcity[3]-bcity[1]
    draw.text(((MAP_W-w_city)/2, y), city, font=f_info, fill="#333333")
    y += h_city + PAD_VERT

    # Separator
    draw.line((PAD_HORIZ, y, MAP_W-PAD_HORIZ, y), fill="#CCCCCC", width=3)
    y += PAD_VERT * 2

    # Datum - Distanz
    date_line = f"{run_date.strftime('%d.%m.%Y')} - {distance}"
    bd2 = dtmp.textbbox((0,0), date_line, font=f_info)
    w_d2, h_d2 = bd2[2]-bd2[0], bd2[3]-bd2[1]
    draw.text(((MAP_W-w_d2)/2, y), date_line, font=f_info, fill="#555555")
    y += h_d2 + PAD_VERT

    # Bib - Name - Zeit
    trip = f"#{bib_no.strip()} - {runner} - {duration}"
    bt2 = dtmp.textbbox((0,0), trip, font=f_meta)
    w_t2, h_t2 = bt2[2]-bt2[0], bt2[3]-bt2[1]
    draw.text(((MAP_W-w_t2)/2, y), trip, font=f_meta, fill="#000000")

        # 7) Download
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    st.download_button(
        label="📥 Poster herunterladen",
        data=buf.getvalue(),
        file_name="running_poster.png",
        mime="image/png",
        key="poster_download"
    )
