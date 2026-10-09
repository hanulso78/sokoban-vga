# tools/names_parts/*.txt (구간별 분석) 를 합쳐 tools/names.txt 를 만든다
#   코드 주소는 그 구간을 맡은 파일의 이름을 먼저 쓴다.  DS 변수는 먼저 나온 이름.
#   HOOKS 의 함수에는 개선판 갈고리 표시를 붙인다.
import os, glob, re
HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = {0x0020, 0x4B61, 0x4BA5, 0x5E2B, 0x47D5, 0x4C10}
MANUAL = {0x0020: 'load_pic ; 그림 파일(RLE)을 풀어 ES:DI 에 (이름은 cs:[0] 먼 포인터)',
          0x0A8C: 'skb_main ; 시작: 디스크 찾기, 기록 읽기, 시스템/입력 장치 묻기, 타이틀, 로비로',
          0x103E: 'check_disk ; 디스크가 준비될 때까지 알림',
          0x10AF: 'save_rect ; 뒷화면 사각형을 58CC+3A98 에 (CX=위치 BX=줄 BP=폭 DX=줄 사이)',
          0x10D2: 'restore_rect ; save_rect 의 반대',
          0x1166: 'wait_ticks ; 시계를 0 으로 하고 [0x226] 틱까지 기다리기',
          0x1186: 'joy_axis ; 조이스틱 축 하나의 시간 재기',
          0x1194: 'joy_read ; 조이스틱 -> AH 에 스캔 코드처럼 (단추=1C, 방향=48/50/4B/4D)',
          0x121F: 'speaker_sweep ; SI->{반주기, 횟수, 늘림}: 스피커를 직접 켜고 끄는 효과음',
          0x1243: 'delay ; BX 틱 기다리기 (AT 가 아니면 빈 루프)',
          0x129A: 'lobby ; 로비: 사람이 EXIT/EDIT/PLAY 문 사이를 걷는다',
          0x1C30: 'lobby_walk ; 로비 사람 걷기 애니메이션',
          0x10F3: 'build_tandy_table ; CGA 바이트 -> Tandy 워드 표 만들기',
          0x1108: 'tandy_expand ; AL 의 네 점 -> DX (4비트씩)'}
order = ['37af', '47d5', '5e2b', '7316', '8458', '92a5', '1c30', '0020']
RANGES = {'0020': (0x0020, 0x1C30), '1c30': (0x1C30, 0x37AF), '37af': (0x37AF, 0x47D5), '47d5': (0x47D5, 0x5E2B),
          '5e2b': (0x5E2B, 0x7316), '7316': (0x7316, 0x8458), '8458': (0x8458, 0x92A5), '92a5': (0x92A5, 0xA2C0)}
code = {}; data = {}; own = {}
for part in order + [os.path.basename(f)[:-4] for f in glob.glob(os.path.join(HERE, 'names_parts', '*.txt'))]:
    fn = os.path.join(HERE, 'names_parts', part + '.txt')
    if not os.path.exists(fn):
        continue
    for ln in open(fn, encoding='utf-8'):
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        body, _, note = ln.partition(';')
        p = body.split()
        if len(p) < 2:
            continue
        k = p[0]
        if ':' in k:                                    # 다른 세그먼트의 변수 "2cec:0670", "bios:041a"
            sg, off = k.split(':')
            sg = -1 if sg == 'bios' else int(sg, 16)          # bios = 절대 세그먼트 0 (0000:04xx)
            data.setdefault(('s%04x:' % sg, int(off, 16)), (re.sub(r'\[.*', '', p[1]), note.strip()))
            continue
        if k[0] in 'dc':
            key = (k[0], int(k[1:], 16))
            data.setdefault(key, (p[1], note.strip()))
        else:
            a = int(k, 16)
            inr = part in RANGES and RANGES[part][0] <= a < RANGES[part][1]
            if a not in code or (inr and not own.get(a)):
                code[a] = (p[1], note.strip()); own[a] = inr
for a, t in MANUAL.items():
    nm, _, note = t.partition(';')
    code[a] = (nm.strip(), note.strip())
out = ['# 이름 (tools/mknames.py 가 names_parts 에서 만든다)  -  "주소 이름 [hook] ; 설명"']
for a in sorted(code):
    nm, note = code[a]
    nm = re.sub(r'\W', '_', nm)
    out.append('%04x %s%s ; %s' % (a, nm, ' hook' if a in HOOKS else '', note))
for (t, a) in sorted(data):
    nm, note = data[(t, a)]
    out.append('%s%04x %s ; %s' % (t, a, re.sub(r'\W', '_', re.sub(r'\[.*', '', nm)), note))
open(os.path.join(HERE, 'names.txt'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(code), 'code', len(data), 'data')
