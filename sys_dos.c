/* ============================================================================
 *  sys_dos.c  -  도스(djgpp) 플랫폼: 옮긴 코드의 int / in / out 을 진짜로 한다
 * ----------------------------------------------------------------------------
 *  화면   원본은 CGA 모드 4 (320x200 4색) 나 Tandy 모드 9 (320x200 16색) 에 그린다.
 *         옮긴 코드는 M[] 안의 B800 자리에 그리고, 여기서 그것을 VGA 모드 13h 로
 *         풀어 보인다 (키를 읽거나 시계를 볼 때, 70분의 1초에 한 번까지).
 *         시작할 때의 글자 화면(시스템 고르기)은 진짜 BIOS/DOS 가 한다.
 *  자판   BIOS (int 16h), DOS (int 21h 07h).  게임이 BIOS 자판 버퍼를 비우면 진짜로 비운다.
 *         원본은 그림이 움직이는 동안 PIC 에서 자판 IRQ 를 막는다 -> 막았다 풀 때 비운다.
 *  시계   int 1Ah 는 BIOS 틱(0:046C)을 읽되, 게임이 시각을 바꾸면(AH=1) 차이만 기억한다.
 *  소리   포트 42h/43h/61h 그대로.  원본의 "loop $" 시간 끌기는 8088 4.77MHz 의 시간만큼
 *         기다린다 (delay_loop) -> 스피커를 직접 켜고 끄는 효과음도 원래 높이로 난다.
 *  파일   DOS 파일 함수 그대로 (점수, 이름, 만든 판을 저장한다)
 * ========================================================================== */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <dpmi.h>
#include <go32.h>
#include <pc.h>
#include <sys/farptr.h>
#include <sys/movedata.h>
#include <time.h>
#include "cpu.h"
#include "skbcode.h"
#ifdef SKBVGA
#include "skbvga.h"
static int use_joystick;
#endif

static int gfx;                 /* 0 글자, 4 CGA, 9 Tandy */
static int vga_on;
static uint8_t vbuf[64000];
static uclock_t last_present;
static int32_t tick_ofs;        /* 게임이 본 시계 = BIOS 틱 + tick_ofs */
static int kbd_masked;
static int dos_ext_pending;      /* int 21h 07h 이 확장 키의 0 을 돌려줬다 */
#ifdef SKBVGA
static struct {
    char name[16];
    uint32_t pos;
} hfiles[64];
#endif

/* ---- 화면 ------------------------------------------------------------------ */
static const uint8_t cga16[16][3] = {
    {0, 0, 0}, {0, 0, 42}, {0, 42, 0}, {0, 42, 42}, {42, 0, 0}, {42, 0, 42}, {42, 21, 0}, {42, 42, 42},
    {21, 21, 21}, {21, 21, 63}, {21, 63, 21}, {21, 63, 63}, {63, 21, 21}, {63, 21, 63}, {63, 63, 21}, {63, 63, 63},
};

static void set_vga(void)
{
    __dpmi_regs r;
    int i;

    memset(&r, 0, sizeof r);
    r.x.ax = 0x0013;
    __dpmi_int(0x10, &r);
    outportb(0x3C8, 0);
#ifdef SKBVGA
    for (i = 0; i < 256; i++) {
        outportb(0x3C9, vga_pal[i][0]);
        outportb(0x3C9, vga_pal[i][1]);
        outportb(0x3C9, vga_pal[i][2]);
    }
#else
    for (i = 0; i < 16; i++) {
        outportb(0x3C9, cga16[i][0]);
        outportb(0x3C9, cga16[i][1]);
        outportb(0x3C9, cga16[i][2]);
    }
#endif
    vga_on = 1;
}

static void present(void)
{
    static const uint8_t pal1[4] = {0, 11, 13, 15};     /* 모드 4 기본: 밝은 팔레트 1 */
    const uint8_t *v = M + 0xB8000;
    uint8_t *d = vbuf;
    int x, y;

    if (!gfx)
        return;
#ifdef SKBVGA
    vga_ms = (uint32_t)(uclock() * 1000 / UCLOCKS_PER_SEC) + 1;
    vga_render(vbuf);
    dosmemput(vbuf, sizeof vbuf, 0xA0000);
    last_present = uclock();
    return;
#endif
    if (gfx == 9) {
        for (y = 0; y < 200; y++) {
            const uint8_t *s = v + (y & 3) * 0x2000 + (y >> 2) * 160;
            for (x = 0; x < 160; x++) {
                *d++ = s[x] >> 4;
                *d++ = s[x] & 15;
            }
        }
    } else {
        for (y = 0; y < 200; y++) {
            const uint8_t *s = v + (y & 1) * 0x2000 + (y >> 1) * 80;
            for (x = 0; x < 80; x++) {
                uint8_t b = s[x];
                *d++ = pal1[b >> 6];
                *d++ = pal1[(b >> 4) & 3];
                *d++ = pal1[(b >> 2) & 3];
                *d++ = pal1[b & 3];
            }
        }
    }
    dosmemput(vbuf, sizeof vbuf, 0xA0000);
    last_present = uclock();
}

