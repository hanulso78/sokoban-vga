# listing.asm 만들기: 코드 세그먼트 전체를 흐름 분석 결과로 풀고 이름/주석을 단다
#   이름: tools/names.txt  ("XXXX 이름 [; 설명]"  - 코드 주소,  "dXXXX 이름" - DS 변수,
#                          "cXXXX 이름" - CS 변수)
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan
from capstone.x86 import *

IMG = scan.IMG
DS = 0xA39 * 16
names = {}; dnames = {}; cnames = {}; notes = {}
try:
    for ln in open('tools/names.txt', encoding='utf-8'):
        ln = ln.rstrip('\n')
        if not ln.strip() or ln.startswith('#'):
            continue
        body, _, note = ln.partition(';')
        p = body.split()
        if len(p) < 2:
            continue
        k, nm = p[0], p[1]
        if k[0] == 'd':
            dnames[int(k[1:], 16)] = nm
        elif k[0] == 'c':
            cnames[int(k[1:], 16)] = nm
        else:
            names[int(k, 16)] = nm
            if note.strip():
                notes[int(k, 16)] = note.strip()
except FileNotFoundError:
    pass


def lab(a):
    if a in names:
        return names[a]
    if a in scan.funcs:
        return 'f_%04x' % a
    return 'L%04x' % a


def dstr(off, term=b'$'):
    s = IMG[DS + off:DS + off + 200]
    e = s.find(term)
    if e < 0:
        return None
    s = s[:e]
    if all(32 <= c < 127 or c in (10, 13, 9) for c in s) and len(s) >= 2:
        return s.decode().replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
    return None


def fix_ops(ins):
    t = ins.op_str
    for op in ins.operands:
        if op.type == X86_OP_IMM and (ins.mnemonic in ('call', 'jmp') or ins.mnemonic.startswith('j')
                                      or ins.mnemonic.startswith('loop')):
            t = lab(op.imm & 0xffff)
    # 메모리 피연산자에 이름
    def rep(m):
        v = int(m.group(1), 16)
        pre = t[:m.start()]
        seg_cs = pre.endswith('cs:[')
        tbl = cnames if seg_cs else dnames
        if v in tbl:
            return '[' + tbl[v] + ']'
        return m.group(0)
    t = re.sub(r'\[0x([0-9a-f]+)\]', lambda m: ('[' + (cnames if t[:m.start()].endswith('cs:') else dnames)[int(m.group(1), 16)] + ']')
               if int(m.group(1), 16) in (cnames if t[:m.start()].endswith('cs:') else dnames) else m.group(0), t)
    return t


out = []
addrs = sorted(scan.code)
prev_end = None
for a in addrs:
    ins = scan.code[a]
    if prev_end is not None and a != prev_end:
        gap = IMG[prev_end:a]
        if not all(b == 0x90 for b in gap):
            out.append('        ; ---- 데이터 %04x..%04x (%d 바이트)' % (prev_end, a, a - prev_end))
            k = 0
            while k < len(gap):
                z = k
                while z < len(gap) and gap[z] == 0: z += 1
                if z - k >= 16:
                    out.append('        db %d dup(0)            ; %04x' % (z - k, prev_end + k)); k = z; continue
                out.append('        db %s   ; %04x' % (', '.join('%02xh' % b for b in gap[k:k + 16]), prev_end + k))
                k += 16
    if a in scan.funcs:
        out.append('')
        out.append(';' + '=' * 70)
        out.append('%s:%s' % (lab(a), ('   ; ' + notes[a]) if a in notes else ''))
    elif a in scan.labels:
        out.append('%s:%s' % (lab(a), ('   ; ' + notes[a]) if a in notes else ''))
    txt = fix_ops(ins)
    cmt = ''
    if ins.mnemonic == 'mov' and ins.operands[0].type == X86_OP_REG and ins.operands[1].type == X86_OP_IMM:
        v = ins.operands[1].imm & 0xffff
        if ins.reg_name(ins.operands[0].reg) in ('dx', 'si', 'bx', 'di'):
            s = dstr(v) or dstr(v, b'\0')
            if s and v > 0x40:
                cmt = '  ; "%s"' % s[:60]
    out.append('%04x  %-8s %-6s %s%s' % (a, ins.bytes.hex()[:8], ins.mnemonic, txt, cmt))
    prev_end = a + ins.size
open('listing.asm', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(out), 'lines')
