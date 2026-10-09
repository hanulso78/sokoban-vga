# -*- coding: utf-8 -*-
"""EXE 안의 그림(스프라이트, 타일, 글꼴)과 자료 파일(icon_dat, lobby_dat, elev.bin)의 색

   바이트마다 네 점의 색을 정한다.  마스크 스프라이트는 그림 쪽 바이트의 색만 쓰인다
   (skbvga.c masked_colors), 불투명 복사(글꼴, 숫자, 판)는 그 바이트 색 그대로.
   OVER[선형주소] = [네 점 RGB] 로 기본 색을 덮어쓴다.
"""
import os, struct, random
from PIL import Image
import art

ROOT = art.ROOT
IMG = art.IMG
hexc = art.hexc
mix = art.mix
shade = art.shade

DEFAULT = ['#101018', '#48c8d8', '#d860b8', '#f4f0e8']
DS = 0xA39 * 16

REGIONS = [(0xA39, 0x9780, 0xDD30), (0x180C, 0, 0xEF70), (0x2703, 0, 0x59E0), (0x2CA1, 0, 0x4B0),
           (0x2CEC, 0, 0xF90)]

OVER = {}


def W(off, seg=DS):
    return struct.unpack('<H', IMG[seg + off:seg + off + 2])[0]


def pix(lin, x):
    """선형 주소의 바이트 안 x 번째 점 값"""
    return (IMG[lin] >> (6 - 2 * x)) & 3


def paint_sprite(lin, wb, rows, fn):
    """lin 에서 시작하는 wb 바이트 x rows 줄 그림(마스크 없이 값만)을 fn(x, y, v) -> RGB 로"""
    for y in range(rows):
        for bx in range(wb):
            a = lin + y * wb + bx
            OVER[a] = [hexc(fn(bx * 4 + p, y, pix(a, p))) for p in range(4)]


