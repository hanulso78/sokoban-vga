/* ============================================================================
 *  skbvga.c  -  개선판: 256색 그림자와 화면 합성 (도스 판과 PC 미리보기가 같이 쓴다)
 * ----------------------------------------------------------------------------
 *  게임 코드(skbcode.c)는 원판 그대로 CGA 메모리에 그린다.  개선판은 메모리 바이트마다
 *  그림자 색 COL[] (네 점의 256색 번호) 을 두고, 원판이 그림을 옮기는 대로 색도 따라
 *  가게 한다 (cpu.h: movs 는 색을 옮기고 보통 쓰기는 지운다).  색의 출처는
 *      - EXE 안의 그림(스프라이트, 타일, 글꼴)   : 시작할 때 SKBVGA.DAT 의 'I' 조각
 *      - 그림 파일(intro1, lobby11 ...)          : f_0020(그림 풀기) 이 끝날 때 'P' 조각
 *      - 자료 파일(icon_dat, lobby_dat, elev.bin): 파일을 읽은 뒤 'F' 조각
 *  마스크 스프라이트(f_4b61, f_4ba5)는 점마다 AND/OR 를 하므로 갈고리에서 색을 계산한다.
 *  화면은 B800 의 CGA 값과 색으로 만든다: 색이 없는 점은 지금 장면의 기본 색(테마).
 *
 *  SKBVGA.DAT (tools/mkvga.py 가 만든다)
 *      0..7   "SKBVGA1" + 0
 *      8..775 팔레트 256 x RGB (0..63)
 *      776..  조각들: 종류 1바이트, 이름 12바이트, 값 4바이트, 길이 4바이트, 자료
 *          'P' 그림: 값 = 줄 수,  자료 = 320 x 줄 수 색 번호
 *          'F' 자료 파일: 자료 = 파일 바이트마다 네 점의 색 (길이 = 파일 길이 x 4)
 *          'I' EXE 이미지: 값 = 적재 이미지 안의 오프셋, 자료 = 바이트마다 네 점의 색
 *          'T' 장면 테마: 이름 = 장면, 자료 = CGA 값 4 x 색 번호, 그 뒤에 (있으면)
 *              바닥 무늬 16x12 와 판 바깥 무늬 16x12 (판 장면만)
 * ========================================================================== */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "cpu.h"
#include "skbvga.h"
#include "skbvars.h"

#define MAXCHUNK 256

typedef struct {
    char type;
    char name[13];
    uint32_t val, len;
    uint8_t *data;
} chunk_t;

uint8_t vga_pal[256][3];
static chunk_t chunks[MAXCHUNK];
static int nchunks;
static int loaded;

int vga_scene;                  /* 지금 장면 (SC_...) */
int vga_fast;                   /* 원판의 긴 기다림 줄이기 (도스 판만 켠다) */
uint32_t vga_ms;                /* 지금 시각 (밀리초, 도스 판이 넣는다; 0 이면 매끄럽게 하기 없음) */
char vga_picname[13];           /* 마지막으로 푼 그림 파일 이름 */

/* 기본 팔레트: 0..15 CGA 16색 (색이 없는 점의 마지막 기댈 곳) */
static const uint8_t cga16[16][3] = {
    {0, 0, 0}, {0, 0, 42}, {0, 42, 0}, {0, 42, 42}, {42, 0, 0}, {42, 0, 42}, {42, 21, 0}, {42, 42, 42},
    {21, 21, 21}, {21, 21, 63}, {21, 63, 21}, {21, 63, 63}, {63, 21, 21}, {63, 21, 63}, {63, 63, 21}, {63, 63, 63},
};

static chunk_t *find_chunk(char type, const char *name)
{
    int i;
    for (i = 0; i < nchunks; i++)
        if (chunks[i].type == type && !strcmp(chunks[i].name, name))
            return &chunks[i];
    return NULL;
}

