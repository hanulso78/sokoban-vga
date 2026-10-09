# -*- coding: utf-8 -*-
"""SKB.EXE 코드 세그먼트를 C 로 옮긴다 (기계적 변환, 원본과 한 명령씩 같게 동작)

   python tools/asm2c.py            -> skbcode.c, skbcode.h

   - 레지스터는 전역 변수(cpu.h), 메모리는 1MB 평면 배열 M[] (실모드 주소 그대로).
   - 세그먼트 값은 적재 세그먼트 LOADSEG 를 더해 옮긴다 (재배치 표를 따라).
   - call 은 원본처럼 복귀 주소를 스택에 넣고 C 함수를 부른다 -> 스택 메모리까지 원본과 같다.
   - 플래그는 쓰이는 것만 계산한다 (함수 안 흐름 분석 + 함수를 부른 곳에서 쓰는 플래그).
     바로 뒤의 조건 분기 하나만 쓰는 cmp/test 따위는 조건식으로 바로 접는다.
   - int / in / out 은 플랫폼 함수(int10() ...)를 부른다.
   - OVERRIDE 에 적은 함수는 옮기지 않는다 (손으로 쓴 C 가 대신한다: 소리, 조이스틱).
   - tools/names.txt 의 이름을 함수 이름으로 쓴다.
"""
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan
from capstone import *
from capstone.x86 import *

IMG = scan.IMG
E = scan.E
code = scan.code
funcs = sorted(scan.funcs)

# ---- 재배치: 코드 세그먼트 안의 세그먼트 값 위치 --------------------------------------
h = struct.unpack('<14H', E[:28])
RELOC = set()
for i in range(h[3]):
    o, s = struct.unpack('<HH', E[h[12] + 4 * i:h[12] + 4 * i + 4])
    a = s * 16 + o
    if a < scan.CEND:
        RELOC.add(a)

OVERRIDE = set()
DSEGV = 0x0A39              # 자료 세그먼트 (원본 값)
SNAMES = {}                 # 세그먼트 값 -> {오프셋: 변수 이름}.  0A39 = DS, 0 = 코드(CS), -1 = 절대 0 (BIOS)
SNOTES = {}                 # (세그먼트, 오프셋) -> 설명
DNAMES = SNAMES.setdefault(DSEGV, {})
HOOK = set()                # 개선판 갈고리: 들어갈 때 VGA_ENTER, 나갈 때 VGA_LEAVE
names = {}
NOTES = {}                  # 함수 주소 -> 설명
# 세그먼트 이름 (SEG(x) 의 x)
SEGNAMES = {0x0000: 'SEG_CODE', 0x0A39: 'SEG_DATA', 0x180C: 'SEG_ELEV_GFX', 0x2703: 'SEG_LOBBY_GFX',
            0x2CA1: 'SEG_HUD_GFX', 0x2CEC: 'SEG_PLAYERS'}
for ln in open(os.path.join(os.path.dirname(__file__), 'names.txt'), encoding='utf-8') if os.path.exists(
        os.path.join(os.path.dirname(__file__), 'names.txt')) else []:
    ln, _, note = ln.partition(';')
    ln = ln.strip()
    note = note.strip()
    if not ln or ln.startswith('#'):
        continue
    p = ln.split()
    if len(p) >= 2 and p[0][0] not in 'dcs':
        names[int(p[0], 16)] = p[1]
        NOTES[int(p[0], 16)] = note
    if len(p) >= 2 and p[0][0] in 'dcs':
        if p[0][0] == 's':
            sg, off = p[0][1:].split(':')[0], p[0].split(':')[1]
            sg, off = int(sg, 16), int(off, 16)
        else:
            sg, off = (DSEGV if p[0][0] == 'd' else 0), int(p[0][1:], 16)
        SNAMES.setdefault(sg, {})[off] = p[1]
        SNOTES[(sg, off)] = note
    if len(p) >= 3 and p[2] == 'override':
        OVERRIDE.add(int(p[0], 16))
    if len(p) >= 3 and p[2] == 'hook':
        HOOK.add(int(p[0], 16))


def fname(a):
    return names.get(a, 'f_%04x' % a)


# 개선판에서만 (실행 중 vga_fast 가 켜졌을 때) 명령 뒤에 덧붙이는 것: 원판의 긴 기다림 줄이기
#   (PC 대조 시험판은 vga_fast 를 켜지 않으므로 원본과 대조가 그대로 맞는다)
VGA_PATCH = {
    0x14F1: 'BX = 3;',          # 로비 EXIT 로 나가기 전 15 틱
    0x15D1: 'BX = 3;',          # 로비 문으로 들어가기 전 15 틱
}

FLAGS = ('C', 'Z', 'S', 'O')
R16 = {'ax': 'AX', 'bx': 'BX', 'cx': 'CX', 'dx': 'DX', 'si': 'SI', 'di': 'DI', 'bp': 'BP', 'sp': 'SP',
       'cs': 'CS_', 'ds': 'DS_', 'es': 'ES_', 'ss': 'SS_'}
R8 = {'al': 'AL', 'ah': 'AH', 'bl': 'BL', 'bh': 'BH', 'cl': 'CL', 'ch': 'CH', 'dl': 'DL', 'dh': 'DH'}

