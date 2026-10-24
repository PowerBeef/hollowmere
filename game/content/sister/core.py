"""The Night Sister, offline: a signed-distance model of the creature and a
ray marcher that renders it lit by her own lantern (numba).

Units are metres; z is up, the character faces +y and her right is +x.
A pose is three arrays (see rig.py): J joint positions, R joint frames
(columns are the local axes) and S scalars. scene() is the whole body as
one distance field; render() marches one image of it.
"""
import math
import numpy as np
from numba import njit, prange

# ---------------------------------------------------------------- layout
# joints
PELVIS, WAIST, CHEST, NECK, HEAD = 0, 1, 2, 3, 4
SH_R, EL_R, WR_R, SH_L, EL_L, WR_L = 5, 6, 7, 8, 9, 10
HIP_R, KN_R, AN_R, TO_R, HIP_L, KN_L, AN_L, TO_L = 11, 12, 13, 14, 15, 16, 17, 18
LGRIP, LGLOBE = 19, 20
FING_R, FING_L = 21, 36          # 5 fingers x 3 joints (knuckle, middle, tip)
HAIR0, NHAIR, HAIRSEG = 51, 7, 5  # 7 strands x 5 points
SWAY = 86                        # hem offset relative to the pelvis
STRIP0 = 87                      # loose bandage strip: 4 points
NJ = 91
# frames
F_HEAD, F_CHEST, F_PELVIS, F_LANT, F_HAND_R, F_HAND_L = 0, 1, 2, 3, 4, 5
NR = 6
# scalars
S_JAW, S_HEM, S_R0, S_R1, S_WAISTZ, S_APRON, S_LIGHT, S_KNEEL, S_FOLD, S_HOLD, S_SEED, S_EYE, S_EYEGLOW = range(13)
NS = 16

# materials
M_NONE, M_SKIN, M_DRESS, M_APRON, M_WHITE, M_SILVER, M_VEIL, M_HAIR, M_BANDAGE, M_EYE, M_SOCKET, \
    M_MOUTH, M_TEETH, M_METAL, M_GLASS, M_NAIL, M_SLEEVE, M_FLESH = range(18)
NMAT = 18


# ---------------------------------------------------------------- helpers
@njit(cache=True, inline='always')
def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


@njit(cache=True, inline='always')
def smin(a, b, k):
    if k <= 0.0:
        return a if a < b else b
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


@njit(cache=True, inline='always')
def smax(a, b, k):
    return -smin(-a, -b, k)


@njit(cache=True, inline='always')
def cone(px, py, pz, ax, ay, az, bx, by, bz, ra, rb):
    """Capsule from a to b with radius ra..rb (linear along the axis)."""
    bax = bx - ax; bay = by - ay; baz = bz - az
    pax = px - ax; pay = py - ay; paz = pz - az
    l2 = bax * bax + bay * bay + baz * baz
    h = 0.0
    if l2 > 1e-12:
        h = clamp((pax * bax + pay * bay + paz * baz) / l2, 0.0, 1.0)
    dx = pax - bax * h; dy = pay - bay * h; dz = paz - baz * h
    return math.sqrt(dx * dx + dy * dy + dz * dz) - (ra + (rb - ra) * h)


@njit(cache=True, inline='always')
def ellip(px, py, pz, rx, ry, rz):
    """Ellipsoid at the origin (approximate distance)."""
    k0 = math.sqrt((px / rx) ** 2 + (py / ry) ** 2 + (pz / rz) ** 2)
    k1 = math.sqrt((px / (rx * rx)) ** 2 + (py / (ry * ry)) ** 2 + (pz / (rz * rz)) ** 2)
    if k1 < 1e-9:
        return -min(rx, min(ry, rz))
    return k0 * (k0 - 1.0) / k1


@njit(cache=True, inline='always')
def rbox(px, py, pz, hx, hy, hz, r):
    qx = abs(px) - hx + r; qy = abs(py) - hy + r; qz = abs(pz) - hz + r
    ox = max(qx, 0.0); oy = max(qy, 0.0); oz = max(qz, 0.0)
    return math.sqrt(ox * ox + oy * oy + oz * oz) + min(max(qx, max(qy, qz)), 0.0) - r


@njit(cache=True, inline='always')
def tolocal(R, k, J, j, x, y, z):
    """World point -> frame k's local coordinates about joint j."""
    dx = x - J[j, 0]; dy = y - J[j, 1]; dz = z - J[j, 2]
    return (R[k, 0, 0] * dx + R[k, 1, 0] * dy + R[k, 2, 0] * dz,
            R[k, 0, 1] * dx + R[k, 1, 1] * dy + R[k, 2, 1] * dz,
            R[k, 0, 2] * dx + R[k, 1, 2] * dy + R[k, 2, 2] * dz)


@njit(cache=True, inline='always')
def jcone(px, py, pz, J, a, b, ra, rb):
    return cone(px, py, pz, J[a, 0], J[a, 1], J[a, 2], J[b, 0], J[b, 1], J[b, 2], ra, rb)


@njit(cache=True, inline='always')
def sphere_bound(px, py, pz, J, j, r):
    dx = px - J[j, 0]; dy = py - J[j, 1]; dz = pz - J[j, 2]
    return math.sqrt(dx * dx + dy * dy + dz * dz) - r


# ---------------------------------------------------------------- noise
@njit(cache=True, inline='always')
def hash3(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 1440670441 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFF) / 65535.0