int vga_load(const char *path)
{
    FILE *f = fopen(path, "rb");
    char magic[8];
    int i;

    for (i = 0; i < 16; i++)
        memcpy(vga_pal[i], cga16[i], 3);
    loaded = 1;
    if (!f)
        return 0;
    if (fread(magic, 1, 8, f) != 8 || memcmp(magic, "SKBVGA1", 8)) {
        fclose(f);
        return 0;
    }
    if (fread(vga_pal, 1, 768, f) != 768) {
        fclose(f);
        return 0;
    }
    while (nchunks < MAXCHUNK) {
        chunk_t *c = &chunks[nchunks];
        uint8_t h[21];
        if (fread(h, 1, 21, f) != 21)
            break;
        c->type = (char)h[0];
        memcpy(c->name, h + 1, 12);
        c->name[12] = 0;
        c->val = h[13] | h[14] << 8 | (uint32_t)h[15] << 16 | (uint32_t)h[16] << 24;
        c->len = h[17] | h[18] << 8 | (uint32_t)h[19] << 16 | (uint32_t)h[20] << 24;
        c->data = malloc(c->len ? c->len : 1);
        if (!c->data || fread(c->data, 1, c->len, f) != c->len)
            break;
        nchunks++;
    }
    fclose(f);
    return nchunks;
}

/* 네 점 색 -> COL 한 칸 */
static uint32_t pack4(const uint8_t *c)
{
    return (uint32_t)c[0] | (uint32_t)c[1] << 8 | (uint32_t)c[2] << 16 | (uint32_t)c[3] << 24;
}

/* 시작: EXE 이미지 안 그림들의 색 */
void vga_reset(void)
{
    int i;
    uint32_t base = (uint32_t)LOADSEG << 4, k;

    memset(COL, 0, sizeof(uint32_t) * MEMSIZE);
    for (i = 0; i < nchunks; i++) {
        chunk_t *c = &chunks[i];
        if (c->type != 'I')
            continue;
        for (k = 0; k < c->len / 4; k++)
            COL[base + c->val + k] = pack4(c->data + k * 4);
    }
    vga_scene = SC_TEXT;
}

/* 파일을 읽었다: 자료 파일이면 색을 붙인다 */
void vga_file_read(const char *name, uint32_t lin, uint32_t pos, uint32_t n)
{
    char nm[13];
    chunk_t *c;
    uint32_t k;
    int i;

    for (i = 0; i < 12 && name[i]; i++)
        nm[i] = (char)tolower((unsigned char)name[i]);
    nm[i] = 0;
    c = find_chunk('F', nm);
    if (!c)
        return;
    for (k = 0; k < n && (pos + k) * 4 + 3 < c->len; k++)
        COL[lin + k] = pack4(c->data + (pos + k) * 4);
}

/* ---- 장면 ------------------------------------------------------------------- */
static const struct {
    const char *prefix;
    int scene;
} pic_scene[] = {{"intro", SC_TITLE}, {"lobby", SC_LOBBY}, {"players", SC_PLAYERS}, {"select", SC_SELECT},
                 {"tour", SC_TOUR}, {"pause", SC_PAUSE}, {"icons", SC_ICONS},
                 {"elev", SC_ELEV}};

/* 그림을 풀었다: 그 그림으로 장면을 안다 */
static void picture_loaded(const char *name)
{
    unsigned i;

    for (i = 0; i < sizeof pic_scene / sizeof pic_scene[0]; i++)
        if (!strncmp(name, pic_scene[i].prefix, strlen(pic_scene[i].prefix)))
            vga_scene = pic_scene[i].scene;
}

/* ---- 음악: 장면마다 곡 --------------------------------------------------------- */
int vga_in_tune;

static int new_level;

int vga_music(void)
{
    static int win;
    if (vga_in_tune)
        win = 1;
    else if (new_level && win && vga_scene == SC_LEVEL && RB(DSEG, draw_to_bg) == 0)
        win = 0;
    new_level = 0;
    if (vga_scene == SC_LEVEL) {
        if (win)                        /* 승리 곡은 다음 판이 시작될 때까지 */
            return MUS_WIN;
        return MUS_PLAY;
    }
    win = 0;
    if (vga_scene == SC_TEXT || vga_scene == SC_PAUSE)
        return vga_scene == SC_PAUSE ? MUS_PLAY : MUS_NONE;
    return MUS_TITLE;
}

/* 판 안에서 F2 로 소리를 끄면 ([9B97]) 음악도 */
int music_muted(void)
{
    return RB(DSEG, sound_off) != 0;
}

