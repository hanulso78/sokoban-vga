# 키를 기다릴 때마다 화면을 찍는다:  python tools/walk2.py 모드 "키 키 ..." 출력.png
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from keys import key
from PIL import Image
mode = sys.argv[1]
from difftest import parse
keys = parse(sys.argv[2])
m = emu.Machine(keys=keys, mode=mode)
shots = []
def blk(mm):
    mm.screen_png('tools/_t.png'); shots.append(Image.open('tools/_t.png').resize((320, 200)))
    cs = mm.mu.reg_read(emu.UC_X86_REG_CS) - emu.LOADSEG; ip = mm.mu.reg_read(emu.UC_X86_REG_IP)
    print(len(shots), '%04X:%04X' % (cs, ip), 'next', hex(mm.keys[0][1]) if mm.keys else None, mm.log[-1:])
m.on_block = blk
print(m.run(int(sys.argv[4]) if len(sys.argv) > 4 else 200000000))
blk(m)
cols = 4
W = Image.new('RGB', (cols * 322, ((len(shots) + cols - 1) // cols) * 202), (60, 60, 60))
for i, im in enumerate(shots):
    W.paste(im, ((i % cols) * 322, (i // cols) * 202))
W.save(sys.argv[3])
