# -*- coding: utf-8 -*-
"""애드립(OPL2) VGM 곡 만들기 틀 - sopwith/tools/mkmusic.py 에서 가져왔다
   Song(악보), render(VGM 으로), bundle(SOUND.DAT 묶기), 음색표, 화음 도움 함수"""
import os, struct, sys, math
SR = 44100
TICK = SR * 65536 / 1193182.0           # BIOS 시계 한 틱 (약 55ms) 의 샘플 수


# ---------------------------------------------------------------- 음색 ------
# (모듈레이터 20 40 60 80 E0), (캐리어 20 40 60 80 E0), C0
P_BASS    = ((0x20, 0x1D, 0xB4, 0x0F, 0x00), (0x21, 0x00, 0xC3, 0x0F, 0x00), 0x3E)
P_UPRIGHT = ((0x01, 0x15, 0xF6, 0x58, 0x00), (0x01, 0x00, 0xF4, 0x58, 0x00), 0x0A)
P_PIZZ    = ((0x01, 0x1C, 0xF8, 0x7A, 0x00), (0x01, 0x02, 0xF6, 0x7A, 0x00), 0x08)
P_PIANO   = ((0x01, 0x4F, 0xF1, 0x53, 0x00), (0x11, 0x06, 0xD2, 0x74, 0x00), 0x06)
P_MUTED   = ((0x21, 0x1A, 0x85, 0x17, 0x00), (0x21, 0x04, 0x74, 0x17, 0x00), 0x0C)
P_BRASS   = ((0x21, 0x16, 0x86, 0x16, 0x00), (0x21, 0x02, 0x74, 0x17, 0x00), 0x0E)
P_TROMB   = ((0x21, 0x1A, 0x53, 0x17, 0x00), (0x21, 0x02, 0x63, 0x18, 0x00), 0x0C)
P_CLAR    = ((0x32, 0x1E, 0x74, 0x17, 0x00), (0x21, 0x04, 0x74, 0x17, 0x00), 0x0A)
P_SAX     = ((0x31, 0x17, 0x73, 0x17, 0x00), (0x21, 0x03, 0x74, 0x17, 0x00), 0x0A)
P_FLUTE   = ((0x61, 0x22, 0x74, 0x16, 0x00), (0x21, 0x02, 0x63, 0x16, 0x00), 0x08)
P_VIBES   = ((0x07, 0x22, 0xF4, 0x45, 0x00), (0x01, 0x04, 0xF3, 0x45, 0x00), 0x02)
P_GLOCK   = ((0x06, 0x1F, 0xF6, 0x44, 0x00), (0x01, 0x06, 0xF4, 0x44, 0x00), 0x00)
P_PLUCK   = ((0x01, 0x1B, 0xF6, 0x56, 0x00), (0x01, 0x08, 0xF4, 0x57, 0x00), 0x0A)
P_PAD     = ((0x21, 0x22, 0x54, 0x24, 0x00), (0x21, 0x10, 0x53, 0x25, 0x00), 0x0C)
P_STRINGS = ((0x31, 0x1C, 0x51, 0x13, 0x00), (0x21, 0x10, 0x52, 0x14, 0x00), 0x0E)
# 리듬부
P_BD      = ((0x00, 0x0B, 0xD8, 0x0F, 0x00), (0x00, 0x04, 0xF5, 0x0F, 0x00), 0x38)
P_HH_SD   = ((0x01, 0x10, 0xF8, 0x0F, 0x00), (0x01, 0x0A, 0xF7, 0x0F, 0x00), 0x39)
P_TOM_CY  = ((0x04, 0x08, 0xF7, 0x0F, 0x00), (0x0E, 0x10, 0xC9, 0x0F, 0x00), 0x3D)

BD, SD, TOM, CYM, HH = 0x10, 0x08, 0x04, 0x02, 0x01

OP1 = [0x00, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x10, 0x11, 0x12]
OP2 = [0x03, 0x04, 0x05, 0x0B, 0x0C, 0x0D, 0x13, 0x14, 0x15]