/* ---- 갈고리 ------------------------------------------------------------------ */
static uint16_t h_es, h_di;
static char h_name[13];

/* 마스크 스프라이트: 들어갈 때 결과 색을 미리 계산해 두고 나갈 때 넣는다 */
#define MAXBLIT 8192
static uint32_t blit_at[MAXBLIT], blit_col[MAXBLIT];
static int nblit;
static const uint8_t *blit_remap;               /* 스프라이트 색 바꾸기 (0 = 그대로) */

/* 목표 칸 위의 상자를 밀면 원판은 움직이는 동안 보통 상자 그림을 쓴다 -> 초록 상자 색으로.
 *  보통 상자 타일과 목표 위 상자 타일의 같은 자리 색으로 바꿈표를 만든다. */
static const uint8_t *goal_box_remap(void)
{
    static uint8_t map[256];
    static int built;
    uint16_t box = RW(DSEG, tile_sprite_tab + 4), boxg = RW(DSEG, tile_sprite_tab + 8);
    int i, p;

    if (!built) {
        uint8_t set[256] = {0};
        for (i = 0; i < 256; i++)
            map[i] = (uint8_t)i;
        for (i = 0; i < 16 * 6; i++) {
            uint32_t a = COL[LIN(DSEG, (uint16_t)(box + 0x60 + i))], b = COL[LIN(DSEG, (uint16_t)(boxg + 0x60 + i))];
            for (p = 0; p < 4; p++) {
                uint8_t f = (uint8_t)(a >> (8 * p)), t = (uint8_t)(b >> (8 * p));
                if (f && t && !set[f]) {
                    map[f] = t;
                    set[f] = 1;
                }
            }
        }
        built = 1;
    }
    return map;
}

/* 지금 그리는 것이 밀려 가는 상자이고, 그 상자가 목표 칸에서 떠났는가 */
static int pushing_goal_box(uint16_t si)
{
    static const int dpos[4] = {1, -1, -19, 19};
    int k, fc = RB(DSEG, player_facing), org;

    if (vga_scene != SC_LEVEL || !RB(DSEG, pushing) || fc > 6 || (fc & 1))
        return 0;
    for (k = 0; k < 5 && si != RW(DSEG, spr_box_h + 2 * k); k++)
        ;
    if (k < 5 ? fc >= 4 : fc < 4 || si != RW(DSEG, tile_sprite_tab + 4) || RW(DSEG, spr_bytes) != 6 || RW(DSEG, spr_src_skip) != 0)
        return 0;                               /* 가로는 미끄러지는 그림, 세로는 통째 상자 타일 (이웃 칸 다시 그리기는 아님) */
    org = (int)RW(DSEG, player_pos) + dpos[fc / 2];
    return org >= 0 && org < 304 && RB(DSEG, (uint16_t)(level_map + org)) == 3;
}

static void masked_colors(uint16_t sseg, uint16_t si, uint16_t di, int rows, int w, int skip, int plane,
                          int interleaved)
{
    int r, x, half;
    nblit = 0;
    for (r = 0; r < rows; r++) {
        for (half = 0; half < (interleaved ? 2 : 1); half++) {
            for (x = 0; x < w; x++) {
                uint16_t ms = (uint16_t)(si + x), is = (uint16_t)(si + x + plane);
                uint32_t da = LIN(DSEG, di), ma = LIN(sseg, ms), ia = LIN(sseg, is);
                uint8_t m = M[ma], im = M[ia];
                uint32_t oc = COL[da], ic = COL[ia], nc = 0;
                int p;
                for (p = 0; p < 4; p++) {
                    int sh = 6 - 2 * p;
                    int mp = (m >> sh) & 3, ip = (im >> sh) & 3;
                    uint32_t c;
                    if (mp == 3 && ip == 0)
                        c = (oc >> (8 * p)) & 0xFF;
                    else {
                        c = (ic >> (8 * p)) & 0xFF;     /* 섞인 경우도 스프라이트 색 */
                        if (blit_remap)
                            c = blit_remap[c];
                    }
                    nc |= c << (8 * p);
                }
                if (nblit < MAXBLIT) {
                    blit_at[nblit] = da;
                    blit_col[nblit++] = nc;
                }
                di++;
            }
            si = (uint16_t)(si + (interleaved ? 2 * w : w));
        }
        if (!interleaved)
            si = (uint16_t)(si + skip);
        di = (uint16_t)(di + 80 - (interleaved ? 2 * w : w));
    }
}

