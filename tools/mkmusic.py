# -*- coding: utf-8 -*-
"""SOKOVGA.EXE 배경음악 - 애드립(OPL2) VGM 곡 셋을 SOUND.DAT 하나로 묶는다.

   쓰는 법 :  python tools/mkmusic.py [--vgm]     (--vgm: 들어 보기용 VGM 파일도 남긴다)

   곡 (skbopl.c 의 순서와 같다)
       SKBTITLE  타이틀, 로비, 선수 방, 엘리베이터, 메뉴   보사노바풍 라운지 곡 (되풀이)
       SKBPLAY   판 안                                   잔잔한 A 단조 퍼즐 곡 (되풀이)
       SKBWIN    판을 깼을 때                            원판 승리 곡(스피커 악보, DS:9BF7)의 금관 편곡
   원판 게임에는 배경음악이 없다 (승리 곡과 발소리, 알림음만 PC 스피커로).
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oplvgm import *

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def chord(names):
    """'F3 A3 C4 E4' -> midi 목록"""
    return [midi(n) for n in names.split()]


# ---------------------------------------------------------------- 타이틀 ---
def song_title():
    s = Song(bpm=112, div=4)
    s.patch(0, 0, P_VIBES)
    s.patch(0, 1, P_PIANO)
    s.patch(0, 2, P_PIANO)
    s.patch(0, 3, P_PIANO)
    s.patch(0, 4, P_UPRIGHT)
    s.patch(0, 5, P_FLUTE)
    # 한 마디 = 16 틱.  화음 (가운데 음역) 과 베이스 뿌리/5도
    prog = [('F3 A3 C4 E4', 'F2', 'C3'), ('D3 F3 A3 C4', 'D2', 'A2'), ('G3 Bb3 D4 F4', 'G2', 'D3'),
            ('G3 Bb3 C4 E4', 'C2', 'G2'), ('G3 A3 C4 E4', 'A2', 'E2'), ('F#3 A3 C4 E4', 'D2', 'A2'),
            ('G3 Bb3 D4 F4', 'G2', 'C3'), ('F3 A3 D4 E4', 'F2', 'C3')]
    mel_a = ('A5/6 G5/2 F5/4 E5/4 '        # 1
             'D5/6 E5/2 F5/4 A5/4 '         # 2
             'G5/6 F5/2 D5/4 Bb4/4 '        # 3
             'C5/12 r/4 '                   # 4
             'E5/6 D5/2 C5/4 E5/4 '         # 5
             'F#5/6 E5/2 D5/4 C5/4 '        # 6
             'Bb4/4 D5/4 C5/4 E5/4 '        # 7
             'F5/12 r/4')                   # 8
    mel_b = ('C6/6 A5/2 F5/4 A5/4 '
             'D6/6 C6/2 A5/4 F5/4 '
             'Bb5/6 A5/2 G5/4 F5/4 '
             'E5/8 G5/4 C6/4 '
             'A5/6 G5/2 E5/4 C5/4 '
             'D5/6 E5/2 F#5/4 A5/4 '
             'G5/4 Bb5/4 A5/4 E5/4 '
             'F5/12 r/4')
    s.loop_tick = 0
    t = 0
    for rep, mel in enumerate((mel_a, mel_b)):
        s.melody(t, mel, 0 if rep == 0 else 5, gap=0.3)
        for bar, (ch, root, fifth) in enumerate(prog):
            b = t + bar * 16
            notes = chord(ch)
            # 보사노바 피아노: 1, 2+, 4 에 짧게
            for st, ln in ((0, 3), (6, 2), (12, 3)):
                for k, m in enumerate(notes[:3]):
                    s.note(b + st, ln, 1 + k, m, gap=0.3)
            # 베이스: 뿌리 - 5도 - 뿌리 - 5도
            for st, m in ((0, midi(root)), (6, midi(fifth)), (8, midi(root)), (14, midi(fifth))):
                s.note(b + st, 2, 4, m, gap=0.4)
            # 북: 큰북 1, 3+ / 테두리(작은북) 엇박 / 하이햇 8분
            for st in range(0, 16, 2):
                s.drum(b + st, HH)
            s.drum(b, BD)
            s.drum(b + 10, BD)
            for st in (3, 6, 12) if bar % 2 == 0 else (2, 6, 10):
                s.drum(b + st, SD)
        t += 8 * 16
    s.end_tick = t
    return s


# ---------------------------------------------------------------- 판 안 ----
def song_play():
    s = Song(bpm=88, div=4)
    s.patch(0, 0, P_GLOCK)
    s.patch(0, 1, P_PAD)
    s.patch(0, 2, P_PAD)
    s.patch(0, 3, P_PLUCK)
    s.patch(0, 4, P_BASS)
    s.patch(0, 5, P_FLUTE)
    prog = [('A3 C4 E4', 'A2'), ('F3 A3 C4', 'F2'), ('C3 E3 G3', 'C3'), ('G3 B3 D4', 'G2'),
            ('A3 C4 E4', 'A2'), ('D3 F3 A3', 'D2'), ('E3 G#3 B3', 'E2'), ('A3 C4 E4', 'A2')]
    mel = ['E5/8 C5/4 D5/4', 'C5/8 A4/8', 'G4/4 C5/4 E5/8', 'D5/12 r/4',
           'E5/4 A5/4 G5/4 E5/4', 'F5/8 D5/8', 'B4/8 G#4/4 B4/4', 'A4/12 r/4',
           'C6/8 B5/4 A5/4', 'A5/8 F5/8', 'G5/4 E5/4 C5/8', 'B4/12 r/4',
           'C5/4 E5/4 A5/8', 'F5/4 D5/4 A4/8', 'E5/4 D5/4 B4/4 G#4/4', 'A4/16']
    s.loop_tick = 0
    t = 0
    for half in range(2):
        for bar, (ch, root) in enumerate(prog):
            b = t + bar * 16
            notes = chord(ch)
            s.note(b, 16, 1, notes[0] + 12, gap=0.2)
            s.note(b, 16, 2, notes[2] + 12, gap=0.2)
            # 뜯는 소리 8분 아르페지오
            arp = [notes[0], notes[1], notes[2], notes[1] + 12 if False else notes[1]]
            for k in range(8):
                s.note(b + k * 2, 2, 3, [notes[0], notes[1], notes[2], notes[1]][k % 4] + 12, gap=0.3)
            s.note(b, 8, 4, midi(root), gap=0.5)
            s.note(b + 8, 8, 4, midi(root) + (7 if bar % 2 else 12), gap=0.5)
            for st in (4, 12):
                s.drum(b + st, HH)
            if bar % 4 == 0:
                s.drum(b, BD)
            s.melody(b, mel[half * 8 + bar], 0 if half == 0 else 5, gap=0.2)
        t += 8 * 16
    s.end_tick = t
    return s


# ---------------------------------------------------------------- 승리 ----
def song_win():
    """원판 스피커 악보 (음 번호 + 12 = MIDI, 48 = 8분음표) 를 금관으로"""
    s = Song(bpm=140, div=4)
    s.patch(0, 0, P_BRASS)
    s.patch(0, 1, P_TROMB)
    s.patch(0, 2, P_TROMB)
    s.patch(0, 3, P_STRINGS)
    s.patch(0, 4, P_BASS)
    s.patch(0, 5, P_BRASS)
    phrases = [
        ([60, 55, 58, 60, 63], 60, ('C4 Eb4 G4', 'C3')),
        ([67, 65, 63, 65, 63, 65], 67, ('Eb4 G4 Bb4', 'Eb3')),
        ([79, 77, 75, 77, 75, 77], 79, ('Bb3 D4 F4', 'Bb2')),
        ([67, 70, 72, 75, 72, 75], 72, ('C4 Eb4 G4', 'C3')),
    ]
    t = 0
    for notes, last, (ch, root) in phrases:
        start = t
        for m in notes:
            s.note(t, 2, 0, m + 12, gap=0.3)
            s.note(t, 2, 5, m, gap=0.3)
            t += 2
        s.note(t, 4, 0, last + 12, gap=0.2)
        s.note(t, 4, 5, last, gap=0.2)
        t += 4
        c = chord(ch)
        s.note(start, t - start, 1, c[0], gap=0.2)
        s.note(start, t - start, 2, c[1], gap=0.2)
        s.note(start, t - start + 2, 3, c[2], gap=0.2)
        s.note(start, t - start, 4, midi(root), gap=0.2)
        s.drum(start, BD | CYM)
        for st in range(start + 2, t, 2):
            s.drum(st, HH)
        t += 2
    s.drum(t - 2, BD | CYM)
    s.end_tick = t + 4
    return s


def main():
    songs = [render(song_title(), 'SKBTITLE'), render(song_play(), 'SKBPLAY'), render(song_win(), 'SKBWIN')]
    if '--vgm' in sys.argv:
        for name, data in songs:
            open(os.path.join(ROOT, name + '.VGM'), 'wb').write(data)
    bundle(os.path.join(ROOT, 'SOUND.DAT'), songs)


if __name__ == '__main__':
    main()
