// SPDX-License-Identifier: MIT
// Hollowmere object renderer (ARM, IWRAM): 3D props drawn as textured
// polygons, plus billboard sprites, depth-sorted together over the world.
//
// Pipeline per prop: cull by distance, frustum and the walls' depth buffer;
// rotate/translate the vertices into camera space and project them with a
// reciprocal table (no divisions); cull back faces against precomputed
// planes; drop faces too small to matter at this distance (LOD); sort the
// rest far to near; then fill each face column by column.
//
// Fill paths (full resolution, columns drawn in pairs, see rasm.s):
//  - wall-like faces (box sides, legs, panels: two vertical edges) are drawn
//    as trapezoids exactly like the world's walls: depth, 1/z and u/z step
//    linearly across the columns and each column is a perspective-correct
//    vertical texture run;
//  - every other face is a convex polygon whose upper and lower outlines are
//    first walked into per-column edge buffers (y and packed u,v), then each
//    column interpolates between them. Faces with a large depth range get
//    perspective-correct edges, small ones are affine;
//  - wide faces clear of the walls are drawn as rows instead (exact u,v).
// Faces farther than g_halfDist take one sample per column pair.
#include "engine.h"
#include "assets.h"
#include "render.h"
#include "objects.h"
#include "dev.h"
#ifndef NOFILL
#define NOFILL 0
#endif


#define NEAR     OBJ_NEAR
#define FARCULL  OBJ_FARCULL
#define MAXV     OBJ_MAXV
#define MAXF     OBJ_MAXF

// per-prop transformed vertices (camera space, 16.16) and their projections,
// in spare VRAM (see gba.ld)
extern s32 g_vf[MAXV], g_vr[MAXV], g_vz[MAXV];
extern s32 g_sx[MAXV], g_sy[MAXV], g_sw[MAXV];
#define s_vf g_vf
#define s_vr g_vr
#define s_vz g_vz
#define s_sx g_sx
#define s_sy g_sy
#define s_sw g_sw

static u8  s_faceOrder[MAXF];
static s16 s_faceKey[MAXF];        // summed vertex depths, 1/256 tile

typedef struct { s32 x, y, w, u, v; } PV;     // projected vertex: column, row, 1/z, texels (or texels/z)
typedef struct { s32 f, r, z, u, v; } CV;     // camera space clip vertex
EWRAM_BSS static CV s_cin[4], s_cout[8];

// per-column polygon outlines
typedef struct { s16 yA[VIEW_W], yB[VIEW_W]; u32 uvA[VIEW_W], uvB[VIEW_W]; } Outline;
extern Outline g_ol;          // VRAM, see gba.ld

extern void col_mask(u8 *p, int n, const u8 *pix, const u8 *cm, u32 tp, u32 step);
extern void col_mask2(u8 *p, int n, const u8 *pix, const u8 *cm, u32 tp, u32 step);
// column-pair drivers (propasm.s)
typedef struct {
    u8 *fb; s32 c0, c1;
    s32 fnear; const u8 *tex;
    u8 lt[NCONE];
} PSpan;
extern void pspan_pair(PSpan *s);
extern void pspan_half(PSpan *s);
s32 g_halfDist = 0x24000;      // faces farther than this are filled one sample per column pair

u32 g_lodScale = 256;    // 256 = full detail; larger drops small faces sooner
#ifdef DEV
EWRAM_BSS u32 g_objStats[4];       // props drawn, faces drawn, columns, sprites
EWRAM_BSS u32 g_objT[4], g_objPix[2], g_objF[6], g_objG[4];
EWRAM_BSS u32 g_flog[64][4]; u32 g_nflog;
extern u32 g_frozenLog;
EWRAM_BSS u32 g_pixCount[3];
EWRAM_BSS u32 g_objPub[20];      // the last complete frame's counters
#endif

static inline s32 mul16(s32 a, s32 b) { return (s32)(((s64)a * b) >> 16); }

// num / den as 16.16 for 0 <= num < den, with a 32-bit division (the 64-bit
// one costs several times the cycles and 190 bytes of stack, here where the
// stack is deepest): both are scaled down until num fits 16 bits, which
// leaves den at least 15 significant bits.
static inline s32 frac16(u32 num, u32 den) {
    while (num >= 0x10000) { num >>= 1; den >>= 1; }
    return (s32)((num << 16) / den);
}

// final light per flashlight cone class for a face at depth f, for the cones
// its columns can fall in
static inline void face_lights(u8 *lt, int c0, int c1, u32 f, int fl, int shade) {
    u32 di = f >> 12; if (di > 255) di = 255;
    int k0 = g_coneOf[c0], k1 = g_coneOf[c1];
    if (k0 > k1) { int t = k0; k0 = k1; k1 = t; }
    if (c0 <= VIEW_W / 2 && c1 >= VIEW_W / 2 - 1) k0 = 0;      // spans the centre
    for (int k = k0; k <= k1; k++) {
        int l = g_flashW[k][di];
        if (l < fl) l = fl;
        l += shade;
        if (l < 0) l = 0; else if (l > 31) l = 31;
        lt[k] = l;
    }
}

// ------------------------------------------------------- wall-like faces
// prop texture blob (build_assets.py): 64x64 and mips 32, 16, 8,
// column-major, then each level as column pairs (P0: 2k|2k+1, P1: 2k+1|2k+2)
static const u16 kPtCM[4] = { 0, 4096, 5120, 5376 };
static const u16 kPtP0[4] = { 5440, 13632, 15680, 16192 };