void vga_enter(uint16_t fn)
{
    switch (fn) {
    case 0x0020: {                      /* 그림 풀기: ES:DI 에 푼다, 이름은 cs:[0] 먼 포인터 */
        uint16_t off = RW(CSEG, 0), seg = RW(CSEG, 2);
        int i;
        h_es = ES_;
        h_di = DI;
        for (i = 0; i < 12 && RB(seg, (uint16_t)(off + i)); i++)
            h_name[i] = (char)tolower(RB(seg, (uint16_t)(off + i)));
        h_name[i] = 0;
        break;
    }
    case 0x4B61:                        /* dst = (dst & [si]) | [si + plane] */
        blit_remap = DS_ == DSEG && pushing_goal_box(SI) ? goal_box_remap() : 0;
        masked_colors(DS_, SI, DI, RW(DSEG, spr_rows), RW(DSEG, spr_bytes), RW(DSEG, spr_src_skip), RW(DSEG, spr_plane_ofs), 0);
        blit_remap = 0;
        break;
    case 0x4BA5:                        /* 줄마다 M0 I0 M1 I1, 폭 w 씩 */
        masked_colors(DS_, SI, DI, RW(DSEG, spr_rows), RW(DSEG, spr_bytes), 0, RW(DSEG, spr_bytes), 1);
        break;
    case 0x4C10:                        /* 원판 승리 곡 (스피커) */
        vga_in_tune = 1;
        break;
    case 0x47D5:                        /* 판 그리기 (뒷화면에) -> 판 장면 */
        if (RB(DSEG, draw_to_bg) == 0)
            vga_scene = SC_LEVEL;
        new_level = 1;
        break;
    }
}

void vga_leave(uint16_t fn)
{
    int i;

    switch (fn) {
    case 0x0020: {
        chunk_t *c = find_chunk('P', h_name);
        uint32_t k, n;
        strcpy(vga_picname, h_name);
        n = c ? c->val * 80 : 0;         /* DI 는 되돌려져 있다: 그림 크기로 */
        picture_loaded(h_name);
        if (!c)
            break;
        for (k = 0; k < n && k * 4 + 3 < c->len; k++)
            COL[LIN(h_es, (uint16_t)(h_di + k))] = pack4(c->data + k * 4);
        break;
    }
    case 0x4C10:
        vga_in_tune = 0;
        break;
    case 0x4B61:
    case 0x4BA5:
        for (i = 0; i < nblit; i++)
            COL[blit_at[i]] = blit_col[i];
        break;
    }
}

/* ---- 화면 만들기 --------------------------------------------------------------
 *  B800 (CGA 모드 4, 두 뱅크) 의 값과 색으로 320x200 색 번호를 만든다.
 *  색이 없는 점: 장면 테마의 네 색 (없으면 CGA 밝은 팔레트 1).
 *  판 장면에서는 바닥(청록)을 판 안쪽이면 돌 타일 무늬, 바깥이면 어두운 무늬로. */
static const uint8_t pal1[4] = {0, 11, 13, 15};
static uint8_t lobby_bg(int x, int y);

/* 편집 단계 (편집기, 시험 플레이) 에서는 상태 줄이 없고 판(19x16 칸 = 304x192) 밖이 비어 있다:
 *  오른쪽과 아래를 강철 테두리로 (판에 닿는 쪽은 그림자, 그 다음 밝은 선) */
static int edit_frame;

/* 팔레트 (6비트 DAC 값) 에서 가장 가까운 색 */
static uint8_t pal_near(int r, int g, int b)
{
    int i, best = 0;
    long bd = 1L << 30;

    for (i = 0; i < 256; i++) {
        long dr = vga_pal[i][0] * 4 - r, dg = vga_pal[i][1] * 4 - g, db = vga_pal[i][2] * 4 - b;
        long dd = dr * dr * 3 + dg * dg * 4 + db * db * 2;
        if (dd < bd) {
            bd = dd;
            best = i;
        }
    }
    return (uint8_t)best;
}