static void maybe_present(void)
{
#ifdef SKBVGA
    music_want(vga_music());
    music_poll();
#endif
    if (gfx && uclock() - last_present > UCLOCKS_PER_SEC / 70)
        present();
}

static void text_mode(void)
{
    __dpmi_regs r;

#ifdef SKBVGA
    music_off();
#endif
    memset(&r, 0, sizeof r);
    r.x.ax = 0x0003;
    __dpmi_int(0x10, &r);
    vga_on = 0;
    gfx = 0;
}

/* ---- 시험 모드 ---------------------------------------------------------------
 *  SKBTEST=스크립트파일 이면 자판 대신 스크립트를 읽는다 (tools/dosshot.py 가 쓴다)
 *     <밀리초> key <이름|16진>    그 시각부터 누른 것으로 친다
 *     <밀리초> shot <이름>        화면을 <이름>.BMP 로
 *     <밀리초> quit
 *  시작 화면의 두 물음(시스템, 입력 장치)에는 SKBMODE(c/t) 와 k 로 답한다.
 * -------------------------------------------------------------------------- */
static int test_on;
static struct {
    long ms;
    char what;                  /* k s q */
    unsigned key;
    char name[16];
} tev[512];
static int ntev, tpos;
static uclock_t tstart;
static int text_ext = -1;
static FILE *tlog;

static long now_ms(void)
{
    return (long)((uclock() - tstart) * 1000 / UCLOCKS_PER_SEC);
}

static unsigned keyval(const char *s)
{
    static const struct {
        const char *n;
        unsigned v;
    } names[] = {{"enter", 0x1C0D}, {"esc", 0x011B}, {"up", 0x4800}, {"down", 0x5000}, {"left", 0x4B00},
                 {"right", 0x4D00}, {"space", 0x3920}, {"bs", 0x0E08}, {"f1", 0x3B00}, {"f2", 0x3C00},
                 {"f10", 0x4400}, {"home", 0x4700}, {"end", 0x4F00}, {"pgup", 0x4900}, {"pgdn", 0x5100},
                 {"del", 0x5300}, {"ins", 0x5200}};
    static const char sc[] = "..1234567890-=..qwertyuiop[]..asdfghjkl;'`.\\zxcvbnm,./";
    unsigned i;
    for (i = 0; i < sizeof names / sizeof names[0]; i++)
        if (!strcmp(s, names[i].n))
            return names[i].v;
    if (strlen(s) == 1) {
        const char *q = strchr(sc, s[0]);
        return (unsigned)(((q ? q - sc : 0) << 8) | (uint8_t)s[0]);
    }
    return (unsigned)strtoul(s, 0, 16);
}

static void save_bmp(const char *name)
{
    static uint8_t pal[768];
    char fn[40];
    FILE *f;
    int y, i;
    uint8_t hdr[54];
    uint32_t v;

    sprintf(fn, "%s.BMP", name);
    f = fopen(fn, "wb");
    if (!f)
        return;
    outportb(0x3C7, 0);
    for (i = 0; i < 768; i++)
        pal[i] = inportb(0x3C9);
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
        uint8_t q[4];
        q[0] = pal[i * 3 + 2] << 2;
        q[1] = pal[i * 3 + 1] << 2;
        q[2] = pal[i * 3] << 2;
        q[3] = 0;
        fwrite(q, 1, 4, f);
    }
    dosmemget(0xA0000, 64000, vbuf);
    for (y = 199; y >= 0; y--)
        fwrite(vbuf + y * 320, 1, 320, f);
    fclose(f);
}

static void present(void);

/* 시각이 된 shot/quit 을 처리 */
static void test_poll(void)
{
    long t = now_ms();
    while (tpos < ntev && tev[tpos].ms <= t && tev[tpos].what != 'k') {
        if (tev[tpos].what == 's') {
            present();
            save_bmp(tev[tpos].name);
            if (tlog)
                fprintf(tlog, "%ld shot %s\n", t, tev[tpos].name);
        } else {
            outportb(0x61, inportb(0x61) & 0xFC);
            if (tlog)
                fclose(tlog);
            {
                __dpmi_regs r;
                memset(&r, 0, sizeof r);
                r.x.ax = 3;
                __dpmi_int(0x10, &r);
            }
            exit(0);
        }
        tpos++;
    }
}

