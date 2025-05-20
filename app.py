import io, math
import gpxpy, streamlit as st
from datetime import datetime
from staticmap import StaticMap, Line, CircleMarker
from PIL import Image, ImageDraw, ImageFont

# ——— Konfiguration ———
MAX_SPEED_M_S   = 10      # >36 km/h filtern
MIN_DT_S        = 1       # mind. 1 s
MAX_PTS_DISPLAY = 2000    # Sampling-Limit
# Karte leicht kleiner für mehr Footer
MAP_W, MAP_H    = 2480, 3000
PAD_HORIZ       = 200     # horizontaler Seitenrand
PAD_VERT        = 40      # vertikaler Abstand
BOTTOM_EXTRA    = 300     # zusätzlicher Unterkante-Puffer

st.set_page_config(layout="wide")
st.title("🏃‍ GPX-Map Generator – Print-Ready")

# ——— Farbauswahl (Sidebar) ———
st.sidebar.header("🎨 Farbauswahl")
route_color        = st.sidebar.color_picker("Streckenfarbe", "#000000")
route_shadow_color = st.sidebar.color_picker("Schattenfarbe der Strecke", "#CCCCCC")
start_color        = st.sidebar.color_picker("Startpunkt-Farbe", "#00b300")
end_color          = st.sidebar.color_picker("Zielpunkt-Farbe", "#e60000")
footer_bg_color    = st.sidebar.color_picker("Footer Hintergrund", "#FFFFFF")
footer_text_color  = st.sidebar.color_picker("Footer Haupttext", "#000000")
footer_meta_color  = st.sidebar.color_picker("Footer Metatext", "#555555")

# ——— Eingaben ———
gpx_file    = st.file_uploader("GPX-Datei (.gpx) hochladen", type="gpx")
event_name  = st.text_input("Name des Laufs / Events")
run_date    = st.date_input("Datum des Laufs")
distance_opt = st.selectbox(
    "Distanz auswählen",
    ["5 km", "10 km", "21,0975 km", "42,195 km", "Andere…"]
)
if distance_opt == "Andere…":
    custom_dist = st.text_input("Eigene Distanz (z.B. '15 km')")
    distance = (custom_dist.strip() or distance_opt)
else:
    distance = distance_opt

city     = st.text_input("Stadt")
bib_no   = st.text_input("Startnummer (ohne #)")
runner   = st.text_input("Dein Name")
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

    # 2) Ausreißer filtern
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

    # 4) Karte rendern
    TILE = "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    m = StaticMap(MAP_W, MAP_H, url_template=TILE)
    m.add_line(Line(pts, color=route_shadow_color, width=18))
    m.add_line(Line(pts, color=route_color, width=10))
    m.add_marker(CircleMarker(pts[0], start_color, 30))
    m.add_marker(CircleMarker(pts[-1], end_color, 30))
    map_img = m.render(zoom=14)
    st.image(map_img, use_container_width=True)

    # 5) Footer-Höhe berechnen
    try:
        f_event = ImageFont.truetype("DejaVuSans-Bold.ttf", 160)
        f_info  = ImageFont.truetype("DejaVuSans.ttf", 100)
        f_meta  = ImageFont.truetype("DejaVuSans.ttf", 100)
    except:
        f_event = f_info = f_meta = ImageFont.load_default()
    ev       = event_name.upper()
    date_str = run_date.strftime('%d.%m.%Y')
    top_line = ev
    mid_line = city
    date_line = f"{date_str} - {distance}"
    bot_line  = f"#{bib_no.strip()} - {runner} - {duration}"

    tmp = Image.new('RGB', (1,1)); dtmp = ImageDraw.Draw(tmp)
    be = dtmp.textbbox((0,0), top_line, font=f_event)
    bm1 = dtmp.textbbox((0,0), mid_line, font=f_info)
    bm2 = dtmp.textbbox((0,0), date_line, font=f_info)
    bm3 = dtmp.textbbox((0,0), bot_line, font=f_meta)
    footer_h = (be[3]-be[1]) + PAD_VERT + (bm1[3]-bm1[1]) + PAD_VERT + 3 + PAD_VERT + (bm2[3]-bm2[1]) + PAD_VERT + (bm3[3]-bm3[1]) + BOTTOM_EXTRA

    # 6) Poster-Canvas
    poster = Image.new("RGB", (MAP_W, MAP_H + footer_h), footer_bg_color)
    poster.paste(map_img, (0, 0))
    draw = ImageDraw.Draw(poster)
    y = MAP_H + PAD_VERT

    # Event-Name
    w_e, h_e = be[2]-be[0], be[3]-be[1]
    draw.text(((MAP_W-w_e)/2, y), top_line, font=f_event, fill=footer_text_color)
    y += h_e + PAD_VERT

    # Stadt
    w_c, h_c = bm1[2]-bm1[0], bm1[3]-bm1[1]
    draw.text(((MAP_W-w_c)/2, y), mid_line, font=f_info, fill=footer_meta_color)
    y += h_c + PAD_VERT

    # Trenner
    draw.line((PAD_HORIZ, y, MAP_W-PAD_HORIZ, y), fill=footer_meta_color, width=3)
    y += PAD_VERT

    # Datum - Distanz
    w_d, h_d = bm2[2]-bm2[0], bm2[3]-bm2[1]
    draw.text(((MAP_W-w_d)/2, y), date_line, font=f_info, fill=footer_meta_color)
    y += h_d + PAD_VERT

    # Startnummer - Name - Zeit
    w_b, h_b = bm3[2]-bm3[0], bm3[3]-bm3[1]
    draw.text(((MAP_W-w_b)/2, y), bot_line, font=f_meta, fill=footer_text_color)

    # 7) Download
    buf = io.BytesIO(); poster.save(buf, format="PNG")
    st.download_button(label="📥 Poster herunterladen", data=buf.getvalue(), file_name="running_poster.png", mime="image/png", key="poster_download")
