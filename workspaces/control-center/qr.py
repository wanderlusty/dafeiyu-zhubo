import io
import sys

import qrcode

qr = qrcode.QRCode(border=2, box_size=6)
qr.add_data(sys.argv[1])
qr.make(fit=True)
image = qr.make_image(fill_color="#1d2530", back_color="white")
out = io.BytesIO()
image.save(out, format="PNG")
sys.stdout.buffer.write(out.getvalue())
