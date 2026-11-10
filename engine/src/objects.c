// SPDX-License-Identifier: MIT
// Hollowmere object renderer driver (Thumb, ROM): culls props and sprites,
// sorts them far to near and hands each one to the IWRAM renderer.
#include "engine.h"
#include "assets.h"
#include "render.h"
#include "objects.h"
#include "dev.h"

EWRAM_BSS PropInst g_props[MAX_PROPS];
int g_numProps;
EWRAM_BSS PropInst g_dynProps[MAX_DYNPROPS];
int g_numDynProps;

#define NEAR     0x1800
#define FARCULL  (12 << 16)

typedef struct { s32 depth, r; s16 idx; u8 kind, pad; } DrawItem;
extern s32 g_zmax8[VIEW_W / 8];
#define s_zmax8 g_zmax8
EWRAM_BSS static DrawItem s_items[MAX_PROPS + MAX_DYNPROPS + MAX_SPRITES];

#ifdef DEV
u32 g_frozenLog;
extern u32 g_objStats[4], g_objT[4], g_objPix[2], g_objF[6], g_objG[4], g_objPub[20], g_pixCount[3];
#endif

// (a * q) >> 14 for a 16.16 value a (|a| < 128 tiles) and a Q14 factor q,
// in 32-bit arithmetic (Thumb has no long multiply)
static inline s32 mulq14(s32 a, s32 q) {
    s32 hi = a >> 16, lo = a & 0xFFFF;
    return ((hi * q) << 2) + ((lo * q) >> 14);
}

// ---------------------------------------------------------------- driver
static int prop_visible(const PropInst *pi, s32 *pf, s32 *pr) {
    const Model *m = &models[pi->model];
    s32 dx = pi->x - g_cam.x, dy = pi->y - g_cam.y;
    s32 rad = (s32)m->radius << 8;
    s32 lim = FARCULL + rad;
    if (dx > lim || dx < -lim || dy > lim || dy < -lim) return 0;
    s32 f = mulq14(dx, g_cam.dirX) + mulq14(dy, g_cam.dirY);
    s32 r = mulq14(dy, g_cam.dirX) - mulq14(dx, g_cam.dirY);
    if (f + rad < NEAR || f - rad > FARCULL) return 0;
    s32 ar = r < 0 ? -r : r;
    if (ar > ((f * 3) >> 2) + rad + (rad >> 1)) return 0;
    // hidden behind walls in every column it could cover?
    s32 fn = f - rad;
    if (fn > NEAR) {
        s32 w = (s32)rcp16((u32)fn);
        // columns of the bounding circle: r/f * COLK, with w = 1/f in 16.16
        // (in 64 bits: a big prop just beyond its radius, the hall stair
        // seen from three tiles, overflows 32 and was culled outright)
        s64 kw = (s64)(w >> 6) * COLK;
        s64 xl = ((s64)((r - rad) >> 6) * kw) >> 20, xr = ((s64)((r + rad) >> 6) * kw) >> 20;
        int cl = xl < -VIEW_W ? -VIEW_W : xl > VIEW_W ? VIEW_W : VIEW_CX + (int)xl;
        int cr = xr < -VIEW_W ? -VIEW_W : xr > VIEW_W ? VIEW_W : VIEW_CX + (int)xr + 1;
        if (cl < 0) cl = 0;
        if (cr > VIEW_W - 1) cr = VIEW_W - 1;
        // the farthest wall in each block of 8 columns tells quickly whether
        // any column of the prop can show
        int vis = 0;
        for (int b = cl >> 3; b <= cr >> 3; b++) if (s_zmax8[b] > fn) { vis = 1; break; }
        if (!vis) return 0;
    }
    *pf = f; *pr = r;
    return 1;
}

