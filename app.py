import io, math
import gpxpy, streamlit as st
from datetime import datetime
from staticmap import StaticMap, Line, CircleMarker
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt

# ——— Konfiguration ———
MAX_SPEED_M_S    = 10      # >36 km/h filtern
MIN_DT_S         = 1       # mind. 1 s
MAX_PTS_DISPLAY  = 2000    # Sampling-Limit
MAP_W, MAP_H     = 2480, 3508  # A4 @300dpi
FOOTER_H         = 300

st.title("🏃‍ GPX-Map Generator – Print-Ready mit Höhenprofil")

# ——— Eingaben ———
gpx_file   = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
event_name = st.text_input("Name des Laufs / Events")
run_date   = st.date_input("Datum des Laufs")
distance_opt = st.selectbox(
    "Distanz auswählen",
    ["5 km", "10 km", "21,0975 km", "42,195 km", "Andere…"]
)
if distance_opt == "Andere…":
    custom_dist = st.text_input("Eigene Distanz (inkl. Einheit, z.B. „15 km“)")
    distance = custom_dist.strip()
else:
    distance = distance_opt

city       = st.text_input("Stadt")
bib_no     = st.text_input("Startnummer (ohne #)")
runner     = st.text_input("Dein Name")
duration   = st.text_input("Zeit (HH:MM:SS)")

if st.button("Poster erzeugen") and gpx_file and event_name and runner and duration:

    # --- 1) GPX parsen + Zeitstempel sammeln
    gpx       = gpxpy.parse(gpx_file)
    raw_pts   = [
        (pt.longitude, pt.latitude, pt.elevation, pt.time)
        for tr in gpx.tracks for seg in tr.segments for pt in seg.points
        if pt.time is not None and pt.elevation is not None
    ]
    if len(raw_pts) < 2:
        st.error("Zu wenige valide GPX-Punkte mit Zeitstempel + Höhe.")
        st.stop()

    # --- 2) GPS-Ausreißer rausfiltern (Speed)
    def haversine(a, b):
        lon1, lat1, lon2, lat2 = map(math.radians,(a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(h))

    clean = [raw_pts[0]]
    for prev, curr in zip(raw_pts, raw_pts[1:]):
        dist = haversine(prev, curr)
        dt   = (curr[3] - prev[3]).total_seconds()
        if dt < MIN_DT_S or (dist/dt) > MAX_SPEED_M_S:
            continue
        clean.append(curr)
    if len(clean) < 2:
        st.error("Zu viele Ausreißer – zu wenige Punkte übrig.")
        st.stop()

    # --- 3) Sampling für die Karte
    pts = [(lon, lat) for lon, lat, _, _ in clean]
    if len(pts) > MAX_PTS_DISPLAY:
        step = len(pts)//MAX_PTS_DISPLAY + 1
        pts = pts[::step]

    # --- 4) Höhenprofil-Daten
    dists, elevs = [0.0], [clean[0][2]]
    cum = 0.0
    for (lon1, lat1, ele1, _), (lon2, lat2, ele2, _) in zip(clean, clean[1:]):
        seg = haversine((lon1,lat1),(lon2,lat2))
        cum += seg
        dists.append(cum/1000.0)      # in km
        elevs.append(ele2)

    # Zeige das Höhenprofil
    fig, ax = plt.subplots()
    ax.plot(dists, elevs)
    ax.set_xlabel("Distanz (km)")
    ax.set_ylabel("Höhe (m)")
    ax.set_title("Höhenprofil")
    st.pyplot(fig)

    # --- 5) Karte rendern
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    m = StaticMap(MAP_W, MAP_H, url_template=TILE)
    # Schattenlinie
    m.add_line(Line(pts, color="#CCCCCC", width=20))
    # Hauptlinie
    m.add_line(Line(pts, color="#000000", width=12))
    # Start-/Ziel-Markierung
    m.add_marker(CircleMarker(pts[0], "#008000", 30))   # grün Start
    m.add_marker(CircleMarker(pts[-1], "#FF0000", 30))  # rot Ziel

    try:
        map_img = m.render(zoom=None)
    except Exception:
        map_img = Image.new("RGB", (MAP_W, MAP_H), "white")
        draw = ImageDraw.Draw(map_img)
        # fallback line
        lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
        min_lon, max_lon = min(lons), max(lons); span_lon = max_lon-min_lon or 1e-6
        min_lat, max_lat = min(lats), max(lats); span_lat = max_lat-min_lat or 1e-6
        scale = min(MAP_W/span_lon, MAP_H/span_lat)
        pix = [((lon-min_lon)*scale, (max_lat-lat)*scale) for lon,lat in pts]
        draw.line(pix, fill="black", width=12)

    st.image(map_img, use_container_width=True)

    # --- 6) Poster zusammensetzen
    poster = Image.new("RGB", (MAP_W, MAP_H + FOOTER_H), "white")
    poster.paste(map_img, (0,0))
    draw = ImageDraw.Draw(poster)
    # Fonts
    try:
        f_big   = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
        f_small = ImageFont.truetype("DejaVuSans.ttf", 80)
    except:
        f_big = f_small = ImageFont.load_default()

    # Footer-Layout
    y0 = MAP_H + 20
    # 1) Event
    ev = event_name.upper()
    w,h = draw.textbbox((0,0), ev, font=f_big)[2:]
    draw.text(((MAP_W-w)/2, y0), ev, font=f_big, fill="black")
    # 2) Datum – Dist – Stadt
    y1 = y0 + h + 10
    date_str = run_date.strftime("%d %B %Y")
    info = f"{date_str} – {distance} – {city}"
    w2,h2 = draw.textbbox((0,0), info, font=f_small)[2:]
    draw.text(((MAP_W-w2)/2, y1), info, font=f_small, fill="black")
    # 3) Bib # Runner – Time
    y2 = y1 + h2 + 10
    bib = "#" + bib_no.strip()
    line3 = f"{bib} {runner} – {duration}"
    w3,h3 = draw.textbbox((0,0), line3, font=f_small)[2:]
    draw.text(((MAP_W-w3)/2, y2), line3, font=f_small, fill="black")

    # --- 7) Download
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    st.image(poster, use_container_width=True)
    st.download_button(
        "📥 Hochauflösendes Poster herunterladen",
        data=buf.getvalue(),
        file_name="running_poster.png",
        mime="image/png"
    )
