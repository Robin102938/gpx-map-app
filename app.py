import io, math
import gpxpy, streamlit as st
from datetime import datetime
from staticmap import StaticMap, Line, CircleMarker
from PIL import Image, ImageDraw, ImageFont

# ——— Konfiguration ———
MAX_SPEED_M_S = 10 # >36 km/h filtern
MIN_DT_S = 1 # mind. 1 s
MAX_PTS_DISPLAY = 2000 # Sampling-Limit
MAP_W, MAP_H = 2480, 3508 # A4 @300dpi
FOOTER_PAD_TOP = 60 # Abstand oberhalb der Textzeilen
FOOTER_PAD_BOT = 200 # extra Unterkante-Puffer

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
    distance = custom_dist.strip() or distance_opt
else:
    distance = distance_opt

city = st.text_input("Stadt")
bib_no = st.text_input("Startnummer (ohne #)")
runner = st.text_input("Dein Name")
duration = st.text_input("Zeit (HH:MM:SS)")

# ——— Poster erzeugen ———
if st.button("Poster erzeugen") and gpx_file and event_name and runner and duration:
    # 1) GPX-Daten parsen
    gpx = gpxpy.parse(gpx_file)
    raw = [(pt.longitude, pt.latitude, pt.elevation, pt.time)
           for tr in gpx.tracks for seg in tr.segments for pt in seg.points
           if pt.time and pt.elevation is not None]
    if len(raw) < 2:
        st.error("Zu wenige valide GPX-Daten.")
        st.stop()

    # 2) Ausreißer filtern (Speed)
    def hav(a,b):
        lon1,lat1,lon2,lat2 = map(math.radians,(a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(h))
    clean=[raw[0]]
    for prev,curr in zip(raw, raw[1:]):
        dist = hav(prev,curr)
        dt = (curr[3]-prev[3]).total_seconds()
        if dt < MIN_DT_S or dist/dt > MAX_SPEED_M_S:
            continue
        clean.append(curr)
    if len(clean) < 2:
        st.error("Kein gültiger Track nach Filter.")
        st.stop()

    # 3) Sampling
    pts=[(lon,lat) for lon,lat,_,_ in clean]
    if len(pts) > MAX_PTS_DISPLAY:
        step = len(pts)//MAX_PTS_DISPLAY+1
        pts = pts[::step]

    # 4) Karte rendern
    TILE="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    m = StaticMap(MAP_W, MAP_H, url_template=TILE)
    m.add_line(Line(pts, color="#CCCCCC", width=18))
    m.add_line(Line(pts, color="#000000", width=10))
    m.add_marker(CircleMarker(pts[0], "#00b300", 30))
    m.add_marker(CircleMarker(pts[-1], "#e60000", 30))
    try:
        map_img = m.render(zoom=None)
    except Exception:
        map_img = Image.new("RGB", (MAP_W, MAP_H), "white")
        df = ImageDraw.Draw(map_img)
        df.line(pts, fill="black", width=10)

    st.image(map_img, use_container_width=True)

    # 5) Footer-Bereich
    try:
        f_event = ImageFont.truetype("DejaVuSans-Bold.ttf", 160)
        f_info = ImageFont.truetype("DejaVuSans.ttf", 100)
        f_meta = ImageFont.truetype("DejaVuSans.ttf", 100)
    except Exception:
        f_event = f_info = f_meta = ImageFont.load_default()
    ev = event_name.upper()
    info = f"{run_date.strftime('%d %B %Y')} – {distance} – {city}"
    bib = f"#{bib_no.strip()} {runner} – {duration}"
    tmp = ImageDraw.Draw(Image.new('RGB',(1,1)))
    be = tmp.textbbox((0,0), ev, font=f_event)
    bi = tmp.textbbox((0,0), info, font=f_info)
    bm = tmp.textbbox((0,0), bib, font=f_meta)

    footer_h = (be[3]-be[1]) + (bi[3]-bi[1]) + (bm[3]-bm[1]) + FOOTER_PAD_TOP + FOOTER_PAD_BOT

    # 6) Poster-Canvas
    poster = Image.new("RGB", (MAP_W, MAP_H + footer_h), "white")
    poster.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(poster)

    y = MAP_H + FOOTER_PAD_TOP
    draw.line((200, y, MAP_W-200, y), fill="#CCCCCC", width=3)
    y += 40

    # Event-Name
    w_e, h_e = be[2]-be[0], be[3]-be[1]
    draw.text(((MAP_W-w_e)/2, y), ev, font=f_event, fill="#000000")
    y += h_e + 60

    # Info-Zeile
    w_i, h_i = bi[2]-bi[0], bi[3]-bi[1]
    draw.text(((MAP_W-w_i)/2, y), info, font=f_info, fill="#555555")
    y += h_i + 50

    # Bib-Zeile
    w_m, h_m = bm[2]-bm[0], bm[3]-bm[1]
    draw.text(((MAP_W-w_m)/2, y), bib, font=f_meta, fill="#555555")

    # 7) Download
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    st.download_button("📥 Poster herunterladen", data=buf.getvalue(),
                       file_name="running_poster.png", mime="image/png")
