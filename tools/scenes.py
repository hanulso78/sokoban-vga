# -*- coding: utf-8 -*-
"""화면 그림별 칠하기 규칙 (tools/art.py 의 Canvas 규칙).  좌표는 320x200, 끝 포함.
   CGA 값: 0 검정, 1 청록, 2 자홍, 3 흰색"""

# ---------------------------------------------------------------------------
#  타이틀: 창고 건물 앞 광장, 벚나무, 로고, 만든 사람들
# ---------------------------------------------------------------------------
TITLE = [
    # 아래 띠 (흰 바탕) -> 남색
    ('map', (0, 96, 319, 199), {3: ('#34507c', '#0a1228')}),
    ('map', [(0, 96), (319, 96), (319, 112), (170, 112), (170, 106), (0, 106)], {3: '#d8bea0', 1: '#d2b898'}),
    # 하늘과 잔디 (왼쪽 위)
    ('map', (0, 0, 124, 60), {3: ('#6fa6e0', '#d6e8f6')}),
    ('map', (0, 24, 124, 108), {1: ('#5aa044', '#3c7a30')}),
    # 옆 건물 벽 (오른쪽 위, 청록/흰 체크) -> 체크의 두 값을 같은 모래색으로 (무늬가 보이지 않게)
    ('map', (244, 0, 319, 64), {1: ('#e8dcc0', '#d8c8a8'), 3: ('#ece0c6', '#dccdae'), 0: '#5a4a3a',
                                2: ('#e8dcc0', '#d8c8a8')}),
    ('blur', (244, 0, 319, 64), 2, (0,)),
    # 앞 건물
    ('map', (124, 0, 243, 62), {1: ('#d4c4a4', '#bca884'), 0: '#3c3028', 3: '#f4ecd8'}),
    # 유리창
    ('map', (130, 0, 232, 16), {2: ('#5a7cc0', '#8aa8dc'), 3: '#e4eef8', 0: '#1c2434', 1: '#a8c4e8'}),
    ('blur', (130, 0, 232, 16), 1, (0,)),
    # 문
    ('map', (160, 22, 195, 56), {0: '#2a1c16', 3: '#e0c890'}),
    # 계단과 테라스: 건물과 같은 따뜻한 돌색 (체크의 두 값을 가까운 색으로)
    ('func', lambda cv: terrace(cv, [(100, 46), (245, 46), (245, 76), (200, 98), (100, 102)])),
    # 분홍 바닥 -> 따뜻한 돌바닥: 체크의 두 값을 가까운 색으로 칠하고 넓게 흐리게
    ('map', (0, 50, 319, 96), {2: '#ccad8e'}),
    ('map', (0, 50, 319, 95), {3: '#d8bea0'}),
    ('map', (244, 55, 319, 130), {1: '#d2b898'}),
    ('map', (0, 96, 319, 132), {2: ('#ccad8e', '#40587e')}),
    ('blur', (0, 60, 319, 134), 2, (0, 1)),
    # 벽돌 광장 (나무 아래)
    ('map', (40, 76, 168, 118), {1: '#d4b898', 0: '#7a5e4a'}),
    ('blur', (40, 76, 168, 118), 1, (0,)),
    # 계단 옆면 (검정/청록 체크 띠): 체크의 검은 점은 중간 톤으로 녹인다
    ('func', lambda cv: soften_checker(cv, [(96, 50), (125, 50), (178, 96), (178, 104), (160, 104), (96, 70)],
                                       '#b8a488')),
    ('blur', [(96, 50), (125, 50), (178, 96), (178, 104), (160, 104), (96, 70)], 1, (0,)),
    # 벚나무
    ('map', [(33, 18), (48, 13), (75, 9), (100, 3), (126, 10), (126, 32), (118, 46), (112, 64), (100, 80),
             (60, 84), (26, 76), (26, 50)], {2: '#f2a6cc', 1: '#5aa046', 0: '#3a2618'}),
    # 덤불
    ('map', [(216, 36), (226, 32), (236, 36), (244, 50), (245, 68), (236, 73), (211, 71), (204, 60), (207, 47)],
     {2: '#e0609c', 1: '#3e8c38', 3: '#fcd8ec', 0: '#1c2c18'}),
    ('blur', [(33, 18), (48, 13), (75, 9), (100, 3), (126, 10), (126, 32), (118, 46), (112, 64), (100, 80),
              (60, 84), (26, 76), (26, 50)], 1, (0, 3)),
    # 오른쪽 끝: 창 둘 (안쪽 자홍 = 방 안 물건) 과 손수레 위 상자
    ('func', lambda cv: windows(cv, (282, 30, 319, 54))),
    ('func', lambda cv: cart(cv, (286, 52, 319, 76))),
    # 로고: 금색 글자, 붉은 테, 어두운 그림자 / 남색 바탕에 크림색 글
    ('map', (0, 118, 319, 164), {1: ('#fff0a0', '#e89020'), 2: '#b02838', 0: '#200810'}),
    ('map', (0, 158, 319, 199), {0: '#f0e6c8'}),
    ('func', lambda cv: pavement_fade(cv)),
    ('func', lambda cv: small_text(cv, 200, 172, 'VGA REMASTER', '#f0c050')),
    ('func', lambda cv: small_text(cv, 200 + small_width('VGA REMASTER  '), 172, 'In-Hak Min', '#f0e6c8')),
]

