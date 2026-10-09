/* ============================================================================
 *  cpu.c  -  8086 상태와 메모리, 원본 적재 (DOS 판과 PC 시험판이 같이 쓴다)
 * ========================================================================== */
#include <string.h>
#include "cpu.h"

uint8_t M[MEMSIZE];
#ifdef SKBVGA
uint32_t COL[MEMSIZE];
#endif
reg16_t cpu_a, cpu_b, cpu_c, cpu_d;
uint16_t SI, DI, BP, SP, CS_, DS_, ES_, SS_;
int CF, ZF, SF, OF;

/* tools/emu.py 의 Machine.__init__ 과 같은 모양으로 메모리를 채운다 */
void cpu_reset(void)
{
    unsigned n;
    uint32_t psp = (uint32_t)(LOADSEG - 0x10) << 4;

    memset(M, 0, sizeof(M));
    memcpy(M + ((uint32_t)LOADSEG << 4), skb_image, skb_image_size);
    M[psp] = 0xCD;
    M[psp + 1] = 0x20;
    M[psp + 2] = 0x00;
    M[psp + 3] = 0xA0;
    M[psp + 0x80] = 0;
    M[psp + 0x81] = 0x0D;
    /* 인터럽트 벡터 -> F000:n*4 ("int n; iret") */
    for (n = 0; n < 256; n++) {
        M[n * 4] = (uint8_t)(n * 4);
        M[n * 4 + 1] = (uint8_t)((n * 4) >> 8);
        M[n * 4 + 2] = 0x00;
        M[n * 4 + 3] = 0xF0;
        M[0xF0000 + n * 4] = 0xCD;
        M[0xF0000 + n * 4 + 1] = (uint8_t)n;
        M[0xF0000 + n * 4 + 2] = 0xCF;
        M[0xF0000 + n * 4 + 3] = 0x90;
    }
    /* BIOS 자료: 자판 버퍼 머리/꼬리, 메모리 크기, 기계 종류 (AT) */
    M[0x41A] = 0x1E;
    M[0x41C] = 0x1E;
    M[0x413] = 0x80;
    M[0x414] = 0x02;
    M[0xFFFFE] = 0xFC;

    AX = BX = CX = DX = SI = DI = BP = 0;
    CS_ = CSEG;
    SS_ = SSEG;
    SP = 0x00C8;
    DS_ = ES_ = LOADSEG - 0x10;
    CF = ZF = SF = OF = 0;
}