JCC = {'je', 'jne', 'jl', 'jg', 'jge', 'jle', 'jb', 'jae', 'jns', 'js', 'ja', 'jbe'}
JCC_USES = {'je': 'Z', 'jne': 'Z', 'jl': 'SO', 'jge': 'SO', 'jg': 'ZSO', 'jle': 'ZSO', 'jb': 'C', 'jae': 'C',
            'jns': 'S', 'js': 'S', 'ja': 'CZ', 'jbe': 'CZ'}


def succs(a):
    """함수 안 흐름에서 다음 명령들 (call 은 넘어간다)"""
    i = code[a]
    m = i.mnemonic
    nxt = a + i.size
    if m in ('ret', 'retf', 'iret'):
        return []
    if m == 'jmp':
        if i.operands[0].type == X86_OP_IMM:
            return [i.operands[0].imm & 0xffff]
        return []
    if m in JCC or m.startswith('loop') or m == 'jcxz':
        return [nxt, i.operands[0].imm & 0xffff]
    return [nxt]


def flag_defs_uses(i):
    """(정의하는 플래그, 쓰는 플래그)"""
    m = i.mnemonic
    if m in ('add', 'sub', 'cmp', 'neg', 'adc'):
        return set('CZSO'), (set('C') if m == 'adc' else set())
    if m in ('and', 'or', 'xor', 'test'):
        return set('CZSO'), set()
    if m in ('inc', 'dec'):
        return set('ZSO'), set()
    if m in ('shl', 'shr'):
        return set('CZSO'), set()
    if m in ('mul',):
        return set('CO'), set()
    if m in ('div',):
        return set(), set()
    if m in ('repe scasb', 'repne scasb'):
        return set(), set()          # CX=0 이면 그대로 -> 정의하지 않는다고 본다 (보수적)
    if m in JCC:
        return set(), set(JCC_USES[m])
    return set(), set()


# ---- 함수마다 명령 모으기 -----------------------------------------------------------------
def body(f):
    seen = set()
    work = [f]
    while work:
        a = work.pop()
        if a in seen or a not in code:
            continue
        seen.add(a)
        work.extend(succs(a))
    return sorted(seen)


BODIES = {f: body(f) for f in funcs}

# ---- 플래그 생존 분석 ------------------------------------------------------------------
ret_uses = {f: set() for f in funcs}


def liveness(f):
    ins = BODIES[f]
    live_in = {a: set() for a in ins}
    live_out = {a: set() for a in ins}
    changed = True
    while changed:
        changed = False
        for a in reversed(ins):
            i = code[a]
            if i.mnemonic in ('ret', 'retf'):
                out = set(ret_uses[f])
            else:
                out = set()
                for s in succs(a):
                    if s in live_in:
                        out |= live_in[s]
            d, u = flag_defs_uses(i)
            inn = (out - d) | u
            if i.mnemonic == 'int':
                inn = out - set('CZ')    # 플랫폼이 CF, ZF 를 정한다
            if out != live_out[a] or inn != live_in[a]:
                live_out[a] = out
                live_in[a] = inn
                changed = True
    return live_in, live_out


LIVE = {}
for it in range(10):
    changed = False
    for f in funcs:
        LIVE[f] = liveness(f)
    for f in funcs:
        li, lo = LIVE[f]
        for a in BODIES[f]:
            i = code[a]
            if i.mnemonic == 'call' and i.operands[0].type == X86_OP_IMM:
                t = i.operands[0].imm & 0xffff
                need = lo[a]
                if t in ret_uses and not need <= ret_uses[t]:
                    ret_uses[t] |= need
                    changed = True
    if not changed:
        break


# ---- 피연산자 ----------------------------------------------------------------------
def has_reloc(i, off_in_ins):
    return (i.address + off_in_ins) in RELOC


def imm_text(i, v, size):
    # 재배치된 즉치값이면 세그먼트
    for k in range(i.size - 1):
        if (i.address + k) in RELOC:
            return 'SEG(%s)' % SEGNAMES.get(v & 0xffff, '0x%x' % (v & 0xffff))
    if size == 1:
        return '0x%x' % (v & 0xff)
    return '0x%x' % (v & 0xffff)


# 번역하는 동안의 세그먼트 레지스터 값 추정 (이름 붙이기에만 쓴다: 모르면 None)
SEGV = {}


def var_name(seg, off):
    if seg is None:
        return None
    return SYM.get((seg, off))


def mem_addr(i, op):
    """(세그먼트 식, 오프셋 식)"""
    mm = op.mem
    parts = []
    base = i.reg_name(mm.base) if mm.base else None
    index = i.reg_name(mm.index) if mm.index else None
    if base:
        parts.append(R16[base])
    if index:
        parts.append(R16[index])
    if mm.disp or not parts:
        d = mm.disp & 0xffff
        segname = i.reg_name(mm.segment) if mm.segment else ('ss' if base == 'bp' else 'ds')
        nm = var_name(SEGV.get(segname), d)
        if not nm and parts:                            # 배열 원소: 이름 + 1, + 2
            for k in (1, 2):
                b = var_name(SEGV.get(segname), (d - k) & 0xffff)
                if b:
                    nm = '%s + %d' % (b, k)
                    break
        parts.append(nm or '0x%x' % d)
    off = ' + '.join(parts)
    if len(parts) > 1:
        off = '(uint16_t)(%s)' % off
    if mm.segment:
        seg = R16[i.reg_name(mm.segment)]
    elif base == 'bp':
        seg = 'SS_'
    else:
        seg = 'DS_'
    return seg, off