/* 지금 누를 수 있는 키 (-1 없음) */
static int test_peek(void)
{
    test_poll();
    if (tpos < ntev && tev[tpos].what == 'k' && tev[tpos].ms <= now_ms())
        return (int)tev[tpos].key;
    return -1;
}

static unsigned test_get(void)
{
    int k;
    while ((k = test_peek()) < 0) {
        __dpmi_yield();
        present();
        if (tpos >= ntev)
            exit(0);
    }
    tpos++;
    if (tlog)
        fprintf(tlog, "%ld key %04X\n", now_ms(), (unsigned)k);
    return (unsigned)k;
}

static void test_init(void)
{
    const char *fn = getenv("SKBTEST");
    FILE *f;
    char ln[128], w[16], a[32];
    long ms;

    if (!fn || !(f = fopen(fn, "r")))
        return;
    while (ntev < 512 && fgets(ln, sizeof ln, f)) {
        a[0] = 0;
        if (sscanf(ln, "%ld %15s %31s", &ms, w, a) < 2)
            continue;
        tev[ntev].ms = ms;
        tev[ntev].what = w[0];
        if (w[0] == 'k')
            tev[ntev].key = keyval(a);
        else
            strncpy(tev[ntev].name, a, 15);
        ntev++;
    }
    fclose(f);
    test_on = 1;
    tlog = fopen("SKBLOG.TXT", "w");
    tstart = uclock();
}

/* ---- 인터럽트 ---------------------------------------------------------------- */
void int10(void)
{
    __dpmi_regs r;

    if (AH == 0x00) {
        memset(M + 0xB8000, 0, 0x8000);
#ifdef SKBVGA
        memset(COL + 0xB8000, 0, 0x8000 * sizeof(uint32_t));
        if (AL != 3) {                      /* 시작 글자 화면도 VGA 로 (보이지 않게) */
            gfx = 4;
            if (!vga_on)
                set_vga();
            present();
            return;
        }
#endif
        if (AL == 4 || AL == 9) {
            gfx = AL;
            if (!vga_on)
                set_vga();
            present();
            return;
        }
        gfx = 0;
        vga_on = 0;
    } else if (gfx) {
        if (AH == 0x0F)
            AX = (uint16_t)(0x2800 | gfx);
        return;                             /* 그래픽 화면에서는 커서 따위를 쓰지 않는다 */
    }
    memset(&r, 0, sizeof r);
    r.x.ax = AX;
    r.x.bx = BX;
    r.x.cx = CX;
    r.x.dx = DX;
    __dpmi_int(0x10, &r);
    AX = r.x.ax;
    BX = r.x.bx;
    CX = r.x.cx;
    DX = r.x.dx;
}

void int12(void)
{
    AX = 640;
}

void int13(void)
{
    AX = 0;                                 /* 디스크는 늘 준비됨 */
    CF = 0;
}

void int16(void)
{
    __dpmi_regs r;

    if (test_on) {
        maybe_present();
        if (AH == 1 || AH == 0x11) {
            int k = test_peek();
            ZF = k < 0;
            if (k >= 0)
                AX = (uint16_t)k;
        } else if (AH == 0 || AH == 0x10)
            AX = (uint16_t)test_get();
        return;
    }
    if (AH == 0 || AH == 0x10) {           /* 막고 읽기: 기다리는 동안 화면을 보인다 */
        present();
        while (_farpeekw(_dos_ds, 0x41A) == _farpeekw(_dos_ds, 0x41C)) {
            __dpmi_yield();
            maybe_present();
        }
    } else
        maybe_present();
    memset(&r, 0, sizeof r);
    r.x.ax = AX;
    __dpmi_int(0x16, &r);
    AX = r.x.ax;
    ZF = (r.x.flags & 0x40) != 0;
}

static uint32_t bios_ticks(void)
{
    return _farpeekl(_dos_ds, 0x46C);
}

void int1a(void)
{
    if (test_on)
        test_poll();
    maybe_present();
    if (AH == 0) {
        uint32_t t = (uint32_t)((int32_t)bios_ticks() + tick_ofs);
        CX = (uint16_t)(t >> 16);
        DX = (uint16_t)t;
        AL = 0;
    } else if (AH == 1) {
        tick_ofs = (int32_t)(((uint32_t)CX << 16) | DX) - (int32_t)bios_ticks();
    }
}