void draw_objects(u8 *fb) {
    int n = 0;
#ifdef DEV
    { extern u32 g_nflog; if (!g_frozenLog) g_nflog = 0; }
    g_objStats[0] = g_objStats[1] = g_objStats[2] = g_objStats[3] = 0;
    g_objT[0] = g_objT[1] = g_objT[2] = g_objT[3] = 0; g_objPix[0] = g_objPix[1] = 0; for (int q = 0; q < 6; q++) g_objF[q] = 0; for (int q = 0; q < 4; q++) g_objG[q] = 0;
    u32 t0 = PROF_T();
#endif
    for (int i = 0; i < g_numProps + g_numDynProps; i++) {
        const PropInst *pi = i < g_numProps ? &g_props[i] : &g_dynProps[i - g_numProps];
        if (pi->flags & PIF_HIDDEN) continue;
        s32 f, r;
        if (!prop_visible(pi, &f, &r)) continue;
        DrawItem *it = &s_items[n++];
        it->depth = f; it->r = r; it->idx = i; it->kind = 0;
    }
    for (int i = 0; i < g_numSprites; i++) {
        RSprite *s = &g_sprites[i];
        if (s->flags & SPR_HIDDEN) continue;
        s32 dx = s->x - g_cam.x, dy = s->y - g_cam.y;
        if (dx > FARCULL || dx < -FARCULL || dy > FARCULL || dy < -FARCULL) continue;
        s32 depth = mulq14(dx, g_cam.dirX) + mulq14(dy, g_cam.dirY);
        if (depth < 0x2000 || depth > FARCULL) continue;
        s32 lat = mulq14(dy, g_cam.dirX) - mulq14(dx, g_cam.dirY);
        s32 alat = lat < 0 ? -lat : lat;
        if (alat > ((depth * 3) >> 2) + (s->worldW << 8)) continue;
        s->dist = depth;
        DrawItem *it = &s_items[n++];
        it->depth = depth; it->idx = i; it->kind = 2;
    }
    DEV_ONLY(g_objT[2] = PROF_T() - t0;)
    // far to near
    for (int i = 1; i < n; i++) {
        DrawItem t = s_items[i];
        int j = i;
        while (j > 0 && s_items[j - 1].depth < t.depth) { s_items[j] = s_items[j - 1]; j--; }
        s_items[j] = t;
    }
    for (int i = 0; i < n; i++) {
        DrawItem *it = &s_items[i];
        if (it->kind == 2) draw_sprite(fb, &g_sprites[it->idx]);
        else {
            int k = it->idx;
            const PropInst *pi = k < g_numProps ? &g_props[k] : &g_dynProps[k - g_numProps];
            draw_prop(fb, pi, it->depth, it->r);
        }
    }
#ifdef DEV
    g_objStats[3] = PROF_T() - t0;
    u32 *o = g_objPub;
    o[0] = g_objStats[3]; o[1] = g_objStats[0]; o[2] = g_objStats[1]; o[3] = g_objStats[2];
    o[4] = g_objT[0]; o[5] = g_objT[1]; o[6] = g_objT[2]; o[7] = g_objT[3];
    o[8] = g_objF[0]; o[9] = g_objF[1]; o[10] = g_objF[2]; o[11] = g_objF[3]; o[12] = g_objF[4]; o[13] = g_objF[5];
    o[17] = g_objG[0]; o[18] = g_objG[1]; o[19] = g_objG[2]; o[13] = g_objG[3] << 24 | (o[13] & 0xFFFFFF);
    o[14] = g_pixCount[0]; o[15] = g_pixCount[1]; o[16] = g_pixCount[2];
    g_pixCount[0] = g_pixCount[1] = g_pixCount[2] = 0;
#endif
}

// ---------------------------------------------------------------- occluders
// Before the world is drawn: mark, per column, the rows that a big opaque
// prop face will paint over anyway, so the wall behind it is not drawn
// (the faces themselves in occ_face, IWRAM).
extern s16 g_covT[VIEW_W], g_covB[VIEW_W];
extern s32 g_covF[VIEW_W];
extern void occ_face(const PropInst *pi, const MFace *fc, const MVert *mv, s32 f0, s32 r0, s32 ca, s32 sa, s32 hb);
extern u32 g_lodScale;
static const Model *model_lod(const Model *m, s32 fc) {
    if (m->far && fc > 0 && ((u32)fc >> 13) > m->farDist) return &models[m->far - 1];
    return m;
}

void occluders_prepass(void) {
    // (covT and covB are adjacent: one fill clears both)
    static const u32 zero = 0, far = 0x7FFFFFFF;
    bios_cpufastset(&zero, g_covT, (VIEW_W * 4 / 4) | (1 << 24));
    bios_cpufastset(&far, g_covF, (VIEW_W * 4 / 4) | (1 << 24));
    for (int i = 0; i < g_numProps + g_numDynProps; i++) {
        const PropInst *pi = i < g_numProps ? &g_props[i] : &g_dynProps[i - g_numProps];
        if (pi->flags & PIF_HIDDEN) continue;
        const Model *m = &models[pi->model];
        if (!m->nocc && !m->far) continue;
        s32 dx = pi->x - g_cam.x, dy = pi->y - g_cam.y;
        if (dx > (6 << 16) || dx < -(6 << 16) || dy > (6 << 16) || dy < -(6 << 16)) continue;
        s32 f0 = mulq14(dx, g_cam.dirX) + mulq14(dy, g_cam.dirY);
        s32 r0 = mulq14(dy, g_cam.dirX) - mulq14(dx, g_cam.dirY);
        if (m->far) {
            u16 rl = (u16)(pi->angle - g_cam.angle);
            s32 cl = lu_cos(rl), sl = lu_sin(rl);
            s32 rc = r0 + ((m->cx * sl + m->cy * cl) >> 6);
            m = model_lod(m, f0 + ((m->cx * cl - m->cy * sl) >> 6) + ((rc < 0 ? -rc : rc) >> 1));
            if (!m->nocc) continue;
        }
        s32 rad = (s32)m->radius << 8;
        if (f0 - rad < 0x4000 || f0 - rad > (5 << 16)) continue;     // far faces cover little
        s32 ar = r0 < 0 ? -r0 : r0;
        if (ar > ((f0 * 3) >> 2) + rad + (rad >> 1)) continue;
        s32 wx = -dx, wy = -dy;
        s32 co = lu_cos(pi->angle), so = lu_sin(pi->angle);
        s32 cmx = (mulq14(wx, co) + mulq14(wy, so)) >> 8;
        s32 cmy = (mulq14(wy, co) - mulq14(wx, so)) >> 8;
        s32 cmz = EYE_256 - pi->z;
        u16 rel = (u16)(pi->angle - g_cam.angle);
        s32 ca = lu_cos(rel), sa = lu_sin(rel);
        s32 hb = ((s32)pi->z - EYE_256) << 8;
        for (int k = 0; k < m->nocc; k++) {
            const MFace *fc = &m->f[k];
            s32 dot = fc->n[0] * cmx + fc->n[1] * cmy + fc->n[2] * cmz - fc->d;
            if (dot <= 0) continue;
            occ_face(pi, fc, m->v, f0, r0, ca, sa, hb);
        }
    }
}


