# 원판 그림 파일(RLE) 풀기 -> PNG 보기
import os, sys
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PAL = [(0, 0, 0), (85, 255, 255), (255, 85, 255), (255, 255, 255)]


def rle(name):
    d = open(os.path.join(ROOT, name.upper()), 'rb').read()
    out = bytearray(); i = 0
    while True:
        c = d[i]; i += 1
        if c & 0x80:
            out += bytes([d[i]]) * (c & 0x7f); i += 1
        else:
            out += d[i:i + c]; i += c
        if d[i] == 0:
            break
    return bytes(out)


def to_img(buf, rows):
    im = Image.new('RGB', (320, rows)); px = im.load()
    for y in range(rows):
        for x in range(320):
            b = buf[y * 80 + x // 4]
            px[x, y] = PAL[(b >> (6 - 2 * (x & 3))) & 3]
    return im


if __name__ == '__main__':
    for pair in [('intro1', 'intro2'), ('lobby11', 'lobby12'), ('players1', 'players2'), ('select1', 'select2'),
                 ('select3', 'select4'), ('tour1', 'tour2'), ('pause1', 'pause1a'), ('icons1', 'icons2')]:
        bufs = [rle(n) for n in pair]
        print(pair, [len(b) for b in bufs])
        buf = b''.join(bufs)
        to_img(buf, len(buf) // 80).resize((640, 2 * (len(buf) // 80)), Image.NEAREST).save('tools/pic_%s.png' % pair[0])
