# -*- coding: utf-8 -*-
"""개선판 그림 규칙 - 원판의 CGA 그림(2비트)을 256색 RGB 로 칠한다 (tools/mkvga.py 가 쓴다)

   화면 그림(SCREENS)은 파일 두세 개를 합친 320x200 한 장으로 칠한 뒤 다시 파일별로 나눈다.
   규칙은 칠하기 목록:
       ('map', 사각형, {CGA값: 색})             색 = '#rrggbb' | ('#위', '#아래') 세로 그러데이션
                                                 | ('h', '#왼', '#오른') 가로 | 함수(x, y) -> (r,g,b)
       ('blur', 사각형, 반지름, 제외값들)        칠한 색을 둘레 평균으로 (디더를 부드럽게)
       ('fill', 사각형, 색)                      통째로 칠하기
       ('fillv', 사각형, CGA값들, 색)            그 값인 점만 칠하기
   사각형은 (x0, y0, x1, y1), 끝 포함.
   그림에 있던 영어 글자는 지우고, 한글은 실행할 때 skbvga.c 가 덧그린다.
"""
import os, struct, math
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
E = open(os.path.join(ROOT, 'SKB.EXE'), 'rb').read()
IMG = E[struct.unpack('<H', E[8:10])[0] * 16:]
DS = 0xA39 * 16

CGA = [(0, 0, 0), (85, 255, 255), (255, 85, 255), (255, 255, 255)]


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


def pixels(buf):
    out = []
    for b in buf:
        out += [(b >> 6) & 3, (b >> 4) & 3, (b >> 2) & 3, b & 3]
    return out


def hexc(h):
    if isinstance(h, tuple):
        return h
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t=0.5):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def shade(c, f):
    c = hexc(c)
    if f >= 1:
        return tuple(min(255, int(v + (255 - v) * (f - 1))) for v in c)
    return tuple(int(v * f) for v in c)


class Canvas:
    def __init__(self, vals, w, h):
        self.v = vals; self.w = w; self.h = h
        self.c = [CGA[x] for x in vals]

    def spec_color(self, spec, x, y, r):
        if isinstance(r, list):
            r = (min(p[0] for p in r), min(p[1] for p in r), max(p[0] for p in r), max(p[1] for p in r))
        if callable(spec):
            return spec(x, y)
        if isinstance(spec, tuple) and len(spec) == 2 and not isinstance(spec[0], int):
            x0, y0, x1, y1 = r
            t = (y - y0) / max(1, y1 - y0)
            return mix(hexc(spec[0]), hexc(spec[1]), t)
        if isinstance(spec, tuple) and len(spec) == 3 and spec[0] == 'h':
            x0, y0, x1, y1 = r
            t = (x - x0) / max(1, x1 - x0)
            return mix(hexc(spec[1]), hexc(spec[2]), t)
        return hexc(spec)

    def rect(self, r):
        """영역의 점들: (x0,y0,x1,y1) 사각형 또는 [(x,y), ...] 다각형"""
        if isinstance(r, list):
            from PIL import ImageDraw
            m = Image.new('L', (self.w, self.h), 0)
            ImageDraw.Draw(m).polygon(r, fill=255, outline=255)
            mp = m.load()
            xs = [p[0] for p in r]; ys = [p[1] for p in r]
            for y in range(max(0, min(ys)), min(self.h - 1, max(ys)) + 1):
                for x in range(max(0, min(xs)), min(self.w - 1, max(xs)) + 1):
                    if mp[x, y]:
                        yield x, y
            return
        x0, y0, x1, y1 = r
        for y in range(max(0, y0), min(self.h - 1, y1) + 1):
            for x in range(max(0, x0), min(self.w - 1, x1) + 1):
                yield x, y

    def apply(self, rules):
        for rule in rules:
            op = rule[0]
            if op == 'map':
                _, r, m = rule
                for x, y in self.rect(r):
                    v = self.v[y * self.w + x]
                    if v in m:
                        self.c[y * self.w + x] = self.spec_color(m[v], x, y, r)
            elif op == 'fill':
                _, r, col = rule
                for x, y in self.rect(r):
                    self.c[y * self.w + x] = self.spec_color(col, x, y, r)
                    self.v[y * self.w + x] = -1
            elif op == 'fillv':
                _, r, vs, col = rule
                for x, y in self.rect(r):
                    if self.v[y * self.w + x] in vs:
                        self.c[y * self.w + x] = self.spec_color(col, x, y, r)
            elif op == 'blur':
                _, r, rad, keep = rule
                src = list(self.c)
                for x, y in self.rect(r):
                    if self.v[y * self.w + x] in keep:
                        continue
                    acc = [0, 0, 0]; n = 0
                    for yy in range(y - rad, y + rad + 1):
                        for xx in range(x - rad, x + rad + 1):
                            if 0 <= xx < self.w and 0 <= yy < self.h and self.v[yy * self.w + xx] not in keep:
                                p = src[yy * self.w + xx]
                                acc[0] += p[0]; acc[1] += p[1]; acc[2] += p[2]; n += 1
                    if n:
                        self.c[y * self.w + x] = (acc[0] // n, acc[1] // n, acc[2] // n)
            elif op == 'func':
                rule[1](self)

    def image(self):
        im = Image.new('RGB', (self.w, self.h))
        im.putdata(self.c)
        return im


# ---------------------------------------------------------------------------
#  화면 그림들
# ---------------------------------------------------------------------------
import scenes

SCREENS = scenes.SCREENS


def screen_canvas(name):
    parts, rules = SCREENS[name]
    buf = b''.join(rle(p) for p in parts)
    rows = len(buf) // 80
    cv = Canvas(pixels(buf), 320, rows)
    cv.apply(rules)
    return cv, parts


def screen_values(name):
    """화면 그림의 원래 CGA 값 (칠하기 전)"""
    parts, rules = SCREENS[name]
    return pixels(b''.join(rle(p) for p in parts))


def screen_images():
    out = []
    for name in SCREENS:
        cv, parts = screen_canvas(name)
        im = cv.image()
        y = 0
        for p in parts:
            n = len(rle(p)) // 80
            out.append(('P', p, n, im.crop((0, y, 320, y + n)), None))
            y += n
    return out


# ---------------------------------------------------------------------------
#  EXE 안의 그림과 자료 파일: 바이트마다 네 점
# ---------------------------------------------------------------------------
import sprites_art


def all_assets():
    return screen_images() + sprites_art.exe_assets() + sprites_art.file_assets()


THEMES = sprites_art.THEMES