void kbd_flush_hook(void)
{
    __dpmi_regs r;

    if (test_on) {                          /* 시각이 지난 키를 버린다 */
        while (test_peek() >= 0)
            tpos++;
        return;
    }

    for (;;) {
        memset(&r, 0, sizeof r);
        r.h.ah = 1;
        __dpmi_int(0x16, &r);
        if (r.x.flags & 0x40)
            break;
        r.h.ah = 0;
        __dpmi_int(0x16, &r);
    }
}

/* DOS 호출: 메모리 자리(DS:DX)를 옮겨 주고 받을 것만 */
static void dos_call(__dpmi_regs *r)
{
    __dpmi_int(0x21, r);
}

void int21(void)
{
    __dpmi_regs r;
    uint8_t ah = AH;
    uint32_t src = LIN(DS_, DX);

    memset(&r, 0, sizeof r);
    r.x.ax = AX;
    r.x.bx = BX;
    r.x.cx = CX;
    r.x.dx = DX;
    switch (ah) {
    case 0x09: {                            /* '$' 로 끝나는 글 */
        unsigned n = 0;
#ifdef SKBVGA
        return;                             /* 개선판: 시작 물음은 보이지 않는다 */
#endif
        while (n < 2000 && M[src + n] != '$')
            n++;
        dosmemput(M + src, n + 1, __tb);
        r.x.ds = __tb >> 4;
        r.x.dx = __tb & 15;
        dos_call(&r);
        return;
    }
    case 0x0A: {                            /* 줄 입력 */
        unsigned len = M[src] + 2;
#ifdef SKBVGA
        {   /* 시스템은 CGA, 입력 장치는 키보드 (/J 면 조이스틱) */
            static int nq;
            M[src + 1] = 1;
            M[src + 2] = (uint8_t)(nq++ == 0 ? 'c' : (use_joystick ? 'j' : 'k'));
            M[src + 3] = 13;
            return;
        }
#endif
        if (test_on) {
            static int nq;
            const char *md = getenv("SKBMODE");
            M[src + 1] = 1;
            M[src + 2] = (uint8_t)(nq++ == 0 ? (md ? md[0] : 'c') : 'k');
            M[src + 3] = 13;
            return;
        }
        dosmemput(M + src, len, __tb);
        r.x.ds = __tb >> 4;
        r.x.dx = __tb & 15;
        dos_call(&r);
        dosmemget(__tb, len, M + src);
        return;
    }
    case 0x01:
    case 0x07:
    case 0x08:
        if (test_on) {
            unsigned k;
            if (text_ext >= 0) {
                AL = (uint8_t)text_ext;
                text_ext = -1;
                return;
            }
            k = test_get();
            AL = (uint8_t)k;
            if (AL == 0 || AL == 0xE0) {
                AL = 0;
                text_ext = (int)(k >> 8);
            }
            return;
        }
        /* 확장 키의 두 번째 바이트는 DOS 가 들고 있다 (BIOS 버퍼는 이미 비었다): 기다리지 않는다 */
        if (gfx && !dos_ext_pending) {
            present();
            while (_farpeekw(_dos_ds, 0x41A) == _farpeekw(_dos_ds, 0x41C)) {
                __dpmi_yield();
                maybe_present();
            }
        }
        dos_call(&r);
        AL = r.h.al;
        dos_ext_pending = !dos_ext_pending && AL == 0;
        return;
    case 0x0E:                              /* 드라이브 고르기: 지금 드라이브만 찾게 */
        AL = 1;
        return;
    case 0x19:
        dos_call(&r);
        AL = r.h.al;
        return;
    case 0x25:
    case 0x35:
        return;                             /* Ctrl-C 처리기는 우리가 따로 */
    case 0x3C:
    case 0x3D: {                            /* 만들기 / 열기: 이름을 옮겨 준다 */
        unsigned n = 0;
        while (n < 127 && M[src + n])
            n++;
        dosmemput(M + src, n + 1, __tb);
        r.x.ds = __tb >> 4;
        r.x.dx = __tb & 15;
        dos_call(&r);
        AX = r.x.ax;
        CF = r.x.flags & 1;
#ifdef SKBVGA
        if (!CF && AX < 64) {
            unsigned k;
            for (k = 0; k < 15 && M[src + k]; k++)
                hfiles[AX].name[k] = (char)M[src + k];
            hfiles[AX].name[k] = 0;
            hfiles[AX].pos = 0;
        }
#endif
        return;
    }
    case 0x3F: {                            /* 읽기: 전송 버퍼를 조각조각 */
        unsigned want = CX, got = 0, chunk;
        CF = 0;
        while (got < want) {
            chunk = want - got;
            if (chunk > 0x4000)
                chunk = 0x4000;
            memset(&r, 0, sizeof r);
            r.h.ah = 0x3F;
            r.x.bx = BX;
            r.x.cx = (uint16_t)chunk;
            r.x.ds = __tb >> 4;
            r.x.dx = __tb & 15;
            dos_call(&r);
            if (r.x.flags & 1) {
                AX = r.x.ax;
                CF = 1;
                return;
            }
            dosmemget(__tb, r.x.ax, M + src + got);
            got += r.x.ax;
            if (r.x.ax < chunk)
                break;
        }
        AX = (uint16_t)got;
#ifdef SKBVGA
        {
            unsigned k;
            for (k = 0; k < got; k++)
                COL[src + k] = 0;
            if (BX < 64) {
                vga_file_read(hfiles[BX].name, src, hfiles[BX].pos, got);
                hfiles[BX].pos += got;
            }
        }
#endif
        return;
    }
    case 0x40: {                            /* 쓰기 */
        unsigned want = CX, put = 0, chunk;
        CF = 0;
        while (put < want) {
            chunk = want - put;
            if (chunk > 0x4000)
                chunk = 0x4000;
            dosmemput(M + src + put, chunk, __tb);
            memset(&r, 0, sizeof r);
            r.h.ah = 0x40;
            r.x.bx = BX;
            r.x.cx = (uint16_t)chunk;
            r.x.ds = __tb >> 4;
            r.x.dx = __tb & 15;
            dos_call(&r);
            if (r.x.flags & 1) {
                AX = r.x.ax;
                CF = 1;
                return;
            }
            put += r.x.ax;
            if (r.x.ax < chunk)
                break;
        }
        AX = (uint16_t)put;
        return;
    }
    case 0x4C:
        text_mode();
        exit(AL);
    default:                                /* 3E 닫기, 42 옮기기 ... */
        dos_call(&r);
        AX = r.x.ax;
        DX = r.x.dx;
        CF = r.x.flags & 1;
        return;
    }
}