static uint8_t frame_color(int x, int y)
{
    static uint8_t fc[5];
    static int ready;
    int d = x >= 304 ? x - 304 : 99, e = y >= 192 ? y - 192 : 99, k = d < e ? d : e;

    if (!ready) {
        fc[0] = pal_near(0x1c, 0x20, 0x28);     /* 판에 닿는 그림자 */
        fc[1] = pal_near(0xb0, 0xbc, 0xc8);     /* 밝은 모서리 */
        fc[2] = pal_near(0x3a, 0x44, 0x50);     /* 바깥 끝 */
        fc[3] = pal_near(0x7a, 0x8a, 0x9a);     /* 강철 */
        fc[4] = pal_near(0x5e, 0x6c, 0x7a);     /* 리벳 그늘 */
        ready = 1;
    }
    if (k == 0)
        return fc[0];
    if (k == 1)
        return fc[1];
    if (x == 319 || y == 199)
        return fc[2];
    if (d < 99 && d >= 6 && d <= 9 && (y % 24) >= 10 && (y % 24) <= 12)
        return fc[4];                            /* 오른쪽 띠의 리벳 */
    return fc[3];
}

/* 판 안쪽 칸: 사람 자리에서 벽이 아닌 칸으로 번지기 */
static uint8_t inside[16][19];

static void compute_inside(void)
{
    static const int dr[4] = {-1, 1, 0, 0}, dk[4] = {0, 0, -1, 1};
    static uint16_t q[304];
    int head = 0, tail = 0, pos = RW(DSEG, player_pos), d;
    const uint8_t *map = M + LIN(DSEG, level_map);

    memset(inside, 0, sizeof inside);
    if (pos >= 304)
        return;
    inside[pos / 19][pos % 19] = 1;
    q[tail++] = (uint16_t)pos;
    while (head < tail) {
        int c = q[head++], r = c / 19, k = c % 19;
        for (d = 0; d < 4; d++) {
            int nr = r + dr[d], nk = k + dk[d];
            if (nr < 0 || nr >= 16 || nk < 0 || nk >= 19 || inside[nr][nk] || map[nr * 19 + nk] == 1)
                continue;
            inside[nr][nk] = 1;
            q[tail++] = (uint16_t)(nr * 19 + nk);
        }
    }
}

/* ---- 로비 엘리베이터 문을 매끄럽게 ----------------------------------------------
 *  원판은 문을 네 단계로만 그린다: 닫힘, 틈 9점, 틈 26점, 다 열림 (단계마다 4틱).
 *  화면의 문 맨 위 흰 띠(안쪽 그림의 흰 줄, 사람 머리보다 위)에서 흰 점 수로 지금 단계의
 *  틈을 재고 (0, 8, 24, 44=다 열림), 보여 주는 틈은 단계가 바뀔 때마다 지금 값에서 새 단계까지
 *  한 단계 시간 동안 고르게 움직인다.  문짝은 로비 그림의
 *  닫힌 문을 옆으로 밀어서, 틈으로는 엘리베이터 안쪽 그림(2703:2790)을 그린다.
 *  사람(로비 사람 색)인 점은 건드리지 않는다. */
static uint8_t man_color[256], door_ready;
static uint8_t door_closed[71][64], door_inside[71][64];
static int door_x0 = -1, door_y0;
static int door_gap_shown = -1;                 /* 보여 주는 틈 (점 x 16) */
static uint32_t door_last_ms, door_t0;
static int door_from, door_to;
static int door_bg_g = -1;                      /* 이번 화면에 보이는 문 틈 (점, -1 = 문 없음) */
static uint8_t man_snap[71][64];                /* 문이 다 열렸을 때 안쪽 사람 (0 = 없음) */

