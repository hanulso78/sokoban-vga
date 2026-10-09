# 키 이름 -> BIOS 키 값 (스캔<<8 | 아스키)
KEYS = {'enter': 0x1C0D, 'esc': 0x011B, 'up': 0x4800, 'down': 0x5000, 'left': 0x4B00, 'right': 0x4D00,
        'space': 0x3920, 'f1': 0x3B00, 'f2': 0x3C00, 'f3': 0x3D00, 'f10': 0x4400, 'bs': 0x0E08,
        'home': 0x4700, 'end': 0x4F00, 'pgup': 0x4900, 'pgdn': 0x5100, 'del': 0x5300, 'ins': 0x5200}
SC = "..1234567890-=..qwertyuiop[]..asdfghjkl;'`.\\zxcvbnm,./"


def key(s):
    if s in KEYS:
        return KEYS[s]
    if len(s) == 1:
        c = s.lower()
        return (SC.index(c) << 8 | ord(s)) if c in SC else ord(s)
    return int(s, 16)
