"""Pull the CCITT G4 page images out of a scanned PDF and save them as PNG (half and full size)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)
os.makedirs(os.path.join(HERE, "extracts"), exist_ok=True)

import re
import struct
from PIL import Image
import io

pdf = os.path.join(os.path.dirname(HERE), "Hosokawa (1989).pdf")
out = os.path.join(HERE, "extracts")
data = open(pdf, "rb").read()

n = 0
for m in re.finditer(rb"/Subtype\s*/Image", data):
    start = data.rfind(b"obj", 0, m.start())
    end = data.find(b"stream", m.end())
    header = data[start:end]
    print(header[:300])
    sstart = end + len(b"stream")
    if data[sstart:sstart + 2] == b"\r\n":
        sstart += 2
    else:
        sstart += 1
    send = data.find(b"endstream", sstart)
    raw = data[sstart:send]
    width = int(re.search(rb"/Width (\d+)", header).group(1))
    height = int(re.search(rb"/Height (\d+)", header).group(1))
    k = re.search(rb"/K (-?\d+)", header)
    blackis1 = b"/BlackIs1 true" in header
    print(n, width, height, len(raw), "K", k.group(1) if k else None, "BlackIs1", blackis1)

    # minimal little-endian TIFF with Group 4 compression wrapping the raw strip
    entries = [
        (256, 4, 1, width),          # ImageWidth
        (257, 4, 1, height),         # ImageLength
        (258, 3, 1, 1),              # BitsPerSample
        (259, 3, 1, 4),              # Compression = CCITT G4
        (262, 3, 1, 0 if not blackis1 else 1),  # Photometric: 0 = WhiteIsZero
        (273, 4, 1, 0),              # StripOffsets (patched)
        (278, 4, 1, height),         # RowsPerStrip
        (279, 4, 1, len(raw)),       # StripByteCounts
    ]
    ifd_off = 8
    ifd_size = 2 + 12 * len(entries) + 4
    strip_off = ifd_off + ifd_size
    entries[5] = (273, 4, 1, strip_off)
    ifd = struct.pack("<H", len(entries))
    for tag, typ, cnt, val in entries:
        ifd += struct.pack("<HHI", tag, typ, cnt) + (struct.pack("<H", val) + b"\0\0" if typ == 3 else struct.pack("<I", val))
    ifd += struct.pack("<I", 0)
    tiff = b"II*\0" + struct.pack("<I", ifd_off) + ifd + raw
    img = Image.open(io.BytesIO(tiff)).convert("L")
    img.save(f"{out}\\hy_p{n}_full.png")
    img.resize((width // 3, height // 3), Image.LANCZOS).save(f"{out}\\hy_p{n}.png")
    n += 1
