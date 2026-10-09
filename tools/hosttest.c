/* ============================================================================
 *  hosttest.c  -  옮긴 C(skbcode.c)를 PC(mingw)에서 돌리는 대조 시험판
 * ----------------------------------------------------------------------------
 *  tools/emu.py 와 똑같은 규칙으로 BIOS/DOS 를 흉내 낸다:
 *    - 시계(int 1Ah AH=0)는 읽을 때마다 한 틱
 *    - 키는 목록에서: (기다릴 폴 수, 키).  int 16h AH=1 이 "없음"을 그만큼 돌려준 뒤 낸다
 *    - 게임이 BIOS 자판 버퍼를 비우면(0:041C 쓰기) 들여다본 키를 버린다
 *    - 파일은 게임 폴더에서 읽기만 한다 (쓰기는 메모리 안에서만)
 *  인터럽트마다 레지스터를, 키 입력 때마다 메모리 CRC 를 기록한다 (emu.py 와 같은 형식)
 *
 *  hosttest 기록파일 모드(c/t) 키목록파일 [게임폴더]
 *     키목록: 줄마다 "기다릴폴수 키값(16진)"
 * ========================================================================== */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "../cpu.h"
#include "../skbcode.h"
#ifdef SKBVGA
#include "../skbvga.h"
static const char *shotdir;
static int nshot;

/* 개선판 화면을 BMP 로 (키를 기다릴 때마다) */
static void vga_shot(void)
{
    static uint8_t buf[64000];
    char fn[512];
    FILE *f;
    uint8_t hdr[54];
    uint32_t v;
    int i, y;

    if (!shotdir)
        return;
    vga_render(buf);
    sprintf(fn, "%s%03d.bmp", shotdir, nshot++);
    f = fopen(fn, "wb");
    if (!f)
        return;
    memset(hdr, 0, sizeof hdr);
    hdr[0] = 'B';
    hdr[1] = 'M';
    v = 54 + 1024 + 64000;
    memcpy(hdr + 2, &v, 4);
    v = 54 + 1024;
    memcpy(hdr + 10, &v, 4);
    v = 40;
    memcpy(hdr + 14, &v, 4);
    v = 320;
    memcpy(hdr + 18, &v, 4);
    v = 200;
    memcpy(hdr + 22, &v, 4);
    hdr[26] = 1;
    hdr[28] = 8;
    fwrite(hdr, 1, 54, f);
    for (i = 0; i < 256; i++) {
        uint8_t q[4] = {(uint8_t)(vga_pal[i][2] << 2), (uint8_t)(vga_pal[i][1] << 2), (uint8_t)(vga_pal[i][0] << 2), 0};
        fwrite(q, 1, 4, f);
    }
    for (y = 199; y >= 0; y--)
        fwrite(buf + y * 320, 1, 320, f);
    fclose(f);
}
#else
#define vga_shot()
#endif

static FILE *trace;
static unsigned long nint, dumpat;
static const char *gamedir = ".";

/* ---- 키 ---- */
static int nkeys, kp;
static unsigned kwait[4096], kval[4096];
static unsigned waitcnt, polls;
static int peeked, ext = -1;
static char answers[2];
static int nans;

/* ---- 시계, 포트 ---- */
static uint32_t ticks;
static uint8_t port61;
static uint8_t vmode = 3;
static int row, col;

/* ---- 파일 ---- */
typedef struct {
    int used;
    uint8_t *data;
    long len, pos;
    char name[16];
} hfile_t;
static hfile_t files[32];

static void quit(const char *why)
{
    vga_shot();
    fprintf(trace, "exit %s\n", why);
    fclose(trace);
    exit(0);
}