def rd(i, op):
    if op.type == X86_OP_REG:
        r = i.reg_name(op.reg)
        return R16.get(r) or R8[r]
    if op.type == X86_OP_IMM:
        return imm_text(i, op.imm, op.size)
    seg, off = mem_addr(i, op)
    return '%s(%s, %s)' % ('RB' if op.size == 1 else 'RW', seg, off)


def wr(i, op, val):
    if op.type == X86_OP_REG:
        r = i.reg_name(op.reg)
        return '%s = %s;' % (R16.get(r) or R8[r], val)
    seg, off = mem_addr(i, op)
    return '%s(%s, %s, %s);' % ('WB' if op.size == 1 else 'WW', seg, off, val)


def cast(sz):
    return 'uint8_t' if sz == 1 else 'uint16_t'


def scast(sz):
    return 'int8_t' if sz == 1 else 'int16_t'


def signbit(sz):
    return 7 if sz == 1 else 15


# ---- 명령 하나 옮기기 ------------------------------------------------------------------
class Tr:
    def __init__(self, f):
        self.f = f
        self.li, self.lo = LIVE[f]
        self.out = []
        self.fold = {}           # jcc 주소 -> 조건식 (바로 앞 명령에서 접은 것)
        self.skipflags = set()   # 플래그 계산을 접어서 안 하는 명령

    def emit(self, s):
        self.out.append(s)

    def flags_code(self, a, live, kind, sz, A, B, R):
        """A, B: 원래 값을 담은 C 식 (임시 변수), R: 결과(넓은 int)"""
        sb = signbit(sz)
        mask = '0xff' if sz == 1 else '0xffff'
        c = []
        if 'Z' in live:
            c.append('ZF = ((%s & %s) == 0);' % (R, mask))
        if 'S' in live:
            c.append('SF = ((%s >> %d) & 1);' % (R, sb))
        if 'C' in live:
            if kind in ('add', 'adc'):
                c.append('CF = (%s > %s);' % (R, mask))
            elif kind in ('sub', 'cmp'):
                c.append('CF = (%s < %s);' % (A, B))
            elif kind in ('and', 'or', 'xor', 'test'):
                c.append('CF = 0;')
            elif kind == 'neg':
                c.append('CF = (%s != 0);' % A)
        if 'O' in live:
            if kind in ('add', 'adc', 'inc'):
                c.append('OF = (((%s ^ %s) & (%s ^ %s)) >> %d) & 1;' % (A, R, B, R, sb))
            elif kind in ('sub', 'cmp', 'dec'):
                c.append('OF = (((%s ^ %s) & (%s ^ %s)) >> %d) & 1;' % (A, B, A, R, sb))
            elif kind in ('and', 'or', 'xor', 'test'):
                c.append('OF = 0;')
            elif kind == 'neg':
                c.append('OF = (%s == %s);' % (A, '0x80' if sz == 1 else '0x8000'))
        return c

    def cond_expr(self, jcc, kind, sz, A, B, R):
        """jcc 조건을 한 식으로 (접을 수 있으면), 아니면 None"""
        st = scast(sz)
        ut = cast(sz)
        if kind == 'cmp':
            return {'je': '%s == %s' % (A, B), 'jne': '%s != %s' % (A, B),
                    'jl': '(%s)%s < (%s)%s' % (st, A, st, B), 'jge': '(%s)%s >= (%s)%s' % (st, A, st, B),
                    'jg': '(%s)%s > (%s)%s' % (st, A, st, B), 'jle': '(%s)%s <= (%s)%s' % (st, A, st, B),
                    'jb': '%s < %s' % (A, B), 'jae': '%s >= %s' % (A, B),
                    'ja': '%s > %s' % (A, B), 'jbe': '%s <= %s' % (A, B),
                    'js': '(%s)(%s - %s) < 0' % (st, A, B), 'jns': '(%s)(%s - %s) >= 0' % (st, A, B)}.get(jcc)
        if kind in ('test', 'and', 'or', 'xor'):
            v = R
            return {'je': '(%s)%s == 0' % (ut, v), 'jne': '(%s)%s != 0' % (ut, v),
                    'js': '(%s)%s < 0' % (st, v), 'jns': '(%s)%s >= 0' % (st, v),
                    'jl': '(%s)%s < 0' % (st, v), 'jge': '(%s)%s >= 0' % (st, v),
                    'jg': '(%s)%s > 0' % (st, v), 'jle': '(%s)%s <= 0' % (st, v)}.get(jcc)
        if kind in ('inc', 'dec', 'add', 'sub', 'shl', 'shr', 'neg'):
            if jcc in ('je', 'jne', 'js', 'jns'):
                v = R
                return {'je': '(%s)%s == 0' % (ut, v), 'jne': '(%s)%s != 0' % (ut, v),
                        'js': '(%s)%s < 0' % (st, v), 'jns': '(%s)%s >= 0' % (st, v)}[jcc]
        return None

    def alu(self, a, i):
        m = i.mnemonic
        ops = i.operands
        dst = ops[0]
        sz = dst.size
        ct = cast(sz)
        defs = flag_defs_uses(i)[0]
        live = self.lo[a] & defs
        # 바로 뒤 조건 분기만 이 플래그를 쓰면 조건식으로 접는다
        nxt = a + i.size
        j = code.get(nxt)
        fold = (j is not None and j.mnemonic in JCC and nxt in BODIES_SET[self.f]
                and not (self.lo[nxt] & defs) and nxt not in scan.labels and nxt not in scan.funcs)
        A0 = rd(i, dst)
        if m in ('cmp', 'test'):
            B0 = rd(i, ops[1])
            if fold:
                ce = (self.cond_expr(j.mnemonic, 'cmp', sz, A0, B0, None) if m == 'cmp' else
                      self.cond_expr(j.mnemonic, 'test', sz, None, None, '(%s & %s)' % (A0, B0)))
                if ce:
                    self.fold[nxt] = ce
                    return
            if not live:
                return
            self.emit('{ %s a_ = %s, b_ = %s; unsigned r_ = %s;' % (
                ct, A0, B0, '(unsigned)a_ - b_' if m == 'cmp' else '(unsigned)(a_ & b_)'))
            for c in self.flags_code(a, live, m, sz, 'a_', 'b_', 'r_'):
                self.emit('  ' + c)
            self.emit('}')
            return
        if m in ('inc', 'dec', 'neg'):
            B0 = '1'
            opx = {'inc': '(unsigned)a_ + 1', 'dec': '(unsigned)a_ - 1', 'neg': '0u - a_'}[m]
            if dst.type == X86_OP_REG:
                short = {'inc': '%s++;' % A0, 'dec': '%s--;' % A0, 'neg': '%s = (%s)(0u - %s);' % (A0, ct, A0)}[m]
            else:
                short = wr(i, dst, '(%s)(%s)' % (ct, {'inc': A0 + ' + 1', 'dec': A0 + ' - 1', 'neg': '0u - ' + A0}[m]))
        else:
            B0 = rd(i, ops[1])
            opx = {'add': '(unsigned)a_ + b_', 'sub': '(unsigned)a_ - b_', 'adc': '(unsigned)a_ + b_ + CF',
                   'and': '(unsigned)(a_ & b_)', 'or': '(unsigned)(a_ | b_)', 'xor': '(unsigned)(a_ ^ b_)'}[m]
            same = (dst.type == X86_OP_REG and ops[1].type == X86_OP_REG and ops[0].reg == ops[1].reg)
            if m in ('xor', 'sub') and same:
                self.emit('%s = 0;' % A0)
                if live:
                    self.emit(' '.join(c for c in ['CF = 0;' if 'C' in live else '', 'ZF = 1;' if 'Z' in live else '',
                                                   'SF = 0;' if 'S' in live else '', 'OF = 0;' if 'O' in live else ''] if c))
                return
            sop = {'add': '+', 'sub': '-', 'and': '&', 'or': '|', 'xor': '^'}.get(m)
            if sop is None:
                short = None
            elif dst.type == X86_OP_REG:
                short = '%s %s= %s;' % (A0, sop, B0)
            else:
                short = wr(i, dst, '(%s)(%s %s %s)' % (ct, A0, sop, B0))
        if short and not live:
            self.emit(short)
            return
        if short and fold and dst.type == X86_OP_REG:
            ce = self.cond_expr(j.mnemonic, m, sz, None, None, A0)
            if ce:
                self.emit(short)
                self.fold[nxt] = ce
                return
        self.emit('{ %s a_ = %s, b_ = %s; unsigned r_ = %s;' % (ct, A0, B0, opx))
        self.emit('  ' + wr(i, dst, '(%s)r_' % ct))
        kind = m
        for c in self.flags_code(a, live, kind, sz, 'a_', 'b_', 'r_'):
            self.emit('  ' + c)
        self.emit('}')

    def shift(self, a, i):
        m = i.mnemonic
        dst, cnt = i.operands
        sz = dst.size
        ct = cast(sz)
        A0 = rd(i, dst)
        live = self.lo[a]
        if cnt.type == X86_OP_IMM and cnt.imm == 1:
            n = '1'
        else:
            n = rd(i, cnt)
        op = '<<' if m == 'shl' else '>>'
        if not live:
            if dst.type == X86_OP_REG:
                self.emit('%s %s= %s;' % (A0, op, n))
            else:
                self.emit(wr(i, dst, '(%s)(%s %s %s)' % (ct, A0, op, n)))
            return
        self.emit('{ %s a_ = %s; unsigned n_ = %s;' % (ct, A0, n))
        self.emit('  if (n_) { unsigned r_ = (unsigned)a_ %s n_;' % op)
        self.emit('    ' + wr(i, dst, '(%s)r_' % ct))
        sb = signbit(sz)
        if 'C' in live:
            if m == 'shl':
                self.emit('    CF = n_ <= %d ? (a_ >> (%d - n_)) & 1 : 0;' % (sb + 1, sb + 1))
            else:
                self.emit('    CF = (a_ >> (n_ - 1)) & 1;')
        if 'Z' in live:
            self.emit('    ZF = ((%s)r_ == 0);' % ct)
        if 'S' in live:
            self.emit('    SF = (r_ >> %d) & 1;' % sb)
        if 'O' in live:
            if m == 'shl':
                self.emit('    OF = ((r_ >> %d) & 1) ^ CF;' % sb)
            else:
                self.emit('    OF = (a_ >> %d) & 1;' % sb)
        self.emit('  }')
        self.emit('}')

    def jcc_cond(self, a, m):
        if a in self.fold:
            return self.fold[a]
        return {'je': 'ZF', 'jne': '!ZF', 'jl': 'SF != OF', 'jge': 'SF == OF', 'jg': '!ZF && SF == OF',
                'jle': 'ZF || SF != OF', 'jb': 'CF', 'jae': '!CF', 'jns': '!SF', 'js': 'SF',
                'ja': '!CF && !ZF', 'jbe': 'CF || ZF'}[m]

    def strop(self, a, i):
        m = i.mnemonic
        rep = m.startswith('rep')
        base = m.split()[-1]
        seg_src = 'DS_'
        # 세그먼트 덮어쓰기 (movs/lods 의 원본 쪽)
        for op in i.operands:
            if op.type == X86_OP_MEM and op.mem.segment and i.reg_name(op.mem.segment) != 'es':
                seg_src = R16[i.reg_name(op.mem.segment)]
        w = 2 if base.endswith('w') else 1
        one = {
            'movsb': 'MOVSB(%s);' % seg_src,
            'movsw': 'MOVSW(%s);' % seg_src,
            'stosb': 'WB(ES_, DI, AL); DI++;',
            'stosw': 'WW(ES_, DI, AX); DI += 2;',
            'lodsb': 'AL = RB(%s, SI); SI++;' % seg_src,
            'lodsw': 'AX = RW(%s, SI); SI += 2;' % seg_src,
        }
        if base in one:
            if rep:
                if base == 'movsb' and True:
                    self.emit('rep_movsb(%s);' % seg_src)
                elif base == 'movsw':
                    self.emit('rep_movsw(%s);' % seg_src)
                elif base == 'stosb':
                    self.emit('rep_stosb();')
                elif base == 'stosw':
                    self.emit('rep_stosw();')
                else:
                    self.emit('while (CX) { %s CX--; }' % one[base])
            else:
                self.emit(one[base])
            return
        if base == 'scasb':
            cond = 'ZF' if m.startswith('repe') else '!ZF'
            live = self.lo[a]
            self.emit('while (CX) { uint8_t b_ = RB(ES_, DI); unsigned r_ = (unsigned)AL - b_; DI++; CX--;')
            self.emit('  ZF = ((uint8_t)r_ == 0); CF = (AL < b_); SF = (r_ >> 7) & 1;'
                      ' OF = (((AL ^ b_) & (AL ^ r_)) >> 7) & 1;')
            self.emit('  if (!(%s)) break; }' % cond)
            return
        raise Exception('strop %s' % m)

    def ins(self, a, i):
        m = i.mnemonic
        ops = i.operands
        if m == 'mov':
            src = rd(i, ops[1])
            if (ops[0].type == X86_OP_REG and i.reg_name(ops[0].reg) in ('si', 'di', 'dx') and
                    ops[1].type == X86_OP_IMM and not src.startswith('SEG(')):
                src = var_name(SEGV.get('es' if i.reg_name(ops[0].reg) == 'di' else 'ds'), ops[1].imm & 0xffff) or src
            self.emit(wr(i, ops[0], src))
            if ops[0].type == X86_OP_MEM and ops[0].mem.disp == 0x41c and not ops[0].mem.base:
                self.emit('kbd_flush_hook();')
        elif m == 'lea':
            seg, off = mem_addr(i, ops[1])
            self.emit('%s = %s;' % (R16[i.reg_name(ops[0].reg)], off))
        elif m == 'lds':
            seg, off = mem_addr(i, ops[1])
            self.emit('{ uint16_t o_ = RW(%s, %s), s_ = RW(%s, (uint16_t)(%s + 2)); %s = o_; DS_ = s_; }' % (
                seg, off, seg, off, R16[i.reg_name(ops[0].reg)]))
        elif m == 'xchg':
            A0, B0 = rd(i, ops[0]), rd(i, ops[1])
            self.emit('{ uint16_t t_ = %s; %s %s }' % (A0, wr(i, ops[0], B0), wr(i, ops[1], 't_')))
        elif m == 'push':
            self.emit('PUSH(%s);' % rd(i, ops[0]))
        elif m == 'pop':
            if ops[0].type == X86_OP_REG:
                self.emit('%s = POP();' % R16[i.reg_name(ops[0].reg)])
            else:
                self.emit('{ uint16_t t_ = POP(); %s }' % wr(i, ops[0], 't_'))
        elif m in ('add', 'sub', 'adc', 'and', 'or', 'xor', 'cmp', 'test', 'inc', 'dec', 'neg'):
            self.alu(a, i)
        elif m in ('shl', 'shr'):
            self.shift(a, i)
        elif m == 'mul':
            s = rd(i, ops[0])
            if ops[0].size == 1:
                self.emit('AX = (uint16_t)(AL * %s);' % s)
                if self.lo[a] & set('CO'):
                    self.emit('CF = OF = (AH != 0);')
            else:
                self.emit('{ uint32_t p_ = (uint32_t)AX * %s; AX = (uint16_t)p_; DX = (uint16_t)(p_ >> 16); }' % s)
                if self.lo[a] & set('CO'):
                    self.emit('CF = OF = (DX != 0);')
        elif m == 'div':
            s = rd(i, ops[0])
            if ops[0].size == 1:
                self.emit('{ uint8_t d_ = %s; uint16_t n_ = AX; if (!d_ || n_ / d_ > 0xff) div_error(0x%04x);'
                          ' AL = (uint8_t)(n_ / d_); AH = (uint8_t)(n_ %% d_); }' % (s, a))
            else:
                self.emit('{ uint16_t d_ = %s; uint32_t n_ = ((uint32_t)DX << 16) | AX;'
                          ' if (!d_ || n_ / d_ > 0xffff) div_error(0x%04x);'
                          ' AX = (uint16_t)(n_ / d_); DX = (uint16_t)(n_ %% d_); }' % (s, a))
        elif m == 'cwde':   # 16비트에서는 cbw
            self.emit('AX = (uint16_t)(int16_t)(int8_t)AL;')
        elif m in ('cld', 'cli', 'sti'):
            self.emit('/* %s */' % m)
        elif m.startswith('rep') or m in ('lodsb', 'lodsw', 'stosb', 'stosw', 'movsb', 'movsw'):
            self.strop(a, i)
        elif m == 'int':
            self.emit('int%02x();' % ops[0].imm)
        elif m == 'in':
            port = rd(i, ops[1])
            self.emit('%s = port_in(%s);' % (rd(i, ops[0]), port))
        elif m == 'out':
            port = rd(i, ops[0])
            self.emit('port_out(%s, %s);' % (port, rd(i, ops[1])))
        elif m == 'call':
            t = ops[0].imm & 0xffff
            self.emit('PUSH(0x%04x); %s();' % (a + i.size, fname(t)))
        elif m == 'ret':
            n = ops[0].imm if ops else 0
            if self.f in HOOK:
                self.emit('VGA_LEAVE(0x%04x); SP += %d; return;' % (self.f, 2 + n))
            else:
                self.emit('SP += %d; return;' % (2 + n))
        elif m == 'retf':
            self.emit('far_return(); return;')
        elif m == 'jmp':
            t = ops[0].imm & 0xffff
            self.emit('goto L%04x;' % t)
        elif m in JCC:
            t = ops[0].imm & 0xffff
            self.emit('if (%s) goto L%04x;' % (self.jcc_cond(a, m), t))
        elif m == 'loop' and (ops[0].imm & 0xffff) == a:
            self.emit('delay_loop(CX); CX = 0;')
        elif m == 'loop':
            self.emit('if (--CX) goto L%04x;' % (ops[0].imm & 0xffff))
        elif m == 'loopne':
            self.emit('if (--CX && !ZF) goto L%04x;' % (ops[0].imm & 0xffff))
        elif m == 'jcxz':
            self.emit('if (CX == 0) goto L%04x;' % (ops[0].imm & 0xffff))
        else:
            raise Exception('%04x %s %s' % (a, m, i.op_str))

    @staticmethod
    def track(i, st):
        """세그먼트 레지스터 값 어림 (이름 붙이기에만): st = {'seg': {ds, es, cs, ss}, 'rc': {레지스터: 상수}, 'stk': [...]}"""
        m = i.mnemonic
        ops = i.operands
        seg, rc, stk = st['seg'], st['rc'], st['stk']
        reg = lambda o: i.reg_name(o.reg) if o.type == X86_OP_REG else None
        SR = ('ds', 'es', 'cs', 'ss')
        if m == 'mov' and ops[0].type == X86_OP_REG:
            d, sr = reg(ops[0]), ops[1]
            if sr.type == X86_OP_IMM and any((i.address + k) in RELOC for k in range(i.size)):
                val = sr.imm & 0xffff
            elif sr.type == X86_OP_IMM and sr.imm == 0:
                val = -1
            elif sr.type == X86_OP_REG:
                val = seg.get(reg(sr)) if reg(sr) in SR else rc.get(reg(sr))
            else:
                val = None
            if d in SR:
                seg[d] = val
            else:
                rc[d] = val
                for big, lo, hi in (('ax', 'al', 'ah'), ('bx', 'bl', 'bh'), ('cx', 'cl', 'ch'), ('dx', 'dl', 'dh')):
                    if d in (lo, hi):
                        rc.pop(big, None)
            return
        if m == 'push':
            r = reg(ops[0])
            stk.append((seg.get(r) if r in SR else rc.get(r)) if r else None)
            return
        if m == 'pop' and ops[0].type == X86_OP_REG:
            r = reg(ops[0])
            v = stk.pop() if stk else None
            if r in SR:
                seg[r] = v
            else:
                rc[r] = v
            return
        if m in ('xor', 'sub') and len(ops) == 2 and reg(ops[0]) and reg(ops[0]) == reg(ops[1]):
            rc[reg(ops[0])] = -1                        # 0 (절대 세그먼트 0 으로 쓰일 때)
            return
        if m in ('lds', 'les'):
            seg['ds' if m == 'lds' else 'es'] = None
        if m in ('pushf', 'pusha'):
            stk.append(None)
            return
        if m == 'popf':
            if stk:
                stk.pop()
            return
        try:
            _, w = i.regs_access()
            for r in w:
                n = i.reg_name(r)
                if n in ('ds', 'es'):
                    seg[n] = None
                rc.pop(n, None)
                for big, lo, hi in (('ax', 'al', 'ah'), ('bx', 'bl', 'bh'), ('cx', 'cl', 'ch'), ('dx', 'dl', 'dh')):
                    if n in (lo, hi):
                        rc.pop(big, None)
        except Exception:
            pass

    def seg_flow(self):
        """함수 안 제어 흐름을 따라 명령마다 들어갈 때의 세그먼트 상태 (다르게 만나면 모름)"""
        f = self.f
        body = BODIES_SET[f]

        def merge(x, y):
            if x is None:
                return y
            z = {'seg': {k: (x['seg'].get(k) if x['seg'].get(k) == y['seg'].get(k) else None)
                         for k in set(x['seg']) | set(y['seg'])},
                 'rc': {k: x['rc'][k] for k in x['rc'] if k in y['rc'] and x['rc'][k] == y['rc'][k]},
                 'stk': ([u if u == v else None for u, v in zip(x['stk'], y['stk'])]
                         if len(x['stk']) == len(y['stk']) else [None] * min(len(x['stk']), len(y['stk'])))}
            return z

        def copy(x):
            return {'seg': dict(x['seg']), 'rc': dict(x['rc']), 'stk': list(x['stk'])}
        st_in = {f: {'seg': dict(ENTRY.get(f) or {'ds': DSEGV, 'es': DSEGV, 'cs': 0, 'ss': None}),
                     'rc': {}, 'stk': []}}
        work = [f]
        n = 0
        while work and n < 200000:
            n += 1
            a = work.pop()
            i = code[a]
            st = copy(st_in[a])
            self.track(i, st)
            m = i.mnemonic
            succ = []
            if m in ('ret', 'retf', 'iret'):
                pass
            elif m == 'jmp':
                succ.append(i.operands[0].imm & 0xffff)
            else:
                if m in JCC or m.startswith('loop') or m == 'jcxz':
                    succ.append(i.operands[0].imm & 0xffff)
                succ.append(a + i.size)
            for t in succ:
                if t not in body:
                    continue
                new = merge(st_in.get(t), st) if t in st_in else copy(st)
                if new != st_in.get(t):
                    st_in[t] = new
                    work.append(t)
        return st_in

    def run(self):
        f = self.f
        flow = self.seg_flow()
        ins = BODIES[f]
        targets = set()
        for a in ins:
            i = code[a]
            if i.mnemonic == 'jmp' or i.mnemonic in JCC or i.mnemonic.startswith('loop') or i.mnemonic == 'jcxz':
                targets.add(i.operands[0].imm & 0xffff)
        lines = []
        prev = None
        for a in ins:
            i = code[a]
            # 흐름이 끊어진 뒤 다음 명령이 이어지지 않으면(떨어진 조각) 앞에서 goto
            if prev is not None and prev != a and code[prev_a].mnemonic not in ('jmp', 'ret', 'retf'):
                lines.append('    goto L%04x;' % a)
                targets.add(a)
            self.out = []
            SEGV.clear()
            SEGV.update((flow.get(a) or {'seg': {}})['seg'])
            self.ins(a, i)
            if a in VGA_PATCH:
                self.out.append('VGA_FAST(%s)' % VGA_PATCH[a])
            txt = '%s %s' % (i.mnemonic, i.op_str)
            lab = 'L%04x:' % a if a in targets or a == f else None
            if lab:
                lines.append((a, lab))
            for k, s in enumerate(self.out):
                if k == len(self.out) - 1:
                    lines.append('    %-60s /* %04x %s */' % (s, a, txt) if len(s) < 60 else '    %s  /* %04x %s */' % (s, a, txt))
                else:
                    lines.append('    ' + s)
            if not self.out:
                lines.append('    %-60s /* %04x %s */' % ('', a, txt))
            prev = a + i.size
            prev_a = a
        # 레이블을 쓰는 곳만 남긴다
        used = set()
        for ln in lines:
            if isinstance(ln, str):
                for mm in re.finditer(r'goto (L[0-9a-f]{4})', ln):
                    used.add(mm.group(1))
        res = []
        for ln in lines:
            if isinstance(ln, tuple):
                if ln[1][:-1] in used:
                    res.append(ln[1])
            else:
                res.append(ln)
        return res