typedef struct {
    u8 *fb; s32 c0, c1;
    s32 yt, yb, w, uw;          // at the centre of column c0 & ~1 (half: of that pair)
    s32 dyt, dyb, dw, duw;      // per column (half: per pair)
    const u8 *tex;              // column-major, at the chosen level
    const u8 *ptex;             // that level's P0 pair layout (P1 follows)
    s32 vt;                     // texel row at the top edge (16.16)
    s32 kstep;                  // texel rows per screen row = kstep * depth
    u32 mask, cshift, psz;      // texel columns - 1, log2 texel rows, pair layout size
    u32 flags;                  // VF_*
    const u8 *cm0;              // the colormap when VF_ONELIGHT
    u8 lt[NCONE];               // light per flashlight cone class
    s32 vr;                     // texel rows top to bottom (VF_TRAP)
} VFace;
#define VF_ONELIGHT 1
#define VF_NOCLIP   2
#define VF_NOZ      4
#define VF_TRAP     8           // top and bottom edges not parallel
extern void vface_pair(VFace *s);
extern void vface_half(VFace *s);
extern s32 g_zmin8[VIEW_W / 8], g_cdmin8[VIEW_W / 8];

// the texture level for a density of d texels per pixel (16.16, level 0)
static inline int pmip_of(u32 d) {
    return d < 0x16A0A ? 0 : d < 0x2D414 ? 1 : d < 0x5A828 ? 2 : 3;
}

IWRAM_CODE static void row_face(u8 *fb, const PV *p, int n, const u8 *tex, const u8 *cm, int persp, int half);
extern PV g_polyPV[8];

