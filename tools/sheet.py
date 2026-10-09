# 여러 BMP/PNG 를 한 장으로:  python tools/sheet.py 출력.png 열수 파일...
import sys
from PIL import Image
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(f).convert('RGB') for f in files]
w = max(i.width for i in ims); h = max(i.height for i in ims)
S = Image.new('RGB', (cols * (w + 2), ((len(ims) + cols - 1) // cols) * (h + 2)), (60, 60, 60))
for k, im in enumerate(ims):
    S.paste(im, ((k % cols) * (w + 2), (k // cols) * (h + 2)))
if S.width < 1400:
    S = S.resize((S.width * 2, S.height * 2), Image.NEAREST)
S.save(out)
