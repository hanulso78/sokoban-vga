/* skbvga.h  -  개선판 256색 그림자와 화면 합성 */
#ifndef SKBVGA_H
#define SKBVGA_H
#include <stdint.h>

enum { SC_TEXT, SC_TITLE, SC_LOBBY, SC_PLAYERS, SC_LEVEL, SC_EDITOR, SC_SELECT, SC_TOUR, SC_PAUSE, SC_ICONS, SC_ELEV };

extern uint8_t vga_pal[256][3];
extern int vga_scene;
extern char vga_picname[13];

int vga_load(const char *path);         /* SKBVGA.DAT */
void vga_reset(void);                   /* cpu_reset 뒤에: EXE 그림 색 */
void vga_file_read(const char *name, uint32_t lin, uint32_t pos, uint32_t n);
void vga_render(uint8_t *out);          /* 320x200 색 번호 */
int vga_music(void);                    /* 지금 장면에 맞는 곡 (MUS_...) */
extern int vga_in_tune;
extern uint32_t vga_ms;                 /* 도스 판: 지금 시각 (밀리초) */                 /* 원판 승리 곡(스피커)을 연주하는 중 */

/* skbopl.c - 애드립 배경음악 */
enum { MUS_NONE, MUS_TITLE, MUS_PLAY, MUS_WIN, MUS_COUNT };
void music_want(int which);
void music_poll(void);
void music_off(void);
int music_muted(void);
int music_found(void);

#endif
