# -*- coding: utf-8 -*-
"""SKBVGA.DAT 만들기 - 개선판의 256색 그림 자료

   python tools/mkvga.py [--sheet 폴더]      -> SKBVGA.DAT  (--sheet: 칠한 그림을 PNG 로도)

   원판 그림은 점마다 2비트(CGA 색 0..3)다.  여기서 그림마다 "원하는 RGB" 를 정하고
   (tools/art.py 의 규칙), 모든 그림의 RGB 를 모아 240색으로 줄여(16..255) 팔레트를 만든 뒤
   색 번호로 바꿔 넣는다.  0..15 는 CGA 16색 그대로 (색이 없는 점과 글자 화면).

   파일 구조는 skbvga.c 머리말 참고.
"""
import os, sys, struct, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..'))
import art

CGA16 = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170), (170, 85, 0),
         (170, 170, 170), (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255), (255, 85, 85),
         (255, 85, 255), (255, 255, 85), (255, 255, 255)]


def build():
    assets = art.all_assets()          # [(종류, 이름, 값, RGB 그림(PIL), 바이트 수 또는 None)]
    # 팔레트: 모든 RGB 를 한 그림에 모아 줄이기
    total = sum(im.width * im.height for _, _, _, im, _ in assets)
    W = 1024
    H = (total + W - 1) // W
    big = Image.new('RGB', (W, H))
    px = big.load()
    k = 0
    for _, _, _, im, _ in assets:
        for p in im.getdata():
            px[k % W, k // W] = p
            k += 1
    q = big.quantize(colors=240, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    qp = (q.getpalette() + [0] * 720)[:240 * 3]
    used = sorted(set(q.getdata()))                 # 실제로 쓰인 번호 (연속이 아닐 수 있다)
    pal = CGA16 + [tuple(qp[i * 3:i * 3 + 3]) if i in used else (0, 0, 0) for i in range(240)]
    cands = [16 + i for i in used]
    cache = {}

    def idx(rgb):
        if rgb in cache:
            return cache[rgb]
        best, bd = 16, 1 << 30
        for i in cands:
            c = pal[i]
            d = (c[0] - rgb[0]) ** 2 * 3 + (c[1] - rgb[1]) ** 2 * 4 + (c[2] - rgb[2]) ** 2 * 2
            if d < bd:
                best, bd = i, d
        cache[rgb] = best
        return best

    out = bytearray(b'SKBVGA1\0')
    for c in pal:
        out += bytes(v * 63 // 255 for v in c)
    for kind, name, val, im, nbytes in assets:
        data = bytes(idx(p) for p in im.getdata())
        out += kind.encode() + name.encode().ljust(12, b'\0') + struct.pack('<II', val, len(data)) + data
    for name, cols in art.THEMES.items():
        data = bytes(idx(c) for c in cols)
        out += b'T' + name.encode().ljust(12, b'\0') + struct.pack('<II', 0, len(data)) + data
    open(os.path.join(ROOT, 'SKBVGA.DAT'), 'wb').write(out)
    print('SKBVGA.DAT', len(out), 'bytes,', len(assets), 'assets')
    return pal, assets, idx


if __name__ == '__main__':
    pal, assets, idx = build()
    if '--sheet' in sys.argv:
        d = sys.argv[sys.argv.index('--sheet') + 1]
        os.makedirs(d, exist_ok=True)
        for kind, name, val, im, nb in assets:
            if kind == 'P':
                q = Image.new('RGB', im.size)
                q.putdata([pal[idx(p)] for p in im.getdata()])
                q.resize((im.width * 2, im.height * 2), Image.NEAREST).save(os.path.join(d, 'P_%s.png' % name))