/* ---- 포트 ------------------------------------------------------------------ */
uint8_t port_in(uint16_t port)
{
    return inportb(port);
}

void port_out(uint16_t port, uint8_t v)
{
    if (port == 0x21) {
        /* 원본은 PIC 에서 자판 IRQ 를 막는다.  막아 두는 대신, 푸는 때에 버퍼를 비운다 */
        int m = (v & 2) != 0;
        if (kbd_masked && !m)
            kbd_flush_hook();
        kbd_masked = m;
        return;
    }
#ifdef SKBVGA
    if (port == 0x61 && vga_in_tune && music_found()) {   /* 승리 곡은 애드립이 대신 */
        outportb(0x61, inportb(0x61) & 0xFC);
        return;
    }
#endif
    outportb(port, v);
}

/* 8088 4.77MHz 에서 "loop $" 한 번 = 17 클럭 */
void delay_loop(uint16_t n)
{
    uclock_t end = uclock() + (uclock_t)n * 17 * UCLOCKS_PER_SEC / 4772727;
    while (uclock() < end) {
#ifdef SKBVGA
        if (n > 200)
            maybe_present();
#endif
    }
}

void far_return(void)
{
    text_mode();
    exit(0);
}

void div_error(uint16_t at)
{
    text_mode();
    printf("divide error at %04X\n", at);
    exit(1);
}

static void on_break(int sig)
{
    (void)sig;
    outportb(0x61, inportb(0x61) & 0xFC);
    text_mode();
    exit(1);
}

int main(int argc, char **argv)
{
    signal(SIGINT, on_break);
    uclock();
    test_init();
    cpu_reset();
#ifdef SKBVGA
    {
        int i;
        for (i = 1; i < argc; i++)
            if ((argv[i][0] == '/' || argv[i][0] == '-') && (argv[i][1] == 'j' || argv[i][1] == 'J'))
                use_joystick = 1;
    }
    if (!vga_load("SKBVGA.DAT")) {
        printf("SKBVGA.DAT not found\n");
        return 1;
    }
    vga_reset();
    vga_fast = 1;
#else
    (void)argc;
    (void)argv;
#endif
    skb_main();
    text_mode();
    return 0;
}