BODIES_SET = {f: set(b) for f, b in BODIES.items()}
ENTRY = {}                  # 함수 -> 들어올 때의 세그먼트 상태 (부르는 곳들의 상태를 합친 것)


def compute_entry():
    """부르는 곳의 DS/ES 를 불리는 함수의 시작 상태로 (바뀌지 않을 때까지)"""
    for _ in range(10):
        calls = {}
        for f in funcs:
            if f in OVERRIDE:
                continue
            flow = Tr(f).seg_flow()
            for a, st in flow.items():
                i = code[a]
                if i.mnemonic == 'call' and i.operands[0].type == X86_OP_IMM:
                    t = i.operands[0].imm & 0xffff
                    cur = {k: st['seg'].get(k) for k in ('ds', 'es', 'cs', 'ss')}
                    # 모르는 곳(None)은 빼고 아는 곳들이 같으면 그 값, 서로 다르면 'X' (모름)
                    if t in calls:
                        calls[t] = {k: (cur[k] if calls[t][k] is None else calls[t][k] if cur[k] is None or
                                        cur[k] == calls[t][k] else 'X') for k in cur}
                    else:
                        calls[t] = cur
        new = {t: {k: (None if x == 'X' else x) for k, x in v.items()} for t, v in calls.items() if t != 0x0A8C}
        if new == ENTRY:
            break
        ENTRY.clear()
        ENTRY.update(new)