def sprite_vals(lin, wb, rows):
    return [[pix(lin + y * wb + x // 4, x & 3) for x in range(wb * 4)] for y in range(rows)]


def smooth_fn(vals, base_fn, keep=(0,)):
    """체크무늬 디더를 이웃과 섞는 색 함수"""
    rows = len(vals); w = len(vals[0])
    cache = {}

    def f(x, y, v):
        c = hexc(base_fn(x, y, v))
        if v in keep:
            return c
        acc = [0, 0, 0]; n = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < rows and vals[yy][xx] not in keep:
                    cc = hexc(base_fn(xx, yy, vals[yy][xx]))
                    wgt = 2 if (dx, dy) == (0, 0) else 1
                    acc = [acc[i] + cc[i] * wgt for i in range(3)]; n += wgt
        return tuple(a // n for a in acc)
    return f


# ---------------------------------------------------------------------------
#  판 타일 (24x16, 앞면 16x12 + 오른쪽/아래 입체 면), 그림 면 = 마스크 + 0x60
# ---------------------------------------------------------------------------
BRICKS = ['#b4452e', '#a63c28', '#c05236', '#9c3822', '#b84c30', '#a84430']


def wall_tile(lin):
    vals = sprite_vals(lin, 6, 16)
    # 앞면 벽돌마다 번호 (이어진 자홍 점)
    bid = {}
    n = 0
    for y in range(12):
        for x in range(16):
            if vals[y][x] == 2 and (x, y) not in bid:
                st = [(x, y)]
                bid[(x, y)] = n
                while st:
                    cx, cy = st.pop()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < 16 and 0 <= ny < 12 and vals[ny][nx] == 2 and (nx, ny) not in bid:
                            bid[(nx, ny)] = n
                            st.append((nx, ny))
                n += 1
    tops = {}
    for (x, y), b in bid.items():
        tops[b] = min(tops.get(b, 99), y)

    def f(x, y, v):
        front = x < 16 and y < 12
        if front:
            if v == 2:
                b = bid.get((x, y), 0)
                c = hexc(BRICKS[(b * 7 + 3) % len(BRICKS)])
                if y == tops.get(b):
                    c = shade(c, 1.25)
                return c
            if v == 3:
                return '#e8a080'
            return '#3e3230' if v == 0 else '#8a5a48'
        # 입체 면: 오른쪽은 어둡게, 아래는 더 어둡게
        side = x >= 16 and y < 12 + (x - 16) // 2 + 1
        if v == 2:
            return '#7a2c1c' if side else '#5c2014'
        if v == 3:
            return '#9a4a34'
        return '#241a18'
    paint_sprite(lin + 0x60, 6, 16, f)


def barrel_tile(lin, body, light, dark, band):
    vals = sprite_vals(lin + 0x60, 6, 16)

    def base(x, y, v):
        k = 1.12 - 0.45 * (x / 23.0) - 0.15 * (y / 15.0)
        if v == 1:
            return shade(body, k)
        if v == 3:
            return shade(light, k)
        if v == 2:
            return shade(band, k)
        return dark
    paint_sprite(lin + 0x60, 6, 16, smooth_fn(vals, base))


def goal_tile(lin):
    def f(x, y, v):
        if v == 0:
            return '#6a4a10'
        t = abs(x - 8) / 8.0 + abs(y - 6) / 6.0
        return mix(hexc('#fff0a0'), hexc('#e0a020'), min(1, t))
    paint_sprite(lin + 0x60, 6, 16, f)


# ---------------------------------------------------------------------------
#  사람 (위에서 본 모습): 자홍 = 셔츠, 흰색 = 머리, 검정 = 바지/그림자, 청록 = 신발
# ---------------------------------------------------------------------------
def person(x, y, v):
    if v == 2:
        return shade('#3a78d0', 1.1 - y * 0.03)
    if v == 3:
        return shade('#f0c890', 1.05 - y * 0.02)
    if v == 1:
        return '#c05030'
    return '#2a2430'


def head_helmet(lin, wb, rows):
    """위에서 본 사람 그림 (마스크 없는 그림 면, 줄 wb 바이트) 의 가장 큰 흰 덩어리 = 머리 -> 안전모"""
    W4 = wb * 4

    def val(x, y):
        return pix(lin + y * wb + x // 4, x & 3)
    seen = set()
    best = []
    for y in range(rows):
        for x in range(W4):
            if val(x, y) == 3 and (x, y) not in seen:
                comp = [(x, y)]
                seen.add((x, y))
                st = [(x, y)]
                while st:
                    cx, cy = st.pop()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < W4 and 0 <= ny < rows and (nx, ny) not in seen and val(nx, ny) == 3:
                            seen.add((nx, ny))
                            comp.append((nx, ny))
                            st.append((nx, ny))
                if len(comp) > len(best):
                    best = comp
    if not best:
        return
    xs = [p[0] for p in best]; ys = [p[1] for p in best]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    r = max(1.0, max(max(xs) - min(xs), max(ys) - min(ys)) / 2.0)
    for x, y in best:
        a = lin + y * wb + x // 4
        old = list(OVER.get(a) or [hexc(person(0, 0, pix(a, q))) for q in range(4)])
        d = ((x - cx + r * 0.35) ** 2 + (y - cy + r * 0.35) ** 2) ** 0.5 / (r * 1.4)
        old[x & 3] = mix(hexc('#fff0a0'), hexc('#d09818'), min(1.0, d))
        OVER[a] = old


def level_sprites():
    tiles = [W(0x1787 + 2 * k) for k in range(6)]
    floor, wall, box, goal, boxgoal, flash = [DS + t for t in tiles]
    wall_tile(wall)
    barrel_tile(box, '#b0743c', '#e8b070', '#3a2210', '#8a5028')
    barrel_tile(boxgoal, '#58b050', '#c0f0a0', '#143818', '#2e8030')
    barrel_tile(flash, '#f0d040', '#fff8c0', '#604000', '#c09020')
    goal_tile(goal)
    # 사람: 서 있는 모습 4, 걷기/밀기 4방향 x 4
    for k in range(4):
        paint_sprite(DS + W(0x9ca2 + 2 * k) + 0x60, 6, 16, person)
    for base in (0x9caa, 0x9cb2, 0x9cca, 0x9cd2):          # 가로 32x16
        for k in range(4):
            paint_sprite(DS + W(base + 2 * k) + 0x80, 8, 16, person)
    for base in (0x9cba, 0x9cc2, 0x9cda, 0x9ce2):          # 세로 24x16
        for k in range(4):
            paint_sprite(DS + W(base + 2 * k) + 0x60, 6, 16, person)
    # 머리 (가장 큰 흰 덩어리) -> 노란 안전모
    for k in range(4):
        head_helmet(DS + W(0x9ca2 + 2 * k) + 0x60, 6, 16)
    for base in (0x9caa, 0x9cb2, 0x9cca, 0x9cd2):
        for k in range(4):
            head_helmet(DS + W(base + 2 * k) + 0x80, 8, 16)
    for base in (0x9cba, 0x9cc2, 0x9cda, 0x9ce2):
        for k in range(4):
            head_helmet(DS + W(base + 2 * k) + 0x60, 6, 16)
    # 가로로 미는 상자 (32x16, 2점씩 밀린 그림 5장): 보통 상자 그림의 색을 밀린 만큼 옮겨 그대로
    bv = sprite_vals(box + 0x60, 6, 16)
    bm = sprite_vals(box, 6, 16)
    for k in range(5):
        a = DS + W(0x9cea + 2 * k)
        fv = sprite_vals(a + 0x80, 8, 16)
        sh = min(range(9), key=lambda d: sum(1 for y in range(16) for x in range(24)
                                              if bm[y][x] == 0 and fv[y][x + d] != bv[y][x]))

        def f(x, y, v, sh=sh):
            bx = x - sh
            if 0 <= bx < 24 and bv[y][bx] == v:
                return '#%02x%02x%02x' % tuple(OVER[box + 0x60 + y * 6 + bx // 4][bx & 3])
            return '#3a2210'
        paint_sprite(a + 0x80, 8, 16, f)


# ---------------------------------------------------------------------------
#  상태 줄 (2CA1:00E6 62x9 + 2CA1:0314 18x9) 과 숫자 글꼴 (2CA1, 2x9)
#  밝은 크림색 띠에 원래 글자 (moves: pushes: time:)
# ---------------------------------------------------------------------------
BAR_TOP = '#6a5030'


def bar_bg(x, y):
    return mix(hexc('#fbf4e2'), hexc('#e2d2ae'), y / 8.0)


def status_bar():
    seg = 0x2CA1 * 16

    def f_at(ox):
        def f(x, y, v):
            if v == 0:
                return '#2e2016'
            if v == 2:
                return '#b06030'
            return bar_bg(x + ox, y)
        return f
    paint_sprite(seg + 0xE6, 62, 9, f_at(0))
    paint_sprite(seg + 0x314, 18, 9, f_at(248))
    # 숫자 0..9 (흰 바탕 검은 글자 -> 크림 바탕 짙은 갈색 글자), ':' 도
    for d in range(10):
        a = seg + W(8 + 2 * d, seg)
        paint_sprite(a, 2, 9, lambda x, y, v: '#2e2016' if v == 0 else bar_bg(x, y))
    paint_sprite(seg + 0x3B6, 2, 9, lambda x, y, v: '#2e2016' if v == 0 else bar_bg(x, y))


# ---------------------------------------------------------------------------
#  타이틀과 로비의 사람, 엘리베이터 문, 선수 방 강조 액자, 번호 칸
# ---------------------------------------------------------------------------
def person_big(x, y, v):
    """옆/뒤에서 본 큰 사람 (타이틀, 로비, 엘리베이터): 자홍 셔츠, 흰 머리와 팔, 검은 바지"""
    if v == 2:
        return '#3a78d0'
    if v == 3:
        return '#f0c890'
    if v == 1:
        return '#c8946a'                                # 청록 = 살의 그늘 (얼굴, 팔)
    return '#24202c'


HELMET = ['#f8d860', '#f0c030', '#d8a020']


def helmet(y, rows):
    """안전모: 위는 밝게"""
    return mix(hexc('#fae070'), hexc('#d8a018'), y / max(1, rows - 1))


def with_hair(frame_rows, hair_rows):
    """큰 사람 색에 노란 안전모: 프레임 높이 frame_rows 줄 가운데 위쪽 hair_rows 줄의 흰 점"""
    def f(x, y, v):
        if v == 3 and y % frame_rows < hair_rows:
            return helmet(y % frame_rows, hair_rows)
        return person_big(x, y, v)
    return f


def helmet_blob(lin, w, rows, buf=None, target=None):
    """줄마다 M0[w] I0[w] M1[w] I1[w] 인 그림에서, 맨 위쪽 흰 점에서 이어진 흰 덩어리(안전모)를
    노랗게.  rows 줄 아래로는 번지지 않는다.  buf/target 을 주면 파일 자료 (lin = 파일 안 위치)"""
    src = IMG if buf is None else buf
    tgt = OVER if target is None else target
    bpr = 4 * w
    W4 = 8 * w                                          # 한 줄의 점 수 (I0 + I1)

    def addr(x, y):
        half, xx = divmod(x, 4 * w)
        return lin + y * bpr + (2 * half + 1) * w + xx // 4, xx & 3

    def val(x, y):
        a, p = addr(x, y)
        return (src[a] >> (6 - 2 * p)) & 3
    top = None
    for y in range(rows):
        if any(val(x, y) == 3 for x in range(W4)):
            top = y
            break
    if top is None:
        return
    seen = set((x, top) for x in range(W4) if val(x, top) == 3)
    st = list(seen)
    while st:
        x, y = st.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W4 and top <= ny < top + rows and (nx, ny) not in seen and val(nx, ny) == 3:
                seen.add((nx, ny))
                st.append((nx, ny))
    ys = [y for x, y in seen]
    y0, y1 = min(ys), max(ys)
    for x, y in seen:
        a, p = addr(x, y)
        old = tgt.get(a) or [hexc(person_big(0, 0, (src[a] >> (6 - 2 * q)) & 3)) for q in range(4)]
        old = list(old)
        t = (y - y0) / max(1, y1 - y0)
        old[p] = mix(hexc('#fae070'), hexc('#d8a018'), t)
        tgt[a] = old


def helmet_ellipse(lin, w, top_rows=4, buf=None, target=None, max_rows=99):
    """줄마다 M0[w] I0[w] M1[w] I1[w] 인 큰 사람 프레임: 맨 위 top_rows 줄의 흰 점 폭으로 안전모의
    둥근 윗부분(타원)을 잡고, 그 안의 흰 점만 노랗게 (아래 얼굴/목의 흰 점은 살색 그대로)"""
    src = IMG if buf is None else buf
    tgt = OVER if target is None else target
    bpr = 4 * w
    W4 = 8 * w

    def addr(x, y):
        half, xx = divmod(x, 4 * w)
        return lin + y * bpr + (2 * half + 1) * w + xx // 4, xx & 3

    def val(x, y):
        a, p = addr(x, y)
        return (src[a] >> (6 - 2 * p)) & 3
    top = None
    for y in range(20):
        if any(val(x, y) == 3 for x in range(W4)):
            top = y
            break
    if top is None:
        return
    xs = [x for y in range(top, top + top_rows) for x in range(W4) if val(x, y) == 3]
    x0, x1 = min(xs), max(xs)
    cx = (x0 + x1) / 2.0
    rx = (x1 - x0) / 2.0 + 1.0
    ry = rx * 0.62                                      # CGA 점은 세로로 길다
    cy = top + ry
    for y in range(top, min(int(cy + ry) + 1, top + max_rows)):
        for x in range(W4):
            if val(x, y) != 3:
                continue
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 > 1.05 and y > cy:
                continue
            a, p = addr(x, y)
            old = list(tgt.get(a) or [hexc(person_big(0, 0, (src[a] >> (6 - 2 * q)) & 3)) for q in range(4)])
            old[p] = mix(hexc('#fae070'), hexc('#d8a018'), (y - top) / max(1.0, 2 * ry))
            tgt[a] = old


def face_lips(lin, w, face_rows, buf=None, target=None):
    """앞모습 얼굴 (맨 위 흰 점부터 face_rows 줄) 안의 자홍 점은 셔츠가 아니라 입술"""
    src = IMG if buf is None else buf
    tgt = OVER if target is None else target
    bpr = 4 * w

    def addr(x, y):
        half, xx = divmod(x, 4 * w)
        return lin + y * bpr + (2 * half + 1) * w + xx // 4, xx & 3
    top = None
    for y in range(20):
        for x in range(8 * w):
            a, p = addr(x, y)
            if (src[a] >> (6 - 2 * p)) & 3 == 3:
                top = y
                break
        if top is not None:
            break
    if top is None:
        return
    for y in range(top, top + face_rows):
        for x in range(8 * w):
            a, p = addr(x, y)
            if (src[a] >> (6 - 2 * p)) & 3 == 2:
                old = list(tgt.get(a) or [hexc(person_big(0, 0, (src[a] >> (6 - 2 * q)) & 3)) for q in range(4)])
                old[p] = hexc('#b8705a')
                tgt[a] = old


def paint_range(lin, n, fn, wb=4):
    """lin 부터 n 바이트를 폭 wb 바이트 그림으로 보고 fn(x, y, v)"""
    rows = (n + wb - 1) // wb
    for y in range(rows):
        for bx in range(wb):
            a = lin + y * wb + bx
            if a < lin + n:
                OVER[a] = [hexc(fn(bx * 4 + p, y, pix(a, p))) for p in range(4)]


def people_and_things():
    # 타이틀 사람 (DS:D3C0..DC58, 4바이트 x 25줄, 마스크 + 0x64)
    # 프레임(마스크 100 + 그림 100 바이트)마다 머리 꼭대기가 0~2줄로 다르다: 맨 위 흰 점 줄부터 3줄이 안전모
    for fa in range(DS + 0xD3C0, DS + 0xDC58, 200):
        vals = sprite_vals(fa + 100, 4, 25)
        top = next((y for y in range(25) if 3 in vals[y]), 0)
        paint_range(fa, 100, person_big, 4)
        paint_range(fa + 100, 100, lambda x, y, v, top=top: helmet(y - top, 3) if v == 3 and top <= y < top + 3
                    else person_big(x, y, v), 4)
    # 로비 사람 (2703, 줄마다 M0 I0 M1 I1 6바이트씩 = 24바이트)
    seg = 0x2703 * 16
    paint_range(seg + 0x30, 0x2790 - 0x30, person_big, 24)
    paint_range(seg + 0x3DC0, 0x59E0 - 0x3DC0, person_big, 24)
    # 뒷모습 ([2] 서 있기 0x30, [0] 문 고르기 0x5D0): 흰 머리 덩어리 전체가 안전모
    for f in (0x30, 0x5D0):
        helmet_blob(seg + f, 6, 12)
    # 옆모습 (돌기, 걷기): 위 5줄만 (그 아래 흰 점은 얼굴)
    for f in (0xB70, 0x1110, 0x16B0, 0x1C50, 0x21F0, 0x3DC0, 0x4360, 0x4900, 0x4EA0, 0x5440):
        helmet_ellipse(seg + f, 6, 4, max_rows=5)
    # 엘리베이터 문 (2703:2790..3DC0, 16바이트 x 71줄 다섯 장)

    def door(x, y, v):
        # 문짝은 강철, 열린 문 안쪽 (자홍/검정 체크) 은 엘리베이터 안 벽과 같은 나무색
        if v == 1:
            return mix(hexc('#c8d0d8'), hexc('#98a2ac'), (x % 32) / 31.0)
        return {0: '#4a2e1e', 3: '#e8ecf0', 2: '#6a3e28'}[v]
    paint_range(seg + 0x2790, 0x3DC0 - 0x2790, door, 16)
    # 엘리베이터 (180C): 눌린 단추 그림 (0x4A..0xA50), 큰 사람 (..0xEE00), 층 숫자 (0xEE00..)
    seg1 = 0x180C * 16
    paint_range(seg1 + 0x4A, 0xA50 - 0x4A, person_big, 4)
    if 0: paint_range(seg1 + 0x4A, 0xA50 - 0x4A, lambda x, y, v: {2: '#f8d878', 0: '#20242a', 3: '#fffaf0',
                                                           1: '#c8ced4'}[v], 4)
    paint_range(seg1 + 0xA50, 0xEE00 - 0xA50, person_big, 4)
    # 엘리베이터 사람 안전모: 서 있는 윗몸 (180C:0040, 줄 40바이트), 팔 뻗은 윗몸 7장 (줄 60바이트)
    helmet_blob(seg1 + 0x40, 10, 40)
    for k in range(7):
        helmet_blob(seg1 + W(2 * k, seg1), 15, 40)
    paint_range(seg1 + 0xEE00, 0xEF70 - 0xEE00, lambda x, y, v: {2: '#d04040', 0: '#20242a', 3: '#fffaf0',
                                                                1: '#c8ced4'}[v], 3)
    # 선수 방 강조 액자 (2CEC:0240, 12바이트 x 48줄): 금색 테
    seg4 = 0x2CEC * 16
    paint_range(seg4 + 0x240, 12 * 48, lambda x, y, v: {2: '#d8a848', 1: '#b8d8f0',
                                                       0: '#1c2028', 3: '#fffaf0'}[v], 12)
    # 이어하기 메뉴 글자 그림 "Single" (2CEC:00FC, 18x8) / "Tournament" (2CEC:018C, 20x9):
    # 메뉴판과 같은 남색 바탕에 크림색 글자
    board = {2: '#22304a', 1: '#22304a', 0: '#f2e6c4', 3: '#f2e6c4'}
    paint_range(seg4 + 0xFC, 18 * 8, lambda x, y, v: board[v], 18)
    paint_range(seg4 + 0x18C, 20 * 9, lambda x, y, v: board[v], 20)
    paint_range(seg4 + 0x480, 4, lambda x, y, v: {2: '#2a2018', 0: '#2a2018', 1: '#f4ecd6', 3: '#f4ecd6'}[v], 2)
    paint_range(seg4 + 0x484, 4, lambda x, y, v: '#f4ecd6', 2)
    # 메뉴 화살표 칸 (2CEC:064C, 2x9, 자홍) -> 금색, 흰 칸 (063A) -> 크림
    paint_range(seg4 + 0x64C, 18, lambda x, y, v: {2: '#f0b040', 0: '#1c2028', 1: '#f0b040', 3: '#fffaf0'}[v], 2)
    paint_range(seg4 + 0x63A, 18, lambda x, y, v: {3: '#e8e0cc', 0: '#1c2028', 1: '#e8e0cc', 2: '#e8e0cc'}[v], 2)
    # 고른 숫자 (2CA1:0490 표: 자홍 바탕) -> 금색 바탕
    seg3 = 0x2CA1 * 16
    for d in range(10):
        a = seg3 + W(0x490 + 2 * d, seg3)
        if a + 18 <= seg3 + 0x4B0:
            paint_range(a, 18, lambda x, y, v: {2: '#f0b040', 0: '#2e2016', 3: '#fffaf0', 1: '#f0b040'}[v], 2)
    paint_range(seg3 + 0x20, 18, lambda x, y, v: {2: '#f0b040', 0: '#2e2016', 3: '#fffaf0', 1: '#f0b040'}[v], 2)


def colors_for_bytes(lin0, buf, cols):
    out = []
    for k, b in enumerate(buf):
        o = OVER.get(lin0 + k)
        if o:
            out += o
        else:
            out += [cols[(b >> 6) & 3], cols[(b >> 4) & 3], cols[(b >> 2) & 3], cols[b & 3]]
    im = Image.new('RGB', (4, len(buf)))
    im.putdata(out)
    return im


def exe_assets():
    OVER.clear()
    people_and_things()
    level_sprites()
    status_bar()
    out = []
    base = [hexc(c) for c in DEFAULT]
    for seg, start, end in REGIONS:
        off = seg * 16 + start
        buf = IMG[off:seg * 16 + end]
        out.append(('I', 'exe%04x' % seg, off, colors_for_bytes(off, buf, base), len(buf)))
    return out


FOVER = {}                              # 파일 이름 -> {오프셋: [네 점 RGB]}


def paint_bitmap(target, off, buf, wb, rows, rules):
    """바이트열 buf 의 off 에서 시작하는 wb x rows 그림을 art.Canvas 규칙으로 칠해 target 에"""
    vals = []
    for y in range(rows):
        vals += art.pixels(buf[off + y * wb:off + (y + 1) * wb])
    cv = art.Canvas(vals, wb * 4, rows)
    cv.apply(rules)
    for y in range(rows):
        for bx in range(wb):
            target[off + y * wb + bx] = [cv.c[y * wb * 4 + bx * 4 + p] for p in range(4)]


def icon_dat():
    import scenes
    buf = open(os.path.join(ROOT, 'ICON_DAT'), 'rb').read()
    t = FOVER.setdefault('icon_dat', {})
    base = {1: '#8a9cb8', 2: '#8a9cb8', 3: '#c8d4e4', 0: '#1c2028'}      # 모서리 그림자 체크 = 바탕
    # 강조 아이콘: F H G E D C B A 차례, 카드 색은 밝은 주황
    for k, name in enumerate('FHGEDCBA'):
        rules = [('map', (0, 0, 55, 65), base)] + scenes.icon_rules(0, 0, name, scenes.ICON_CARD_HI)
        paint_bitmap(t, 0x59C + k * 0x39C, buf, 14, 66, rules)
    # 대화 상자 판 (14x66)
    paint_bitmap(t, 0, buf, 14, 66, [('map', (0, 0, 55, 65), {2: scenes.ICON_CARD, 1: '#e8dcc4', 3: '#fffaf0',
                                                              0: '#1c2028'})])
    # 세로 단추 OK (16x24) / CANCEL (16x40): 고른 것은 주황, 아닌 것은 크림
    for off, rows, hi in [(0x39C, 24, True), (0x3FC, 24, False), (0x45C, 40, True), (0x4FC, 40, False)]:
        bg = '#f0a030' if hi else '#e8dcc4'
        paint_bitmap(t, off, buf, 4, rows, [('map', (0, 0, 15, rows - 1), {2: bg, 1: '#e8dcc4', 3: '#fffaf0',
                                                                          0: '#1c2028'})])


def lobby_dat():
    """로비 사람 걷기 프레임 (lobby_dat, 58CC 에 읽어 4BA5 로 그린다): 큰 사람 색"""
    buf = open(os.path.join(ROOT, 'LOBBY_DA'), 'rb').read()
    t = FOVER.setdefault('lobby_dat', {})
    for k in range(len(buf)):
        y, x4 = divmod(k, 24)
        t[k] = [hexc(person_big(x4 * 4 + p, y, (buf[k] >> (6 - 2 * p)) & 3)) for p in range(4)]
    # 엘리베이터에 타는 뒷모습 (1C20..2D00) 은 흰 덩어리 전체, 내리는 앞모습은 위 3줄만
    for f in (0x1C20, 0x21C0, 0x2760, 0x2D00):
        helmet_blob(f, 6, 12, buf, t)
    for f in (0x0, 0x5A0, 0xB40, 0x10E0, 0x1680):
        helmet_ellipse(f, 6, 3, buf, t, max_rows=3)
        face_lips(f, 6, 11, buf, t)


def file_assets():
    out = []
    FOVER.clear()
    icon_dat()
    lobby_dat()
    base = [hexc(c) for c in DEFAULT]
    for name, disk in [('icon_dat', 'ICON_DAT'), ('lobby_dat', 'LOBBY_DA')]:
        fn = os.path.join(ROOT, disk)
        if os.path.exists(fn):
            buf = open(fn, 'rb').read()
            over = FOVER.get(name, {})
            cols = []
            for k, b in enumerate(buf):
                o = over.get(k)
                cols += o if o else [base[(b >> 6) & 3], base[(b >> 4) & 3], base[(b >> 2) & 3], base[b & 3]]
            im = Image.new('RGB', (4, len(buf)))
            im.putdata([hexc(c) for c in cols])
            out.append(('F', name, 0, im, len(buf)))
    return out


# ---------------------------------------------------------------------------
#  장면 테마: 색이 없는 점의 네 색, 판 장면은 바닥 무늬(안/밖) 16x12 두 장
# ---------------------------------------------------------------------------
def floor_tex():
    random.seed(7)
    out = []
    for y in range(12):
        for x in range(16):
            c = hexc('#5e6672')
            if y == 0 or x == 0:
                c = hexc('#6e7784')
            if y == 11 or x == 15:
                c = hexc('#4a515c')
            k = random.uniform(0.94, 1.05)
            out.append(tuple(min(255, int(v * k)) for v in c))
    return out


def outside_tex():
    out = []
    for y in range(12):
        for x in range(16):
            c = hexc('#121826')
            if (x + y * 3) % 16 == 0:
                c = hexc('#1a2234')
            out.append(c)
    return out


THEMES = {
    # 로비: 원판이 닫힌 엘리베이터 문을 직접 값(청록)으로 칠한다 -> 강철 문 색
    'lobby': [hexc(c) for c in ['#40484f', '#aab3bc', '#6a3e28', '#e8ecf0']],
    'elev': [hexc(c) for c in ['#20242a', '#b0b8c0', '#6a3e28', '#e8ecf0']],
    'level': [hexc(c) for c in ['#101018', '#5e6672', '#d860b8', '#f4f0e8']] + floor_tex() + outside_tex(),
}