// v0 bottom-left, v1 bottom-right, v2 top-right, v3 top-left (seen from the front)
__attribute__((optimize("Os"))) IWRAM_CODE static void vert_face(u8 *fb, const MFace *fc, const u8 *tex, int fl, int shade) {
    int ia = fc->v[0], ib = fc->v[1], ita = fc->v[3], itb = fc->v[2];
    s32 fa = s_vf[ia], fb_ = s_vf[ib];
    if (fa < NEAR && fb_ < NEAR) return;
    s32 ua = fc->uv[0] << 16, ub = fc->uv[2] << 16;
    s32 xa, xb, wa, wb, yta, ytb, yba, ybb;
    if (fa >= NEAR && fb_ >= NEAR) {
        xa = s_sx[ia]; xb = s_sx[ib]; wa = s_sw[ia]; wb = s_sw[ib];
        yba = s_sy[ia]; ybb = s_sy[ib]; yta = s_sy[ita]; ytb = s_sy[itb];
    } else {
        // clip the near end against the near plane
        s32 ra = s_vr[ia], rb = s_vr[ib];
        s32 zba = s_vz[ia], zbb = s_vz[ib], zta = s_vz[ita], ztb = s_vz[itb];
        s32 t = frac16((u32)(NEAR - (fa < NEAR ? fa : fb_)), (u32)(fa < NEAR ? fb_ - fa : fa - fb_));
        if (fa < NEAR) {
            ra += mul16(rb - ra, t); zba += mul16(zbb - zba, t); zta += mul16(ztb - zta, t);
            ua += mul16(ub - ua, t); fa = NEAR;
        } else {
            rb += mul16(ra - rb, t); zbb += mul16(zba - zbb, t); ztb += mul16(zta - ztb, t);
            ub += mul16(ua - ub, t); fb_ = NEAR;
        }
        wa = (s32)rcp16((u32)fa); wb = (s32)rcp16((u32)fb_);
        xa = (VIEW_CX << 16) + mul16(ra, wa) * COLK; xb = (VIEW_CX << 16) + mul16(rb, wb) * COLK;
        yta = (HORIZON << 16) - mul16(zta, wa) * FOCAL; ytb = (HORIZON << 16) - mul16(ztb, wb) * FOCAL;
        yba = (HORIZON << 16) - mul16(zba, wa) * FOCAL; ybb = (HORIZON << 16) - mul16(zbb, wb) * FOCAL;
    }
    if (xa > xb) {      // seen from behind (two-sided)
        s32 t;
        t = xa; xa = xb; xb = t;   t = wa; wa = wb; wb = t;    t = ua; ua = ub; ub = t;
        t = yta; yta = ytb; ytb = t; t = yba; yba = ybb; ybb = t;
    }
    int c0 = (xa + 0x7FFF) >> 16, c1 = (xb - 0x8000) >> 16;
    if (c0 > c1 && (fc->flags & FF_THIN)) {
        // a pole narrower than a column: stretched over the column it is in
        c0 = c1 = ((xa >> 1) + (xb >> 1)) >> 16;
        xa = c0 << 16; xb = xa + 0x10000;
    }
    if (c0 < 0) c0 = 0;
    if (c1 > VIEW_W - 1) c1 = VIEW_W - 1;
    if (c0 > c1) return;
    s32 dx = xb - xa;
    if (dx < 0x100) dx = 0x100;
    s32 inv = (s32)rcp16((u32)dx);
    // texel rows per screen row = vr / (yb - yt), and the face's screen
    // height is H * FOCAL / depth (a parallelogram), so step = kstep * depth
    s32 H = s_vz[ita] - s_vz[ia], Hb = s_vz[itb] - s_vz[ib];
    int trap = (H - Hb > (H >> 6)) || (Hb - H > (H >> 6));
    if (H < Hb) H = Hb;
    if (H < 0x100) H = 0x100;
    s32 vr0 = (s32)(fc->uv[1] - fc->uv[7]) << 16;
    s32 kst0 = mul16(vr0, (s32)rcp16((u32)(H * FOCAL)));
    // texture level from the density at the middle of the face
    s32 wm = (wa + wb) >> 1;
    u32 fm = rcp16((u32)wm);
    u32 dv = (u32)mul16(kst0, (s32)fm);
    s32 du = mul16(ub - ua, inv); if (du < 0) du = -du;
    u32 dens = (u32)du > dv ? (u32)du : dv;
    int m = pmip_of(dens);
    VFace vf;
    vf.fb = fb; vf.c0 = c0; vf.c1 = c1;
    vf.tex = tex + kPtCM[m];
    vf.ptex = tex + kPtP0[m];
    vf.mask = (64 >> m) - 1; vf.cshift = 6 - m; vf.psz = 4096 >> (2 * m);
    vf.vt = ((s32)fc->uv[7] << 16) >> m;
    vf.kstep = kst0 >> m;
    vf.vr = vr0 >> m;
    s32 uwa = mul16(ua >> m, wa), uwb = mul16(ub >> m, wb);
    s32 dyt = mul16(ytb - yta, inv), dyb = mul16(ybb - yba, inv);
    s32 dw = mul16(wb - wa, inv), duw = mul16(uwb - uwa, inv);
    // light: one colormap for the whole face if every cone it spans agrees
    face_lights(vf.lt, c0, c1, fm, fl, shade);
    int k0 = g_coneOf[c0], k1 = g_coneOf[c1];
    if (k0 > k1) { int t = k0; k0 = k1; k1 = t; }
    if (c0 <= VIEW_W / 2 && c1 >= VIEW_W / 2 - 1) k0 = 0;
    u32 flags = VF_ONELIGHT;
    for (int k = k0 + 1; k <= k1; k++) if (vf.lt[k] != vf.lt[k0]) { flags = 0; break; }
    vf.cm0 = g_colormap + (vf.lt[k0] << 8);
    // in front of every wall and no lintel to clip against: skip those tests
    u32 ffar = rcp16((u32)(wa < wb ? wa : wb));
    int noz = 1, noclip = 1;
    for (int b = c0 >> 3; b <= c1 >> 3; b++) {
        if (g_zmin8[b] <= (s32)ffar) noz = 0;
        if (g_cdmin8[b] < (s32)ffar) noclip = 0;
    }
    if (noz) flags |= VF_NOZ;
    if (noclip) flags |= VF_NOCLIP;
    else if (g_multiAny) clip_for_depth(c0, c1, (s32)fm);
    if (trap) flags |= VF_TRAP;
    vf.flags = flags;
    DEV_ONLY(g_objStats[2] += c1 - c0 + 1;)
    // a wide, low face in front of every wall and lintel in its columns, its
    // texels no smaller than half a pixel: rows (fewer, and exact along them)
#ifndef NOVROWS
    if (noz && noclip && dens < 0x20000) {
#else
    if (0) {
#endif
        s32 ytop = yta < ytb ? yta : ytb, ybot = yba > ybb ? yba : ybb;
        s32 hr = (ybot - ytop) >> 16;
        if (hr < 18 && c1 - c0 > 2 * hr + 8) {
            PV *p = g_polyPV;
            s32 vt = (s32)fc->uv[7] << 16, vb = (s32)fc->uv[1] << 16;
            p[0].x = xa; p[0].y = yta; p[0].w = wa; p[0].u = mul16(ua, wa); p[0].v = mul16(vt, wa);
            p[1].x = xb; p[1].y = ytb; p[1].w = wb; p[1].u = mul16(ub, wb); p[1].v = mul16(vt, wb);
            p[2].x = xb; p[2].y = ybb; p[2].w = wb; p[2].u = p[1].u;        p[2].v = mul16(vb, wb);
            p[3].x = xa; p[3].y = yba; p[3].w = wa; p[3].u = p[0].u;        p[3].v = mul16(vb, wa);
            int cmid = (c0 + c1) >> 1;
            const u8 *cm = g_colormap + (vf.lt[g_coneOf[cmid]] << 8);
            if (!NOFILL) row_face(fb, p, 4, tex, cm, 1, (s32)rcp16((u32)(wa > wb ? wa : wb)) >= g_halfDist);
            return;
        }
    }
    // interpolants at the centre of the even column starting the first pair
    int cs = c0 & ~1;
    s32 t = (cs << 16) + 0x8000 - xa;
    s32 yt = yta + mul16(t, dyt) + 0x7FFF, yb = yba + mul16(t, dyb) + 0x7FFF;
    s32 w = wa + mul16(t, dw), uw = uwa + mul16(t, duw);
    s32 wnear = wa > wb ? wa : wb;
    if (c1 - c0 >= 3 && (s32)rcp16((u32)wnear) >= g_halfDist) {
        // far: one sample per column pair, at the pair's centre
        vf.yt = yt + (dyt >> 1); vf.yb = yb + (dyb >> 1); vf.w = w + (dw >> 1); vf.uw = uw + (duw >> 1);
        vf.dyt = dyt * 2; vf.dyb = dyb * 2; vf.dw = dw * 2; vf.duw = duw * 2;
        if (!NOFILL) vface_half(&vf);
        return;
    }
    vf.yt = yt; vf.yb = yb; vf.w = w; vf.uw = uw;
    vf.dyt = dyt; vf.dyb = dyb; vf.dw = dw; vf.duw = duw;
    if (!NOFILL) vface_pair(&vf);
}

// ------------------------------------------------------- general polygons
// one outline chain into the per-column edge buffers (propasm.s)
typedef struct {
    const PV *p; const u8 *list; s32 len, c0, c1;
    s16 *ey; u32 *euv; s32 persp;
} ChainArgs;
extern void chain_walk(ChainArgs *a);

// Row rasterizer for faces wider than tall that no wall or lintel overlaps.
// Along a row the depth of a horizontal face is constant, so u,v are exactly
// linear: only the row ends need a perspective divide. The polygon is cut
// into bands between vertex rows; each band is two straight edges (asm).
typedef struct {
    u8 *fb; s32 r, r1;
    s32 eA[4], eB[4];          // x u v w at the row centre
    s32 dA[4], dB[4];          // per row
    const u8 *tex; const u8 *cm; s32 persp;
    s32 half;                  // one sample per pixel pair
} RSpan;
extern void rspan_draw(RSpan *s);

__attribute__((optimize("Os"))) IWRAM_CODE static void edge_at(s32 *e, s32 *d, const PV *a, const PV *b, s32 yc) {
    s32 dy = b->y - a->y;
    if (dy < 0x100) dy = 0x100;
    s32 inv = (s32)rcp16((u32)dy);
    d[0] = mul16(b->x - a->x, inv); d[1] = mul16(b->u - a->u, inv);
    d[2] = mul16(b->v - a->v, inv); d[3] = mul16(b->w - a->w, inv);
    s32 t = yc - a->y;
    e[0] = a->x + mul16(t, d[0]); e[1] = a->u + mul16(t, d[1]);
    e[2] = a->v + mul16(t, d[2]); e[3] = a->w + mul16(t, d[3]);
}

__attribute__((optimize("Os"))) IWRAM_CODE static void row_face(u8 *fb, const PV *p, int n, const u8 *tex, const u8 *cm, int persp, int half) {
    int iT = 0, iB = 0;
    for (int i = 1; i < n; i++) {
        if (p[i].y < p[iT].y) iT = i;
        if (p[i].y > p[iB].y) iB = i;
    }
    int r0 = (p[iT].y + 0x7FFF) >> 16, r1 = (p[iB].y - 0x8000) >> 16;
    if (r0 < ROW0) r0 = ROW0;
    if (r1 > ROW1 - 1) r1 = ROW1 - 1;
    if (r0 > r1) return;
    u8 la[8], lb[8];
    int na = 0, nb = 0;
    for (int i = iT;; ) { la[na++] = i; if (i == iB) break; i = i + 1 == n ? 0 : i + 1; }
    for (int i = iT;; ) { lb[nb++] = i; if (i == iB) break; i = i == 0 ? n - 1 : i - 1; }
    extern RSpan g_rspan;     // VRAM scratch (see gba.ld)
    #define sp g_rspan
    sp.fb = fb; sp.tex = tex; sp.cm = cm; sp.persp = persp; sp.half = half;
    int ka = 0, kb = 0;
    for (int r = r0; r <= r1; ) {
        s32 yc = (r << 16) + 0x8000;
        while (ka < na - 2 && yc > p[la[ka + 1]].y) ka++;
        while (kb < nb - 2 && yc > p[lb[kb + 1]].y) kb++;
        const PV *a1 = &p[la[ka + 1]], *b1 = &p[lb[kb + 1]];
        edge_at(sp.eA, sp.dA, &p[la[ka]], a1, yc);
        edge_at(sp.eB, sp.dB, &p[lb[kb]], b1, yc);
        s32 yend = a1->y < b1->y ? a1->y : b1->y;
        int re = (yend - 0x8000) >> 16;
        if (re > r1) re = r1;
        if (re < r) re = r;
        sp.r = r; sp.r1 = re;
        rspan_draw(&sp);
        r = re + 1;
    }
    #undef sp
}

extern PV g_polyPV[8];        // VRAM scratch (see gba.ld): keeps the stack shallow
extern void poly_depth_cull(const PV *p, int n, int c0, int c1) __attribute__((long_call));
__attribute__((optimize("Os"))) IWRAM_CODE static void poly_face(u8 *fb, const MFace *fc, int nvx, const u8 *tex, int fl, int shade) {
    PV *p = g_polyPV;
    int n = 0, needClip = 0;
    for (int k = 0; k < nvx; k++) if (s_vf[fc->v[k]] < NEAR) needClip = 1;
    if (!needClip) {
        for (int k = 0; k < nvx; k++) {
            int vi = fc->v[k];
            PV *q = &p[n++];
            q->x = s_sx[vi]; q->y = s_sy[vi]; q->w = s_sw[vi];
            q->u = fc->uv[2 * k] << 16; q->v = fc->uv[2 * k + 1] << 16;
        }
    } else {
        CV *in = s_cin, *out = s_cout;
        for (int k = 0; k < nvx; k++) {
            int vi = fc->v[k];
            in[k].f = s_vf[vi]; in[k].r = s_vr[vi]; in[k].z = s_vz[vi];
            in[k].u = fc->uv[2 * k] << 16; in[k].v = fc->uv[2 * k + 1] << 16;
        }
        int no = 0;
        for (int k = 0; k < nvx; k++) {
            const CV *a = &in[k], *b = &in[k + 1 == nvx ? 0 : k + 1];
            int ina = a->f >= NEAR, inb = b->f >= NEAR;
            if (ina) out[no++] = *a;
            if (ina != inb) {
                s32 t = ina ? frac16((u32)(a->f - NEAR), (u32)(a->f - b->f)) : frac16((u32)(NEAR - a->f), (u32)(b->f - a->f));
                CV *o = &out[no++];
                o->f = NEAR;
                o->r = a->r + mul16(b->r - a->r, t);
                o->z = a->z + mul16(b->z - a->z, t);
                o->u = a->u + mul16(b->u - a->u, t);
                o->v = a->v + mul16(b->v - a->v, t);
            }
        }
        if (no < 3) return;
        for (int k = 0; k < no; k++) {
            s32 w = (s32)rcp16((u32)out[k].f);
            PV *q = &p[n++];
            q->w = w;
            q->x = (VIEW_CX << 16) + mul16(out[k].r, w) * COLK;
            q->y = (HORIZON << 16) - mul16(out[k].z, w) * FOCAL;
            q->u = out[k].u; q->v = out[k].v;
        }
    }
    int iL = 0, iR = 0;
    s32 wmin = p[0].w, wmax = p[0].w, ymin = p[0].y, ymax = p[0].y;
    for (int i = 1; i < n; i++) {
        if (p[i].x < p[iL].x) iL = i;
        if (p[i].x > p[iR].x) iR = i;
        if (p[i].w < wmin) wmin = p[i].w;
        if (p[i].w > wmax) wmax = p[i].w;
        if (p[i].y < ymin) ymin = p[i].y;
        if (p[i].y > ymax) ymax = p[i].y;
    }
    int c0 = (p[iL].x + 0x7FFF) >> 16, c1 = (p[iR].x - 0x8000) >> 16;
    if (c0 < 0) c0 = 0;
    if (c1 > VIEW_W - 1) c1 = VIEW_W - 1;
    if (c0 > c1) return;
    // the whole face behind the walls in its columns? entirely in front of them?
    u32 fnear = rcp16((u32)wmax), ffar = rcp16((u32)wmin);
    int any = 0, clear = 1;
    for (int c = c0; c <= c1; c++) if ((s32)fnear < g_zbuf[c]) { any = 1; break; }
    if (!any) return;
    if (c1 - c0 > ((ymax - ymin) >> 16) + 2) {
        // (by blocks of 8 columns: the nearest wall and lintel of each)
        for (int b = c0 >> 3; b <= c1 >> 3; b++)
            if ((s32)ffar >= g_zmin8[b] + 0x1800 || (s32)ffar >= g_cdmin8[b]) { clear = 0; break; }   // touching a wall is fine
    } else clear = 0;
    int persp = (wmax - wmin) > (wmin >> 2);
    if (persp)
        for (int i = 0; i < n; i++) { p[i].u = mul16(p[i].u, p[i].w); p[i].v = mul16(p[i].v, p[i].w); }
    if (clear && c1 - c0 > ((ymax - ymin) >> 16) + 2) {
        // wide and clear of the walls: rows (exact u,v along a row)
        u8 lt[NCONE];
        int cm = (c0 + c1) >> 1;
        face_lights(lt, cm, cm, rcp16((u32)((wmin + wmax) >> 1)), fl, shade);
        if (!NOFILL) row_face(fb, p, n, tex, g_colormap + (lt[g_coneOf[cm]] << 8), persp, (s32)fnear >= g_halfDist);
        return;
    }
    u8 la[8], lb[8];
    int na = 0, nb = 0;
    for (int i = iL;; ) { la[na++] = i; if (i == iR) break; i = i + 1 == n ? 0 : i + 1; }
    for (int i = iL;; ) { lb[nb++] = i; if (i == iR) break; i = i == 0 ? n - 1 : i - 1; }
    ChainArgs ca;
    ca.p = p; ca.list = la; ca.len = na; ca.c0 = c0; ca.c1 = c1;
    ca.ey = g_ol.yA; ca.euv = g_ol.uvA; ca.persp = persp;
    chain_walk(&ca);
    ca.list = lb; ca.len = nb; ca.ey = g_ol.yB; ca.euv = g_ol.uvB;
    chain_walk(&ca);
    // a wall between its nearest and farthest points in some column (the
    // stair flight through the dining-room wall): test it column by column
    if (persp)
        for (int c = c0; c <= c1; c++) {
            s32 z = g_zbuf[c];
            if (z > (s32)fnear && z < (s32)ffar - 0x1800) { poly_depth_cull(p, n, c0, c1); break; }
        }
    DEV_ONLY(g_objStats[2] += c1 - c0 + 1;)
    if (g_multiAny) clip_for_depth(c0, c1, (s32)((fnear + ffar) >> 1));
    u8 lt[NCONE];
    face_lights(lt, c0, c1, rcp16((u32)((wmin + wmax) >> 1)), fl, shade);
    PSpan sp;
    sp.fb = fb; sp.c0 = c0; sp.c1 = c1; sp.fnear = (s32)fnear; sp.tex = tex;
    for (int k = 0; k < NCONE; k++) sp.lt[k] = lt[k];
    if (NOFILL) return;
    if (c1 - c0 >= 3 && (s32)fnear >= g_halfDist) pspan_half(&sp);
    else pspan_pair(&sp);
}

// ------------------------------------------------------------- bench hook
// time one synthetic vertical face: cols columns of rows rows (debug cmd 10)
#ifdef VBENCH
u32 vface_bench(u8 *fb, int rows, int cols, int full) {
    VFace vf;
    vf.fb = fb; vf.c0 = 0; vf.c1 = cols - 1;
    vf.yt = ((ROW0 + 4) << 16) + 0x7FFF; vf.yb = vf.yt + (rows << 16);
    vf.w = 0x8000; vf.uw = 0;                      // depth 2 tiles
    vf.dyt = 0; vf.dyb = 0; vf.dw = 0; vf.duw = full ? 0x4000 : 0x8000;
    vf.tex = proptex[0] + kPtCM[0]; vf.ptex = proptex[0] + kPtP0[0];
    vf.mask = 63; vf.cshift = 6; vf.psz = 4096;
    vf.vt = 0; vf.kstep = 0x8000; vf.vr = 64 << 16;
    vf.flags = VF_ONELIGHT | VF_NOCLIP | VF_NOZ;
    vf.cm0 = g_colormap + (31 << 8);
    for (int k = 0; k < NCONE; k++) vf.lt[k] = 31;
    u32 t0 = PROF_T();
    if (full) vface_pair(&vf); else vface_half(&vf);
    return PROF_T() - t0;
}
#endif

// ---------------------------------------------------------------- props
extern u16 g_vmark[MAXV];          // vertex used by this prop (stamp), in VRAM
#define s_vmark g_vmark
static u16 s_stamp;

IWRAM_CODE void draw_prop(u8 *fb, const PropInst *pi, s32 f0, s32 r0) {
    const Model *m = &models[pi->model];
    u16 rel = (u16)(pi->angle - g_cam.angle);
    s32 ca = lu_cos(rel), sa = lu_sin(rel);
    if (m->far) m = model_lod(m, prop_centre_depth(m, f0, r0, ca, sa));
    int nv = m->nv, nf = m->nf;
    if (nv > MAXV || nf > MAXF) return;
    // camera position in model space (1/256 tile) for back-face culling
    s32 wx = g_cam.x - pi->x, wy = g_cam.y - pi->y;
    s32 co = lu_cos(pi->angle), so = lu_sin(pi->angle);
    s32 cmx = (s32)(((s64)wx * co + (s64)wy * so) >> 22);
    s32 cmy = (s32)(((s64)wy * co - (s64)wx * so) >> 22);
    s32 cmz = EYE_256 - pi->z;
    // distance in 1/8 tiles, scaled by the detail level (an origin behind
    // the camera plane, with part of the prop still in front, is at zero)
    u32 lodd = f0 > 0 ? ((u32)f0 >> 13) * g_lodScale >> 8 : 0;
    // pass 1: faces turned towards the camera and big enough at this distance
    if (++s_stamp == 0) { for (int i = 0; i < MAXV; i++) s_vmark[i] = 0; s_stamp = 1; }
    u16 st = s_stamp;
    const MFace *mf = m->f;
    int ncand = 0;
    for (int i = 0; i < nf; i++) {
        const MFace *fc = &mf[i];
        if (fc->lod < lodd && fc->lod != 255) continue;      // (255: always drawn)
        s32 dot = fc->n[0] * cmx + fc->n[1] * cmy + fc->n[2] * cmz - fc->d;
        if (dot <= 0 && !(fc->flags & FF_2SIDED)) continue;
        s_faceOrder[ncand++] = i;
        s_vmark[fc->v[0]] = st; s_vmark[fc->v[1]] = st; s_vmark[fc->v[2]] = st;
        if (fc->v[3] != 0xFF) s_vmark[fc->v[3]] = st;
    }
    if (!ncand) return;
    DEV_ONLY(u32 tx0 = PROF_T();)
    // pass 2: transform only the vertices those faces use
    s32 hb = ((s32)pi->z - EYE_256) << 8;            // base height relative to the eye, 16.16
    const MVert *mv = m->v;
    for (int i = 0; i < nv; i++) {
        if (s_vmark[i] != st) continue;
        s32 x = mv[i].x, y = mv[i].y;
        s32 f = f0 + ((x * ca - y * sa) >> 6);
        s32 r = r0 + ((x * sa + y * ca) >> 6);
        s32 z = hb + (mv[i].z << 8);
        s_vf[i] = f; s_vr[i] = r; s_vz[i] = z;
        if (f >= NEAR) {
            s32 w = (s32)rcp16((u32)f);
            s_sw[i] = w;
            s_sx[i] = (VIEW_CX << 16) + mul16(r, w) * COLK;
            s_sy[i] = (HORIZON << 16) - mul16(z, w) * FOCAL;
        }
    }
    // pass 3: sort far to near
    int nvis = 0;
    for (int ci = 0; ci < ncand; ci++) {
        int i = s_faceOrder[ci];
        const MFace *fc = &mf[i];
        int nvx = fc->v[3] == 0xFF ? 3 : 4;
        s32 key = 0, fmax = -0x7FFFFFFF;
        for (int k = 0; k < nvx; k++) { s32 f = s_vf[fc->v[k]]; key += f; if (f > fmax) fmax = f; }
        if (fmax < NEAR) continue;
        key >>= 8;
        if (key > 32767) key = 32767; else if (key < -32768) key = -32768;
        int j = nvis++;
        while (j > 0 && s_faceKey[j - 1] < key) { s_faceKey[j] = s_faceKey[j - 1]; s_faceOrder[j] = s_faceOrder[j - 1]; j--; }
        s_faceKey[j] = key; s_faceOrder[j] = i;
    }
    DEV_ONLY(g_objT[3] += PROF_T() - tx0;)
    if (!nvis) return;
    DEV_ONLY(g_objStats[0]++;)
    s32 hd = g_halfDist;
    if (m->mflags & MF_HALF) g_halfDist = 0;
    for (int fi = 0; fi < nvis; fi++) {
        const MFace *fc = &mf[s_faceOrder[fi]];
        const u8 *tex = proptex[fc->tex == FACE_TEXINST ? pi->tex : fc->tex];
        s32 lx = fc->cx, ly = fc->cy;
        s32 gxw = pi->x + ((lx * co - ly * so) >> 6);
        s32 gyw = pi->y + ((lx * so + ly * co) >> 6);
        int fl = (g_lightgrid[(((gyw >> 15) & 63) << 6) | ((gxw >> 15) & 63)] & LG_LIGHT) + pi->light;
        int shade = FF_SHADE(fc->flags);
        DEV_ONLY(g_objStats[1]++;)
        DEV_ONLY(u32 tq = PROF_T();)
#ifdef FACELOG
        u32 c2 = g_objStats[2];
        u32 px0 = ((volatile u32 *)0x02037000)[12];
#endif
        if (fc->flags & FF_VERT) { vert_face(fb, fc, tex, fl, shade); DEV_ONLY(g_objT[0] += PROF_T() - tq; g_objF[0]++;) }
        else { poly_face(fb, fc, fc->v[3] == 0xFF ? 3 : 4, tex, fl, shade); DEV_ONLY(g_objT[1] += PROF_T() - tq; g_objF[1]++;) }
#ifdef FACELOG
        if (g_nflog < 64 && !g_frozenLog) {
            u32 *L = g_flog[g_nflog++];
            L[0] = pi->model | (s_faceOrder[fi] << 8) | ((fc->flags & FF_VERT) << 16);
            L[1] = PROF_T() - tq; L[2] = g_objStats[2] - c2; L[3] = ((volatile u32 *)0x02037000)[12] - px0;
        }
#endif
    }
    g_halfDist = hd;
}

// ---------------------------------------------------------------- sprites
__attribute__((optimize("Os"))) IWRAM_CODE void draw_sprite(u8 *fb, RSprite *s) {
    const SpriteImg *img = s->img;
    s32 dx = s->x - g_cam.x, dy = s->y - g_cam.y;
    s32 depth = s->dist;
    s32 lat = (s32)(((s64)dy * g_cam.dirX - (s64)dx * g_cam.dirY) >> 14);
    u32 invD = rcp16((u32)depth);                                   // 16.16
    s32 scx = (VIEW_CX << 16) + mul16(lat, (s32)invD) * COLK;
    s32 hpx = (s32)(((u64)(FOCAL * s->worldH) * invD) >> 8);       // physical px, 16.16
    s32 wcol = (s32)(((u64)(COLK * s->worldW) * invD) >> 8);        // columns, 16.16
    if (wcol <= 0x4000 || hpx <= 0x4000) return;
    s32 bottom = (HORIZON << 16) + (s32)((((s64)(EYE_256 - s->zoff) * FOCAL) * invD) >> 8);
    s32 topY = bottom - hpx;
    s32 left = scx - (wcol >> 1);
    int c0 = (left + 0xFFFF) >> 16, c1 = (left + wcol + 0xFFFF) >> 16;
    if (c1 <= 0 || c0 >= VIEW_W) return;
    if (c0 < 0) c0 = 0;
    if (c1 > VIEW_W) c1 = VIEW_W;
    DEV_ONLY(g_objStats[3]++;)
    u32 txStep = (u32)img->w * rcp16((u32)wcol);                   // texels per column 16.16
    u32 tyStep = (u32)img->h * rcp16((u32)hpx);                    // texels per row 16.16
    s32 rowScale = (s32)(((u64)(u32)hpx * rcp_tab[img->h]) >> 24);  // rows per texel 16.16
    u32 txPos = (u32)mul16((c0 << 16) - left, (s32)txStep);
    u32 di = depth >> 12; if (di > 255) di = 255;
    int gx = (s->x >> 15) & 63, gy = (s->y >> 15) & 63;
    u32 gl = g_lightgrid[(gy << 6) | gx] & LG_LIGHT;
    u32 boost = s->lightBoost;
    if (s->flags & SPR_OWNLIGHT) { gl = boost; boost = 0; }    // lit by her own lantern: a floor, not the grid
    if (g_multiAny) clip_for_depth(c0, c1 - 1, depth);
    // far (or the lowest detail): column pairs whose two columns agree are
    // drawn from the first one's texels
    int pairs = depth >= g_halfDist;
    for (int col = c0; col < c1; col++, txPos += txStep) {
        if (depth >= g_zbuf[col]) continue;
        int two = pairs && !(col & 1) && col + 1 < c1 && depth < g_zbuf[col + 1] &&
                  g_coneOf[col] == g_coneOf[col + 1] && g_clipDepth[col] == g_clipDepth[col + 1] &&
                  g_clipTop[col] == g_clipTop[col + 1];
        u32 tx = txPos >> 16;
        if (tx >= img->w) continue;
        if (s->flags & SPR_FLIPX) tx = img->w - 1 - tx;
        u32 l;
        if (s->flags & SPR_FULLBRIGHT) l = 31;
        else {
            l = g_flashW[g_coneOf[col]][di];
            if (gl > l) l = gl;
            l += boost; if (l > 31) l = 31;
        }
        const u8 *cm = g_colormap + (l << 8);
        int lim = ROW0;
        if (depth > g_clipDepth[col] && g_clipTop[col] > lim) lim = g_clipTop[col];
        const u8 *post = (const u8 *)img + img->offs[tx];
        while (post[0] != 0xFF) {
            int ptop = post[0], plen = post[1];
            const u8 *pix = post + 2;
            post += 2 + plen;
            s32 sy0 = topY + ptop * rowScale;
            s32 sy1 = sy0 + plen * rowScale;
            int y0 = (sy0 + 0xFFFF) >> 16, y1 = (sy1 + 0xFFFF) >> 16;
            if (y0 < lim) y0 = lim;
            if (y1 > ROW1) y1 = ROW1;
            if (y0 >= y1) continue;
            u32 tp = (u32)mul16((y0 << 16) - sy0, (s32)tyStep);
            int cnt = y1 - y0;
            u32 last = tp + (u32)(cnt - 1) * tyStep;
            while (cnt > 0 && (last >> 16) >= (u32)plen) { cnt--; last -= tyStep; }
            if (cnt > 0) {
                if (two) col_mask2(fb + y0 * 240 + col, cnt, pix, cm, tp, tyStep);
                else col_mask(fb + y0 * 240 + col, cnt, pix, cm, tp, tyStep);
            }
        }
        if (two) { col++; txPos += txStep; }
    }
}


// ---------------------------------------------------------------- occluders
// Before the world is drawn: mark, per column, the rows that a big opaque
// prop face will paint over anyway, so the wall behind it is not drawn.
extern s16 g_covT[VIEW_W], g_covB[VIEW_W];
extern s32 g_covF[VIEW_W];

#ifdef PIXCNT
#define OCC_CODE __attribute__((section(".romcode.occ"), long_call, noinline))
#else
#define OCC_CODE IWRAM_CODE
#endif
__attribute__((optimize("Os"))) OCC_CODE void occ_face(const PropInst *pi, const MFace *fc, const MVert *mv,
                                s32 f0, s32 r0, s32 ca, s32 sa, s32 hb) {
    const MVert *A = &mv[fc->v[0]], *B = &mv[fc->v[1]];
    s32 fa = f0 + ((A->x * ca - A->y * sa) >> 6), ra = r0 + ((A->x * sa + A->y * ca) >> 6);
    s32 fb_ = f0 + ((B->x * ca - B->y * sa) >> 6), rb = r0 + ((B->x * sa + B->y * ca) >> 6);
    if (fa < 0x4000 || fb_ < 0x4000) return;
    s32 wa = (s32)rcp16((u32)fa), wb = (s32)rcp16((u32)fb_);
    s32 xa = (VIEW_CX << 16) + mul16(ra, wa) * COLK, xb = (VIEW_CX << 16) + mul16(rb, wb) * COLK;
    s32 zta = hb + (mv[fc->v[3]].z << 8), ztb = hb + (mv[fc->v[2]].z << 8);
    s32 zba = hb + (A->z << 8), zbb = hb + (B->z << 8);
    s32 yta = (HORIZON << 16) - mul16(zta, wa) * FOCAL, ytb = (HORIZON << 16) - mul16(ztb, wb) * FOCAL;
    s32 yba = (HORIZON << 16) - mul16(zba, wa) * FOCAL, ybb = (HORIZON << 16) - mul16(zbb, wb) * FOCAL;
    if (xa > xb) {
        s32 t;
        t = xa; xa = xb; xb = t; t = wa; wa = wb; wb = t;
        t = yta; yta = ytb; ytb = t; t = yba; yba = ybb; ybb = t;
    }
    // one column in from each side, one row in from top and bottom
    int c0 = ((xa + 0x7FFF) >> 16) + 1, c1 = ((xb - 0x8000) >> 16) - 1;
    if (c0 < 0) c0 = 0;
    if (c1 > VIEW_W - 1) c1 = VIEW_W - 1;
    if (c0 > c1) return;
    s32 dx = xb - xa;
    if (dx < 0x10000) return;
    s32 inv = (s32)rcp16((u32)dx);
    s32 dyt = mul16(ytb - yta, inv), dyb = mul16(ybb - yba, inv), dw = mul16(wb - wa, inv);
    s32 t = (c0 << 16) + 0x8000 - xa;
    s32 yt = yta + mul16(t, dyt), yb = yba + mul16(t, dyb), w = wa + mul16(t, dw);
    for (int c = c0; c <= c1; c++, yt += dyt, yb += dyb, w += dw) {
        int y0 = ((yt + 0x7FFF) >> 16) + 1, y1 = ((yb + 0x7FFF) >> 16) - 1;
        if (y1 - y0 < 2) continue;
        int cur = g_covB[c] - g_covT[c];
        if (g_covF[c] != 0x7FFFFFFF && cur >= y1 - y0) continue;
        g_covT[c] = y0; g_covB[c] = y1;
        g_covF[c] = (s32)rcp16((u32)w) + 0x800;      // a little farther: rounding safety
    }
}
