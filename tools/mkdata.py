# skbdata.c 만들기: SKB.EXE 의 적재 이미지 (머리 뒤 전부).  재배치는 LOADSEG=1000h 로 해 둔다
# (재배치 자리는 모두 코드 안이라 옮긴 C 는 쓰지 않지만, 에뮬레이터와 메모리를 대조하려고)
import struct, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
E = open(os.path.join(ROOT, 'SKB.EXE'), 'rb').read()
h = struct.unpack('<14H', E[:28])
img = bytearray(E[h[4] * 16:])
for i in range(h[3]):
    o, s = struct.unpack('<HH', E[h[12] + 4 * i:h[12] + 4 * i + 4])
    a = s * 16 + o
    v = struct.unpack('<H', img[a:a + 2])[0]
    img[a:a + 2] = struct.pack('<H', (v + 0x1000) & 0xFFFF)
out = ['/* skbdata.c - SKB.EXE 적재 이미지 (tools/mkdata.py 가 만든다) */', '#include "cpu.h"',
       'const unsigned skb_image_size = %d;' % len(img), 'const uint8_t skb_image[%d] = {' % len(img)]
for k in range(0, len(img), 24):
    out.append(','.join('%d' % b for b in img[k:k + 24]) + ',')
out.append('};')
open(os.path.join(ROOT, 'skbdata.c'), 'w').write('\n'.join(out) + '\n')
print(len(img))
