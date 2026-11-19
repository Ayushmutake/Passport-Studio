import io

import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="PassPort Studio", page_icon="🖼", layout="wide")

PHOTO_SIZES = {
    "35 × 45 mm — Standard passport": (35, 45),
    "51 × 51 mm — US passport": (51, 51),
    "40 × 60 mm — Visa photo": (40, 60),
    "25 × 35 mm — Small format": (25, 35),
}
SHEET_SIZES = {
    "A4 — 210 × 297 mm": (210, 297),
    "4 × 6 inch — 102 × 152 mm": (102, 152),
    "5 × 7 inch — 127 × 178 mm": (127, 178),
}
MARGIN = 5  # mm
DPI = 300
PX_PER_MM = DPI / 25.4


@st.cache_data(show_spinner=False)
def load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # respect phone-camera rotation
    return img.convert("RGB")


def crop_to_size(img, w_mm, h_mm, zoom, ox, oy, px_per_mm):
    """Crop to the exact aspect ratio (never stretches), then resize."""
    W, H = round(w_mm * px_per_mm), round(h_mm * px_per_mm)
    iw, ih = img.size
    target = w_mm / h_mm
    if iw / ih > target:
        ch, cw = ih, ih * target
    else:
        cw, ch = iw, iw / target
    cw, ch = cw / zoom, ch / zoom
    sx, sy = (iw - cw) * ox, (ih - ch) * oy
    return img.resize((W, H), Image.LANCZOS, box=(sx, sy, sx + cw, sy + ch))


def build_sheet(photos, ph, sh, spacing):
    """photos: list of (image, qty, zoom, ox, oy). Returns (sheet, cols, rows, used)."""
    pw, pheight = ph
    sw, sheight = sh
    cols = max(0, int((sw - MARGIN * 2 + spacing) // (pw + spacing)))
    rows = max(0, int((sheight - MARGIN * 2 + spacing) // (pheight + spacing)))
    grid_w = cols * pw + (cols - 1) * spacing
    grid_h = rows * pheight + (rows - 1) * spacing
    off_x, off_y = (sw - grid_w) / 2, (sheight - grid_h) / 2

    sheet = Image.new("RGB", (round(sw * PX_PER_MM), round(sheight * PX_PER_MM)), "white")

    copies = []
    for img, qty, zoom, ox, oy in photos:
        tile = crop_to_size(img, pw, pheight, zoom, ox, oy, PX_PER_MM)
        copies.extend([tile] * qty)

    used = 0
    for i, tile in enumerate(copies[: cols * rows]):
        r, c = divmod(i, cols)
        x = round((off_x + c * (pw + spacing)) * PX_PER_MM)
        y = round((off_y + r * (pheight + spacing)) * PX_PER_MM)
        sheet.paste(tile, (x, y))
        used += 1
    return sheet, cols, rows, len(copies), used


# ───────── UI ─────────
st.title("PassPort Studio")
st.caption("Upload photos, auto-crop to passport size, download a print-ready 300 DPI sheet.")

with st.sidebar:
    st.header("Layout settings")
    photo_label = st.selectbox("Photo size", list(PHOTO_SIZES))
    sheet_label = st.selectbox("Sheet size", list(SHEET_SIZES))
    spacing = st.select_slider("Spacing between photos (mm)", options=[2, 3, 5], value=3)

ph, sh = PHOTO_SIZES[photo_label], SHEET_SIZES[sheet_label]

files = st.file_uploader(
    "Upload photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True
)

if not files:
    st.info("Upload one or more photos to get started.")
    st.stop()

photos = []
st.subheader("Photos")
for i, f in enumerate(files):
    img = load_image(f.getvalue())
    with st.expander(f"{f.name}", expanded=len(files) == 1):
        c1, c2 = st.columns([1, 2])
        qty = c2.number_input("Copies", 1, 60, 1, key=f"qty{i}")
        zoom = c2.slider("Zoom", 1.0, 3.0, 1.0, 0.01, key=f"zoom{i}")
        ox = c2.slider("Left / right", 0.0, 1.0, 0.5, 0.01, key=f"ox{i}")
        oy = c2.slider("Up / down", 0.0, 1.0, 0.35, 0.01, key=f"oy{i}")
        c1.image(crop_to_size(img, *ph, zoom, ox, oy, 8), caption="Crop preview")
    photos.append((img, int(qty), zoom, ox, oy))

sheet, cols, rows, total, used = build_sheet(photos, ph, sh, spacing)
slots = cols * rows

if total > slots:
    st.warning(
        f"Too many copies for this sheet ({total} copies, {slots} slots). "
        "Extra copies are not shown — reduce quantities or choose a larger sheet."
    )

st.subheader("Print preview")
st.caption(f"{photo_label.split(' — ')[0]} photos · {sheet_label.split(' — ')[0]} sheet · "
           f"{cols}×{rows} grid · {used}/{slots} slots used")

preview = sheet.copy()
preview.thumbnail((1000, 1400))
_, mid, _ = st.columns([1, 2, 1])
mid.image(preview, use_container_width=True)

png = io.BytesIO()
sheet.save(png, "PNG", dpi=(DPI, DPI))
pdf = io.BytesIO()
sheet.save(pdf, "PDF", resolution=DPI)

d1, d2, _ = st.columns([1, 1, 3])
d1.download_button("⬇ Download PNG", png.getvalue(), "passport-photos.png", "image/png",
                   type="primary", use_container_width=True)
d2.download_button("⬇ Download PDF", pdf.getvalue(), "passport-photos.pdf", "application/pdf",
                   use_container_width=True)