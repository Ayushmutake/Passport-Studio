import base64
import html
import io

import streamlit as st
from PIL import Image, ImageDraw, ImageOps

st.set_page_config(page_title="PassPort Studio — Photo Print Layout", page_icon="🖼", layout="wide")

PHOTO_SIZES = {
    "35 × 45 mm — Standard passport": (35, 45),
    "51 × 51 mm — US passport": (51, 51),
    "40 × 60 mm — Visa photo": (40, 60),
    "25 × 35 mm — Small format": (25, 35),
}
SHEET_SIZES = {
    "A4 — 210 × 297 mm": ("A4", 210, 297),
    "4 × 6 inch — 102 × 152 mm": ("4×6 in", 102, 152),
    "5 × 7 inch — 127 × 178 mm": ("5×7 in", 127, 178),
}
SPACINGS = {"2 mm — tight": 2, "3 mm — standard": 3, "5 mm — loose": 5}
MARGIN = 5  # mm
DPI = 300
PX_PER_MM = DPI / 25.4
PREVIEW_PPM = 6  # preview resolution (px per mm)
CROP_LEN, CROP_GAP = 2, 0.6  # mm
DEF_ZOOM, DEF_OX, DEF_OY = 1.0, 0.5, 0.35

# ───────────────────────── Styling (matches the HTML version) ─────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{--ink:#0f0f0f;--paper:#f7f4ef;--cream:#ede9e0;--accent:#c84b2f;--accent-light:#fdf0ec;--mid:#6b6560;--border:#d4cec4;}

html, body, .stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp [data-baseweb], .stMarkdown, [data-testid="stExpander"] summary {font-family:'DM Sans',sans-serif !important;}
.stApp{background:var(--paper);color:var(--ink);}

/* hide default Streamlit chrome */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebarHeader"], [data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"], #MainMenu, footer {display:none !important;}

/* fixed dark header */
.ps-header{position:fixed;top:0;left:0;right:0;height:64px;background:var(--ink);color:#fff;
  display:flex;align-items:center;padding:0 2rem;z-index:999999;}
.ps-logo{display:flex;align-items:center;gap:10px;}
.ps-logo-icon{width:32px;height:32px;background:var(--accent);border-radius:6px;display:flex;align-items:center;justify-content:center;}
.ps-logo-icon svg{width:18px;height:18px;fill:#fff;}
.ps-logo-text{font-family:'DM Serif Display',serif !important;font-size:20px;letter-spacing:-0.3px;}
.ps-logo-text span{color:var(--accent);}

/* layout */
[data-testid="stMainBlockContainer"], .block-container{padding:96px 2rem 3rem !important;max-width:100% !important;}
section[data-testid="stSidebar"]{width:340px !important;min-width:340px !important;background:#fff;border-right:1px solid var(--border);}
section[data-testid="stSidebar"] > div{width:340px !important;}
[data-testid="stSidebarUserContent"]{padding:80px 1.5rem 2rem !important;}

/* sidebar sections */
.section-title{font-size:10px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--mid);margin:0 0 12px;}
.section-title.sep{border-top:1px solid var(--border);padding-top:1.25rem;margin-top:1.25rem;}
.badge{font-size:11px;background:var(--ink);color:#fff;border-radius:10px;padding:1px 7px;margin-left:4px;letter-spacing:0;}

/* upload zone */
[data-testid="stFileUploaderDropzone"]{border:1.5px dashed var(--border);border-radius:10px;background:var(--paper);transition:all .2s;}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--accent);background:var(--accent-light);}
[data-testid="stFileUploaderDropzone"] button{border-radius:6px;font-size:12px;}

