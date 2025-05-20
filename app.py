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
FOOTER_H         = 350     # Erhöht für mehr Abstand

st.title("🏃‍ GPX-Map Generator – Print-Ready mit Höhenprofil")

# ——— Eingaben ———
gpx_file    = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
event_name  = st.text_input("Name des Laufs / Events")
run_date    = st.date_input("Datum des Laufs")
distance_opt = st.selectbox(
    "Distanz auswählen",
    ["5 km", "10 km", "21,0975 km", "42,195 km", "Andere…"]
)
if distance_opt == "Andere…":
    custom_dist = st.text_input("Eigene Distanz (inkl. Einheit, z.B. „15 km“)")
    distance = custom_dist.strip()
else:
    distance = distance_opt

city        = st.text_input("Stadt")
bib_no      = st.text_input("Startnummer (ohne #)")
runner      = st.text_input("Dein Name")
duration    = st.text_input("Zeit (HH:MM:SS)")

# ——— Poster-Generierung ———
if st.button("Poster erzeugen") and gpx_file and event_name and runner and duration:
    # 1) GPX parsen
    gpx = gpxpy.parse(gpx_file)
    raw = [
        (pt.longitude, pt.latitude, pt.elevation, pt.time)
        for tr in gpx.tracks for seg in tr.segments for pt in seg.points
        if pt.time and pt.elevation is not None
    ]
    if len(raw) < 2:
        st.error("Zu wenige valide GPX-Daten.")
        st.stop()

    # 2) Ausreißer-Filter
    def hav(a,b):
        lon1,lat1,lon2,lat2 = map(math.radians,(a[0],a[1],b[0],b[1]))
        dlon, dlat = lon2-lon1, lat2-lat1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2*6371000*math.asin(math.sqrt(h))

    clean = [raw[0]]
    for p,c in zip(raw, raw[1:]):
        dist = hav(p,c)
        dt   = (c[3]-p[3]).total_seconds()
        if dt < MIN_DT_S or dist/dt > MAX_SPEED_M_S:
            continue
        clean.append(c)
    if len(clean) < 2:
        st.error("Kein gültiger Track nach Filter.")
        st.stop()

    # 3) Sampling
    pts = [(lon,lat) for lon,lat,_,_ in clean]
    if len(pts)>MAX_PTS_DISPLAY:
        step = len(pts)//MAX_PTS_DISPLAY + 1
        pts = pts[::step]

    # 4) Höhenprofil
    d, e = [0.0], [clean[0][2]]
    cum = 0.0
    for (lon1,lat1,ele1,_),(lon2,lat2,ele2,_) in zip(clean,clean[1:]):
        seg = hav((lon1,lat1),(lon2,lat2))
        cum += seg
        d.append(cum/1000)
        e.append(ele2)
    fig, ax = plt.subplots()
    ax.plot(d,e, linewidth=2)
    ax.set_xlim(0, d[-1])
    ax.set_ylabel("Höhe (m)")
    ax.set_xlabel("Distanz (km)")
    ax.grid(alpha=0.3)
    st.pyplot(fig)

    # 5) Karte rendern
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    m = StaticMap(MAP_W, MAP_H, url_template=TILE)
    m.add_line(Line(pts, color="#CCCCCC", width=20))
    m.add_line(Line(pts, color="#000000", width=14))  # dickere Linie
    m.add_marker(CircleMarker(pts[0], "#00b300", 40))  # größerer Startpunkt
    m.add_marker(CircleMarker(pts[-1], "#e60000", 40)) # größerer Zielpunkt
    try:
        map_img = m.render(zoom=None)
    except:
        map_img = Image.new("RGB", (MAP_W, MAP_H), "white")
        draw_f = ImageDraw.Draw(map_img)
        draw_f.line(pts, fill="black", width=14)

    st.image(map_img, use_container_width=True)

    # 6) Poster-Canvas
    poster = Image.new("RGB", (MAP_W, MAP_H+FOOTER_H), "white")
    poster.paste(map_img, (0,0))
    draw = ImageDraw.Draw(poster)
    try:
        f_big   = ImageFont.truetype("DejaVuSans-Bold.ttf", 140)
        f_small = ImageFont.truetype("DejaVuSans.ttf", 80)
    except:
        f_big = f_small = ImageFont.load_default()

    # Footer sauber positionieren
    y0 = MAP_H + 30
    # Linie als Separator
    draw.line((200, y0, MAP_W-200, y0), fill="#cccccc", width=3)
    y0 += 20

    # Event-Name
    ev = event_name.upper()
    w,h = draw.textbbox((0,0), ev, font=f_big)[2:]
    draw.text(((MAP_W-w)/2, y0), ev, fill="black", font=f_big)
    y0 += h + 10

    # Datum – Distanz – Stadt
    info = f"{run_date.strftime('%d %B %Y')}  –  {distance}  –  {city}"
    w2,h2 = draw.textbbox((0,0), info, font=f_small)[2:]
    draw.text(((MAP_W-w2)/2, y0), info, fill="black", font=f_small)
    y0 += h2 + 10

    # Bib – Runner – Zeit
    bib = f"#{bib_no.strip()} {runner}  –  {duration}"
    w3,h3 = draw.textbbox((0,0), bib, font=f_small)[2:]
    draw.text(((MAP_W-w3)/2, y0), bib, fill="black", font=f_small)

    # 7) Download
    buf = io.BytesIO()
    poster.save(buf, format="PNG")
    st.image(poster, use_container_width=True)
    st.download_button(
        "📥 Hochauflösendes Poster herunterladen",
        data=buf.getvalue(),
        file_name="running_poster.png",
        mime="image/png"
    )