// ------------------------------------------------------- deep polygons
// The span rasterizer tests a face against the walls with the face's
// nearest depth. For a face that runs a long way into the distance (a stair
// flight seen end-on, a long table) that lets it through walls it is behind
// in the columns where it is far away. For such faces, drop each column in
// which even the nearest of its pixels is behind the wall.
typedef struct { s32 x, y, w, u, v; } PVc;
typedef struct { s16 yA[VIEW_W], yB[VIEW_W]; u32 uvA[VIEW_W], uvB[VIEW_W]; } OutlineC;
extern OutlineC g_ol;

void poly_depth_cull(const PVc *p, int n, int c0, int c1) {
    // the plane of 1/z over the screen through the widest triangle
    int i1 = 1, i2 = 2;
    s64 best = 0;
    for (int a = 1; a < n - 1; a++)
        for (int b = a + 1; b < n; b++) {
            s64 cr = (s64)(p[a].x - p[0].x) * (p[b].y - p[0].y) - (s64)(p[b].x - p[0].x) * (p[a].y - p[0].y);
            if (cr < 0) cr = -cr;
            if (cr > best) { best = cr; i1 = a; i2 = b; }
        }
    if (best == 0) return;
    s64 dx1 = p[i1].x - p[0].x, dy1 = p[i1].y - p[0].y, dw1 = p[i1].w - p[0].w;
    s64 dx2 = p[i2].x - p[0].x, dy2 = p[i2].y - p[0].y, dw2 = p[i2].w - p[0].w;
    s64 det = (dx1 * dy2 - dx2 * dy1) >> 16;
    if (det == 0) return;
    s64 A = (dw1 * dy2 - dw2 * dy1) / det;           // 1/z per pixel across, 16.16
    s64 B = (dx1 * dw2 - dx2 * dw1) / det;           // and down
    if (A > -0x8000 && A < 0x8000 && B > -0x8000 && B < 0x8000) {
        // the usual case, in 32 bits (Thumb has no long multiply): 1/z in
        // 26.6, stepped across the columns, the rows in 1/16 px
        s32 a6 = (s32)A << 6, b2 = (s32)B << 2, y0 = p[0].y >> 12;
        s32 wc = (s32)(((s64)p[0].w << 6) + ((A * (((s64)c0 << 16) + 0x8000 - p[0].x)) >> 10));
        for (int c = c0; c <= c1; c++, wc += a6) {
            s32 ya = g_ol.yA[c], yb = g_ol.yB[c];       // either chain can be the top one
            if (ya == yb) continue;
            s32 wa = wc + b2 * (ya - y0), wb = wc + b2 * (yb - y0);
            s32 wn = (wa > wb ? wa : wb) >> 6;
            if (wn > 0 && (s32)rcp16((u32)wn) >= g_zbuf[c]) g_ol.yB[c] = ya;      // behind the wall here
        }
        return;
    }
    for (int c = c0; c <= c1; c++) {
        s32 ya = g_ol.yA[c], yb = g_ol.yB[c];
        if (ya == yb) continue;
        s64 bx = A * (((s64)c << 16) + 0x8000 - p[0].x);
        s32 wa = p[0].w + (s32)((bx + B * (((s64)ya << 12) - p[0].y)) >> 16);
        s32 wb = p[0].w + (s32)((bx + B * (((s64)yb << 12) - p[0].y)) >> 16);
        s32 wn = wa > wb ? wa : wb;
        if (wn <= 0) continue;
        if ((s32)rcp16((u32)wn) >= g_zbuf[c]) g_ol.yB[c] = ya;
    }
}