# ---- 변수 이름표 (skbvars.h) ------------------------------------------------------------
#  같은 이름이 여러 세그먼트에 있거나 C 이름과 겹치면 세그먼트 접두어를 붙인다
SEGTAG = {DSEGV: '', 0: 'cs_', -1: 'bios_', 0x2CEC: 'pl_', 0x2CA1: 'hud_', 0x180C: 'elev_', 0x2703: 'lobby_'}
SYM = {}


def build_syms():
    reserved = set(names.values()) | set(SEGNAMES.values()) | {
        'M', 'COL', 'LIN', 'SEG', 'RB', 'RW', 'WB', 'WW', 'PUSH', 'POP', 'AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'BP',
        'SP', 'CS_', 'DS_', 'ES_', 'SS_', 'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH', 'CF', 'ZF', 'SF', 'OF',
        'DF', 'DSEG', 'CSEG', 'int', 'char', 'short', 'long', 'unsigned', 'signed', 'void', 'if', 'else', 'goto',
        'while', 'for', 'do', 'return', 'break', 'continue', 'switch', 'case', 'default', 'time', 'delay'}
    count = {}
    for sg, tbl in SNAMES.items():
        for off, nm in tbl.items():
            count[nm] = count.get(nm, 0) + 1
    used = set()
    for sg in sorted(SNAMES):
        for off, nm in sorted(SNAMES[sg].items()):
            sym = nm
            if count[nm] > 1 or nm in reserved or sym in used:
                sym = SEGTAG.get(sg, 's%04x_' % sg) + nm
            while sym in used or sym in reserved:
                sym += '_'
            used.add(sym)
            SYM[(sg, off)] = sym


