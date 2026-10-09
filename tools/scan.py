# 코드 흐름 따라가기: 코드 세그먼트(0) 의 함수 시작점, 코드 바이트, 덮지 못한 구간, 간접 분기
import re, struct, sys
from capstone import *
from capstone.x86 import *

E = open('SKB.EXE', 'rb').read()
HDR = struct.unpack('<H', E[8:10])[0] * 16
IMG = E[HDR:]
CEND = 0xA2C0
md = Cs(CS_ARCH_X86, CS_MODE_16); md.detail = True
code = {}; funcs = set(); labels = set(); indirect = []
EXTRA = []                                   # 손으로 찾은 진입점 (tools/roots.txt)
try:
    for ln in open('tools/roots.txt'):
        ln = ln.split('#')[0].strip()
        if ln:
            EXTRA.append(int(ln.split()[0], 16))
except FileNotFoundError:
    pass


def dis(a):
    return next(md.disasm(IMG[a:a + 16], a), None)


def run(roots):
    work = list(roots)
    while work:
        a = work.pop()
        while 0 <= a < CEND and a not in code:
            ins = dis(a)
            if ins is None:
                print('bad at %04x' % a, file=sys.stderr); break
            code[a] = ins
            g = ins.groups; op = ins.operands
            m = ins.mnemonic
            if m == 'call' and op[0].type == X86_OP_IMM:
                t = op[0].imm & 0xffff; funcs.add(t); work.append(t)
            elif m == 'call':
                indirect.append(a)
            elif (X86_GRP_JUMP in g or m.startswith('loop') or m == 'jcxz') and op[0].type == X86_OP_IMM:
                t = op[0].imm & 0xffff; labels.add(t); work.append(t)
                if m == 'jmp': break
            elif m in ('jmp', 'ljmp'):
                indirect.append(a); break
            elif m in ('ret', 'retf', 'iret'):
                break
            elif m == 'lcall':
                indirect.append(a)
            a += ins.size


roots = [0xA8C] + EXTRA
funcs |= set(roots)
run(roots)

if __name__ == '__main__':
    cov = set()
    for a, i in code.items(): cov.update(range(a, a + i.size))
    gaps = []; a = 0
    while a < CEND:
        if a not in cov:
            s = a
            while a < CEND and a not in cov: a += 1
            gaps.append((s, a))
        else: a += 1
    print('funcs', len(funcs), 'code bytes', len(cov))
    for a in sorted(set(indirect)):
        print('indirect %04x: %s %s' % (a, code[a].mnemonic, code[a].op_str))
    for s, e in gaps:
        print('gap %04x-%04x (%d) %s' % (s, e, e - s, IMG[s:min(e, s + 16)].hex()))