/* photo items */
[class*="st-key-item_"]{background:var(--paper);border:1px solid var(--border);border-radius:8px;padding:8px;gap:.4rem !important;margin-bottom:8px;}
[class*="st-key-item_"]:hover{border-color:#b0a89a;}
.photo-row{display:flex;align-items:center;gap:10px;}
.photo-thumb{width:42px;border-radius:4px;border:1px solid var(--border);background:var(--cream);display:block;flex-shrink:0;}
.photo-info{min-width:0;flex:1;}
.photo-name{font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px;}
.photo-copies{font-size:11px;color:var(--mid);}
.qty-num{font-size:14px;font-weight:600;text-align:center;}
[class*="st-key-minus_"] button, [class*="st-key-plus_"] button{width:26px;height:26px;min-height:26px;padding:0;border-radius:50%;
  line-height:1;font-size:15px;background:#fff;color:var(--ink);border:1px solid var(--border);}
[class*="st-key-plus_"] button{background:var(--ink);color:#fff;border-color:var(--ink);}
[class*="st-key-plus_"] button:hover{background:var(--accent);border-color:var(--accent);color:#fff;}
[class*="st-key-minus_"] button p, [class*="st-key-plus_"] button p{color:inherit;font-size:15px;line-height:1;}
[class*="st-key-item_"] [data-testid="stExpander"]{border:none;background:transparent;}
[class*="st-key-item_"] [data-testid="stExpander"] summary{padding:.1rem 0;color:var(--accent);font-size:11px;}
[class*="st-key-item_"] [data-testid="stExpander"] summary p{font-size:11px;color:var(--accent);}
[class*="st-key-reset_"] button{font-size:11px;min-height:0;padding:3px 8px;border-radius:5px;color:var(--mid);}

/* inputs */
[data-testid="stWidgetLabel"] p{font-size:12px;font-weight:500;color:var(--mid);}
[data-baseweb="select"] > div{border-radius:6px;border-color:var(--border);background:#fff;font-size:13px;}

/* buttons */
.stButton button, .stDownloadButton button{border-radius:6px;font-size:13px;font-weight:500;border:1px solid var(--border);
  background:#fff;color:var(--ink);transition:all .15s;}
.stButton button:hover, .stDownloadButton button:hover{background:var(--cream);border-color:var(--border);color:var(--ink);}
.st-key-dl_png button{background:var(--accent);color:#fff;border:none;}
.st-key-dl_png button:hover{background:#b03d22;color:#fff;}
.st-key-dl_pdf button{background:var(--ink);color:#fff;border:none;}
.st-key-dl_pdf button:hover{background:#2a2a2a;color:#fff;}
.st-key-dl_png button p, .st-key-dl_pdf button p{color:#fff;}
.st-key-dl_png button:disabled{background:var(--accent) !important;color:#fff !important;opacity:.4;cursor:not-allowed;}
.st-key-dl_pdf button:disabled{background:var(--ink) !important;color:#fff !important;opacity:.4;cursor:not-allowed;}
.st-key-dl_png button:disabled p, .st-key-dl_pdf button:disabled p{color:#fff !important;}
[class*="st-key-item_"] [data-testid="stExpander"]{margin-top:8px;}
.photo-copies{white-space:nowrap;}
[class*="st-key-item_"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:4px !important;}
[class*="st-key-item_"] [data-testid="stColumn"]{min-width:0 !important;}
[class*="st-key-item_"] [data-testid="stColumn"]:first-child{flex:1 1 auto !important;width:auto !important;}
[class*="st-key-item_"] [data-testid="stColumn"]:not(:first-child){flex:0 0 28px !important;width:28px !important;min-width:28px !important;}
[class*="st-key-minus_"] button, [class*="st-key-plus_"] button{width:26px !important;}
[class*="st-key-item_"] [data-testid="stElementContainer"]{width:auto;}

/* stats */
.stats-bar{display:flex;background:var(--paper);border:1px solid var(--border);border-radius:8px;overflow:hidden;}
.stat-item{flex:1;padding:10px 8px;text-align:center;border-right:1px solid var(--border);}
.stat-item:last-child{border-right:none;}
.stat-val{font-size:18px;font-weight:600;line-height:1;}
.stat-label{font-size:10px;color:var(--mid);margin-top:2px;}

/* main */
.preview-title{font-family:'DM Serif Display',serif !important;font-size:22px;}
.preview-subtitle{font-size:13px;color:var(--mid);margin-top:2px;}
.overflow-warn{background:#fef3ed;border:1px solid #f5c4a1;border-radius:6px;padding:10px 14px;font-size:13px;color:#7a3b10;margin-bottom:1rem;}
.sheet-container{display:flex;justify-content:center;align-items:flex-start;background:var(--cream);border:1px solid var(--border);
  border-radius:10px;padding:2rem;overflow:auto;}
.print-sheet{background:#fff;box-shadow:0 4px 24px rgba(0,0,0,.12);max-width:100%;height:auto;flex-shrink:0;display:block;}
.empty-preview{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:400px;gap:12px;color:var(--mid);}
.empty-preview .big-icon{font-size:52px;opacity:.4;}
.empty-preview h3{font-family:'DM Serif Display',serif !important;font-size:20px;color:var(--ink);margin:0;padding:0;font-weight:400;}
.empty-preview p{font-size:14px;margin:0;}
</style>
"""

HEADER = """
<div class="ps-header"><div class="ps-logo">
  <div class="ps-logo-icon"><svg viewBox="0 0 18 18"><rect x="2" y="2" width="6" height="8" rx="1"/><rect x="10" y="2" width="6" height="8" rx="1"/><rect x="2" y="12" width="6" height="4" rx="1"/><rect x="10" y="12" width="6" height="4" rx="1"/></svg></div>
  <span class="ps-logo-text">Pass<span>Port</span> Studio</span>
</div></div>
"""


# ───────────────────────── Image helpers ─────────────────────────
@st.cache_data(show_spinner=False)
def load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # respect phone-camera rotation
    return img.convert("RGB")


def crop_to_size(img, w_mm, h_mm, zoom, ox, oy, ppm):
    """Crop to the exact aspect ratio (never stretches), then resize."""
    W, H = max(1, round(w_mm * ppm)), max(1, round(h_mm * ppm))
    iw, ih = img.size
    target = w_mm / h_mm
    if iw / ih > target:
        ch, cw = ih, ih * target
    else:
        cw, ch = iw, iw / target
    cw, ch = cw / zoom, ch / zoom
    sx, sy = (iw - cw) * ox, (ih - ch) * oy
    return img.resize((W, H), Image.LANCZOS, box=(sx, sy, sx + cw, sy + ch))


def to_b64(img, fmt="JPEG", quality=90):
    buf = io.BytesIO()
    img.save(buf, fmt, quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


def grid_for(ph, sh_w, sh_h, spacing):
    pw, pheight = ph
    cols = max(0, int((sh_w - MARGIN * 2 + spacing) // (pw + spacing)))
    rows = max(0, int((sh_h - MARGIN * 2 + spacing) // (pheight + spacing)))
    return cols, rows


def build_sheet(photos, ph, sh_w, sh_h, spacing, ppm, preview=False, marks=False):
    """photos: list of (image, qty, zoom, ox, oy). Returns (sheet, used)."""
    pw, pheight = ph
    cols, rows = grid_for(ph, sh_w, sh_h, spacing)
    grid_w = cols * pw + (cols - 1) * spacing
    grid_h = rows * pheight + (rows - 1) * spacing
    off_x, off_y = (sh_w - grid_w) / 2, (sh_h - grid_h) / 2

    sheet = Image.new("RGB", (round(sh_w * ppm), round(sh_h * ppm)), "white")
    d = ImageDraw.Draw(sheet)

    copies = []
    for img, qty, zoom, ox, oy in photos:
        tile = crop_to_size(img, pw, pheight, zoom, ox, oy, ppm)
        copies.extend([tile] * qty)

    t, ln, off = max(1, round(0.15 * ppm)), round(CROP_LEN * ppm), round((CROP_GAP + CROP_LEN) * ppm)
    used = 0
    for i in range(cols * rows):
        r, c = divmod(i, cols)
        x = round((off_x + c * (pw + spacing)) * ppm)
        y = round((off_y + r * (pheight + spacing)) * ppm)
        w, h = round(pw * ppm), round(pheight * ppm)
        if i < len(copies):
            sheet.paste(copies[i], (x, y))
            used += 1
        elif preview:
            d.rectangle([x, y, x + w - 1, y + h - 1], fill="#f0eeea")  # empty slot (screen only)
        if preview and marks:
            for right in (0, 1):
                for bottom in (0, 1):
                    ex, ey = (x + w if right else x), (y + h if bottom else y)
                    hx = ex + (off - ln) if right else ex - off
                    hy = ey - (t if bottom else 0)
                    d.rectangle([hx, hy, hx + ln - 1, hy + t - 1], fill="#999999")
                    vx = ex - (t if right else 0)
                    vy = ey + (off - ln) if bottom else ey - off
                    d.rectangle([vx, vy, vx + t - 1, vy + ln - 1], fill="#999999")
    return sheet, used


# ───────────────────────── State / callbacks ─────────────────────────
st.session_state.setdefault("uploader_n", 0)


def bump_qty(key, delta):
    st.session_state[key] = max(1, st.session_state.get(key, 1) + delta)


def reset_crop(fid):
    st.session_state[f"zoom_{fid}"] = DEF_ZOOM
    st.session_state[f"ox_{fid}"] = DEF_OX
    st.session_state[f"oy_{fid}"] = DEF_OY


def clear_all():
    st.session_state.uploader_n += 1  # new key => empty uploader


def title(text, sep=True):
    st.markdown(f'<div class="section-title{" sep" if sep else ""}">{text}</div>', unsafe_allow_html=True)


# ───────────────────────── UI ─────────────────────────
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(HEADER, unsafe_allow_html=True)

# containers keep sidebar order: Upload → Photos → Settings → Summary,
# while letting us fill settings first (photo thumbnails need the photo size)
up_c = st.sidebar.container()
list_c = st.sidebar.container()
set_c = st.sidebar.container()
stat_c = st.sidebar.container()

with set_c:
    title("Layout Settings")
    photo_label = st.selectbox("Photo size", list(PHOTO_SIZES))
    sheet_label = st.selectbox("Sheet size", list(SHEET_SIZES))
    spacing_label = st.selectbox("Spacing between photos", list(SPACINGS), index=1)
    marks_label = st.selectbox("Crop / cut marks", ["Show crop marks", "Hide crop marks"])

ph = PHOTO_SIZES[photo_label]
sheet_name, sh_w, sh_h = SHEET_SIZES[sheet_label]
spacing = SPACINGS[spacing_label]
show_marks = marks_label == "Show crop marks"
cols, rows = grid_for(ph, sh_w, sh_h, spacing)
slots = cols * rows

with up_c:
    title("Upload Photos", sep=False)
    files = st.file_uploader(
        "Upload photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_n}", label_visibility="collapsed",
    )

photos = []
with list_c:
    if files:
        title(f'Photos <span class="badge">{len(files)}</span>')
        for f in files:
            fid = getattr(f, "file_id", None) or f"{f.name}-{f.size}"
            img = load_image(f.getvalue())
            qk = f"qty_{fid}"
            st.session_state.setdefault(qk, 1)
            st.session_state.setdefault(f"zoom_{fid}", DEF_ZOOM)
            st.session_state.setdefault(f"ox_{fid}", DEF_OX)
            st.session_state.setdefault(f"oy_{fid}", DEF_OY)
            zoom = st.session_state[f"zoom_{fid}"]
            ox, oy = st.session_state[f"ox_{fid}"], st.session_state[f"oy_{fid}"]
            qty = st.session_state[qk]

            name = html.escape(f.name.rsplit(".", 1)[0])
            thumb = to_b64(crop_to_size(img, *ph, zoom, ox, oy, 4))
            with st.container(key=f"item_{fid}"):
                c0, c1, c2, c3 = st.columns([6, 1, 1, 1], vertical_alignment="center", gap="small")
                c0.markdown(
                    f'<div class="photo-row"><img class="photo-thumb" src="data:image/jpeg;base64,{thumb}" />'
                    f'<div class="photo-info"><div class="photo-name" title="{name}">{name}</div>'
                    f'<div class="photo-copies">{qty} cop{"y" if qty == 1 else "ies"}</div></div></div>',
                    unsafe_allow_html=True,
                )
                c1.button("−", key=f"minus_{fid}", on_click=bump_qty, args=(qk, -1), help="Remove one copy")
                c2.markdown(f'<div class="qty-num">{qty}</div>', unsafe_allow_html=True)
                c3.button("+", key=f"plus_{fid}", on_click=bump_qty, args=(qk, 1), help="Add one more copy")
                with st.expander("Adjust crop"):
                    st.slider("Zoom", 1.0, 3.0, step=0.01, key=f"zoom_{fid}")
                    st.slider("Left / right", 0.0, 1.0, step=0.01, key=f"ox_{fid}")
                    st.slider("Up / down", 0.0, 1.0, step=0.01, key=f"oy_{fid}")
                    st.button("Reset crop", key=f"reset_{fid}", on_click=reset_crop, args=(fid,))
            photos.append((img, int(qty), zoom, ox, oy))

total = sum(p[1] for p in photos)
with stat_c:
    title("Summary")
    st.markdown(
        f'<div class="stats-bar">'
        f'<div class="stat-item"><div class="stat-val">{len(photos)}</div><div class="stat-label">Photos</div></div>'
        f'<div class="stat-item"><div class="stat-val">{total}</div><div class="stat-label">Copies</div></div>'
        f'<div class="stat-item"><div class="stat-val">{slots}</div><div class="stat-label">Slots</div></div></div>',
        unsafe_allow_html=True,
    )

# ───────────────────────── Main area ─────────────────────────
png_bytes = pdf_bytes = b""
preview_html = ""
if photos:
    full, used = build_sheet(photos, ph, sh_w, sh_h, spacing, PX_PER_MM)  # print-ready: blank empty slots, no marks
    buf = io.BytesIO()
    full.save(buf, "PNG", dpi=(DPI, DPI))
    png_bytes = buf.getvalue()
    buf = io.BytesIO()
    full.save(buf, "PDF", resolution=DPI)
    pdf_bytes = buf.getvalue()

    prev, _ = build_sheet(photos, ph, sh_w, sh_h, spacing, PREVIEW_PPM, preview=True, marks=show_marks)
    preview_html = (
        f'<div class="sheet-container"><img class="print-sheet" style="width:{sh_w}mm" '
        f'src="data:image/jpeg;base64,{to_b64(prev, quality=92)}" /></div>'
    )
    subtitle = (f"{ph[0]}×{ph[1]}mm photos · {sheet_name} sheet · {cols}×{rows} grid · "
                f"{min(total, slots)}/{slots} slots used")
else:
    subtitle = "Upload photos to get started"
    preview_html = (
        '<div class="sheet-container"><div class="empty-preview"><div class="big-icon">🖼</div>'
        "<h3>No photos yet</h3><p>Upload passport photos from the sidebar to arrange them</p></div></div>"
    )

tb, b1, b2, b3 = st.columns([4, 1.3, 1.7, 1.8], vertical_alignment="center")
tb.markdown(
    f'<div class="preview-title">Print Preview</div><div class="preview-subtitle">{subtitle}</div>',
    unsafe_allow_html=True,
)
b1.button("🗑 Clear all", key="clear", on_click=clear_all, use_container_width=True)
b2.download_button("⬇ Download PDF", pdf_bytes, "passport-photos.pdf", "application/pdf",
                   key="dl_pdf", disabled=not photos, use_container_width=True)
b3.download_button("⬇ Download PNG", png_bytes, "passport-photos.png", "image/png",
                   key="dl_png", disabled=not photos, use_container_width=True)

if total > slots:
    st.markdown(
        '<div class="overflow-warn">⚠️ Too many copies for this sheet — extra copies are not shown. '
        "Reduce quantities or choose a larger sheet.</div>",
        unsafe_allow_html=True,
    )

st.markdown(preview_html, unsafe_allow_html=True)
