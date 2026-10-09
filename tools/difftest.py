# 원본(에뮬레이터)과 옮긴 C(hosttest.exe)를 같은 입력으로 돌려 기록을 대조한다
#   python tools/difftest.py 모드(c/t) "키 키 ..."     (키: 이름 또는 폴수:이름)
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu
from keys import key
ROOT = emu.ROOT
SCR = os.environ.get('SKBTMP', os.path.join(ROOT, 'tools'))


def parse(spec):
    ks = []
    for t in spec.split():
        if t.startswith('b:'):                   # 막고 읽을 때만
            ks.append((-1, key(t[2:])))
        elif ':' in t:
            n, k = t.split(':', 1)
            ks.append((int(n), key(k)))
        else:
            ks.append((0, key(t)))
    return ks


def run_both(mode, ks, maxinsn=0):
    kf = os.path.join(SCR, '_keys.txt')
    open(kf, 'w').write(''.join('%d %x\n' % k for k in ks))
    ta, tb = os.path.join(SCR, '_emu.txt'), os.path.join(SCR, '_host.txt')
    m = emu.Machine(keys=list(ks), mode=mode)
    m.trace = open(ta, 'w')
    r = m.run(maxinsn)
    m.trace.write('exit %s\n' % r.split(' ', 1)[-1])
    m.trace.close()
    subprocess.run([os.path.join(ROOT, os.environ.get('SKBHOST', 'hosttest.exe')), tb, mode, kf, ROOT], check=True)
    return m, ta, tb


def compare(ta, tb):
    A = open(ta).read().splitlines()
    B = open(tb).read().splitlines()
    for k in range(max(len(A), len(B))):
        a = A[k] if k < len(A) else '<끝>'
        b = B[k] if k < len(B) else '<끝>'
        if a != b:
            print('첫 차이: 줄 %d' % (k + 1))
            for j in range(max(0, k - 3), k):
                print('   ', A[j])
            print('emu ', a)
            print('host', b)
            return k
    print('같다: %d 줄, 끝 = %s' % (len(A), A[-1] if A else ''))
    return None


def memdiff(mode, ks, n):
    os.environ['SKBDUMPAT'] = str(n)
    fa, fb = os.path.join(SCR, '_emu.bin'), os.path.join(SCR, '_host.bin')
    os.environ['SKBDUMP'] = fa
    m = emu.Machine(keys=list(ks), mode=mode)
    m.trace = open(os.devnull, 'w')
    m.run()
    os.environ['SKBDUMP'] = fb
    kf = os.path.join(SCR, '_keys.txt')
    subprocess.run([os.path.join(ROOT, os.environ.get('SKBHOST', 'hosttest.exe')), os.devnull, mode, kf, ROOT], check=True)
    A = open(fa, 'rb').read(); B = open(fb, 'rb').read()
    diffs = [k for k in range(0x10000, 0xC0000) if A[k] != B[k]]
    print('다른 바이트 %d 개' % len(diffs))
    runs = []
    for k in diffs:
        if runs and k <= runs[-1][1] + 4:
            runs[-1][1] = k
        else:
            runs.append([k, k])
    for s0, e0 in runs[:30]:
        seg = 'DS:%04X' % (s0 - (emu.DSEG << 4)) if (emu.DSEG << 4) <= s0 < (emu.DSEG << 4) + 0x10000 else '%05X' % s0
        print('  %s..+%d  emu %s  host %s' % (seg, e0 - s0 + 1, A[s0:min(e0 + 1, s0 + 16)].hex(), B[s0:min(e0 + 1, s0 + 16)].hex()))


if __name__ == '__main__':
    ks = parse(sys.argv[2])
    m, ta, tb = run_both(sys.argv[1], ks)
    k = compare(ta, tb)
    if k is not None and len(sys.argv) < 4:
        memdiff(sys.argv[1], ks, k + 1)