@njit(cache=True)
def vnoise(x, y, z, seed):
    ix = int(math.floor(x)); iy = int(math.floor(y)); iz = int(math.floor(z))
    fx = x - ix; fy = y - iy; fz = z - iz
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); fz = fz * fz * (3 - 2 * fz)
    a = hash3(ix, iy, iz, seed); b = hash3(ix + 1, iy, iz, seed)
    c = hash3(ix, iy + 1, iz, seed); d = hash3(ix + 1, iy + 1, iz, seed)
    e = hash3(ix, iy, iz + 1, seed); f = hash3(ix + 1, iy, iz + 1, seed)
    g = hash3(ix, iy + 1, iz + 1, seed); h = hash3(ix + 1, iy + 1, iz + 1, seed)
    l0 = (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy
    l1 = (e + (f - e) * fx) + ((g + (h - g) * fx) - (e + (f - e) * fx)) * fy
    return l0 + (l1 - l0) * fz


@njit(cache=True)
def fbm(x, y, z, octaves, seed):
    s = 0.0; a = 0.5; n = 0.0
    for o in range(octaves):
        s += a * vnoise(x, y, z, seed + o * 17)
        n += a
        x *= 2.03; y *= 2.03; z *= 2.03
        a *= 0.5
    return s / n


# ---------------------------------------------------------------- body parts
@njit(cache=True, inline='always')
def strip_prof(ph):
    """Overlapping bandage strips: each rises towards its lower edge, where
    the next one tucks under it."""
    f = ph - math.floor(ph)
    if f < 0.9:
        return (f / 0.9) ** 0.7
    return 1.0 - (f - 0.9) / 0.1


@njit(cache=True)
def head_d(lx, ly, lz, S):
    """Bandaged head in its own frame (x right, y face, z up), mouth open by
    S_JAW: the lower face stretches down and the mouth gapes."""
    jaw = S[S_JAW]
    z = lz
    if z < -0.02:
        z = -0.02 + (z + 0.02) / (1.0 + 0.9 * jaw)        # stretch the lower face
    skull = ellip(lx, ly + 0.004, z - 0.012, 0.071, 0.090, 0.110)
    jawd = ellip(lx, ly - 0.018, z + 0.058, 0.050, 0.070, 0.062)
    d = smin(skull, jawd, 0.04)
    # cheekbones under the wrappings, sunken cheeks below them
    d = smin(d, ellip(abs(lx) - 0.043, ly - 0.052, z + 0.004, 0.022, 0.022, 0.016), 0.015)
    d = smax(d, -ellip(abs(lx) - 0.048, ly - 0.052, z + 0.040, 0.020, 0.030, 0.024), 0.02)
    # brow ridge and nose under the bandage
    d = smin(d, ellip(lx, ly - 0.070, z - 0.040, 0.050, 0.020, 0.012), 0.015)
    d = smin(d, ellip(lx, ly - 0.088, z + 0.004, 0.012, 0.016, 0.022), 0.012)
    # the wrappings: overlapping strips slanting across the face, a few
    # crossing the other way, lumpy where they have soaked and sagged
    p1 = strip_prof((lz * 0.92 + lx * 0.38) * 24.0)
    d -= 0.0021 * p1
    cross = vnoise(lx * 18.0 + 3.0, ly * 18.0, lz * 18.0, 31)
    if cross > 0.56:
        p2 = strip_prof((lz * 0.80 - lx * 0.60) * 21.0 + 0.3)
        d -= 0.0026 * p2 * min(1.0, (cross - 0.56) * 12.0)
    d -= 0.0016 * (vnoise(lx * 40.0, ly * 40.0, lz * 40.0, 32) - 0.5)
    return d


@njit(cache=True)
def head_parts(lx, ly, lz, S):
    """Returns (distance, material) of head, eye socket, eye, mouth, teeth."""
    jaw = S[S_JAW]
    d = head_d(lx, ly, lz, S)
    mat = M_BANDAGE
    # torn places where the wrappings have rotted away: grey skin beneath
    tear = vnoise(lx * 34.0 + 5.0, ly * 34.0, lz * 34.0, 33) * 0.7 + vnoise(lx * 80.0, ly * 80.0, lz * 80.0, 34) * 0.3
    if tear > 0.70 and ly > 0.0:
        d += 0.0024
        mat = M_FLESH
    # her left eye is bare: a ragged hole in the wrappings, the eye deep in it
    ex, ey, ez = -0.031, 0.072, 0.014
    rag = 0.0035 * (vnoise(math.atan2(lz - ez, lx - ex) * 3.0, 0.0, 0.0, 35) - 0.5)
    hole = ellip(lx - ex, ly - ey - 0.012, lz - ez, 0.024, 0.030, 0.019) - rag
    if -hole > d:
        d = -hole
        mat = M_SOCKET
    eye = math.sqrt((lx - ex) ** 2 + (ly - ey + 0.006) ** 2 + (lz - ez) ** 2) - 0.0122
    if eye < d:
        d = eye
        mat = M_EYE
    # mouth: a slit in the wrappings, a torn gaping hole when the jaw drops
    mz = -0.052 - 0.05 * jaw
    ang = math.atan2((lz - mz) / (0.006 + 0.042 * jaw), lx)
    mrag = 0.003 * (vnoise(ang * 4.0, 1.0, 0.0, 36) - 0.5) * (0.4 + jaw)
    mouth = ellip(lx + 0.004, ly - 0.075, lz - mz, 0.027 + 0.010 * jaw, 0.04, 0.0055 + 0.042 * jaw) - mrag
    if -mouth > d:
        d = -mouth
        mat = M_MOUTH
        if ly > 0.083 and jaw > 0.05:
            mat = M_SOCKET                                # lips and gums at the edge
    if jaw > 0.05:
        # long uneven teeth along the top and bottom of the gap, some gone
        for k in range(8):
            for row in range(2):
                hh = hash3(k, row, 7, 40)
                if hh < 0.14:
                    continue
                tx = -0.024 + k * 0.0068 + (hh - 0.5) * 0.002
                tl = (0.006 + 0.012 * hash3(k, row, 3, 41) ** 2) * (0.6 + 0.6 * jaw)
                tw = 0.0030 + 0.0016 * hash3(k, row, 5, 42)
                lean = (hash3(k, row, 9, 43) - 0.5) * 0.008
                if row == 0:
                    t0 = mz + 0.0035 + 0.040 * jaw
                    t = cone(lx, ly, lz, tx, 0.071, t0 + 0.004, tx * 0.94 + lean, 0.074, t0 - tl, tw, tw * 0.3)
                else:
                    t0 = mz - 0.0035 - 0.040 * jaw
                    t = cone(lx, ly, lz, tx + 0.003, 0.069, t0 - 0.004, tx * 0.94 + lean, 0.072, t0 + tl * 0.8, tw, tw * 0.3)
                if t < d:
                    d = t
                    mat = M_TEETH
    return d, mat


@njit(cache=True)
def veil_d(x, y, z, J, R, S):
    """A nursing sister's veil: a starched cap over the crown and the back of
    the head, framing the face, and a drape hanging down her back."""
    lx, ly, lz = tolocal(R, F_HEAD, J, HEAD, x, y, z)
    cap = ellip(lx, ly + 0.004, lz - 0.012, 0.071 + 0.020, 0.090 + 0.019, 0.110 + 0.020)
    cap = max(cap, -cap - 0.016)                       # a shell
    # open over the face: in front of the hairline, which runs down the cheeks
    front = ly - (0.040 - 0.35 * max(0.0, -lz - 0.02) + 0.12 * max(0.0, lz - 0.06))
    cap = smax(cap, front, 0.006)
    cap = max(cap, -(lz + 0.10))                       # stops at the jaw
    # the drape: a starched sheet from the back of the head down over the
    # nape to the shoulder blades, a rounded point below
    cx, cy, cz = tolocal(R, F_CHEST, J, CHEST, x, y, z)
    hcx, hcy, hcz = tolocal(R, F_CHEST, J, CHEST, J[HEAD, 0], J[HEAD, 1], J[HEAD, 2])
    t = clamp((hcz - 0.03 - cz) / 0.40, 0.0, 1.0)
    w = 0.075 + 0.11 * t
    hd = ellip(lx, ly + 0.004, lz - 0.012, 0.071, 0.090, 0.110)
    back = smin(hd, torso_d(x, y, z, J, R), 0.16)
    sheet = abs(back - 0.024 - 0.018 * t) - 0.0065
    side = abs(cx) - w
    bottom = cz - (hcz - 0.03 - 0.40 * (1.0 - 0.30 * (cx / max(w, 0.05)) ** 2))
    top = cz - hcz + 0.01
    drape = max(max(sheet, side), max(max(-bottom, top), cy - hcy + 0.03)) * 0.8
    return min(cap, drape)


@njit(cache=True)
def skirt_d(x, y, z, J, R, S):
    """The sodden skirt, waist to a torn hem at mid-calf, draped over the legs."""
    wz = S[S_WAISTZ]
    hem0 = S[S_HEM]
    px = J[PELVIS, 0]; py = J[PELVIS, 1]
    u = clamp((wz - z) / max(wz - hem0, 0.1), 0.0, 1.2)
    # the hem lags behind the body
    sx = px + J[SWAY, 0] * u * u
    sy = py + J[SWAY, 1] * u * u
    dx = x - sx; dy = y - sy
    # in the pelvis frame for the folds
    lx = R[F_PELVIS, 0, 0] * dx + R[F_PELVIS, 1, 0] * dy
    ly = R[F_PELVIS, 0, 1] * dx + R[F_PELVIS, 1, 1] * dy
    th = math.atan2(ly, lx)
    r = S[S_R0] + (S[S_R1] - S[S_R0]) * (u ** 0.85)
    ex = 1.10 - 0.08 * u
    ey = 0.92 + 0.03 * u
    rho = math.sqrt((lx / ex) ** 2 + (ly / ey) ** 2)
    ph = S[S_FOLD]
    fold = (0.005 + 0.030 * u) * (0.55 * math.sin(9.0 * th + 2.5 * u + ph) +
                                  0.45 * math.sin(5.0 * th - 3.0 * u + 1.7 + ph * 0.7))
    d = (rho - r - fold) * 0.85
    # the legs push the cloth out as she strides
    for hp, kn, an in ((HIP_R, KN_R, AN_R), (HIP_L, KN_L, AN_L)):
        leg = min(jcone(x, y, z, J, hp, kn, 0.090, 0.072), jcone(x, y, z, J, kn, an, 0.066, 0.052))
        d = smin(d, leg, 0.07 * u + 0.02)
    # waist and torn hem
    d = max(d, z - wz)
    tear = 0.035 * (vnoise(th * 2.6 + 3.0, 0.5, ph * 0.1, 11) - 0.5) + \
        0.05 * max(0.0, vnoise(th * 5.1, 7.3, 1.0, 12) - 0.62) * 3.0
    hem = hem0 + 0.02 * math.sin(th * 3.0 + ph) - tear
    d = max(d, hem - z)
    return d


@njit(cache=True)
def torso_d(x, y, z, J, R):
    lx, ly, lz = tolocal(R, F_CHEST, J, CHEST, x, y, z)
    chest = ellip(lx, ly + 0.005, lz - 0.01, 0.128, 0.090, 0.160)
    lx2, ly2, lz2 = tolocal(R, F_PELVIS, J, WAIST, x, y, z)
    waist = ellip(lx2, ly2, lz2 + 0.02, 0.100, 0.076, 0.150)
    d = smin(chest, waist, 0.08)
    # narrow sloping shoulders: from the base of the neck down to each arm
    d = smin(d, jcone(x, y, z, J, NECK, SH_R, 0.040, 0.044), 0.05)
    d = smin(d, jcone(x, y, z, J, NECK, SH_L, 0.040, 0.044), 0.05)
    return d


@njit(cache=True)
def arm_d(x, y, z, J, sh, el, wr):
    up = jcone(x, y, z, J, sh, el, 0.040, 0.034)
    fo = jcone(x, y, z, J, el, wr, 0.034, 0.029)
    return smin(up, fo, 0.02)


@njit(cache=True)
def hand_d(x, y, z, J, R, f, wr, fing):
    lx, ly, lz = tolocal(R, f, J, wr, x, y, z)
    palm = rbox(lx, ly, lz - 0.048, 0.034, 0.010, 0.040, 0.008)
    d = palm
    nail = 1e9
    for k in range(5):
        b = fing + 3 * k
        rr = 0.0085 if k < 4 else 0.0095
        a = jcone(x, y, z, J, b, b + 1, rr, rr * 0.92)
        c = jcone(x, y, z, J, b + 1, b + 2, rr * 0.9, rr * 0.7)
        d = smin(d, min(a, c), 0.008)
        d = smin(d, sphere_bound(x, y, z, J, b + 1, rr * 1.08), 0.006)
        n = sphere_bound(x, y, z, J, b + 2, rr * 0.75)
        if n < nail:
            nail = n
    # knuckle joint at the wrist
    d = smin(d, sphere_bound(x, y, z, J, wr, 0.024), 0.02)
    return d, nail


@njit(cache=True)
def legs_d(x, y, z, J):
    d = 1e9
    for kn, an, to in ((KN_R, AN_R, TO_R), (KN_L, AN_L, TO_L)):
        shin = jcone(x, y, z, J, kn, an, 0.040, 0.028)
        foot = jcone(x, y, z, J, an, to, 0.030, 0.020)
        heel = sphere_bound(x, y, z, J, an, 0.030)
        d = min(d, smin(smin(shin, foot, 0.03), heel, 0.02))
    return d


@njit(cache=True)
def lantern_d(x, y, z, J, R):
    """Hurricane lantern hung from its bail; local z up its axis, the bail top
    at the grip. Returns (distance, material)."""
    lx, ly, lz = tolocal(R, F_LANT, J, LGRIP, x, y, z)
    lz += 0.275                                     # local origin at the base
    rho = math.sqrt(lx * lx + ly * ly)
    base = max(rho - 0.066, max(-lz, lz - 0.036))
    base = smin(base, max(rho - 0.058, max(-lz + 0.03, lz - 0.046)), 0.004)
    glass = ellip(lx, ly, lz - 0.112, 0.050, 0.050, 0.068)
    top = max(rho - 0.046, max(-(lz - 0.176), lz - 0.198))
    hood = cone(lx, ly, lz, 0.0, 0.0, 0.196, 0.0, 0.0, 0.232, 0.042, 0.016)
    d = min(base, min(top, hood))
    mat = M_METAL
    # guard wires round the globe
    for k in range(4):
        a = 0.785 + k * 1.5708
        c = math.cos(a); s = math.sin(a)
        w = min(cone(lx, ly, lz, 0.061 * c, 0.061 * s, 0.036, 0.064 * c, 0.064 * s, 0.11, 0.0035, 0.0035),
                cone(lx, ly, lz, 0.064 * c, 0.064 * s, 0.11, 0.048 * c, 0.048 * s, 0.182, 0.0035, 0.0035))
        d = min(d, w)
    # bail
    for sx in (-1.0, 1.0):
        bail = min(cone(lx, ly, lz, sx * 0.050, 0.0, 0.188, sx * 0.040, 0.0, 0.255, 0.0032, 0.0032),
                   cone(lx, ly, lz, sx * 0.040, 0.0, 0.255, 0.0, 0.0, 0.276, 0.0032, 0.0032))
        d = min(d, bail)
    if glass < d:
        return glass, M_GLASS
    return d, mat


@njit(cache=True)
def scene(x, y, z, J, R, S, shadow):
    """Distance to the whole figure and the material there. shadow: leave out
    the lantern (it is the light) and the small things."""
    best = 1e9
    mat = M_NONE
    # ---- head, veil, hair
    hb = sphere_bound(x, y, z, J, HEAD, 0.20)
    if hb < 0.05:
        lx, ly, lz = tolocal(R, F_HEAD, J, HEAD, x, y, z)
        d, m = head_parts(lx, ly, lz, S)
        # neck, under the head
        nk = jcone(x, y, z, J, NECK, HEAD, 0.034, 0.030)
        if m == M_BANDAGE:
            d = smin(d, nk, 0.03)
        elif nk < d:
            d = nk; m = M_BANDAGE
        if d < best:
            best = d; mat = m
    else:
        best = hb
    vb = sphere_bound(x, y, z, J, HEAD, 0.48)
    if vb < 0.05:
        v = veil_d(x, y, z, J, R, S)
        if v < best:
            best = v; mat = M_VEIL
    elif vb < best:
        best = vb
    # ---- dress: bodice, sleeves, skirt
    t = torso_d(x, y, z, J, R)
    sr = arm_d(x, y, z, J, SH_R, EL_R, WR_R)
    sl = arm_d(x, y, z, J, SH_L, EL_L, WR_L)
    dress = smin(t, smin(sr, sl, 0.0), 0.05)
    sk = skirt_d(x, y, z, J, R, S)
    dress = smin(dress, sk, 0.06)
    dm = M_DRESS
    if min(sr, sl) < t and min(sr, sl) < sk:
        dm = M_SLEEVE
    if dress < best:
        best = dress; mat = dm
    # ---- apron over it: a bib on the chest and a skirt panel in front
    lx, ly, lz = tolocal(R, F_PELVIS, J, PELVIS, x, y, z)
    wz = S[S_WAISTZ]
    if True:
        # skirt panel: the skirt surface lifted a little, a front sector only
        ap = sk - 0.010
        ang = math.atan2(lx, ly)                     # 0 straight ahead
        ap = max(ap, (abs(ang) - 0.80 - 0.15 * clamp((wz - z) / 0.5, 0.0, 1.0)) * 0.22)
        ap = max(ap, S[S_APRON] + 0.05 * (vnoise(ang * 7.0, 3.0, 0.0, 21) - 0.5) +
                 0.06 * max(0.0, vnoise(ang * 13.0, 5.0, 1.0, 22) - 0.6) * 2.5 - z)
        ap = max(ap, z - wz - 0.01)
        cx, cy, cz = tolocal(R, F_CHEST, J, CHEST, x, y, z)
        bib = t - 0.008
        bib = max(bib, abs(cx) - 0.072 - 0.10 * clamp(-cz - 0.15, 0.0, 0.2))
        bib = max(bib, -cy)
        bib = max(bib, cz - 0.10)
        bib = max(bib, -(cz + 0.30))
        a = min(ap, bib)
        # straps from the bib over the shoulders
        for sx in (-1.0, 1.0):
            st = abs(cx - sx * (0.070 + 0.02 * clamp(cz - 0.10, 0.0, 0.2) / 0.2)) - 0.013
            st = max(st, t - 0.008)
            st = max(st, max(-(cz - 0.08), cz - 0.26))
            a = min(a, st)
        if a < best:
            best = a; mat = M_APRON
        # belt with a silver buckle
        belt = max(t - 0.011, abs(z - wz + 0.005) - 0.024)
        if belt < best:
            best = belt; mat = M_WHITE
        bx, by, bz = tolocal(R, F_PELVIS, J, WAIST, x, y, z)
        buck = rbox(bx, by - 0.094, bz + 0.005, 0.030, 0.006, 0.020, 0.006)
        if buck < best:
            best = buck; mat = M_SILVER
        # white cuffs at the wrists
        for el, wr in ((EL_R, WR_R), (EL_L, WR_L)):
            ex = J[wr, 0] - J[el, 0]; ey = J[wr, 1] - J[el, 1]; ez = J[wr, 2] - J[el, 2]
            L = math.sqrt(ex * ex + ey * ey + ez * ez)
            tt = ((x - J[el, 0]) * ex + (y - J[el, 1]) * ey + (z - J[el, 2]) * ez) / (L * L)
            cf = max(jcone(x, y, z, J, el, wr, 0.038, 0.034), abs(tt - 0.91) * L - 0.032)
            if cf < best:
                best = cf; mat = M_WHITE
    # ---- hands
    for f, wr, fing in ((F_HAND_R, WR_R, FING_R), (F_HAND_L, WR_L, FING_L)):
        b = sphere_bound(x, y, z, J, wr, 0.20)
        if b < 0.03:
            h, nail = hand_d(x, y, z, J, R, f, wr, fing)
            if h < best:
                best = h; mat = M_SKIN
                if nail < 0.004:
                    mat = M_NAIL
        elif b < best:
            best = b
    # ---- legs below the hem
    if z < S[S_HEM] + 0.12:
        l = legs_d(x, y, z, J)
        if l < best:
            best = l; mat = M_SKIN
    # ---- hair: wet strands from under the veil
    if not shadow and S[S_KNEEL] < -1.0:
        for k in range(NHAIR):
            j0 = HAIR0 + k * HAIRSEG
            for s in range(HAIRSEG - 1):
                rr = 0.0085 - 0.0013 * s
                h = jcone(x, y, z, J, j0 + s, j0 + s + 1, rr, rr - 0.001)
                if h < best:
                    best = h; mat = M_HAIR
    if not shadow:
        # a loose strip of bandage hanging from the jaw
        for s in range(3):
            h = jcone(x, y, z, J, STRIP0 + s, STRIP0 + s + 1, 0.009, 0.008)
            if h < best:
                best = h; mat = M_BANDAGE
    # ---- the lantern
    if S[S_LIGHT] > 0.0 and not shadow:
        b = sphere_bound(x, y, z, J, LGLOBE, 0.22)
        if b < 0.03:
            l, lm = lantern_d(x, y, z, J, R)
            if l < best:
                best = l; mat = lm
        elif b < best:
            best = b
    return best, mat


# ---------------------------------------------------------------- shading
@njit(cache=True)
def dist(x, y, z, J, R, S, shadow):
    d, m = scene(x, y, z, J, R, S, shadow)
    return d


@njit(cache=True)
def normal(x, y, z, J, R, S):
    e = 0.0008
    a = dist(x + e, y - e, z - e, J, R, S, False)
    b = dist(x - e, y - e, z + e, J, R, S, False)
    c = dist(x - e, y + e, z - e, J, R, S, False)
    d = dist(x + e, y + e, z + e, J, R, S, False)
    nx = a - b - c + d; ny = -a - b + c + d; nz = -a + b - c + d
    l = math.sqrt(nx * nx + ny * ny + nz * nz) + 1e-12
    return nx / l, ny / l, nz / l


@njit(cache=True)
def soft_shadow(x, y, z, lx, ly, lz, J, R, S):
    dx = lx - x; dy = ly - y; dz = lz - z
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    dx /= L; dy /= L; dz /= L
    t = 0.012
    res = 1.0
    for i in range(40):
        if t > L - 0.07:
            break
        h = dist(x + dx * t, y + dy * t, z + dz * t, J, R, S, True)
        if h < 0.0005:
            return 0.0
        res = min(res, 10.0 * h / t)
        t += max(h, 0.006)
    return clamp(res, 0.0, 1.0)


@njit(cache=True)
def ambient_occ(x, y, z, nx, ny, nz, J, R, S):
    o = 0.0
    w = 1.0
    for i in range(4):
        h = 0.012 + 0.03 * i
        d = dist(x + nx * h, y + ny * h, z + nz * h, J, R, S, True)
        o += (h - d) * w
        w *= 0.6
    return clamp(1.0 - 3.2 * o, 0.0, 1.0)


@njit(cache=True)
def srgb2lin(c):
    return c ** 2.2


@njit(cache=True)
def material(m, x, y, z, J, R, S):
    """Base colour (linear), specular strength, shininess, emissive flag."""
    seed = int(S[S_SEED])
    if m == M_DRESS or m == M_SLEEVE:
        lx, ly, lz = tolocal(R, F_PELVIS, J, PELVIS, x, y, z)
        n = fbm(lx * 9.0, ly * 9.0, z * 5.0, 3, seed + 1)
        wet = clamp((0.75 - z) / 0.6, 0.0, 1.0)                  # soaked towards the hem
        r, g, b = 0.11, 0.125, 0.19
        k = (0.85 + 0.3 * n) * (1.0 - 0.30 * wet)
        r *= k; g *= k; b *= k
        # tide line and silt
        tide = math.exp(-((z - 0.62 - 0.03 * (n - 0.5)) / 0.018) ** 2)
        silt = clamp((fbm(lx * 14.0, ly * 14.0, z * 9.0, 3, seed + 2) - 0.5) * 3.0, 0.0, 1.0) * wet
        r = r + (0.30 - r) * (0.35 * tide + 0.45 * silt)
        g = g + (0.27 - g) * (0.35 * tide + 0.45 * silt)
        b = b + (0.18 - b) * (0.35 * tide + 0.45 * silt)
        streak = clamp((fbm(lx * 40.0, ly * 40.0, z * 2.0, 2, seed + 14) - 0.62) * 4.0, 0.0, 1.0)
        r *= 1.0 - 0.35 * streak; g *= 1.0 - 0.35 * streak; b *= 1.0 - 0.30 * streak
        return srgb2lin(r), srgb2lin(g), srgb2lin(b), 0.14 + 0.25 * streak, 14.0, False
    if m == M_APRON:
        lx, ly, lz = tolocal(R, F_PELVIS, J, PELVIS, x, y, z)
        n = fbm(lx * 7.0, ly * 7.0, z * 7.0, 4, seed + 3)
        r, g, b = 0.60, 0.59, 0.53
        mud = clamp((fbm(lx * 11.0, ly * 11.0, z * 6.0, 3, seed + 4) - 0.45 + 0.45 * clamp((0.85 - z) / 0.35, 0.0, 1.0)) * 2.5, 0.0, 1.0)
        drip = clamp((fbm(lx * 60.0, ly * 60.0, z * 3.0, 2, seed + 15) - 0.60) * 5.0, 0.0, 1.0) * clamp((1.1 - z) / 0.3, 0.0, 1.0)
        mud = clamp(mud + 0.6 * drip, 0.0, 1.0)
        tide = math.exp(-((z - 0.70 - 0.04 * (n - 0.5)) / 0.012) ** 2)
        r = r * (0.88 + 0.2 * n); g = g * (0.88 + 0.2 * n); b = b * (0.86 + 0.2 * n)
        r = r + (0.40 - r) * (0.75 * mud + 0.5 * tide)
        g = g + (0.35 - g) * (0.75 * mud + 0.5 * tide)
        b = b + (0.25 - b) * (0.75 * mud + 0.5 * tide)
        return srgb2lin(r), srgb2lin(g), srgb2lin(b), 0.12, 12.0, False
    if m == M_WHITE:
        n = fbm(x * 30.0, y * 30.0, z * 30.0, 2, seed + 5)
        v = 0.70 + 0.12 * n
        return srgb2lin(v), srgb2lin(v * 0.98), srgb2lin(v * 0.90), 0.15, 14.0, False
    if m == M_SILVER:
        return srgb2lin(0.62), srgb2lin(0.62), srgb2lin(0.60), 1.6, 60.0, False
    if m == M_VEIL:
        lx, ly, lz = tolocal(R, F_HEAD, J, HEAD, x, y, z)
        n = fbm(lx * 12.0, ly * 12.0, z * 9.0, 3, seed + 6)
        r, g, b = 0.86, 0.85, 0.79
        alg = clamp((fbm(lx * 6.0, ly * 6.0, z * 4.0, 3, seed + 7) - 0.48) * 2.2, 0.0, 1.0)
        edge = clamp((J[HEAD, 2] - 0.30 - z) / 0.15, 0.0, 1.0)
        k = 0.86 + 0.18 * n
        r *= k; g *= k; b *= k
        a = clamp(0.6 * alg + 0.6 * edge * alg, 0.0, 0.85)
        r = r + (0.34 - r) * a; g = g + (0.38 - g) * a; b = b + (0.28 - b) * a
        return srgb2lin(r), srgb2lin(g), srgb2lin(b), 0.10, 10.0, False
    if m == M_BANDAGE:
        lx, ly, lz = tolocal(R, F_HEAD, J, HEAD, x, y, z)
        ph = (lz * 0.92 + lx * 0.38) * 24.0
        f = ph - math.floor(ph)
        edge = clamp((f - 0.82) / 0.08, 0.0, 1.0) * (1.0 - clamp((f - 0.93) / 0.07, 0.0, 1.0))
        along = lx * 0.92 - lz * 0.38
        fib = fbm(along * 60.0, ph * 9.0, ly * 60.0, 3, seed + 18)
        n = fbm(lx * 40.0, ly * 40.0, lz * 40.0, 3, seed + 8)
        v = 0.56 + 0.12 * (fib - 0.5) + 0.10 * (n - 0.5) - 0.12 * edge
        r, g, b = v * 1.03, v * 0.95, v * 0.78
        # seeping through: rust round the eye and mouth, grey-green elsewhere
        seep = clamp((fbm(lx * 18.0, ly * 18.0, lz * 18.0, 3, seed + 9) - 0.52) * 3.0, 0.0, 1.0)
        near = math.exp(-((lx + 0.031) ** 2 + (lz - 0.014) ** 2) / 0.0009) + \
            math.exp(-(lx ** 2 + (lz + 0.055 + 0.05 * S[S_JAW]) ** 2) / 0.0012)
        rs = clamp(seep * 0.7 + near * 0.8, 0.0, 0.9)
        r = r + (0.30 - r) * rs; g = g + (0.16 - g) * rs; b = b + (0.11 - b) * rs
        # wet strands of hair stuck across the wrappings
        hair = 0.0
        for k in range(4):
            x0 = (0.052, 0.020, -0.054, 0.036)[k]
            sl = (0.10, -0.05, 0.06, 0.16)[k]
            xs = x0 + sl * (lz - 0.06) + 0.005 * math.sin(lz * 70.0 + k * 2.0)
            wd = (0.0062, 0.0052, 0.0060, 0.0040)[k] - 0.012 * max(0.0, 0.06 - lz) * 0.12
            top = (0.07, 0.075, 0.06, 0.075)[k]
            bot = (-0.11, -0.01, -0.12, -0.05)[k]
            if lz < top and lz > bot:
                hair = max(hair, clamp(1.0 - abs(lx - xs) / max(wd, 0.0015), 0.0, 1.0))
        if hair > 0.0:
            r = r + (0.035 - r) * hair; g = g + (0.033 - g) * hair; b = b + (0.036 - b) * hair
            return srgb2lin(r), srgb2lin(g), srgb2lin(b), 0.10 + 0.3 * hair, 10.0 + 30.0 * hair, False
        return srgb2lin(r), srgb2lin(g), srgb2lin(b), 0.10, 10.0, False
    if m == M_SKIN:
        n = fbm(x * 25.0, y * 25.0, z * 25.0, 3, seed + 10)
        vein = clamp(1.0 - abs(fbm(x * 18.0, y * 18.0, z * 18.0, 2, seed + 11) - 0.5) * 14.0, 0.0, 1.0)
        r, g, b = 0.56, 0.61, 0.60
        k = 0.85 + 0.25 * n
        r *= k; g *= k; b *= k
        r = r + (0.30 - r) * 0.5 * vein; g = g + (0.36 - g) * 0.5 * vein; b = b + (0.44 - b) * 0.5 * vein
        return srgb2lin(r), srgb2lin(g), srgb2lin(b), 0.45, 24.0, False
    if m == M_NAIL:
        return srgb2lin(0.24), srgb2lin(0.24), srgb2lin(0.27), 0.6, 30.0, False
    if m == M_HAIR:
        return srgb2lin(0.045), srgb2lin(0.042), srgb2lin(0.045), 0.9, 40.0, False
    if m == M_EYE:
        lx, ly, lz = tolocal(R, F_HEAD, J, HEAD, x, y, z)
        # drowned: a yellowed, veined white, a clouded grey iris, a pinprick pupil
        gx, gz = lx + 0.031 - S[S_EYE] * 0.003, lz - 0.014
        rr = math.sqrt(gx * gx + gz * gz)
        vein = clamp(1.0 - abs(fbm(lx * 400.0, ly * 400.0, lz * 400.0, 2, seed + 16) - 0.5) * 10.0, 0.0, 1.0)
        r, g, b = 0.80, 0.78, 0.66
        r = r + (0.55 - r) * vein * 0.6 * clamp(rr / 0.012, 0.0, 1.0)
        g = g + (0.20 - g) * vein * 0.6 * clamp(rr / 0.012, 0.0, 1.0)
        b = b + (0.18 - b) * vein * 0.6 * clamp(rr / 0.012, 0.0, 1.0)
        if rr < 0.0058:
            k = 0.5 + 0.5 * fbm(gx * 900.0, gz * 900.0, 0.0, 2, seed + 17)
            r, g, b = 0.50 * k + 0.1, 0.56 * k + 0.1, 0.58 * k + 0.12
        if rr < 0.0016:
            r, g, b = 0.12, 0.12, 0.13
        return srgb2lin(r), srgb2lin(g), srgb2lin(b), 1.4, 80.0, False
    if m == M_SOCKET:
        return srgb2lin(0.16), srgb2lin(0.07), srgb2lin(0.06), 0.3, 20.0, False
    if m == M_MOUTH:
        return srgb2lin(0.025), srgb2lin(0.008), srgb2lin(0.008), 0.0, 20.0, False
    if m == M_FLESH:
        n = fbm(x * 120.0, y * 120.0, z * 120.0, 2, seed + 19)
        return srgb2lin(0.36 + 0.1 * n), srgb2lin(0.36 + 0.08 * n), srgb2lin(0.30 + 0.06 * n), 0.6, 30.0, False
    if m == M_TEETH:
        n = fbm(x * 90.0, y * 90.0, z * 90.0, 2, seed + 12)
        lx, ly, lz = tolocal(R, F_HEAD, J, HEAD, x, y, z)
        gum = clamp(1.0 - abs(abs(lz + 0.052 + 0.05 * S[S_JAW]) - 0.045 * S[S_JAW]) / 0.012, 0.0, 1.0)
        v = 0.55 + 0.12 * n
        return srgb2lin(v), srgb2lin(v * 0.90 - 0.10 * gum), srgb2lin(v * 0.62 - 0.12 * gum), 0.5, 30.0, False
    if m == M_METAL:
        n = fbm(x * 40.0, y * 40.0, z * 40.0, 3, seed + 13)
        return srgb2lin(0.30 + 0.1 * n), srgb2lin(0.25 + 0.08 * n), srgb2lin(0.17), 1.0, 26.0, False
    if m == M_GLASS:
        return 1.0, 0.8, 0.45, 0.0, 1.0, True
    return 0.5, 0.0, 0.5, 0.0, 1.0, False


@njit(cache=True, parallel=True)
def render(W, H, ss, cam, right, up, plane0, plane_w, plane_h, J, R, S, fill, out_rgb, out_a, out_em):
    """cam: eye position; the image covers the rectangle plane0 + u*right +
    v*up (u in 0..plane_w left to right, v in 0..plane_h bottom to top).
    Writes ss x ss supersampled rgb (sRGB), coverage and emissive coverage."""
    WS = W * ss; HS = H * ss
    gx, gy, gz = J[LGLOBE, 0], J[LGLOBE, 1], J[LGLOBE, 2]
    light = S[S_LIGHT]
    for i in prange(HS):
        for j in range(WS):
            u = (j + 0.5) / WS * plane_w
            v = (1.0 - (i + 0.5) / HS) * plane_h
            tx = plane0[0] + u * right[0] + v * up[0]
            ty = plane0[1] + u * right[1] + v * up[1]
            tz = plane0[2] + u * right[2] + v * up[2]
            dx = tx - cam[0]; dy = ty - cam[1]; dz = tz - cam[2]
            L = math.sqrt(dx * dx + dy * dy + dz * dz)
            dx /= L; dy /= L; dz /= L
            # march from where the ray enters her bounding cylinder
            t = max(0.0, L - 1.3)
            hit = False
            m = 0
            for k in range(260):
                px = cam[0] + dx * t; py = cam[1] + dy * t; pz = cam[2] + dz * t
                d, m = scene(px, py, pz, J, R, S, False)
                if d < 0.0004:
                    hit = True
                    break
                t += d * 0.9
                if t > L + 1.4:
                    break
            if not hit:
                continue
            px = cam[0] + dx * t; py = cam[1] + dy * t; pz = cam[2] + dz * t
            br, bg, bb, spec, shin, emis = material(m, px, py, pz, J, R, S)
            out_a[i, j] = 1.0
            if emis:
                # the globe: a hot core round the flame
                lx, ly, lz = tolocal(R, F_LANT, J, LGRIP, px, py, pz)
                rr = math.sqrt(lx * lx + ly * ly + ((lz + 0.163) * 0.6) ** 2)
                core = clamp(1.0 - rr / 0.05, 0.0, 1.0)
                out_rgb[i, j, 0] = 1.0
                out_rgb[i, j, 1] = 0.62 + 0.36 * core
                out_rgb[i, j, 2] = 0.22 + 0.60 * core ** 2
                out_em[i, j] = 1.0
                continue
            if m == M_EYE and br > 0.25 and S[S_EYEGLOW] > 0.0:
                out_rgb[i, j, 0] = 0.92
                out_rgb[i, j, 1] = 0.92
                out_rgb[i, j, 2] = 0.80
                out_em[i, j] = 1.0
                continue
            nx, ny, nz = normal(px, py, pz, J, R, S)
            vx, vy, vz = -dx, -dy, -dz
            ao = ambient_occ(px, py, pz, nx, ny, nz, J, R, S)
            # lantern
            cr = 0.0; cg = 0.0; cb = 0.0
            if light > 0.0:
                lx = gx - px; ly = gy - py; lz = gz - pz
                ld = math.sqrt(lx * lx + ly * ly + lz * lz)
                lx /= ld; ly /= ld; lz /= ld
                ndl = nx * lx + ny * ly + nz * lz
                wrap = clamp((ndl + 0.25) / 1.25, 0.0, 1.0)
                if wrap > 0.0:
                    sh = soft_shadow(px, py, pz, gx, gy, gz, J, R, S)
                    att = light / (1.0 + (ld / 0.55) ** 2)
                    hx = lx + vx; hy = ly + vy; hz = lz + vz
                    hl = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
                    sp = max(0.0, (nx * hx + ny * hy + nz * hz) / hl) ** shin * spec * (ndl > 0.0)
                    k = att * sh
                    cr += k * (wrap * br + sp) * 1.00
                    cg += k * (wrap * bg + sp) * 0.66
                    cb += k * (wrap * bb + sp) * 0.34
            # cold fill from the viewer's side (moon, distant torches)
            fx, fy, fz = fill[0], fill[1], fill[2]
            fd = max(0.0, nx * fx + ny * fy + nz * fz)
            hx = fx + vx; hy = fy + vy; hz = fz + vz
            hl = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
            fsp = max(0.0, (nx * hx + ny * hy + nz * hz) / hl) ** shin * spec * 0.5
            fi = fill[3]
            cr += fi * (fd * br * 0.80 + fsp * 0.8)
            cg += fi * (fd * bg * 0.90 + fsp * 0.9)
            cb += fi * (fd * bb * 1.10 + fsp * 1.1)
            # ambient and a thin cold rim to hold the silhouette in the dark
            amb = fill[4] * ao
            rim = (1.0 - max(0.0, nx * vx + ny * vy + nz * vz)) ** 3 * fill[5] * min(1.0, (br + bg + bb) * 4.0)
            cr += amb * br * 0.8 + rim * 0.55
            cg += amb * bg * 0.9 + rim * 0.62
            cb += amb * bb * 1.1 + rim * 0.75
            # tone map and gamma
            cr = cr / (1.0 + 0.35 * cr); cg = cg / (1.0 + 0.35 * cg); cb = cb / (1.0 + 0.35 * cb)
            out_rgb[i, j, 0] = clamp(cr, 0.0, 1.0) ** (1 / 2.2)
            out_rgb[i, j, 1] = clamp(cg, 0.0, 1.0) ** (1 / 2.2)
            out_rgb[i, j, 2] = clamp(cb, 0.0, 1.0) ** (1 / 2.2)
