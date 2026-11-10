"""List and save the images embedded in the Kida-Goto-Makihara PDF (DCT = JPEG, CCITT G4 = bilevel scans)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)
os.makedirs(os.path.join(HERE, "extracts"), exist_ok=True)

import io
import re
import struct

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
pdf = os.path.join(os.path.dirname(HERE), "Kida (2002).pdf")
out = os.path.join(HERE, "extracts", "kgm")
import os
os.makedirs(out, exist_ok=True)
data = open(pdf, "rb").read()

n = 0
for m in re.finditer(rb"/Subtype\s*/Image", data):
    start = data.rfind(b"obj", 0, m.start())
    end = data.find(b"stream", m.end())
    header = data[start:end]
    w = re.search(rb"/Width\s+(\d+)", header)
    h = re.search(rb"/Height\s+(\d+)", header)
    if not (w and h):
        continue
    width, height = int(w.group(1)), int(h.group(1))
    filt = re.search(rb"/Filter\s*\[?\s*/(\w+)", header)
    filt = filt.group(1).decode() if filt else "none"
    sstart = end + 6
    sstart += 2 if data[sstart:sstart + 2] == b"\r\n" else 1
    send = data.find(b"endstream", sstart)
    raw = data[sstart:send]
    print(n, width, height, filt, len(raw))
    try:
        if filt == "DCTDecode":
            img = Image.open(io.BytesIO(raw))
        elif filt == "CCITTFaxDecode":
            k = re.search(rb"/K\s+(-?\d+)", header)
            entries = [(256, 4, 1, width), (257, 4, 1, height), (258, 3, 1, 1), (259, 3, 1, 4),
                       (262, 3, 1, 1 if b"/BlackIs1 true" in header else 0), (273, 4, 1, 0),
                       (278, 4, 1, height), (279, 4, 1, len(raw))]
            ifd_size = 2 + 12 * len(entries) + 4
            entries[5] = (273, 4, 1, 8 + ifd_size)
            ifd = struct.pack("<H", len(entries))
            for tag, typ, cnt, val in entries:
                ifd += struct.pack("<HHI", tag, typ, cnt) + (struct.pack("<H", val) + b"\0\0" if typ == 3 else struct.pack("<I", val))
            ifd += struct.pack("<I", 0)
            img = Image.open(io.BytesIO(b"II*\0" + struct.pack("<I", 8) + ifd + raw))
        else:
            n += 1
            continue
        img = img.convert("L")
        img.save(f"{out}\\im{n:02d}_{width}x{height}.png")
    except Exception as e:
        print("  skip", e)
    n += 1