# 7줄 높이 작은 글꼴 (타이틀 제작진 줄에 맞춘다)
SMALL = {
    'V': ['#...#', '#...#', '#...#', '#...#', '.#.#.', '.#.#.', '..#..'],
    'G': ['.###', '#...', '#...', '#.##', '#..#', '#..#', '.###'],
    'A': ['.##.', '#..#', '#..#', '####', '#..#', '#..#', '#..#'],
    'R': ['###.', '#..#', '#..#', '###.', '#.#.', '#..#', '#..#'],
    'E': ['####', '#...', '#...', '###.', '#...', '#...', '####'],
    'M': ['#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'],
    'S': ['.###', '#...', '#...', '.##.', '...#', '...#', '###.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'I': ['###', '.#.', '.#.', '.#.', '.#.', '.#.', '###'],
    'H': ['#..#', '#..#', '#..#', '####', '#..#', '#..#', '#..#'],
    'n': ['....', '....', '###.', '#..#', '#..#', '#..#', '#..#'],
    'a': ['....', '....', '.###', '#..#', '#..#', '#..#', '.###'],
    'k': ['#...', '#...', '#..#', '#.#.', '##..', '#.#.', '#..#'],
    'i': ['#', '.', '#', '#', '#', '#', '#'],
    '-': ['...', '...', '...', '###', '...', '...', '...'],
    ' ': ['..', '..', '..', '..', '..', '..', '..'],
}


def small_width(text):
    return sum(len(SMALL[c][0]) + 1 for c in text)


def small_text(cv, x, y, text, col):
    import art
    c = art.hexc(col)
    for ch in text:
        g = SMALL[ch]
        for r, row in enumerate(g):
            for k, b in enumerate(row):
                if b == '#' and 0 <= x + k < cv.w and 0 <= y + r < cv.h:
                    cv.c[(y + r) * cv.w + x + k] = c
        x += len(g[0]) + 1


def soften_checker(cv, poly, mid):
    """영역 안의 체크 무늬 검은 점 (좌우가 검지 않은 점) 을 중간 톤으로"""
    import art
    c = art.hexc(mid)
    for x, y in cv.rect(poly):
        i = y * cv.w + x
        if cv.v[i] == 0 and 0 < x < cv.w - 1 and cv.v[i - 1] != 0 and cv.v[i + 1] != 0:
            cv.c[i] = c
            cv.v[i] = 1


def windows(cv, r):
    """오른쪽 끝 창 둘: 청록/흰 체크는 벽, 흰 틀, 안쪽 자홍은 방 안 물건, 청록 덩어리는 유리"""
    import art
    x0, y0, x1, y1 = r
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            i = y * cv.w + x
            v = cv.v[i]
            l = cv.v[i - 1] if x > 0 else -1
            rr = cv.v[i + 1] if x < cv.w - 1 else -1
            if v in (1, 3) and l in (1, 3) and rr in (1, 3) and l != v and rr != v:
                continue                                # 벽 체크: 옆 벽 규칙의 색 그대로
            if v == 3:
                cv.c[i] = art.hexc('#f0ece4')
            elif v == 2:
                cv.c[i] = art.hexc('#8a5a44')
            elif v == 1:
                cv.c[i] = art.hexc('#c8bca6')
            else:
                cv.c[i] = art.hexc('#302824')


def terrace(cv, poly):
    """계단과 테라스: 흰/청록 체크 점만 테라스 돌색 (두 색의 중간), 꽉 찬 청록은 건물 벽 그대로"""
    import art
    mid = art.hexc('#d4c6ac')
    for x, y in cv.rect(poly):
        i = y * cv.w + x
        v = cv.v[i]
        l = cv.v[i - 1] if x > 0 else -1
        r = cv.v[i + 1] if x < cv.w - 1 else -1
        if v in (1, 3) and l in (1, 3) and r in (1, 3) and l != v and r != v:
            cv.c[i] = mid
        elif v in (1, 3) and ((l in (1, 3) and l != v) or (r in (1, 3) and r != v)):
            cv.c[i] = mid                               # 체크의 가장자리
        elif v == 0 and ((157 <= x <= 192 and y <= 53) or (166 <= x <= 191 and y <= 59)):
            cv.c[i] = art.hexc('#2a1c16')               # 문틀과 문 안쪽: 문 윗부분과 같은 색
        elif v == 0:
            cv.c[i] = art.hexc('#6a5a4a')
        elif v == 2:
            cv.c[i] = art.hexc('#c8a890')
        elif not (124 <= x <= 243 and y <= 61):     # 건물 벽 밖의 꽉 찬 점: 계단 모서리
            cv.c[i] = mid


def cart(cv, r):
    """손수레와 상자: 바닥 체크 (좌우가 흰 자홍 점, 또는 체크 속 흰 점) 는 바닥색, 나머지는 수레/상자 색"""
    import art
    x0, y0, x1, y1 = r
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            i = y * cv.w + x
            v = cv.v[i]
            l = cv.v[i - 1] if x > 0 else -1
            rr = cv.v[i + 1] if x < cv.w - 1 else -1
            if (v == 2 and l == 3 and rr == 3) or (v == 3 and l == 2 and rr == 2):
                continue                                # 바닥 체크: 이미 흐리게 칠한 바닥색 그대로
            elif v == 2:
                cv.c[i] = art.hexc('#a8743e')           # 상자
            elif v == 1:
                cv.c[i] = art.hexc('#8a98a8')           # 쇠
            elif v == 3:
                cv.c[i] = art.hexc('#e8e2d8')
            else:
                cv.c[i] = art.hexc('#2a2420')


def pavement_fade(cv):
    """바닥 끝자락 (y 96..140) 의 체크 모양 자홍 점 (좌우가 흰 점) 은 로고 테두리가 아니라 바닥:
    둘레의 남색과 섞어 녹인다"""
    import art
    for y in range(96, 141):
        for x in range(1, cv.w - 1):
            i = y * cv.w + x
            if cv.v[i] == 2 and cv.v[i - 1] == 3 and cv.v[i + 1] == 3:
                t = min(1.0, (y - 96) / 30.0)
                cv.c[i] = art.mix(art.mix(art.hexc('#ccad8e'), art.hexc('#34507c'), t), cv.c[i - 1], 0.5)

def couch(cv, poly):
    """검은 소파 (자홍 점 무늬) -> 짙은 가죽"""
    import art
    for x, y in cv.rect(poly):
        i = y * cv.w + x
        v = cv.v[i]
        if v == 0 and 0 < x < cv.w - 1 and cv.v[i - 1] == 3 and cv.v[i + 1] == 3:
            cv.c[i] = cv.c[i + 1]                       # 소파 가장자리 섞임 점 -> 바닥
        elif v == 0:
            cv.c[i] = art.mix(art.hexc('#5a3220'), art.hexc('#3a2014'), (y - 136) / 64.0)
        elif v == 2 and 0 < x < cv.w - 1 and cv.v[i - 1] == 0 and cv.v[i + 1] == 0:
            cv.c[i] = art.hexc('#8a5636')
        elif v == 1 and 152 < y <= 180:
            cv.c[i] = art.mix(art.hexc('#5a3220'), art.hexc('#3a2014'), (y - 136) / 64.0)
        elif v == 1 and y > 180:
            cv.c[i] = art.hexc('#2a2226')
        elif v == 1 and y <= 152:
            cv.c[i] = art.hexc('#9a6440')


def lamps(cv, y0, y1):
    """천장 등: 검은 고리(테두리) 안쪽 전체를 켜진 등으로, 테두리는 밝은 금속, 둘레 천장은 은은한 빛"""
    import art
    seen = set()
    boxes = []
    for y in range(y0, y1 + 1):
        for x in range(cv.w):
            if cv.v[y * cv.w + x] == 0 and (x, y) not in seen:
                comp = [(x, y)]
                seen.add((x, y))
                st = [(x, y)]
                while st:
                    cx, cy = st.pop()
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < cv.w and y0 <= ny <= y1 and (nx, ny) not in seen                                     and cv.v[ny * cv.w + nx] == 0:
                                seen.add((nx, ny))
                                comp.append((nx, ny))
                                st.append((nx, ny))
                xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
                boxes.append((min(xs), min(ys), max(xs), max(ys), comp))
    rim = art.hexc('#a09888')
    for bx0, by0, bx1, by1, comp in boxes:
        cx = (bx0 + bx1) / 2.0
        rx = max(1.0, (bx1 - bx0) / 2.0)
        cy = (by0 + by1) / 2.0 if by0 > 0 else by1 - 3.0     # 위가 잘린 먼 등: 보이는 아래쪽 기준
        ry = max(1.0, (by1 - by0) / 2.0) if by0 > 0 else 3.0
        for x, y in comp:
            cv.c[y * cv.w + x] = rim
        # 고리 안쪽: 줄마다 처음 검은 점과 마지막 검은 점 사이의 검지 않은 점
        for y in range(by0, by1 + 1):
            zs = [x for x in range(bx0, bx1 + 1) if cv.v[y * cv.w + x] == 0]
            if len(zs) < 2:
                continue
            for x in range(zs[0] + 1, zs[-1]):
                i = y * cv.w + x
                if cv.v[i] != 0:
                    d = min(1.0, (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) ** 0.5)
                    cv.c[i] = art.mix(art.hexc('#fffcee'), art.hexc('#f4d27c'), d)
        # 둘레 천장에 은은한 빛
        for y in range(max(0, by0 - 3), min(25, by1 + 4)):
            for x in range(max(0, bx0 - 6), min(cv.w, bx1 + 7)):
                i = y * cv.w + x
                if cv.v[i] == 3 and not (bx0 <= x <= bx1 and by0 <= y <= by1):
                    dx = max(bx0 - x, x - bx1, 0) / 6.0
                    dy = max(by0 - y, y - by1, 0) / 3.0
                    k = max(0.0, 1.0 - max(dx, dy)) * 0.35
                    if k > 0:
                        cv.c[i] = art.mix(cv.c[i], art.hexc('#fff0c0'), k)


def mural(cv, x0, y0, x1, y1):
    """로비 벽화: 청록/흰 체크 = 하늘, 검정/흰 체크 = 바위, 흰 덩어리 = 눈, 꽉 찬 청록 = 먼 산, 검정 = 윤곽"""
    import art
    V = lambda x, y: cv.v[y * cv.w + x] if x0 <= x <= x1 and y0 <= y <= y1 else -1

    def checker(x, y, pair):
        v = V(x, y)
        if v not in pair:
            return False
        for (ax, ay), (bx, by) in (((x - 1, y), (x + 1, y)), ((x, y - 1), (x, y + 1))):
            a, b = V(ax, ay), V(bx, by)
            o = pair[0] if v == pair[1] else pair[1]
            if a == o and (b == o or b == -1) or b == o and a == -1:
                return True
        return False
    cls = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            v = V(x, y)
            if checker(x, y, (1, 3)):
                cls[(x, y)] = 'sky'
            elif checker(x, y, (0, 3)):
                cls[(x, y)] = 'rock'
            elif v == 3:
                cls[(x, y)] = 'snow'
            elif v == 1:
                cls[(x, y)] = 'far'
            else:
                cls[(x, y)] = 'line'
    # 체크 속 겹친 점 (같은 값 두 개): 양옆이 하늘/바위면 따라간다
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = cls[(x, y)]
            if c in ('snow', 'far'):
                l, r = cls.get((x - 1, y)), cls.get((x + 1, y))
                l2, r2 = cls.get((x - 2, y)), cls.get((x + 2, y))
                if 'sky' in (l, r) and 'sky' in (l2, r2, l, r) and (l == 'sky' or r == 'sky'):
                    if (l == 'sky' and (r == 'sky' or r2 == 'sky')) or (r == 'sky' and l2 == 'sky'):
                        cls[(x, y)] = 'sky'
    # 작은 눈/먼 산 덩어리 (3점 이하) 는 체크 가장자리의 점: 둘레에 많은 쪽 (하늘/바위) 으로
    seen = set()
    for (x, y), c in list(cls.items()):
        if c not in ('snow', 'far') or (x, y) in seen:
            continue
        comp = [(x, y)]
        seen.add((x, y))
        st = [(x, y)]
        while st:
            cx, cy = st.pop()
            for n in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if n not in seen and cls.get(n) == c:
                    seen.add(n)
                    comp.append(n)
                    st.append(n)
        if len(comp) > 3:
            continue
        cnt = {}
        for cx, cy in comp:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    k = cls.get((cx + dx, cy + dy))
                    if k in ('sky', 'rock'):
                        cnt[k] = cnt.get(k, 0) + 1
        if cnt:
            k = max(cnt, key=cnt.get)
            for p in comp:
                cls[p] = k
    t = lambda y: (y - y0) / float(y1 - y0)
    for (x, y), c in cls.items():
        i = y * cv.w + x
        if c == 'sky':
            col = art.mix(art.hexc('#4a88d8'), art.hexc('#b4d6f2'), t(y))
        elif c == 'rock':
            col = art.mix(art.hexc('#707a8a'), art.hexc('#5a6272'), t(y))
        elif c == 'snow':
            col = art.mix(art.hexc('#fbfcfe'), art.hexc('#d8e2ee'), t(y))
        elif c == 'far':
            col = art.mix(art.hexc('#7ea4cc'), art.hexc('#5a82b0'), t(y))
        else:
            col = art.hexc('#2a3444')
        cv.c[i] = col


def wall_corner(cv, poly, c0, c1, gx0, gx1):
    """벽지 조각: 흰 점 = 벽지 바탕 (가로 그라데이션 c0 -> c1, gx0..gx1), 흰 점 사이의 검은 점 = 벽지 무늬.
    소파 윤곽(이어진 검은 점)과 바닥 타일(자홍) 옆 선은 그대로"""
    import art
    V = lambda x, y: cv.v[y * cv.w + x] if 0 <= x < cv.w and 0 <= y < cv.h else -1
    for x, y in cv.rect(poly):
        i = y * cv.w + x
        v = cv.v[i]
        if v == 3:
            cv.c[i] = art.mix(art.hexc(c0), art.hexc(c1), (x - gx0) / float(gx1 - gx0))
        elif v == 0 and ((V(x - 1, y) == 3 and V(x + 1, y) == 3) or (V(x, y - 1) == 3 and V(x, y + 1) == 3)):
            cv.c[i] = art.hexc('#9a8a70')


def floor_edge_dots(cv, rects):
    """벽과 바닥이 만나는 줄: 크림 바닥 위의 벽지 점 -> 바닥 색"""
    for r in rects:
        for x, y in cv.rect(r):
            i = y * cv.w + x
            if cv.v[i] == 0 and 0 < x < cv.w - 1 and cv.v[i - 1] == 3 and cv.v[i + 1] == 3                     and cv.v[i + cv.w] != 0:
                cv.c[i] = cv.c[i + 1]


# ---------------------------------------------------------------------------
#  로비: 엘리베이터 세 문 (출구 / 편집 / 게임), 대리석 바닥, 가죽 소파
# ---------------------------------------------------------------------------
PLATE = '#27303e'
LOBBY = [
    # 천장, 조명
    ('map', (0, 0, 319, 26), {3: ('#d8d0c0', '#ece6da'), 0: '#5a5048', 1: '#fff2b0', 2: '#fff2b0'}),
    ('func', lambda cv: lamps(cv, 0, 21)),
    # 옆 벽지 (흰 바탕 검은 점)
    ('map', (0, 0, 49, 150), {3: ('h', '#b8a88c', '#d4c6aa'), 0: '#9a8a70'}),
    ('map', (268, 0, 319, 150), {3: ('h', '#d4c6aa', '#b8a88c'), 0: '#9a8a70'}),
    # 안쪽 벽 윗부분
    ('map', (48, 25, 268, 62), {3: '#ece6da', 0: '#3a3430'}),
    # 벽화: 하늘, 눈 덮인 산
    ('map', (62, 31, 252, 56), {1: ('#78aee8', '#b8d8f4'), 3: '#f4f6fa', 0: '#2a3444', 2: '#9aa8b8'}),
    ('func', lambda cv: mural(cv, 63, 35, 251, 55)),
    # 가운데 어두운 돌 벽 (문 둘레)
    ('map', (48, 58, 268, 142), {0: '#302a36', 3: '#d8d0c0'}),      # 한 색 (그라데이션은 띠가 생긴다)
    # 출구 문 (나무), 창 (젖빛 유리)
    # 문짝은 한 색 (세로 그라데이션은 256색으로 줄이면 띠가 생긴다), 왼쪽 가장자리 밝게 / 오른쪽 어둡게
    ('map', (56, 73, 88, 141), {1: '#8a5a36', 3: '#d8d0c0', 0: '#2a1a10'}),
    ('map', (57, 75, 58, 139), {1: '#a06e44'}),
    ('map', (85, 75, 86, 139), {1: '#6c4428'}),
    ('map', (59, 76, 83, 97), {3: '#c8dae6', 0: '#90a8b8'}),
    ('blur', (60, 77, 82, 96), 1, ()),
    # 엘리베이터 문 (강철)
    ('map', (102, 69, 170, 141), {1: ('h', '#c8d0d8', '#98a2ac'), 0: '#40484f', 3: '#e8ecf0'}),
    ('map', (183, 69, 249, 141), {1: ('h', '#c8d0d8', '#98a2ac'), 0: '#40484f', 3: '#e8ecf0'}),
    # 호출 단추
    ('map', (170, 104, 182, 118), {3: '#c8d0d8', 2: '#e04040', 0: '#303038'}),
    ('map', (254, 104, 267, 118), {3: '#c8d0d8', 2: '#e04040', 0: '#303038'}),
    # 표지판 (글자는 지우고 한글을 덧그린다)
    # 표지판: 흰 판에 자홍 글자 -> 짙은 판에 붉게 빛나는 글자 (판 안쪽만)
    ('map', (54, 59, 90, 69), {3: '#2e2a34', 2: '#ff6a50', 0: '#1c1820', 1: '#2e2a34'}),
    ('map', (118, 59, 154, 69), {3: '#2e2a34', 2: '#ff6a50', 0: '#1c1820', 1: '#2e2a34'}),
    ('map', (198, 59, 234, 69), {3: '#2e2a34', 2: '#ff6a50', 0: '#1c1820', 1: '#2e2a34'}),
    # 대리석 바닥
    ('map', (0, 140, 319, 199), {2: ('#7c3444', '#9a4656'), 3: ('#e6e0d4', '#f6f2ea'), 0: '#3a2e2e'}),
    # 가죽 소파: 검은 점과, 검은 점 사이에 박힌 자홍 점만
    # 소파 윗선 (청록 대각선) 위는 벽지: 왼쪽 (22,140)->(0,151), 오른쪽 (297,140)->(319,151)
    ('map', [(0, 138), (47, 138), (47, 140), (22, 140), (0, 153)], {3: ('h', '#b8a88c', '#d4c6aa'), 0: '#9a8a70',
                                                                 1: '#9a6440'}),
    ('map', [(319, 138), (268, 138), (268, 140), (297, 140), (319, 153)], {3: ('h', '#d4c6aa', '#b8a88c'),
                                                                        0: '#9a8a70', 1: '#9a6440'}),
    ('func', lambda cv: couch(cv, [(0, 152), (22, 140), (44, 140), (68, 150), (68, 178), (44, 199), (0, 199)])),
    ('func', lambda cv: couch(cv, [(319, 152), (297, 140), (276, 140), (250, 150), (250, 178), (276, 199),
                                   (319, 199)])),
    # 소파와 바닥 타일 사이까지 내려온 벽지 (원판도 점 무늬가 이어진다)
    ('func', lambda cv: wall_corner(cv, [(36, 139), (49, 139), (49, 141), (46, 142), (43, 146), (40, 148), (36, 148)],
                                    '#b8a88c', '#d4c6aa', 0, 49)),
    ('func', lambda cv: wall_corner(cv, [(283, 139), (270, 139), (270, 141), (273, 142), (276, 146), (279, 148),
                                         (283, 148)], '#d4c6aa', '#b8a88c', 268, 319)),
]
LOBBY_LABELS = [(59, 60, '출구', '#f4e6b0', '#101010'), (123, 60, '편집', '#f4e6b0', '#101010'),
                (203, 60, '게임', '#f4e6b0', '#101010')]

# ---------------------------------------------------------------------------
#  선수 방: 벽돌 벽, 액자 넷(선수 1..4), 이름표, 메뉴판, 시간판
# ---------------------------------------------------------------------------
BOARD = '#22304a'
BOARD_TEXT = '#f2e6c4'
# 액자 넷: 선수 1 의 원판 위치를 기준으로 (나무 판 32..79 x 13..61, 초상 바탕 41..70 x 22..52)
FRAME_OFS = [(0, 0), (95, 25), (0, 76), (95, 116)]
SHIRTS = ['#d04850', '#3a9a58', '#3a70c8', '#e08a30']
WOOD = '#9a6a3c'
SKY = '#b8d8f0'
PLATES = [(12, 60, 100, 75), (108, 84, 196, 99), (12, 136, 100, 151), (108, 176, 196, 191)]
PLAYERS = [
    # 벽: 청록 벽돌 -> 붉은 벽돌, 자홍 띠 -> 강철 보
    ('map', (0, 0, 319, 199), {1: '#b45a3e', 0: '#3a2c28', 2: '#5a6270', 3: '#e0d8c8'}),
    ('func', lambda cv: brick_vary(cv, (0, 0, 319, 199), 1)),
] + [('map', (32 + dx, 13 + dy, 79 + dx, 61 + dy), {2: WOOD, 1: WOOD, 3: '#c89a64'}) for dx, dy in FRAME_OFS] + [
    ('map', (30 + dx, 11 + dy, 81 + dx, 63 + dy), {2: WOOD}) for dx, dy in FRAME_OFS] + [
    ('map', (14 + dx, 44 + dy, 27 + dx, 60 + dy), {2: '#5a3e28'}) for dx, dy in FRAME_OFS] + [
    ('map', (41 + dx, 22 + dy, 70 + dx, 52 + dy), {2: sh, 1: SKY, 0: '#1c2028', 3: '#f4f0e8'})
    for (dx, dy), sh in zip(FRAME_OFS, SHIRTS)] + [
    ('map', r, {3: '#f4ecd6', 0: '#2a2018', 2: '#8a5a30', 1: '#c8b890'}) for r in PLATES] + [
    # 메뉴판과 시간판
    ('map', (213, 24, 312, 79), {2: BOARD, 3: '#e8e0cc', 0: '#0e1420'}),
    ('map', (213, 108, 312, 164), {2: BOARD, 3: '#e8e0cc', 0: '#0e1420'}),
    ('map', (233, 27, 309, 40), {0: BOARD_TEXT}),
    ('map', (233, 44, 309, 58), {0: BOARD_TEXT}),
    ('map', (233, 61, 309, 74), {0: BOARD_TEXT}),
    ('map', (238, 114, 290, 124), {0: BOARD_TEXT}),
    ('map', (237, 147, 293, 158), {0: BOARD_TEXT}),
]
PLAYERS_LABELS = [(236, 28, '나가기', BOARD_TEXT, '#000000'), (236, 45, '게임 하기', BOARD_TEXT, '#000000'),
                  (236, 62, '취소', BOARD_TEXT, '#000000'), (240, 112, '제한 시간', BOARD_TEXT, '#000000'),
                  (258, 146, '분', BOARD_TEXT, '#000000')]


def brick_vary(cv, r, val, tones=None):
    """이어진 벽돌(같은 값)마다 조금씩 다른 색 (tones[0] 으로 칠해 둔 점만)"""
    import art
    tones = tones or ['#b45a3e', '#a8503a', '#c06444', '#9e4a34', '#b85e40']
    seen = {}
    x0, y0, x1, y1 = r
    k = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            i = y * cv.w + x
            if cv.v[i] != val or i in seen or cv.c[i] != art.hexc(tones[0]):
                continue
            st = [i]; seen[i] = k; comp = [i]
            while st:
                j = st.pop()
                jx, jy = j % cv.w, j // cv.w
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = jx + dx, jy + dy
                    if x0 <= nx <= x1 and y0 <= ny <= y1:
                        n = ny * cv.w + nx
                        if n not in seen and cv.v[n] == val and cv.c[n] == art.hexc(tones[0]):
                            seen[n] = k; st.append(n); comp.append(n)
            c = art.hexc(tones[(k * 7 + 2) % len(tones)])
            top = min(j // cv.w for j in comp)
            for j in comp:
                cv.c[j] = art.shade(c, 1.2) if j // cv.w == top else c
            k += 1


# ---------------------------------------------------------------------------
#  쉬는 화면 (P): 내 점수판, 명예의 전당, 밀기/이동/시간 기록 카드
# ---------------------------------------------------------------------------
CARD = ('#ece0c4', '#ece0c4')
CARD_TEXT = '#3a2a1a'
PAUSE = [
    # 바탕 벽돌: 자홍 -> 짙은 보라 벽돌
    ('map', (0, 0, 319, 199), {2: '#4e3c62', 0: '#1c1628', 1: '#6a5a80', 3: '#8a7aa0'}),
    ('func', lambda cv: brick_vary(cv, (0, 0, 319, 199), 2, ['#4e3c62', '#463858', '#56446a', '#4a3a5e'])),
    # 판들 (청록 -> 크림)
    ('map', (25, 22, 92, 90), {1: CARD, 3: '#fffaf0', 0: '#241a14', 2: '#c04848'}),
    ('map', (125, 12, 295, 81), {1: CARD, 3: '#fffaf0', 0: '#241a14', 2: '#c04848'}),
    ('map', (27, 107, 92, 175), {1: CARD, 3: '#fffaf0', 0: '#241a14', 2: '#c04848'}),
    ('map', (127, 107, 192, 175), {1: CARD, 3: '#fffaf0', 0: '#241a14', 2: '#c04848'}),
    ('map', (223, 107, 289, 175), {1: CARD, 3: '#fffaf0', 0: '#241a14', 2: '#c04848'}),
    # 카드 그림 (하늘색 바탕)
    ('map', (29, 108, 89, 138), {1: ('#9cc8ec', '#d4e8f8'), 2: '#d04850', 3: '#f8f4ec', 0: '#1c1c24'}),
    ('map', (129, 108, 189, 138), {1: ('#9cc8ec', '#d4e8f8'), 2: '#3a70c8', 3: '#f8f4ec', 0: '#1c1c24'}),
    ('map', (225, 108, 287, 138), {1: ('#9cc8ec', '#d4e8f8'), 2: '#e08a30', 3: '#f8f4ec', 0: '#1c1c24'}),
    # 영어 글자 지우기
]
PAUSE_LABELS = [(179, 13, '명예의 전당', CARD_TEXT, None), (154, 66, '저장', CARD_TEXT, None),
                (217, 66, '계속', CARD_TEXT, None), (37, 77, '내 점수', CARD_TEXT, None),
                (48, 137, '밀기', CARD_TEXT, None), (148, 137, '이동', CARD_TEXT, None),
                (248, 137, '시간', CARD_TEXT, None), (73, 148, '나', '#a03030', None), (173, 148, '나', '#a03030', None),
                (28, 161, '최고', '#305a90', None), (128, 161, '최고', '#305a90', None)]

# ---------------------------------------------------------------------------
#  판 고르기 (대회): 1..99 표.  원판 그림의 49 칸이 46 으로 잘못 그려진 것은 고친다
# ---------------------------------------------------------------------------
PANEL = '#ece0c4'
PANEL_TEXT = '#3a2a1a'
SELECT = [
    ('map', (0, 0, 319, 199), {1: '#b45a3e', 0: '#3a2c28', 2: '#5a6270', 3: '#e0d8c8'}),
    ('func', lambda cv: brick_vary(cv, (0, 0, 319, 199), 1)),
    ('map', (42, 4, 281, 189), {1: PANEL, 3: '#fffaf0', 0: '#2a2018', 2: '#8a6a50'}),
    ('func', lambda cv: fix_49(cv)),
]

# ---------------------------------------------------------------------------
#  대회 점수판: 이름 / 푼 판 / 판 / 점수, 단추 시작 / 그만 / 저장
# ---------------------------------------------------------------------------
TOUR = [
    ('map', (0, 0, 319, 199), {1: '#b45a3e', 0: '#3a2c28', 2: '#5a6270', 3: '#e0d8c8'}),
    ('func', lambda cv: brick_vary(cv, (0, 0, 319, 199), 1)),
    ('map', (33, 45, 287, 150), {1: PANEL, 3: '#fffaf0', 0: '#2a2018', 2: '#b8a080'}),
    ('map', (43, 36, 275, 50), {3: '#f8f0dc', 0: '#2a2018', 2: '#8a6a50', 1: PANEL}),
]


def fix_49(cv):
    """원판 판 고르기 그림의 49 칸이 '46' 으로 잘못 그려져 있다: 옆 칸 '59' 의 9 를 베껴 온다"""
    for y in range(81, 89):
        for x in range(140, 148):
            cv.v[y * cv.w + x] = cv.v[(y + 11) * cv.w + x + 20]
            cv.c[y * cv.w + x] = cv.c[(y + 11) * cv.w + x + 20]


# ---------------------------------------------------------------------------
#  편집기 아이콘 화면: 벽 / 상자 / 목표 / 저장 / 지우기 / 불러오기 / 시험 / 나가기
# ---------------------------------------------------------------------------
# 아이콘 (56x66): 뒷화면 위치와 한글 이름.  icon_dat 의 강조 아이콘도 같은 모양
ICON_POS = {'A': (36, 16), 'B': (92, 34), 'C': (176, 9), 'D': (20, 99), 'E': (76, 105), 'F': (240, 47),
            'G': (228, 109), 'H': (148, 79)}
ICON_NAME = {'A': '벽', 'B': '상자', 'C': '목표', 'D': '저장', 'E': '지우기', 'F': '불러오기', 'G': '시험',
             'H': '나가기'}
ICON_CARD = '#c65a7c'
ICON_CARD_HI = '#f0a030'
ICON_TEXT = '#fff4dc'


# 아이콘마다 그림 색.  원판은 면을 체크 무늬(두 값이 번갈아)로 그렸다: 체크는 한 면으로 묶어 한 색.
#  갈래: s0..s3 = 한 값, dAB = A/B 체크.  (x0, y0, x1, y1) 은 아이콘 안 좌표 (56x66, 끝 포함), 먼저 맞는 것.
ICON_ART = {
    'A': [((5, 3, 18, 51), {'s3': '#c4603e', 's0': '#dccfb6'}),                       # 벽돌 (흰 벽돌, 검은 줄눈)
          ((18, 4, 47, 50), {'s1': '#d98c5e', 's0': '#9a5236', 's3': '#f2caa0',       # 쌓는 벽: 밝은 면
                             'd02': '#6e3626', 'd01': '#b87050', 'd12': '#8a4a34'})],  # 그늘 면
    'B': [((2, 4, 49, 53), {'d13': '#e2b47a', 'd12': '#b9814a', 'd01': '#6f4b2d', 'd02': '#8f3f59',
                            's0': '#3a2616', 's3': '#f0d6a8', 's1': '#d4a066'})],            # 나무 상자
    'C': [((6, 24, 18, 41), {'s3': '#d6a462', 's0': '#5a3a20', 's1': '#8c9aa8'}),     # 쌓인 짐
          ((33, 23, 46, 41), {'s3': '#d6a462', 's0': '#5a3a20', 's1': '#8c9aa8'}),
          ((6, 7, 45, 43), {'s3': '#f3ead6', 's2': '#b98a5e', 's1': '#8e9cab', 's0': '#3a3028'}),  # 창고 복도
          ((3, 2, 48, 52), {'s3': '#e6decb', 's0': '#2a2420'})],
    'D': [((41, 2, 49, 53), {'d01': '#5e7384', 's1': '#8aa2b4', 's0': '#26303a', 's2': '#5e7384'}),  # 서랍장 옆
          ((3, 2, 49, 53), {'s1': '#a9bccb', 's3': '#f4efe0', 's0': '#26303a'})],      # 서랍 (강철), 서류
    'E': [((9, 2, 44, 25), {'s2': '#d6e9f3', 'd02': '#8fb2c6', 's0': '#2c3642', 's3': '#ffffff'}),  # 유리 뚜껑
          ((6, 25, 48, 53), {'s3': '#e2e6ec', 's0': '#4a525c', 's1': '#a8dcf2', 's2': '#c85a6a'})],  # 크롬 몸통
    'F': [((2, 2, 49, 52), {'s3': '#fbf5e8', 's1': '#f39a3a', 's0': '#3a2418', 's2': '#cf6a34'})],  # 금붕어 카드
    'G': [((5, 11, 47, 46), {'d13': '#e8d8a6', 's1': '#e8d8a6', 's3': '#e8d8a6', 's0': '#2e6a36',
                             's2': '#4e8a4a'})],                                        # 미로: 모래 길, 산울타리
    'H': [((3, 2, 7, 53), {'s1': '#9aa8b8', 's0': '#2c3440'}),                         # 엘리베이터 문틀
          ((44, 2, 49, 53), {'s1': '#9aa8b8', 's0': '#2c3440', 's2': '#9aa8b8'}),
          ((8, 3, 43, 8), {'s3': '#eef2f6', 's1': '#b8c4d0', 's0': '#2c3440'}),
          ((8, 9, 43, 39), {'d02': '#9a6a46', 's2': '#9a6a46', 's0': '#2c2420'}),       # 안쪽 나무 벽
          ((8, 40, 43, 46), {'s1': '#c4ccd6', 's3': '#eef2f6', 's0': '#2c3440'}),
          ((8, 47, 43, 53), {'s1': '#8a6a50', 's2': '#6a4e3a', 's3': '#8a6a50', 's0': '#2c3440'})],  # 깔개
}
ICON_DEFAULT = {'s0': '#1e1a20', 's1': '#9cc8d8', 's2': '#b06080', 's3': '#f4f0e8'}
_icon_cache = {}


def _icon_normal(key):
    """보통 아이콘의 값 (56x66) 과 카드 자리 (강조 아이콘 ICON_DAT 와 다른 곳)"""
    if key in _icon_cache:
        return _icon_cache[key]
    import art, os
    x0, y0 = ICON_POS[key]
    vals = art.screen_values('icons')
    nv = [[vals[(y0 + y) * 320 + x0 + x] if x0 + x < 320 else 0 for x in range(56)] for y in range(66)]
    buf = open(os.path.join(art.ROOT, 'ICON_DAT'), 'rb').read()
    off = 0x59C + 'FHGEDCBA'.index(key) * 0x39C
    hv = []
    for y in range(66):
        hv += art.pixels(buf[off + y * 14:off + (y + 1) * 14])
    card = set((x, y) for y in range(66) for x in range(56) if nv[y][x] == 2 and hv[y * 56 + x] == 1)
    _icon_cache[key] = (nv, card)
    return nv, card


def icon_paint(cv, ox, oy, key, card_col):
    """아이콘 하나를 칠한다 (보통 아이콘 화면, 또는 강조 아이콘 비트맵 - 둘 다 보통 아이콘 값으로 가른다)"""
    import art
    nv, card = _icon_normal(key)
    V = lambda x, y: nv[y][x] if 0 <= x < 56 and 0 <= y < 66 else -1
    cl = {}
    for y in range(66):
        for x in range(56):
            v = nv[y][x]
            l, r, u, d = V(x - 1, y), V(x + 1, y), V(x, y - 1), V(x, y + 1)
            if l == r == u == d and l not in (v, -1):
                cl[(x, y)] = 'd%d%d' % (min(v, l), max(v, l))
            else:
                cl[(x, y)] = 's%d' % v
    # 체크 면 가장자리: 이웃 둘 이상이 같은 체크이고 내 값이 그 체크의 값이면 그 면으로
    for _ in range(2):
        new = {}
        for (x, y), c in cl.items():
            if c[0] != 's' or (x, y) in card:
                continue
            cnt = {}
            for n in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                k = cl.get(n)
                if k and k[0] == 'd' and str(nv[y][x]) in k[1:] and n not in card:
                    cnt[k] = cnt.get(k, 0) + 1
            if cnt:
                k = max(cnt, key=cnt.get)
                if cnt[k] >= 2:
                    new[(x, y)] = k
        cl.update(new)
    for y in range(63):
        for x in range(52):
            X, Y = ox + x, oy + y
            if not (0 <= X < cv.w and 0 <= Y < cv.h):
                continue
            i = Y * cv.w + X
            if (x, y) in card:
                cv.c[i] = art.hexc(card_col)
                continue
            cls = cl[(x, y)]
            col = None
            for (x0, y0, x1, y1), m in ICON_ART.get(key, []):
                if x0 <= x <= x1 and y0 <= y <= y1 and cls in m:
                    col = m[cls]
                    break
            if col is None:
                if cls[0] == 'd':
                    a, b = int(cls[1]), int(cls[2])
                    col = art.mix(art.hexc(ICON_DEFAULT['s%d' % a]), art.hexc(ICON_DEFAULT['s%d' % b]), 0.5)
                else:
                    col = ICON_DEFAULT[cls]
            cv.c[i] = art.hexc(col)


def icon_rules(ox, oy, key, card, text=ICON_TEXT):
    """아이콘 하나 (왼쪽 위 ox, oy)"""
    return [('func', lambda cv: icon_paint(cv, ox, oy, key, card))]


ICONS = [
    # 바탕 (청록/흰 체크) -> 부드러운 푸른 회색, 테두리 입체 -> 강철
    ('map', (0, 0, 319, 199), {1: '#8a9cb8', 3: '#c8d4e4', 0: '#1c2028', 2: '#6a7890'}),
    ('blur', (12, 8, 300, 175), 1, (0, 2)),
    ('map', (0, 175, 319, 199), {1: '#7a8a9a', 3: '#b0bcc8', 0: '#2a3038'}),
    ('map', (300, 0, 319, 199), {1: '#7a8a9a', 3: '#b0bcc8', 0: '#2a3038'}),
] + sum((icon_rules(x, y, k, ICON_CARD) for k, (x, y) in ICON_POS.items()), [])

# ---------------------------------------------------------------------------
#  엘리베이터 안: 층 단추판 (층 = 판 번호), 지움 / 확인
# ---------------------------------------------------------------------------
ELEV = [
    # 왼쪽 문 (강철), 오른쪽 벽 (짙은 나무 판)
    ('map', (0, 0, 146, 170), {1: ('h', '#c4ccd4', '#8e98a2'), 0: '#343a42', 3: '#e8ecf0', 2: '#8e98a2'}),
    ('map', (146, 0, 319, 172), {2: '#6a3e28', 0: '#4a2a1a', 1: '#b0b8c0', 3: '#e8ecf0'}),
    ('blur', (147, 0, 319, 170), 1, ()),
    # 단추판 (금속), 단추 (놋쇠), 층 표시창 (붉은 빛)
    ('map', (166, 4, 254, 112), {1: ('#d8dee4', '#a8b0b8'), 0: '#20242a', 3: '#f4f6f8', 2: '#e0b050'}),
    ('map', (198, 8, 226, 20), {2: '#401414'}),
    ('map', (194, 104, 228, 120), {1: '#a8b0b8', 2: '#401414', 0: '#20242a', 3: '#f4f6f8'}),
    # 바닥
    ('map', (0, 160, 146, 199), {1: '#6a4a38', 2: '#8a6048', 0: '#2a1a14', 3: '#d8c8b0'}),
    ('blur', (0, 170, 146, 199), 1, (0,)),
    ('map', (146, 165, 319, 199), {1: '#b0b8c0', 3: '#d8d0c4', 0: '#2a2420', 2: '#8a6048'}),
]

LABELS = {}                 # 원판 글자를 그대로 쓴다 (한글로 바꾸지 않는다)

SCREENS = {
    'title': (['intro1', 'intro2'], TITLE),
    'lobby': (['lobby11', 'lobby12'], LOBBY),
    'players': (['players1', 'players2'], PLAYERS),
    'select': (['select1', 'select2', 'select3', 'select4'], SELECT),
    'tour': (['tour1', 'tour2'], TOUR),
    'pause': (['pause1', 'pause1a'], PAUSE),
    'icons': (['icons1', 'icons2'], ICONS),
    'elev': (['elev.bin'], ELEV),
}