static uint32_t crctab[256];
static uint32_t crc32(const uint8_t *p, uint32_t n)
{
    uint32_t c = 0xFFFFFFFF;
    while (n--)
        c = crctab[(c ^ *p++) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFF;
}

static void trace_int(int n)
{
    nint++;
    fprintf(trace, "%lu int%02X %04X %04X %04X %04X %04X %04X %04X %04X %04X %04X", nint, n, AX, BX, CX, DX,
            SI, DI, BP, SP, DS_, ES_);
    if ((n == 0x16 && (AH == 0 || AH == 1)) || (n == 0x21 && (AH == 1 || AH == 7 || AH == 8)) || nint % 64 == 0)
        fprintf(trace, " crc %08X %08X", crc32(M + 0x10000, 0x30000), crc32(M + 0xB8000, 0x8000));
    fputc('\n', trace);
    if (dumpat && nint == dumpat) {
        FILE *d = fopen(getenv("SKBDUMP"), "wb");
        fwrite(M, 1, MEMSIZE, d);
        fclose(d);
    }
}

static int peek_key(int blocking)
{
    if (kp >= nkeys)
        return -1;
    if (kwait[kp] == 0xFFFFFFFFu)           /* 막고 읽을 때만 내는 키 */
        return blocking ? (int)kval[kp] : -1;
    if (waitcnt < kwait[kp]) {
        waitcnt++;
        return -1;
    }
    return (int)kval[kp];
}

static unsigned pop_key(void)
{
    unsigned k = kval[kp++];
    waitcnt = 0;
    peeked = 0;
    return k;
}

void kbd_flush_hook(void)
{
    if (peeked && kp < nkeys) {
        pop_key();
        ext = -1;
    }
}

static void setzf(int z)
{
    ZF = z;
}

void int10(void)
{
    trace_int(0x10);
    switch (AH) {
    case 0x00:
        vmode = AL;
        memset(M + 0xB8000, 0, 0x8000);
#ifdef SKBVGA
        memset(COL + 0xB8000, 0, 0x8000 * sizeof(uint32_t));
#endif
        break;
    case 0x0F:
        AX = 0x5000 | vmode;
        break;
    case 0x02:
        row = DH;
        col = DL;
        break;
    case 0x03:
        DX = (uint16_t)((row << 8) | col);
        break;
    }
}

void int12(void)
{
    trace_int(0x12);
    AX = 640;
}

void int13(void)
{
    trace_int(0x13);
    AX = 0;
    CF = 0;
}

void int16(void)
{
    int k;

    trace_int(0x16);
#ifdef SKBVGA
    {   /* SKBSHOTPOLL=N: 들여다보기 N 번마다 화면도 */
        static long every = -1, cnt;
        if (every < 0)
            every = getenv("SKBSHOTPOLL") ? atol(getenv("SKBSHOTPOLL")) : 0;
        if (every > 0 && (AH == 1 || AH == 0x11) && ++cnt % every == 0)
            vga_shot();
    }
#endif
    if (AH == 1 || AH == 0x11) {
        k = peek_key(0);
        if (k < 0) {
            setzf(1);
            if (kp >= nkeys || kwait[kp] == 0xFFFFFFFFu) {
                if (++polls > 20000)
                    quit(kp >= nkeys ? "keys exhausted" : "polling past block key");
            } else
                polls = 0;
        } else {
            AX = (uint16_t)k;
            setzf(0);
            peeked = 1;
        }
    } else if (AH == 0 || AH == 0x10) {
        vga_shot();
        while (peek_key(1) < 0)
            if (kp >= nkeys)
                quit("keys exhausted (blocking read)");
        AX = (uint16_t)pop_key();
    } else if (AH == 2) {
        AX &= 0xFF00;
    }
}

void int1a(void)
{
    trace_int(0x1A);
#ifdef SKBVGA
    {   /* SKBSHOTTICK=N: 시계 읽기 N 번마다 화면도 */
        static long every = -1, cnt;
        if (every < 0)
            every = getenv("SKBSHOTTICK") ? atol(getenv("SKBSHOTTICK")) : 0;
        if (every > 0 && ++cnt % every == 0)
            vga_shot();
    }
#endif
    if (AH == 0) {
        ticks++;
        CX = (uint16_t)(ticks >> 16);
        DX = (uint16_t)ticks;
        AX = 0;
    } else if (AH == 1) {
        ticks = ((uint32_t)CX << 16) | DX;
    }
}

static char *cstr(uint16_t seg, uint16_t off, char term)
{
    static char buf[256];
    int n = 0;
    while (n < 255 && RB(seg, off) != (uint8_t)term)
        buf[n++] = (char)RB(seg, off++);
    buf[n] = 0;
    return buf;
}

void int21(void)
{
    int ok = 1, h;
    unsigned c, k;
    uint8_t ah = AH, al = AL;

    trace_int(0x21);
    switch (ah) {
    case 0x09:
        break;
    case 0x0A: {
        uint32_t buf = LIN(DS_, DX);
        char a = nans < 2 ? answers[nans++] : 'k';
        M[buf + 1] = 1;
        M[buf + 2] = (uint8_t)a;
        M[buf + 3] = 13;
        break;
    }
    case 0x01:
    case 0x07:
    case 0x08:
        if (ext < 0)
            vga_shot();
        if (ext >= 0) {
            c = (unsigned)ext;
            ext = -1;
        } else {
            while (peek_key(1) < 0)
                if (kp >= nkeys)
                    { char w[40]; sprintf(w, "keys exhausted (int21 %02X)", ah); quit(w); }
            k = pop_key();
            c = k & 0xFF;
            if (c == 0 || c == 0xE0) {
                c = 0;
                ext = (int)(k >> 8);
            }
        }
        AX = (uint16_t)((ah << 8) | c);
        break;
    case 0x0B:
        AX = (uint16_t)((ah << 8) | ((ext >= 0 || peek_key(0) >= 0) ? 0xFF : 0));
        break;
    case 0x19:
        AL = 2;
        break;
    case 0x0E:
        AL = 5;
        break;
    case 0x3C:
    case 0x3D: {
        char path[512], *nm = cstr(DS_, DX, 0), *p;
        FILE *fp = NULL;
        long len = 0;
        uint8_t *data = NULL;
        {   /* 도스 8.3: 이름 8 자, 확장자 3 자로 자른다 */
            char b[16], *q = b, *dot = strchr(nm, '.');
            int n = 0;
            while (nm[n] && nm[n] != '.' && n < 8)
                *q++ = nm[n++];
            if (dot) {
                *q++ = '.';
                for (n = 1; dot[n] && n <= 3; n++)
                    *q++ = dot[n];
            }
            *q = 0;
            snprintf(path, sizeof(path), "%s/%s", gamedir, b);
        }
        for (p = path + strlen(gamedir) + 1; *p; p++)
            *p = (char)toupper((unsigned char)*p);
        if (ah == 0x3D) {
            fp = fopen(path, "rb");
            if (!fp) {
                AX = 2;
                ok = 0;
                break;
            }
            fseek(fp, 0, SEEK_END);
            len = ftell(fp);
            fseek(fp, 0, SEEK_SET);
            data = malloc((size_t)len + 1);
            if (fread(data, 1, (size_t)len, fp) != (size_t)len)
                len = 0;
            fclose(fp);
        } else {
            data = malloc(1);
        }
        for (h = 5; h < 32 && files[h].used; h++)
            ;
        files[h].used = 1;
        strncpy(files[h].name, nm, 15);
        files[h].data = data;
        files[h].len = len;
        files[h].pos = 0;
        AX = (uint16_t)h;
        break;
    }
    case 0x3F:
        h = BX;
        if (h >= 32 || !files[h].used) {
            AX = 6;
            ok = 0;
            break;
        }
        {
            long n = CX, i;
            if (n > files[h].len - files[h].pos)
                n = files[h].len - files[h].pos;
            if (n < 0)
                n = 0;
            for (i = 0; i < n; i++)
                M[LIN(DS_, DX + i)] = files[h].data[files[h].pos + i];
#ifdef SKBVGA
            for (i = 0; i < n; i++)
                COL[LIN(DS_, DX + i)] = 0;
            vga_file_read(files[h].name, LIN(DS_, DX), (uint32_t)files[h].pos, (uint32_t)n);
#endif
            files[h].pos += n;
            AX = (uint16_t)n;
        }
        break;
    case 0x40:
        h = BX;
        if (h < 32 && files[h].used) {
            long n = CX, i;
            if (files[h].pos + n > files[h].len) {
                files[h].data = realloc(files[h].data, (size_t)(files[h].pos + n + 1));
                files[h].len = files[h].pos + n;
            }
            for (i = 0; i < n; i++)
                files[h].data[files[h].pos + i] = M[LIN(DS_, DX + i)];
            files[h].pos += n;
        }
        AX = CX;
        break;
    case 0x42: {
        long pos = (long)(int32_t)(((uint32_t)CX << 16) | DX);
        h = BX;
        files[h].pos = al == 0 ? pos : al == 1 ? files[h].pos + pos : files[h].len + pos;
        AX = (uint16_t)files[h].pos;
        DX = (uint16_t)(files[h].pos >> 16);
        break;
    }
    case 0x3E:
        h = BX;
        if (h < 32 && files[h].used) {
            free(files[h].data);
            files[h].used = 0;
        }
        break;
    case 0x4C:
        quit("4C");
        break;
    default:
        break;
    }
    CF = !ok;
}

uint8_t port_in(uint16_t port)
{
    if (port == 0x61)
        return port61;
    return 0xFF;
}

void port_out(uint16_t port, uint8_t v)
{
    if (port == 0x61)
        port61 = v;
}

void delay_loop(uint16_t n)
{
    (void)n;
}

void far_return(void)
{
    quit("retf");
}

void div_error(uint16_t at)
{
    fprintf(trace, "divide error at %04X\n", at);
    quit("div");
}

int main(int argc, char **argv)
{
    FILE *kf;
    unsigned i;

    if (argc < 4) {
        fprintf(stderr, "hosttest trace mode keys [gamedir]\n");
        return 1;
    }
    for (i = 0; i < 256; i++) {
        uint32_t c = i;
        int k;
        for (k = 0; k < 8; k++)
            c = (c & 1) ? 0xEDB88320 ^ (c >> 1) : c >> 1;
        crctab[i] = c;
    }
    trace = fopen(argv[1], "w");
    answers[0] = argv[2][0];
    answers[1] = 'k';
    kf = fopen(argv[3], "r");
    if (kf) {
        while (nkeys < 4096 && fscanf(kf, "%d %x", (int *)&kwait[nkeys], &kval[nkeys]) == 2)
            nkeys++;
        fclose(kf);
    }
    if (argc > 4)
        gamedir = argv[4];
    if (getenv("SKBDUMPAT"))
        dumpat = strtoul(getenv("SKBDUMPAT"), 0, 10);
    cpu_reset();
#ifdef SKBVGA
    {
        char pth[512];
        snprintf(pth, sizeof pth, "%s/SKBVGA.DAT", gamedir);
        vga_load(pth);
        vga_reset();
        shotdir = getenv("SKBSHOT");
    }
#endif
    skb_main();
    quit("return");
    return 0;
}