def fnum_block(m):
    f = 440.0 * 2.0 ** ((m - 69) / 12.0)
    for blk in range(8):
        fn = int(round(f * (1 << (20 - blk)) / 49716.0))
        if fn < 1024 and (fn >= 300 or blk == 7):
            return fn, blk
    return 1023, 7


NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi(name):
    k = NAMES[name[0]]
    i = 1
    while i < len(name) and name[i] in '#b':
        k += 1 if name[i] == '#' else -1
        i += 1
    return (int(name[i:]) + 1) * 12 + k


def seq(text):
    """'E5/4 B4/2 r/2 ...' -> [(시작, 길이, midi 또는 None)]"""
    out, t = [], 0
    for tok in text.split():
        name, ln = tok.split('/')
        ln = int(ln)
        out.append((t, ln, None if name == 'r' else midi(name)))
        t += ln
    return out, t


# ---------------------------------------------------------------- 악보 틀 ---
class Song:
    def __init__(self, bpm=None, div=4, tick_samples=None):
        self.tick_samples = tick_samples if tick_samples else SR * 60.0 / bpm / div
        self.ev = []
        self.loop_tick = None
        self.end_tick = 0

    def patch(self, t, ch, p):
        self.ev.append((t, 0, 'patch', ch, p))

    def note(self, t, ln, ch, m, gap=0.12, shift=0):
        if m is None:
            return
        self.ev.append((t, 2, 'on', ch, m + shift))
        self.ev.append((t + ln - min(gap, ln * 0.5), 1, 'off', ch, 0))
        self.end_tick = max(self.end_tick, t + ln)

    def melody(self, t, text, ch, shift=0, gap=0.12):
        notes, total = seq(text)
        for st, ln, m in notes:
            self.note(t + st, ln, ch, m, gap, shift)
        return total

    def drum(self, t, mask):
        self.ev.append((t, 3, 'drum', mask, 0))
        self.end_tick = max(self.end_tick, t + 1)

    def tom_pitch(self, t, m):
        self.ev.append((t, 0, 'tompitch', 8, m))


class Writer:
    def __init__(self):
        self.d = bytearray()
        self.samples = 0

    def w(self, reg, val):
        self.d += bytes((0x5A, reg & 0xFF, val & 0xFF))

    def wait_until(self, s):
        n = int(round(s)) - self.samples
        if n <= 0:
            return
        self.samples += n
        while n > 65535:
            self.d += bytes((0x61, 0xFF, 0xFF))
            n -= 65535
        self.d += bytes((0x61, n & 0xFF, n >> 8))

    def patch(self, ch, p):
        mod, car, c0 = p
        for r, v in zip((0x20, 0x40, 0x60, 0x80, 0xE0), mod):
            self.w(r + OP1[ch], v)
        for r, v in zip((0x20, 0x40, 0x60, 0x80, 0xE0), car):
            self.w(r + OP2[ch], v)
        self.w(0xC0 + ch, c0)