build_syms()


def write_vars():
    o = ['/* skbvars.h - tools/asm2c.py 가 names.txt 에서 만든다 (손대지 말 것)',
         ' *  원본 변수와 표의 이름 = 그 세그먼트 안의 오프셋.  RB(DS_, player_pos) 처럼 쓴다. */',
         '#ifndef SKBVARS_H', '#define SKBVARS_H', '', '/* 세그먼트 (SEG(x) 의 x) */']
    for v, nm in sorted(SEGNAMES.items()):
        o.append('#define %-28s 0x%04x' % (nm, v))
    title = {DSEGV: '자료 세그먼트 0A39 (DS)', 0: '코드 세그먼트 (CS)', -1: 'BIOS 자료 영역 (절대 세그먼트 0, 0000:04xx)'}
    for sg in sorted(SNAMES, key=lambda g: (g != DSEGV, g)):
        o.append('')
        o.append('/* %s */' % title.get(sg, '세그먼트 %04X (%s)' % (sg, SEGNAMES.get(sg, '?'))))
        for off in sorted(SNAMES[sg]):
            note = SNOTES.get((sg, off), '')
            o.append('#define %-28s 0x%04x%s' % (SYM[(sg, off)], off, ('   /* %s */' % note.replace('*/', '* /'))
                                                     if note else ''))
    o.append('')
    o.append('#endif')
    open('skbvars.h', 'w', encoding='utf-8').write('\n'.join(o) + '\n')


