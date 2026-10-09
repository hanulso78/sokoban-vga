/* ============================================================================
 *  cpu.h  -  옮긴 코드(skbcode.c)가 쓰는 8086 상태와 메모리
 * ----------------------------------------------------------------------------
 *  원본은 손으로 짠 어셈블리라 레지스터로 값을 주고받고 세그먼트를 수시로 바꾼다.
 *  그래서 옮긴 C 도 레지스터를 전역 변수로 두고, 메모리는 실모드 주소 그대로인
 *  평면 배열 M[] (1MB + 64KB) 로 둔다.  세그먼트:오프셋 계산, 16비트 넘침, 스택
 *  내용까지 원본과 같아서 에뮬레이터(tools/emu.py)와 메모리를 통째로 대조할 수 있다.
 *
 *  원본의 적재 세그먼트는 LOADSEG (PSP 는 그 앞 10h).  SEG(x) 는 원본 EXE 안의
 *  세그먼트 값 x 를 실제 세그먼트로 바꾼다 (재배치).
 * ========================================================================== */
#ifndef CPU_H
#define CPU_H

#include <stdint.h>

#define LOADSEG 0x1000
#define SEG(x) ((uint16_t)(LOADSEG + (x)))
#define MEMSIZE 0x110000

/* 원본의 세그먼트들 */
#define CSEG SEG(0x0000)        /* 코드 (앞 0A8Ch 는 자료) */
#define SSEG SEG(0x0A2C)        /* 스택 (200 바이트) */
#define DSEG SEG(0x0A39)        /* 자료: 변수, 문자열, 화면 버퍼 둘, 그림 */
#define GSEG1 SEG(0x180C)       /* 그림 */
#define GSEG2 SEG(0x2703)       /* 그림 (로비 사람) */
#define GSEG3 SEG(0x2CA1)
#define GSEG4 SEG(0x2CEC)

extern uint8_t M[MEMSIZE];

typedef union {
    uint16_t x;
    struct {
        uint8_t l, h;
    } b;
} reg16_t;

extern reg16_t cpu_a, cpu_b, cpu_c, cpu_d;
extern uint16_t SI, DI, BP, SP, CS_, DS_, ES_, SS_;
extern int CF, ZF, SF, OF;

#define AX cpu_a.x
#define AL cpu_a.b.l
#define AH cpu_a.b.h
#define BX cpu_b.x
#define BL cpu_b.b.l
#define BH cpu_b.b.h
#define CX cpu_c.x
#define CL cpu_c.b.l
#define CH cpu_c.b.h
#define DX cpu_d.x
#define DL cpu_d.b.l
#define DH cpu_d.b.h

#define LIN(s, o) (((uint32_t)(uint16_t)(s) << 4) + (uint16_t)(o))

/* 개선판(SKBVGA)은 메모리 바이트마다 그림자 색 COL[] 을 둔다: 바이트의 네 점(2비트씩,
 * 위 비트가 왼쪽)마다 256색 번호 하나씩, 0 은 "색 없음"(원래 CGA 값으로 칠한다).
 * 보통 쓰기(WB/WW)는 색을 지우고, 문자열 복사(movs)는 색도 같이 옮긴다.  그림 불러오기와
 * 마스크 스프라이트는 skbvga.c 의 갈고리가 색을 계산한다. */
#ifdef SKBVGA
extern uint32_t COL[MEMSIZE];
#define COL_CLR(a) (COL[a] = 0)
#define COL_CPY(d, s) (COL[d] = COL[s])
#else
#define COL_CLR(a) ((void)0)
#define COL_CPY(d, s) ((void)0)
#endif

static inline uint8_t RB(uint16_t s, uint16_t o)
{
    return M[LIN(s, o)];
}

static inline uint16_t RW(uint16_t s, uint16_t o)
{
    return (uint16_t)(M[LIN(s, o)] | (M[LIN(s, (uint16_t)(o + 1))] << 8));
}

static inline void WB(uint16_t s, uint16_t o, uint8_t v)
{
    uint32_t a = LIN(s, o);
    M[a] = v;
    COL_CLR(a);
}

static inline void WW(uint16_t s, uint16_t o, uint16_t v)
{
    uint32_t a = LIN(s, o), b = LIN(s, (uint16_t)(o + 1));
    M[a] = (uint8_t)v;
    M[b] = (uint8_t)(v >> 8);
    COL_CLR(a);
    COL_CLR(b);
}

static inline void PUSH(uint16_t v)
{
    SP -= 2;
    WW(SS_, SP, v);
}

static inline uint16_t POP(void)
{
    uint16_t v = RW(SS_, SP);
    SP += 2;
    return v;
}

/* 한 바이트 복사 (movs): 색도 같이 */
static inline void CPB(uint16_t ds, uint16_t so, uint16_t es, uint16_t eo)
{
    uint32_t d = LIN(es, eo), a = LIN(ds, so);
    M[d] = M[a];
    COL_CPY(d, a);
}

static inline void MOVSB(uint16_t sseg)
{
    CPB(sseg, SI, ES_, DI);
    SI++;
    DI++;
}

static inline void MOVSW(uint16_t sseg)
{
    CPB(sseg, SI, ES_, DI);
    CPB(sseg, (uint16_t)(SI + 1), ES_, (uint16_t)(DI + 1));
    SI += 2;
    DI += 2;
}

/* rep 문자열 명령 (방향 플래그는 늘 0) */
static inline void rep_movsb(uint16_t sseg)
{
    while (CX) {
        MOVSB(sseg);
        CX--;
    }
}

static inline void rep_movsw(uint16_t sseg)
{
    while (CX) {
        MOVSW(sseg);
        CX--;
    }
}

static inline void rep_stosb(void)
{
    while (CX) {
        WB(ES_, DI, AL);
        DI++;
        CX--;
    }
}

static inline void rep_stosw(void)
{
    while (CX) {
        WW(ES_, DI, AX);
        DI += 2;
        CX--;
    }
}

/* ---- 개선판 갈고리 (skbvga.c): 원본 동작은 그대로 두고 256색 그림자만 다룬다 ---- */
#ifdef SKBVGA
void vga_enter(uint16_t fn);
void vga_leave(uint16_t fn);
#define VGA_ENTER(fn) vga_enter(fn)
#define VGA_LEAVE(fn) vga_leave(fn)
extern int vga_fast;                /* 도스 개선판: 원판의 긴 기다림을 줄인다 */
#define VGA_FAST(stmt) if (vga_fast) { stmt }
#else
#define VGA_FAST(stmt)
#define VGA_ENTER(fn)
#define VGA_LEAVE(fn)
#endif

/* ---- 플랫폼 (sys_dos.c / tools/hosttest.c) ---- */
void int10(void);
void int12(void);
void int13(void);
void int16(void);
void int1a(void);
void int21(void);
uint8_t port_in(uint16_t port);
void port_out(uint16_t port, uint8_t v);
void delay_loop(uint16_t n);        /* 8088 의 "loop $" n 번만큼 시간 끌기 */
void kbd_flush_hook(void);          /* 게임이 BIOS 자판 버퍼를 비웠다 */
void far_return(void);              /* 주 프로그램 끝 (retf) */
void div_error(uint16_t at);

void cpu_reset(void);               /* 적재: M[] 를 채우고 레지스터를 시작 값으로 */
extern const uint8_t skb_image[];   /* skbdata.c: 적재 이미지 (tools/mkdata.py) */
extern const unsigned skb_image_size;

#endif
