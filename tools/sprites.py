# 원본 EXE 안의 마스크 스프라이트 보기
import os, struct
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
E = open(os.path.join(ROOT, 'SKB.EXE'), 'rb').read()
IMG = E[struct.unpack('<H', E[8:10])[0] * 16:]
DS = 0xA39 * 16
PAL = [(0, 0, 0), (85, 255, 255), (255, 85, 255), (255, 255, 255)]
BG = (60, 90, 60)


def W(off, seg=DS):
    return struct.unpack('<H', IMG[seg + off:seg + off + 2])[0]


def masked(off, wb, rows, plane, seg=DS):
    im = Image.new('RGB', (wb * 4, rows), BG); px = im.load()
    for y in range(rows):
        for x in range(wb * 4):
            b = seg + off + y * wb + x // 4
            sh = 6 - 2 * (x & 3)
            m = (IMG[b] >> sh) & 3; v = (IMG[b + plane] >> sh) & 3
            if m != 3:
                px[x, y] = PAL[v]
            elif v:
                px[x, y] = (255, 0, 0)
    return im


def sheet(items, scale=4, cols=8):
    ims = [masked(*it) for it in items]
    cw = max(i.width for i in ims) * scale + 4; ch = max(i.height for i in ims) * scale + 4
    S = Image.new('RGB', (cw * cols, ch * ((len(ims) + cols - 1) // cols)), (40, 40, 40))
    for k, im in enumerate(ims):
        S.paste(im.resize((im.width * scale, im.height * scale), Image.NEAREST), ((k % cols) * cw, (k // cols) * ch))
    return S


if __name__ == '__main__':
    tiles = [(W(0x1787 + 2 * k), 6, 16, 0x60) for k in range(6)]
    stand = [(W(0x9ca2 + 2 * k), 6, 16, 0x60) for k in range(4)]
    walk = [(W(0x9caa + 2 * k), 8, 16, 0x80) for k in range(8)] + [(W(0x9cba + 2 * k), 6, 16, 0x60) for k in range(8)]
    push = [(W(0x9cca + 2 * k), 8, 16, 0x80) for k in range(8)] + [(W(0x9cda + 2 * k), 6, 16, 0x60) for k in range(8)]
    box = [(W(0x9cea + 2 * k), 8, 16, 0x80) for k in range(5)]
    sheet(tiles + stand + walk + push + box).save('tools/spr_game.png')
    print([hex(t[0]) for t in tiles], [hex(t[0]) for t in stand])
