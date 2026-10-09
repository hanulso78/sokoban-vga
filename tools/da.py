# 빠른 역어셈블: python dis.py seg off [count]
import sys, struct
from capstone import *
E = open('SKB.EXE','rb').read()
HDR = struct.unpack('<H', E[8:10])[0]*16
IMG = E[HDR:]
md = Cs(CS_ARCH_X86, CS_MODE_16)
seg = int(sys.argv[1],16); off = int(sys.argv[2],16); n = int(sys.argv[3]) if len(sys.argv)>3 else 60
base = seg*16
for i in md.disasm(IMG[base+off:base+off+n*8], off):
    print('%04x:%04x  %-20s %s %s' % (seg, i.address, i.bytes.hex(), i.mnemonic, i.op_str))
    n -= 1
    if n == 0: break
