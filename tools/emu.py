# SKB.EXE (소코반) 를 unicorn(8086 실모드)으로 돌리는 기준 에뮬레이터
#   - BIOS/DOS 는 필요한 만큼만 흉내 낸다.
#   - 시계(int 1Ah)는 읽을 때마다 한 틱씩 간다 -> 결정적이다.
#   - 자판(int 16h)은 미리 준 키 목록을 차례로 낸다.  키가 없으면 "없음"을 N 번 돌려준 뒤
#     다음 키를 낸다 (keys 의 원소: (기다릴 폴 수, 스캔<<8|아스키)).
import struct, sys, os
from unicorn import *
from unicorn.x86_const import *

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
EXE = os.path.join(ROOT, 'SKB.EXE')

LOADSEG = 0x1000                # 적재 세그먼트 (PSP = LOADSEG - 0x10)
PSP = LOADSEG - 0x10
BIOSSEG = 0xF000
DSEG = LOADSEG + 0xA39


class Exit(Exception):
    pass


class Machine:
    def __init__(self, keys=None, mode='c', files_dir=ROOT, trace=False):
        mu = self.mu = Uc(UC_ARCH_X86, UC_MODE_16)
        mu.mem_map(0, 0x110000)
        E = open(EXE, 'rb').read()
        h = struct.unpack('<14H', E[:28])
        hdr = h[4] * 16
        img = bytearray(E[hdr:])
        for i in range(h[3]):
            o, s = struct.unpack('<HH', E[h[12] + 4 * i:h[12] + 4 * i + 4])
            a = s * 16 + o
            v = struct.unpack('<H', img[a:a + 2])[0]
            img[a:a + 2] = struct.pack('<H', (v + LOADSEG) & 0xFFFF)
        mu.mem_write(LOADSEG * 16, bytes(img))
        mu.mem_write(PSP * 16, b'\xcd\x20')
        mu.mem_write(PSP * 16 + 2, struct.pack('<H', 0xA000))
        mu.mem_write(PSP * 16 + 0x80, b'\x00\r')
        for n in range(256):
            mu.mem_write(n * 4, struct.pack('<HH', n * 4, BIOSSEG))
            mu.mem_write(BIOSSEG * 16 + n * 4, bytes([0xCD, n, 0xCF, 0x90]))
        # BIOS 자료: 자판 버퍼 머리/꼬리 (게임이 직접 비운다)
        mu.mem_write(0x41A, struct.pack('<HH', 0x1E, 0x1E))
        mu.mem_write(0x413, struct.pack('<H', 640))
        mu.mem_write(0xFFFFE, bytes([0xFC]))          # 기계 종류: AT (시간 끌기를 BIOS 시계로 한다)
        mu.hook_add(UC_HOOK_MEM_WRITE, self.on_flush, None, 0x41C, 0x41D)
        mu.reg_write(UC_X86_REG_CS, LOADSEG + h[11])
        mu.reg_write(UC_X86_REG_IP, h[10])
        mu.reg_write(UC_X86_REG_SS, LOADSEG + h[7])
        mu.reg_write(UC_X86_REG_SP, h[8])
        mu.reg_write(UC_X86_REG_DS, PSP)
        mu.reg_write(UC_X86_REG_ES, PSP)
        mu.hook_add(UC_HOOK_INTR, self.on_int)
        mu.hook_add(UC_HOOK_INSN, self.on_in, None, 1, 0, UC_X86_INS_IN)
        mu.hook_add(UC_HOOK_INSN, self.on_out, None, 1, 0, UC_X86_INS_OUT)
        self.keys = list(keys or [])
        self.wait = 0               # 현재 키 앞에서 "없음"을 돌려준 횟수
        self.answers = [mode, 'k']  # 시스템 선택(c/t), 입력 장치(k/j)
        self.files_dir = files_dir
        self.handles = {}
        self.ticks = 0
        self.vmode = 3
        self.text = []
        self.row = self.col = 0
        self.log = []
        self.hooks = {}             # 코드 주소(선형) -> 함수
        self.polls = 0
        self.port61 = 0
        self.tone = 0
        self.pit_lo = True
        self.nint16 = 0
        self.on_block = None        # 키를 기다리며 막힐 때 부르는 함수
        self.peeked = False
        self.trace = None           # 대조용 기록 파일
        self.nint = 0
        self.dumpat = int(os.environ.get('SKBDUMPAT', '0'))
        self.dumpfile = os.environ.get('SKBDUMP', '')
        self.ext = None             # int 21h 07: 확장 키의 두 번째 바이트

    def lin(self, seg, off):
        return seg * 16 + off

    def rb(self, a, n):
        return bytes(self.mu.mem_read(a, n))

    def dsb(self, off, n):
        return self.rb(DSEG * 16 + off, n)

    def w(self, off):
        return struct.unpack('<H', self.dsb(off, 2))[0]

    def add_hook(self, seg, off, fn):
        a = (LOADSEG + seg) * 16 + off
        self.mu.hook_add(UC_HOOK_CODE, lambda mu, addr, size, ud: fn(self), None, a, a)

    def cstr(self, seg, off, term=0):
        s = b''
        while True:
            c = self.mu.mem_read(seg * 16 + off, 1)[0]
            if c == term:
                return s.decode('latin1')
            s += bytes([c])
            off += 1

    def setcf(self, on):
        f = self.mu.reg_read(UC_X86_REG_EFLAGS)
        self.mu.reg_write(UC_X86_REG_EFLAGS, (f | 1) if on else (f & ~1))

    def setzf(self, on):
        f = self.mu.reg_read(UC_X86_REG_EFLAGS)
        self.mu.reg_write(UC_X86_REG_EFLAGS, (f | 0x40) if on else (f & ~0x40))

    # ---- 자판 ----
    def peek_key(self, blocking=False):
        if not self.keys:
            return None
        n, k = self.keys[0]
        if n < 0:                           # 막고 읽을 때만 내는 키
            return k if blocking else None
        if self.wait < n:
            self.wait += 1
            return None
        return k

    def pop_key(self):
        n, k = self.keys.pop(0)
        self.wait = 0
        self.peeked = False
        return k

    def on_flush(self, mu, access, addr, size, value, ud):
        # 게임이 BIOS 자판 버퍼를 비운다: 들여다본(int 16h AH=1) 키를 버린다
        if self.peeked and self.keys:
            self.pop_key()
            self.ext = None

    def on_int(self, mu, n, ud):
        r = mu.reg_read
        ax = r(UC_X86_REG_AX)
        ah, al = ax >> 8, ax & 0xFF
        if self.trace:
            self.trace_int(n, ah)
        if n == 0x10:
            self.int10(ah, al)
        elif n == 0x16:
            self.nint16 += 1
            if ah in (1, 0x11):
                k = self.peek_key()
                if k is None:
                    self.setzf(True)
                    if not self.keys or self.keys[0][0] < 0:
                        self.polls += 1
                        if self.polls > 20000:
                            raise Exit('keys exhausted' if not self.keys else 'polling past block key')
                    else:
                        self.polls = 0
                else:
                    mu.reg_write(UC_X86_REG_AX, k)
                    self.setzf(False)
                    self.peeked = True
            elif ah in (0, 0x10):
                if self.on_block:
                    self.on_block(self)
                while self.peek_key(True) is None:
                    if not self.keys:
                        raise Exit('keys exhausted (blocking read)')
                mu.reg_write(UC_X86_REG_AX, self.pop_key())
            elif ah == 2:
                mu.reg_write(UC_X86_REG_AX, ax & 0xFF00)
        elif n == 0x1A:
            if ah == 0:
                self.ticks += 1
                mu.reg_write(UC_X86_REG_CX, (self.ticks >> 16) & 0xFFFF)
                mu.reg_write(UC_X86_REG_DX, self.ticks & 0xFFFF)
                mu.reg_write(UC_X86_REG_AX, 0)
            elif ah == 1:
                self.ticks = (r(UC_X86_REG_CX) << 16) | r(UC_X86_REG_DX)
        elif n == 0x21:
            self.int21(ah, al)
        elif n == 0x12:
            mu.reg_write(UC_X86_REG_AX, 640)
        elif n == 0x13:
            mu.reg_write(UC_X86_REG_AX, 0)
            self.setcf(False)
        elif n == 0x20:
            raise Exit(0)
        else:
            self.log.append('int %02X ax=%04X' % (n, ax))

    def trace_int(self, n, ah):
        import zlib
        r = self.mu.reg_read
        self.nint += 1
        regs = [r(x) for x in (UC_X86_REG_AX, UC_X86_REG_BX, UC_X86_REG_CX, UC_X86_REG_DX, UC_X86_REG_SI,
                               UC_X86_REG_DI, UC_X86_REG_BP, UC_X86_REG_SP, UC_X86_REG_DS, UC_X86_REG_ES)]
        ln = '%d int%02X %s' % (self.nint, n, ' '.join('%04X' % v for v in regs))
        if (n == 0x16 and ah in (0, 1)) or (n == 0x21 and ah in (1, 7, 8)) or self.nint % 64 == 0:
            ln += ' crc %08X %08X' % (zlib.crc32(self.rb(0x10000, 0x30000)), zlib.crc32(self.rb(0xB8000, 0x8000)))
        self.trace.write(ln + '\n')
        if self.nint == self.dumpat:
            open(self.dumpfile, 'wb').write(self.rb(0, 0x110000))

    def int10(self, ah, al):
        mu = self.mu
        if ah == 0x00:
            self.vmode = al
            mu.mem_write(0xB8000, bytes(0x8000))
            self.log.append('mode %d' % al)
        elif ah == 0x0F:
            mu.reg_write(UC_X86_REG_AX, 0x5000 | self.vmode)
        elif ah == 0x02:
            dx = mu.reg_read(UC_X86_REG_DX)
            self.row, self.col = dx >> 8, dx & 0xFF
        elif ah == 0x03:
            mu.reg_write(UC_X86_REG_DX, (self.row << 8) | self.col)
        elif ah == 0x0B:
            pass
        else:
            self.log.append('int10 ah=%02X al=%02X' % (ah, al))

    def int21(self, ah, al):
        mu = self.mu
        r = mu.reg_read
        ok = True
        if ah == 0x09:
            s = self.cstr(r(UC_X86_REG_DS), r(UC_X86_REG_DX), ord('$'))
            self.text.append(s)
        elif ah == 0x0A:
            buf = r(UC_X86_REG_DS) * 16 + r(UC_X86_REG_DX)
            ans = self.answers.pop(0) if self.answers else 'k'
            mu.mem_write(buf + 1, bytes([1, ord(ans), 13]))
        elif ah in (0x01, 0x07, 0x08):
            if self.ext is None and self.on_block:
                self.on_block(self)
            if self.ext is not None:
                c, self.ext = self.ext, None
            else:
                while self.peek_key(True) is None:
                    if not self.keys:
                        raise Exit('keys exhausted (int21 %02X)' % ah)
                k = self.pop_key()
                c = k & 0xFF
                if c == 0 or c == 0xE0:
                    c = 0
                    self.ext = k >> 8
            mu.reg_write(UC_X86_REG_AX, (ah << 8) | c)
        elif ah == 0x0B:
            k = self.ext is not None or self.peek_key() is not None
            mu.reg_write(UC_X86_REG_AX, (ah << 8) | (0xFF if k else 0))
        elif ah == 0x0C:
            self.ext = None
            if al in (1, 6, 7, 8, 0xA):
                return self.int21(al, 0xFF)
        elif ah == 0x19:
            mu.reg_write(UC_X86_REG_AX, (ax := r(UC_X86_REG_AX)) & 0xFF00 | 2)
        elif ah == 0x0E:
            mu.reg_write(UC_X86_REG_AX, r(UC_X86_REG_AX) & 0xFF00 | 5)
        elif ah == 0x3D or ah == 0x3C:
            name = self.cstr(r(UC_X86_REG_DS), r(UC_X86_REG_DX))
            base, dot, ext = name.upper().partition('.')
            path = os.path.join(self.files_dir, base[:8] + (dot + ext[:3] if dot else ''))   # 도스 8.3
            if ah == 0x3D and not os.path.exists(path):
                mu.reg_write(UC_X86_REG_AX, 2)
                ok = False
                self.log.append('open fail %s' % name)
            else:
                data = bytearray(open(path, 'rb').read()) if ah == 0x3D else bytearray()
                hnd = 5
                while hnd in self.handles:
                    hnd += 1
                self.handles[hnd] = [data, 0, name, ah == 0x3C]
                mu.reg_write(UC_X86_REG_AX, hnd)
                self.log.append('open %s -> %d (%d bytes)' % (name, hnd, len(data)))
        elif ah == 0x3F and r(UC_X86_REG_BX) not in self.handles:
            self.log.append('read bad handle %d' % r(UC_X86_REG_BX))
            mu.reg_write(UC_X86_REG_AX, 6)
            ok = False
        elif ah == 0x3F:
            hd = self.handles[r(UC_X86_REG_BX)]
            n = r(UC_X86_REG_CX)
            d = bytes(hd[0][hd[1]:hd[1] + n])
            mu.mem_write(r(UC_X86_REG_DS) * 16 + r(UC_X86_REG_DX), d)
            hd[1] += len(d)
            mu.reg_write(UC_X86_REG_AX, len(d))
        elif ah == 0x40:
            hd = self.handles.get(r(UC_X86_REG_BX))
            n = r(UC_X86_REG_CX)
            d = self.rb(r(UC_X86_REG_DS) * 16 + r(UC_X86_REG_DX), n)
            if hd is not None:
                hd[0][hd[1]:hd[1] + n] = d
                hd[1] += n
                hd[3] = True
            mu.reg_write(UC_X86_REG_AX, n)
        elif ah == 0x42:
            hd = self.handles[r(UC_X86_REG_BX)]
            pos = (r(UC_X86_REG_CX) << 16) | r(UC_X86_REG_DX)
            if pos & 0x80000000:
                pos -= 1 << 32
            hd[1] = pos if al == 0 else (hd[1] + pos if al == 1 else len(hd[0]) + pos)
            mu.reg_write(UC_X86_REG_AX, hd[1] & 0xFFFF)
            mu.reg_write(UC_X86_REG_DX, hd[1] >> 16)
        elif ah == 0x3E:
            self.handles.pop(r(UC_X86_REG_BX), None)
        elif ah == 0x4C:
            raise Exit(al)
        elif ah in (0x25, 0x35):
            pass
        else:
            self.log.append('int21 ah=%02X' % ah)
        self.setcf(not ok)

    def on_in(self, mu, port, size, ud):
        if port == 0x61:
            return self.port61
        if port == 0x201:
            return 0xFF
        return 0xFF

    def on_out(self, mu, port, size, value, ud):
        if port == 0x61:
            self.port61 = value & 0xFF
        elif port == 0x42:
            if self.pit_lo:
                self.tone = (self.tone & 0xFF00) | (value & 0xFF)
            else:
                self.tone = (self.tone & 0xFF) | ((value & 0xFF) << 8)
            self.pit_lo = not self.pit_lo

    def run(self, maxinsn=0):
        mu = self.mu
        try:
            while True:
                cs = mu.reg_read(UC_X86_REG_CS)
                ip = mu.reg_read(UC_X86_REG_IP)
                mu.emu_start(cs * 16 + ip, 0x200000, count=maxinsn)
                if getattr(self, 'stop_now', False):
                    return 'stopped'
                if maxinsn:
                    return 'count'
                cs = mu.reg_read(UC_X86_REG_CS)
                ip = mu.reg_read(UC_X86_REG_IP)
                raise RuntimeError('emu stopped at %04X:%04X' % (cs - LOADSEG, ip))
        except Exit as e:
            return 'exit %s' % (e.args[0],)

    def stop(self):
        self.stop_now = True
        self.mu.emu_stop()

    # ---- 화면 ----
    def screen_png(self, fn):
        from PIL import Image
        vram = self.rb(0xB8000, 0x8000)
        im = Image.new('RGB', (320, 200))
        px = im.load()
        if self.vmode == 9:
            pal = TANDY
            for y in range(200):
                base = (y & 3) * 0x2000 + (y >> 2) * 160
                for x in range(320):
                    b = vram[base + (x >> 1)]
                    c = (b >> 4) if not x & 1 else (b & 15)
                    px[x, y] = pal[c]
        else:
            pal = [(0, 0, 0), (85, 255, 255), (255, 85, 255), (255, 255, 255)]
            for y in range(200):
                base = (y & 1) * 0x2000 + (y >> 1) * 80
                for x in range(320):
                    b = vram[base + (x >> 2)]
                    px[x, y] = pal[(b >> (6 - 2 * (x & 3))) & 3]
        im.resize((640, 400), Image.NEAREST).save(fn)


TANDY = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170), (170, 85, 0),
         (170, 170, 170), (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255), (255, 85, 85),
         (255, 85, 255), (255, 255, 85), (255, 255, 255)]

if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000000
    m = Machine(keys=[])
    print(m.run(n))
    cs = m.mu.reg_read(UC_X86_REG_CS); ip = m.mu.reg_read(UC_X86_REG_IP)
    print('at %04X:%04X' % (cs - LOADSEG, ip), 'mode', m.vmode, 'ticks', m.ticks)
    print('\n'.join(m.log[-30:]))
    print(repr(''.join(m.text))[:500])
    m.screen_png(os.path.join(ROOT, 'tools', 'shot.png'))