static void door_prepare(int x0, int y0)
{
    chunk_t *a = find_chunk('P', "lobby11"), *b = find_chunk('P', "lobby12"), *e = find_chunk('I', "exe2703");
    chunk_t *ld = find_chunk('F', "lobby_dat");
    int x, y;
    uint32_t k;

    memset(man_color, 0, sizeof man_color);
    if (!a || !b || !e)
        return;
    for (y = 0; y < 71; y++)
        for (x = 0; x < 64; x++) {
            int yy = y0 + y, xx = x0 + x;
            chunk_t *c = yy < 100 ? a : b;
            int ry = yy < 100 ? yy : yy - 100;
            door_closed[y][x] = c->data[ry * 320 + xx];
            door_inside[y][x] = e->data[(0x2790 + y * 16 + x / 4) * 4 + (x & 3)];
        }
    /* 사람 색: 로비 사람 프레임 (2703:0030..2790, 3DC0..) 과 lobby_dat */
    for (k = 0x30 * 4; k < 0x2790 * 4 && k < e->len; k++)
        man_color[e->data[k]] = 1;
    for (k = 0x3DC0 * 4; k < e->len; k++)
        man_color[e->data[k]] = 1;
    if (ld)
        for (k = 0; k < ld->len; k++)
            man_color[ld->data[k]] = 1;
    /* 문 색은 사람 색에서 뺀다 */
    for (y = 0; y < 71; y++)
        for (x = 0; x < 64; x++) {
            man_color[door_closed[y][x]] = 0;
            man_color[door_inside[y][x]] = 0;
        }
    door_x0 = x0;
    door_y0 = y0;
    door_ready = 1;
}

static void door_smooth(uint8_t *out)
{
    int off = (int)RW(DSEG, door_addr) - backbuf, x0, y0, x, y, k, whites = 0, gap, g, shown, front;
    uint32_t row;

    door_bg_g = -1;
    if (vga_scene != SC_LOBBY || !vga_ms || off < 0 || off >= 16000)
        return;
    y0 = off / 80;
    x0 = (off % 80) * 4;
    if (y0 + 71 > 200 || x0 + 64 > 320)
        return;
    if (!door_ready || door_x0 != x0 || door_y0 != y0)
        door_prepare(x0, y0);
    if (!door_ready)
        return;
    /* 지금 움직이지 않는 다른 엘리베이터 문 (EDIT x 104 / PLAY x 184, y 70) 은 늘 닫혀 있다:
     *  원판이 문짝 그림으로 다시 그린 자리도 로비 그림의 문 색으로 (두 문이 같아 보이게) */
    for (k = 0; k < 2; k++) {
        int ox = k ? 184 : 104;
        if (ox == x0 || y0 != 70)
            continue;
        for (y = 0; y < 71; y++)
            for (x = 0; x < 64; x++) {
                uint8_t *o = out + (70 + y) * 320 + ox + x;
                if (!man_color[*o])
                    *o = lobby_bg(ox + x, 70 + y);
            }
    }
    /* 지금 단계: 문 맨 위 흰 띠 (안쪽 그림의 2번째 줄) 의 흰 점 수 */
    row = 0xB8000 + ((y0 + 2) & 1) * 0x2000 + ((y0 + 2) >> 1) * 80;
    for (x = 0; x < 64; x++) {
        uint8_t b = M[row + (x0 + x) / 4];
        if (((b >> (6 - 2 * ((x0 + x) & 3))) & 3) == 3)
            whites++;
    }
    gap = whites >= 40 ? 64 : whites;           /* 다 열리면 안쪽의 흰 띠가 거의 다 (44점) */
    /* 단계가 바뀌면: 지금 보이는 틈에서 새 단계까지 한 단계 시간(4틱 = 220ms) 동안 고르게 */
    if (door_gap_shown < 0 || vga_ms - door_last_ms > 1000) {
        door_from = door_to = gap * 16;
        door_t0 = vga_ms;
    } else if (gap * 16 != door_to) {
        door_from = door_gap_shown;
        door_to = gap * 16;
        door_t0 = vga_ms;
    }
    {
        uint32_t dt = vga_ms - door_t0;
        door_gap_shown = dt >= 220 ? door_to : door_from + (door_to - door_from) * (int)dt / 220;
    }
    door_last_ms = vga_ms;
    shown = door_gap_shown / 16;
    if (gap == 64) {                            /* 다 열림: 안쪽 사람을 찍어 둔다 */
        for (y = 0; y < 71; y++)
            for (x = 0; x < 64; x++) {
                uint8_t c = out[(y0 + y) * 320 + x0 + x];
                man_snap[y][x] = man_color[c] ? c : 0;
            }
    } else if (gap == 0)
        memset(man_snap, 0, sizeof man_snap);
    door_bg_g = shown;
    if (shown == gap && gap == 64)
        return;                                 /* 다 열려 멈춰 있다: 원판 그림 그대로 */
    if (shown == gap && gap == 0) {
        /* 닫혀 멈춰 있다: 원판은 문짝 그림과 뒷화면(로비 그림)을 섞어 다시 그리므로 색이 조각난다.
         *  사람이 아닌 점은 로비 그림의 닫힌 문으로 */
        for (y = 0; y < 71; y++)
            for (x = 0; x < 64; x++) {
                uint8_t *o = out + (y0 + y) * 320 + x0 + x;
                if (!man_color[*o])
                    *o = door_closed[y][x];
            }
        return;
    }
    g = shown;
    /* 사람이 문 앞인가: 문 바로 아래 줄들에 사람 색이 있으면 (발이 바닥에) */
    front = 0;
    for (y = 71; y < 82 && y0 + y < 200 && !front; y++)
        for (x = 0; x < 64; x++)
            if (man_color[out[(y0 + y) * 320 + x0 + x]]) {
                front = 1;
                break;
            }
    for (y = 0; y < 71; y++) {
        uint8_t *o = out + (y0 + y) * 320 + x0;
        for (x = 0; x < 64; x++) {
            int panel = x < 32 - g / 2 || x >= 32 + (g + 1) / 2;
            uint8_t c;
            if (man_color[o[x]] && (front || !panel))
                continue;                       /* 앞에 선 사람, 틈으로 보이는 안쪽 사람 */
            if (x < 32 - g / 2)
                c = door_closed[y][x + g / 2];  /* 왼쪽 문짝: 왼쪽으로 밀렸다 */
            else if (x >= 32 + (g + 1) / 2)
                c = door_closed[y][x - (g + 1) / 2];
            else if (!front && man_snap[y][x])
                c = man_snap[y][x];             /* 원판은 이미 문짝으로 가렸지만 틈으로 보일 사람 */
            else
                c = door_inside[y][x];
            o[x] = c;
        }
    }
}

