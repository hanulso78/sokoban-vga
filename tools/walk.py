# 키를 넣어 가며 화면을 여러 장 찍는다:  python tools/walk.py 모드 "폴수:키 ..." 명령어수 간격
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from PIL import Image
from keys import key
mode = sys.argv[1]
keys = []
for t in sys.argv[2].split():
    n, k = t.split(':')
    keys.append((int(n), key(k)))
total = int(sys.argv[3]); step = int(sys.argv[4])
m = emu.Machine(keys=keys, mode=mode)
shots = []
done = 0
while done < total:
    r = m.run(step); done += step
    m.screen_png('tools/_t.png'); shots.append(Image.open('tools/_t.png').resize((320, 200)))
    cs = m.mu.reg_read(emu.UC_X86_REG_CS) - emu.LOADSEG; ip = m.mu.reg_read(emu.UC_X86_REG_IP)
    print(len(shots), r, '%04X:%04X' % (cs, ip), 'keys left', len(m.keys), 'ticks', m.ticks, m.log[-2:])
    if r != 'count': break
cols = 4
W = Image.new('RGB', (cols * 322, ((len(shots) + cols - 1) // cols) * 202), (60, 60, 60))
for i, im in enumerate(shots):
    W.paste(im, ((i % cols) * 322, (i // cols) * 202))
W.save(sys.argv[5] if len(sys.argv) > 5 else 'tools/walk.png')
