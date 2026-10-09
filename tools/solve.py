# -*- coding: utf-8 -*-
"""소코반 풀이기 (시험 입력 만들기용): 원판 판 파일에서 판을 읽어 이동 순서(u/d/l/r)를 찾는다
   python tools/solve.py 판번호        -> 한 줄에 이동 글자들
   상자 위치 집합을 상태로 하는 밀기 단위 너비 우선 탐색 + 막다른 구석 가지치기."""
import os, sys
from collections import deque

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NAMES = ['TABL012', 'TABL034', 'TABLE56', 'TABLE78', 'TABL910'] + ['TAB%02d%02d' % (a, a + 1) for a in range(11, 50, 2)]
W = 19


def load(level):
    d = open(os.path.join(ROOT, NAMES[(level - 1) // 2]), 'rb').read()
    rec = d[((level - 1) % 2) * 306:((level - 1) % 2) * 306 + 306]
    pos = rec[0] | rec[1] << 8
    m = list(rec[2:])
    return pos, m


def solve(level):
    pos, m = load(level)
    walls = {i for i, c in enumerate(m) if c == 1}
    goals = {i for i, c in enumerate(m) if c == 3 or c == 0x17}
    boxes = frozenset(i for i, c in enumerate(m) if c >= 10)
    D = {'u': -W, 'd': W, 'l': -1, 'r': 1}
    # 막다른 칸: 목표가 아닌 구석
    dead = set()
    for i in range(304):
        if i in walls or i in goals:
            continue
        v = (i - W in walls) or (i + W in walls)
        h = (i - 1 in walls) or (i + 1 in walls)
        if v and h:
            dead.add(i)

    def reach(p, bx):
        seen = {p: ''}
        q = deque([p])
        while q:
            c = q.popleft()
            for k, dd in D.items():
                n = c + dd
                if 0 <= n < 304 and n not in walls and n not in bx and n not in seen:
                    seen[n] = seen[c] + k
                    q.append(n)
        return seen

    def norm(p, bx):
        return min(reach(p, bx))

    start = (norm(pos, boxes), boxes)
    prev = {start: None}
    q = deque([(pos, boxes)])
    while q:
        p, bx = q.popleft()
        if bx <= goals:
            # 되짚기
            path = []
            key = (norm(p, bx), bx)
            while prev[key]:
                (pk, mv) = prev[key]
                path.append(mv)
                key = pk
            return ''.join(reversed(path))
        r = reach(p, bx)
        for b in bx:
            for k, dd in D.items():
                stand = b - dd
                to = b + dd
                if stand in r and to not in walls and to not in bx and 0 <= to < 304 and to not in dead:
                    nb = frozenset((bx - {b}) | {to})
                    key = (norm(b, nb), nb)
                    if key not in prev:
                        prev[key] = ((norm(p, bx), bx), r[stand] + k)
                        q.append((b, nb))
    return None


if __name__ == '__main__':
    print(solve(int(sys.argv[1])))