/* ---- 로비에서 걷는 사람을 매끄럽게 --------------------------------------------------
 *  원판은 2틱(110ms)마다 8점씩 옮긴다.  사람 자리([0x258], 48x60)가 옆으로 바뀌면, 지난
 *  자리에서 새 자리까지 그 시간 동안 사람 그림을 조금씩 밀어 그린다 (한 걸음 늦게 따라감).
 *  사람 점은 로비 그림과 다른 점으로 가려내고, 사람이 비운 자리는 로비 그림으로 채운다. */
static int man_x = -1, man_y, man_px, man_py;
static uint32_t man_t0;

static uint8_t lobby_bg(int x, int y)
{
    chunk_t *c = find_chunk('P', y < 100 ? "lobby11" : "lobby12");
    if (!c)
        return 0;
    return c->data[(y < 100 ? y : y - 100) * 320 + x];
}

/* 사람 뒤 배경: 문 자리면 지금 보이는 문 (틈 door_bg_g), 아니면 로비 그림 */
static uint8_t man_bg(int x, int y)
{
    int dx = x - door_x0, dy = y - door_y0, g = door_bg_g;

    if (door_ready && g >= 0 && dx >= 0 && dx < 64 && dy >= 0 && dy < 71) {
        if (dx < 32 - g / 2)
            return door_closed[dy][dx + g / 2];
        if (dx >= 32 + (g + 1) / 2)
            return door_closed[dy][dx - (g + 1) / 2];
        return door_inside[dy][dx];
    }
    return lobby_bg(x, y);
}

