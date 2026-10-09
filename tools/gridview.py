# 그림 일부를 확대해 10점 격자와 좌표를 그린다:  python tools/gridview.py 화면 x0 y0 x1 y1 [배율] [출력]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import art, scenes
name = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6])
sc = int(sys.argv[6]) if len(sys.argv) > 6 else 4
out = sys.argv[7] if len(sys.argv) > 7 else 'tools/gv.png'
parts = scenes.SCREENS[name][0]
buf = b''.join(art.rle(p) for p in parts)
v = art.pixels(buf)
im = Image.new('RGB', (320, len(buf) // 80)); im.putdata([art.CGA[x] for x in v])
im = im.crop((x0, y0, x1 + 1, y1 + 1)).resize(((x1 - x0 + 1) * sc, (y1 - y0 + 1) * sc), Image.NEAREST)
d = ImageDraw.Draw(im)
for x in range((x0 + 9) // 10 * 10, x1 + 1, 10):
    d.line([((x - x0) * sc, 0), ((x - x0) * sc, im.height)], fill=(255, 0, 0) if x % 50 == 0 else (150, 150, 150))
    d.text(((x - x0) * sc + 2, 2), str(x), fill=(255, 0, 0))
for y in range((y0 + 9) // 10 * 10, y1 + 1, 10):
    d.line([(0, (y - y0) * sc), (im.width, (y - y0) * sc)], fill=(255, 0, 0) if y % 50 == 0 else (150, 150, 150))
    d.text((2, (y - y0) * sc + 2), str(y), fill=(255, 0, 0))
im.save(out)