def main():
    out = ['/* skbcode.c - SKB.EXE 코드 세그먼트를 tools/asm2c.py 로 옮긴 것 (손대지 말 것) */',
           '#include "cpu.h"', '#include "skbcode.h"', '#include "skbvars.h"', '']
    write_vars()
    compute_entry()
    hdr = ['/* skbcode.h - tools/asm2c.py 가 만든다 */', '#ifndef SKBCODE_H', '#define SKBCODE_H']
    for f in funcs:
        hdr.append('void %s(void);%s' % (fname(f), '   /* 손으로 쓴 C */' if f in OVERRIDE else ''))
    hdr.append('#endif')
    for f in funcs:
        if f in OVERRIDE:
            continue
        tr = Tr(f)
        # 먼저 한 번 돌려 접기 정보를 모은다 (jcc 는 뒤에 오므로 한 번에 된다)
        lines = tr.run()
        uses = ''.join(sorted(ret_uses[f]))
        out.append('/* %04x %s%s%s */' % (f, fname(f), (': ' + NOTES[f]) if NOTES.get(f) else '',
                                          ('  (돌려주는 플래그: ' + uses + ')') if uses else ''))
        out.append('void %s(void)' % fname(f))
        out.append('{')
        if f in HOOK:
            out.append('    VGA_ENTER(0x%04x);' % f)
        out.extend(lines)
        out.append('}')
        out.append('')
    open('skbcode.c', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    open('skbcode.h', 'w', encoding='utf-8').write('\n'.join(hdr) + '\n')
    print('functions', len(funcs), 'lines', len(out))


if __name__ == '__main__':
    main()