static void man_smooth(uint8_t *out)
{
    static uint8_t man[60][80];
    int off = (int)RW(DSEG, spr_dest) - backbuf, x, y, mx, my, sh, bx0, bx1;
    uint32_t dt;

    if (vga_scene != SC_LOBBY || !vga_ms || !door_ready || off < 0 || off >= 16000)
        return;
    mx = (off % 80) * 4;
    my = off / 80;
    if (man_x < 0 || vga_ms - man_t0 > 1000 || my != man_y) {
        man_px = man_x = mx;
        man_py = man_y = my;
        man_t0 = vga_ms;
    } else if (mx != man_x) {                   /* 옆으로 한 걸음: 지금 보이는 자리에서 새 자리로 */
        dt = vga_ms - man_t0;
        man_px = dt >= 110 ? man_x : man_px + (man_x - man_px) * (int)dt / 110;
        man_x = mx;
        man_t0 = vga_ms;
    }
    dt = vga_ms - man_t0;
    if (dt >= 110 || man_px == man_x || my + 60 > 200)
        return;
    sh = (man_px + (man_x - man_px) * (int)dt / 110) - man_x;    /* 그릴 자리 - 실제 자리 */
    if (sh == 0 || sh < -24 || sh > 24)
        return;
    /* 사람 점 떼어 내기 (실제 자리의 48x60) */
    for (y = 0; y < 60; y++)
        for (x = 0; x < 48; x++) {
            int xx = mx + x;
            uint8_t c = xx < 320 ? out[(my + y) * 320 + xx] : 0;
            man[y][x] = (xx < 320 && c != man_bg(xx, my + y)) ? c : 0;
        }
    /* 실제 자리의 사람 점은 배경으로 지우고, 밀린 자리에 다시 */
    bx0 = mx + (sh < 0 ? sh : 0);
    bx1 = mx + 48 + (sh > 0 ? sh : 0);
    for (y = 0; y < 60; y++)
        for (x = 0; x < 48; x++)
            if (man[y][x] && mx + x < 320)
                out[(my + y) * 320 + mx + x] = man_bg(mx + x, my + y);
    for (y = 0; y < 60; y++)
        for (x = 0; x < 48; x++) {
            int xx = mx + x + sh;
            if (man[y][x] && xx >= 0 && xx < 320)
                out[(my + y) * 320 + xx] = man[y][x];
        }
    (void)bx0;
    (void)bx1;
}

void vga_render(uint8_t *out)
{
    const uint8_t *theme = pal1, *floor_tex = NULL, *out_tex = NULL;
    chunk_t *t;
    uint8_t *o = out;
    int x, y;
    static const char *const scene_name[] = {"text", "title", "lobby", "players", "level", "editor", "select",
                                             "tour", "pause", "icons", "elev"};

    if (vga_scene >= 0 && vga_scene < (int)(sizeof scene_name / sizeof scene_name[0])) {
        t = find_chunk('T', scene_name[vga_scene]);
        if (t && t->len >= 4)
            theme = t->data;
        if (t && t->len >= 4 + 2 * 192) {
            floor_tex = t->data + 4;
            out_tex = t->data + 4 + 192;
        }
    }
    if (vga_scene == SC_LEVEL && floor_tex)
        compute_inside();
    edit_frame = vga_scene == SC_LEVEL && RB(DSEG, custom_level) != 0;
    for (y = 0; y < 200; y++) {
        uint32_t row = 0xB8000 + (y & 1) * 0x2000 + (y >> 1) * 80;
        int cr = y / 12;
        for (x = 0; x < 80; x++) {
            uint8_t b = M[row + x];
            uint32_t c = COL[row + x];
            int p;
            for (p = 0; p < 4; p++) {
                uint8_t cc = (uint8_t)(c >> (8 * p));
                int v = (b >> (6 - 2 * p)) & 3;
                if (!cc && vga_scene == SC_LOBBY && v == 1) {
                    cc = lobby_bg(x * 4 + p, y);    /* 닫힌 문: 로비 그림의 문 */
                    if (!cc)
                        cc = theme[v];
                } else if (!cc) {
                    int px = x * 4 + p;
                    if (edit_frame && v == 1 && (px >= 304 || y >= 192))
                        cc = frame_color(px, y);    /* 편집 단계: 판 밖 (오른쪽, 아래) 은 강철 테두리 */
                    else if (floor_tex && v == 1 && cr < 16 && px < 304)
                        cc = (inside[cr][px >> 4] ? floor_tex : out_tex)[(y % 12) * 16 + (px & 15)];
                    else if (floor_tex && v == 1 && y < 190)
                        cc = out_tex[(y % 12) * 16 + (px & 15)];
                    else
                        cc = theme[v];
                }
                *o++ = cc;
            }
        }
    }
    door_smooth(out);
    man_smooth(out);
}