def render(song, name):
    v = Writer()
    rhythm = 0x20
    v.w(0x01, 0x20)
    v.w(0x08, 0x00)
    v.patch(6, P_BD)
    v.patch(7, P_HH_SD)
    v.patch(8, P_TOM_CY)
    for ch, m in ((6, 36), (7, 60), (8, 50)):
        fn, blk = fnum_block(m)
        v.w(0xA0 + ch, fn & 0xFF)
        v.w(0xB0 + ch, blk << 2 | fn >> 8)
    v.w(0xBD, rhythm)

    events = sorted(song.ev, key=lambda e: (e[0], e[1]))
    loop_offset = None
    last_b0 = {}
    i = 0
    while i < len(events):
        t = events[i][0]
        if song.loop_tick is not None and loop_offset is None and t >= song.loop_tick:
            v.wait_until(song.loop_tick * song.tick_samples)
            loop_offset = len(v.d)
        v.wait_until(t * song.tick_samples)
        mask = 0
        while i < len(events) and events[i][0] == t:
            e = events[i]
            kind = e[2]
            if kind == 'patch':
                v.patch(e[3], e[4])
            elif kind == 'on':
                fn, blk = fnum_block(e[4])
                v.w(0xB0 + e[3], blk << 2 | fn >> 8)
                v.w(0xA0 + e[3], fn & 0xFF)
                v.w(0xB0 + e[3], 0x20 | blk << 2 | fn >> 8)
                last_b0[e[3]] = blk << 2 | fn >> 8
            elif kind == 'off':
                v.w(0xB0 + e[3], last_b0.get(e[3], 0))     # 음높이는 두고 키만 뗀다
            elif kind == 'drum':
                mask |= e[3]
            elif kind == 'tompitch':
                fn, blk = fnum_block(e[4])
                v.w(0xA8, fn & 0xFF)
                v.w(0xB8, blk << 2 | fn >> 8)
            i += 1
        if mask:
            v.w(0xBD, rhythm & ~mask)
            v.w(0xBD, rhythm | mask)

    v.wait_until(song.end_tick * song.tick_samples)
    for ch in range(9):
        v.w(0xB0 + ch, 0x00)
    v.w(0xBD, rhythm)
    v.d += b'\x66'

    DATA = 0x100
    hdr = bytearray(DATA)
    hdr[0:4] = b'Vgm '
    struct.pack_into('<I', hdr, 0x04, DATA + len(v.d) - 4)
    struct.pack_into('<I', hdr, 0x08, 0x151)
    struct.pack_into('<I', hdr, 0x18, v.samples)
    if loop_offset is not None:
        struct.pack_into('<I', hdr, 0x1C, DATA + loop_offset - 0x1C)
        struct.pack_into('<I', hdr, 0x20, v.samples - int(round(song.loop_tick * song.tick_samples)))
    struct.pack_into('<I', hdr, 0x34, DATA - 0x34)
    struct.pack_into('<I', hdr, 0x50, 3579545)                 # YM3812 클럭
    print('%-12s %6d bytes  %5.1fs%s' % (name, DATA + len(v.d),
          v.samples / SR, '  (loop)' if loop_offset is not None else ''))
    return name, bytes(hdr) + bytes(v.d)


def bundle(path, songs):
    head = bytearray(b'SWSND10\0')
    head += struct.pack('<H', len(songs))
    off = len(head) + 20 * len(songs)
    body = bytearray()
    for name, data in songs:
        head += name.encode('ascii').ljust(12, b'\0')[:12]
        head += struct.pack('<II', off + len(body), len(data))
        body += data
    with open(path, 'wb') as f:
        f.write(bytes(head) + bytes(body))
    print('%s  %d bytes, %d songs' % (os.path.basename(path), len(head) + len(body), len(songs)))



# ---------------------------------------------------------------- 도움 함수 --
TONES = {'G': 'G B D', 'D7': 'D F# A C', 'C': 'C E G', 'A7': 'A C# E G', 'D': 'D F# A',
         'E7': 'E G# B D', 'Am': 'A C E', 'Em': 'E G B', 'G7': 'G B D F', 'F': 'F A C',
         'Dm': 'D F A', 'Gm': 'G Bb D', 'Cm': 'C Eb G', 'Eb': 'Eb G Bb', 'Bb': 'Bb D F'}


def pcs(name):
    return [(NAMES[x[0]] + x[1:].count('#') - x[1:].count('b')) % 12 for x in TONES[name].split()]


def voicing(name, lo=55, n=3):
    """lo 위로 가장 가까운 화음 음 n 개 (닫힌 화음)"""
    p = pcs(name)
    out, m = [], lo
    while len(out) < n:
        if m % 12 in p:
            out.append(m)
        m += 1
    return out


def bass_root(name, lo=36):
    r = pcs(name)[0]
    m = lo + (r - lo % 12) % 12
    return m


