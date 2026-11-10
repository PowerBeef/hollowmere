# SPDX-License-Identifier: MIT
"""Poses for the Night Sister: joint positions and frames from a handful of
body parameters, with two-bone IK for the limbs (see core.py for layout).
Metres; z up; she faces +y and her right is +x."""
import math
import numpy as np
from core import *

# limb lengths: she is very tall, with long forearms and long hands
THIGH, SHIN, ANKLE_H = 0.48, 0.47, 0.07
UPPER, FORE = 0.33, 0.33
FINGER = (0.066, 0.058)          # proximal, distal


def rot(axis, a):
    """Rotation matrix about x, y or z by a radians."""
    c, s = math.cos(a), math.sin(a)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 'y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def norm(v):
    return v / (np.linalg.norm(v) + 1e-12)


def ik(a, target, l1, l2, pole):
    """Middle joint of a two-bone chain from a reaching target, bending
    towards pole; the end is clamped to reach."""
    d = target - a
    L = np.linalg.norm(d)
    L = min(max(L, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    dn = norm(d)
    end = a + dn * L
    x = (l1 * l1 - l2 * l2 + L * L) / (2 * L)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    p = pole - a
    p = norm(p - dn * np.dot(p, dn))
    return a + dn * x + p * h, end


def frame_from(z_axis, y_hint):
    """Orthonormal frame (columns x, y, z) with z along z_axis and y as near
    y_hint as possible."""
    z = norm(z_axis)
    y = norm(y_hint - z * np.dot(y_hint, z))
    x = np.cross(y, z)
    return np.stack([x, y, z], axis=1)


class Pose:
    """Body parameters (angles in degrees) -> J, R, S arrays."""

    def __init__(self, **kw):
        self.p = dict(
            pelvis=(0.0, 0.0, 1.02), pelvis_yaw=0.0, pelvis_roll=0.0,
            lean=9.0, chest_roll=0.0, chest_yaw=0.0, chest_lean=6.0,
            neck_lean=22.0, head_pitch=-6.0, head_roll=19.0, head_yaw=0.0,
            foot_r=(0.10, 0.05, 0.0), foot_l=(-0.10, -0.02, 0.0), foot_pitch_r=0.0, foot_pitch_l=0.0,
            knee_r=None, knee_l=None, legs_r=None, legs_l=None,
            hand_r=(0.25, 0.20, 0.92), elbow_pole_r=(0.6, -0.4, 1.2), hand_r_up=(0.0, 0.0, 1.0),
            hand_l=(-0.27, 0.03, 0.55), elbow_pole_l=(-0.6, -0.3, 1.2), hand_l_up=None,
            curl_r=(70, 80, 85, 85, 40), curl_l=(25, 30, 35, 40, 20), spread_l=10.0, spread_r=4.0,
            lantern='hand', lantern_swing=(0.0, 0.0), lantern_pos=None,
            jaw=0.0, hem=0.27, r0=0.112, r1=0.26, apron=0.60, fold=0.0, sway=(0.0, 0.0),
            light=1.6, kneel=0.0, seed=7, hair_swing=(0.0, 0.0), eye=0.0, eyeglow=1.0,
            palm_l=None, palm_r=None, fingers_l=None,
        )
        self.p.update(kw)

    def build(self):
        p = self.p
        J = np.zeros((NJ, 3))
        R = np.zeros((NR, 3, 3))
        S = np.zeros(NS)
        d2r = math.radians
        auto = p['pelvis'][2] is None
        pel = np.array([p['pelvis'][0], p['pelvis'][1], 1.0 if auto else p['pelvis'][2]], float)
        Rp = rot('z', d2r(p['pelvis_yaw'])) @ rot('y', d2r(p['pelvis_roll']))
        if auto:
            # as high as both feet allow, knees a touch bent
            zs = []
            for side, foot in ((1, p['foot_r']), (-1, p['foot_l'])):
                hip = pel[:2] + (Rp @ np.array([0.095 * side, 0, 0]))[:2]
                f = np.array(foot, float)
                hd = np.hypot(f[0] - hip[0], f[1] - hip[1])
                Lm = (THIGH + SHIN) * 0.985
                zs.append(ANKLE_H + f[2] + math.sqrt(max(Lm * Lm - hd * hd, 0.01)) + 0.03)
            pel = np.array([pel[0], pel[1], min(zs) + p.get('dip', 0.0)])
        J[PELVIS] = pel
        R[F_PELVIS] = Rp
        J[WAIST] = pel + Rp @ np.array([0, 0.0, 0.12])
        # spine: lean forward (about the x axis: +y is forward, so a
        # forward lean is a negative rotation about x... towards +y)
        Rs = Rp @ rot('z', d2r(p['chest_yaw'])) @ rot('y', d2r(p['chest_roll'])) @ rot('x', -d2r(p['lean']))
        J[CHEST] = J[WAIST] + Rs @ np.array([0, 0, 0.25])
        Rc = Rs @ rot('x', -d2r(p['chest_lean']))
        R[F_CHEST] = Rc
        J[NECK] = J[CHEST] + Rc @ np.array([0, -0.005, 0.175])
        Rn = Rc @ rot('x', -d2r(p['neck_lean']))
        Rh = Rn @ rot('z', d2r(p['head_yaw'])) @ rot('y', d2r(p['head_roll'])) @ rot('x', -d2r(p['head_pitch']))
        R[F_HEAD] = Rh
        J[HEAD] = J[NECK] + Rn @ np.array([0, 0.01, 0.13]) + Rh @ np.array([0, 0.0, 0.11])
        J[SH_R] = J[CHEST] + Rc @ np.array([0.170, -0.012, 0.105])
        J[SH_L] = J[CHEST] + Rc @ np.array([-0.170, -0.012, 0.105])
        J[HIP_R] = pel + Rp @ np.array([0.095, 0, -0.03])
        J[HIP_L] = pel + Rp @ np.array([-0.095, 0, -0.03])
        # legs: ankle targets (x, y, lift) and foot pitch (toes up +), or
        # explicit (knee, ankle, toe) points
        fd = Rp @ np.array([0, 1, 0])
        for hp, kn, an, to, foot, fp, kp, ex in ((HIP_R, KN_R, AN_R, TO_R, p['foot_r'], p['foot_pitch_r'], p['knee_r'], p['legs_r']),
                                                (HIP_L, KN_L, AN_L, TO_L, p['foot_l'], p['foot_pitch_l'], p['knee_l'], p['legs_l'])):
            if ex is not None:
                J[kn], J[an], J[to] = (np.array(q, float) for q in ex)
                continue
            f = np.array(foot, float)
            ankle = np.array([f[0], f[1], ANKLE_H + f[2]])
            pole = np.array(kp, float) if kp is not None else J[hp] + fd * 0.6 + np.array([0, 0, -0.4])
            k, a = ik(J[hp], ankle, THIGH, SHIN, pole)
            J[kn], J[an] = k, a
            fp_ = d2r(fp)
            J[to] = a + fd * 0.17 * math.cos(fp_) + np.array([0, 0, -0.05 + 0.17 * math.sin(fp_)])
        # arms
        for sh, el, wr, fr, hand, pole, upv, curl, spread, palm in (
                (SH_R, EL_R, WR_R, F_HAND_R, p['hand_r'], p['elbow_pole_r'], p['hand_r_up'], p['curl_r'], p['spread_r'], p['palm_r']),
                (SH_L, EL_L, WR_L, F_HAND_L, p['hand_l'], p['elbow_pole_l'], p['hand_l_up'], p['curl_l'], p['spread_l'], p['palm_l'])):
            e, w = ik(J[sh], np.array(hand, float), UPPER, FORE, np.array(pole, float))
            J[el], J[wr] = e, w
            fdir = norm(w - e)
            if upv is not None:
                # hand z continues the forearm, bent to point along upv
                zax = norm(fdir * 0.4 + norm(np.array(upv, float)) * 0.6)
            else:
                zax = fdir
            ph = np.array(palm, float) if palm is not None else Rc @ np.array([-1.0 if sh == SH_R else 1.0, 0.3, 0])
            R[fr] = frame_from(zax, ph)
        self._fingers(J, R, F_HAND_R, WR_R, FING_R, p['curl_r'], p['spread_r'], 1.0)
        self._fingers(J, R, F_HAND_L, WR_L, FING_L, p['curl_l'], p['spread_l'], -1.0)
        # lantern
        if p['lantern'] == 'hand':
            Rh_ = R[F_HAND_R]
            grip = J[WR_R] + Rh_ @ np.array([0.0, 0.016, 0.075])
            sw = p['lantern_swing']
            Rl = rot('x', d2r(sw[0])) @ rot('y', d2r(sw[1]))
        else:
            grip = np.array(p['lantern_pos'], float) + np.array([0, 0, 0.275])
            Rl = rot('z', 0.3)
        J[LGRIP] = grip
        R[F_LANT] = Rl
        J[LGLOBE] = grip + Rl @ np.array([0, 0, 0.112 - 0.275])
        # hair: wet clumps escaping from under the veil at the sides of the
        # face, hanging down over the shoulders (the strands stuck across
        # the face are painted on the bandages)
        roots = [(0.064, 0.030, -0.030), (0.058, 0.050, 0.005), (0.050, 0.020, -0.075),
                 (-0.064, 0.032, -0.035), (-0.054, 0.046, 0.000), (0.030, 0.050, -0.090), (-0.040, 0.030, -0.085)]
        lens = [0.42, 0.30, 0.36, 0.40, 0.26, 0.22, 0.30]
        rng = np.random.default_rng(int(p['seed']))
        hs = np.array(p['hair_swing'], float)
        for k, (r, L) in enumerate(zip(roots, lens)):
            pt = J[HEAD] + Rh @ np.array(r)
            side = Rh @ norm(np.array([r[0], 0.25, -0.2]))
            pts = [pt]
            for s in range(1, HAIRSEG):
                t = s / (HAIRSEG - 1)
                drop = np.array([0, 0, -L / (HAIRSEG - 1)])
                out = side * (0.010 if s == 1 else 0.002)
                wig = rng.normal(0, 0.005, 3) * np.array([1, 1, 0.2])
                pt = pt + drop + out + np.array([hs[0], hs[1], 0]) * t * 0.4 + wig
                # lie on the body rather than float: pull back towards the chest
                if s >= 2:
                    pt = pt + R[F_CHEST] @ np.array([0, -0.006, 0])
                pts.append(pt)
            for s in range(HAIRSEG):
                J[HAIR0 + k * HAIRSEG + s] = pts[s]
        # a loose end of bandage hanging under her jaw
        sp = J[HEAD] + Rh @ np.array([0.040, 0.050, -0.085])
        J[STRIP0] = sp
        for s in range(1, 4):
            sp = sp + np.array([0.004 + hs[0] * 0.2, 0.006 + hs[1] * 0.2, -0.045])
            J[STRIP0 + s] = sp
        J[SWAY] = np.array([p['sway'][0], p['sway'][1], 0.0])
        S[S_JAW] = p['jaw']
        S[S_HEM] = p['hem']
        S[S_R0] = p['r0']
        S[S_R1] = p['r1']
        S[S_WAISTZ] = J[WAIST][2] + 0.04
        S[S_APRON] = p['apron']
        S[S_LIGHT] = p['light']
        S[S_KNEEL] = p['kneel']
        S[S_FOLD] = p['fold']
        S[S_SEED] = p['seed']
        S[S_EYE] = p['eye']
        S[S_EYEGLOW] = p['eyeglow']
        return J, R, S

    def _fingers(self, J, R, fr, wr, base, curl, spread, side):
        Rh = R[fr]
        # knuckles across the end of the palm (x across, z along the hand,
        # y out of the palm: fingers curl towards +y)
        for k in range(5):
            if k < 4:
                kx = (-0.024 + 0.016 * k) * side
                knuck = np.array([kx, 0.004, 0.088 - 0.004 * abs(k - 1.5)])
                splay = math.radians(spread * (k - 1.5) / 1.5) * side
                Lp, Ld = FINGER[0] * (0.82 if k == 3 else 1.0), FINGER[1] * (0.85 if k == 3 else 1.0)
            else:
                knuck = np.array([-0.034 * side, 0.012, 0.030])
                splay = -math.radians(38) * side
                Lp, Ld = 0.042, 0.036
            c = math.radians(curl[k])
            d1 = np.array([math.sin(splay), math.sin(c * 0.5) * 0.9, math.cos(splay) * math.cos(c * 0.5)])
            d1 = norm(d1)
            d2 = norm(np.array([math.sin(splay) * 0.6, math.sin(c * 1.1), math.cos(c * 1.1)]))
            a = J[wr] + Rh @ knuck
            b = a + Rh @ d1 * Lp
            t = b + Rh @ d2 * Ld
            J[base + 3 * k] = a
            J[base + 3 * k + 1] = b
            J[base + 3 * k + 2] = t
