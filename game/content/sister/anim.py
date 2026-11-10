# SPDX-License-Identifier: MIT
"""The Night Sister's animations as Poses: walk and chase cycles (phase 0..1,
right heel strike at 0); standing idle, breathing; searching with the
lantern held up, looking from side to side; kneeling at prayer with the
lantern on the floor, rocking; getting up from prayer; pushing a door open;
and the lunge.

The loops (idle, search, kneel) are at their old still pose at phase 0, so
that frame is the one the game always had."""
import math
import numpy as np
from rig import Pose

TAU = 2 * math.pi
WALK_CYCLE = 1.125         # metres per walk cycle (two steps): 0.75 tiles
CHASE_CYCLE = 1.5          # metres per chase cycle: 1 tile


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def foot_cycle(psi, cycle, duty, lift, width, pitch_strike, pitch_off):
    """Ankle (x, y, lift) and foot pitch for leg phase psi (0 = heel strike),
    the body still and the ground sliding back underneath."""
    half = cycle * duty / 2
    if psi < duty:
        s = psi / duty
        y = half - 2 * half * s
        z = 0.0
        pitch = pitch_strike * max(0.0, 1 - s * 5) - pitch_off * smooth((s - 0.6) / 0.4)
        z += 0.05 * smooth((s - 0.7) / 0.3)              # heel rising
    else:
        s = (psi - duty) / (1 - duty)
        y = -half + 2 * half * smooth(s)
        z = lift * math.sin(math.pi * s) ** 0.8
        pitch = -pitch_off * (1 - smooth(s * 1.4)) + pitch_strike * smooth((s - 0.6) / 0.4)
    return (width, y, z), pitch


def walk(phi, seed=7):
    """Slow, deliberate, one foot placed nearly in front of the other; the
    lantern swinging a little; the head hanging to one side."""
    fr, pr = foot_cycle(phi % 1, WALK_CYCLE, 0.58, 0.07, 0.075, 12, 28)
    fl, pl = foot_cycle((phi + 0.5) % 1, WALK_CYCLE, 0.58, 0.07, -0.075, 12, 28)
    s1 = math.sin(TAU * phi)
    c1 = math.cos(TAU * phi)
    s2 = math.sin(2 * TAU * phi)
    return Pose(
        pelvis=(0.012 * s1, 0.0, None), dip=-0.012,
        pelvis_yaw=5 * s1, pelvis_roll=-2.5 * s1,
        lean=11 + 1.5 * s2, chest_yaw=-6 * s1, chest_roll=1.5 * s1,
        head_roll=19 + 1.5 * s2, head_yaw=-2 * s1, head_pitch=-6 + 1.5 * math.cos(2 * TAU * phi),
        foot_r=fr, foot_l=fl, foot_pitch_r=pr, foot_pitch_l=pl,
        hand_r=(0.25 + 0.01 * s1, 0.20 + 0.03 * c1, 0.92 + 0.01 * s2),
        lantern_swing=(8 * math.sin(2 * TAU * phi - 1.1), 3 * math.sin(TAU * phi - 0.7)),
        hand_l=(-0.27, 0.03 + 0.11 * c1, 0.56 + 0.03 * abs(c1)),
        curl_l=(25, 30, 35, 40, 20),
        sway=(-0.02 * math.sin(TAU * phi - 0.6), -0.03),
        fold=0.9 * s1, seed=seed, hair_swing=(0.0, -0.01),
    )


def chase(phi, seed=7):
    """Lurching at you: long fast strides, bent forward, the head thrust out,
    the free hand reaching, the lantern swinging wildly."""
    fr, pr = foot_cycle(phi % 1, CHASE_CYCLE, 0.46, 0.17, 0.085, 10, 35)
    fl, pl = foot_cycle((phi + 0.5) % 1, CHASE_CYCLE, 0.46, 0.17, -0.085, 10, 35)
    s1 = math.sin(TAU * phi)
    c1 = math.cos(TAU * phi)
    s2 = math.sin(2 * TAU * phi)
    c2 = math.cos(2 * TAU * phi)
    return Pose(
        pelvis=(0.02 * s1, 0.04, None), dip=-0.05 - 0.02 * c2,
        pelvis_yaw=9 * s1, pelvis_roll=-4 * s1,
        lean=26 + 3 * s2, chest_yaw=-10 * s1, chest_roll=3 * s1, chest_lean=10,
        neck_lean=12, head_pitch=-22 + 3 * c2, head_roll=14 + 4 * s1, head_yaw=-4 * s1,
        foot_r=fr, foot_l=fl, foot_pitch_r=pr, foot_pitch_l=pl,
        hand_r=(0.27, 0.30 + 0.16 * -c1, 0.98 + 0.05 * s2), elbow_pole_r=(0.7, -0.5, 1.2),
        lantern_swing=(-18 * math.sin(TAU * phi + 0.4), 9 * math.sin(2 * TAU * phi)),
        hand_l=(-0.16, 0.55 + 0.12 * c1, 1.22 + 0.06 * s2), elbow_pole_l=(-0.45, 0.3, 0.4), hand_l_up=(0.0, 1.0, 0.25),
        palm_l=(0.2, -0.3, -1.0), curl_l=(15, 12, 10, 12, 5), spread_l=26,
        jaw=0.25 + 0.1 * s2,
        sway=(-0.04 * math.sin(TAU * phi - 0.6), -0.09), hem=0.29,
        fold=1.4 * s1, seed=seed, hair_swing=(0.0, -0.04),
    )


def idle(phi=0.0, seed=7):
    """Standing, breathing: a slow rise and fall of the chest, the head
    lolling a little further over, the lantern turning on its bail."""
    s = math.sin(TAU * phi)
    b = (1 - math.cos(TAU * phi)) / 2            # breath in: 0 at phase 0, 1 half way
    return Pose(
        pelvis=(0.004 * s, 0.0, None), dip=-0.01 - 0.006 * b,
        lean=12 - 1.5 * b, chest_lean=6 + 2.0 * b, head_roll=26 + 2.5 * s, head_pitch=-4 - 2.0 * b, head_yaw=4 - 3 * s,
        foot_r=(0.085, 0.03, 0.0), foot_l=(-0.085, -0.03, 0.0), foot_pitch_r=0, foot_pitch_l=0,
        hand_r=(0.25, 0.19, 0.91 + 0.012 * b), lantern_swing=(1.0 + 3.0 * s, 2.0 * s),
        hand_l=(-0.26 - 0.006 * s, 0.06, 0.52 + 0.010 * b), curl_l=(12 + 6 * b, 18 + 6 * b, 24 + 6 * b, 30 + 6 * b, 10), spread_l=22,
        seed=seed, hair_swing=(0.004 * s, 0.0),
    )


def search(phi=0.0, seed=7):
    """Holding the lantern up beside her face to see by it, and turning
    slowly from one side to the other with it: head, shoulders and lantern."""
    s = math.sin(TAU * phi)
    t = (1 - math.cos(TAU * phi)) / 2            # 0 looking to her left (the old pose), 1 to her right
    turn = -52 * t                               # degrees the shoulders have come round
    c, sn = math.cos(math.radians(turn)), math.sin(math.radians(turn))

    def round_(p):                               # a point carried round with the shoulders
        return (p[0] * c - p[1] * sn, p[0] * sn + p[1] * c, p[2])
    return Pose(
        pelvis=(0.0, 0.0, None), dip=-0.01, pelvis_yaw=0.3 * turn,
        lean=4, chest_lean=2, neck_lean=14, head_roll=8 - 12 * t, head_pitch=4 - 4 * math.sin(math.pi * t),
        head_yaw=18 - 30 * t, chest_yaw=8 + 0.7 * turn,
        foot_r=(0.09, 0.05, 0.0), foot_l=(-0.09, -0.04, 0.0),
        hand_r=round_((0.24, 0.30, 1.72 + 0.05 * math.sin(math.pi * t))),
        elbow_pole_r=round_((0.9, -0.2, 1.2)), hand_r_up=(0.0, 0.4, 1.0),
        palm_r=round_((-1.0, 0.0, 0.0)), curl_r=(80, 85, 90, 90, 50),
        lantern_swing=(-6.0 + 6.0 * s, 4.0 - 8.0 * s),
        hand_l=round_((-0.25, 0.08, 0.55)), curl_l=(20, 28, 34, 40, 14), spread_l=14,
        seed=seed, hair_swing=(0.008 * s, 0.0),
    )


def kneel(phi=0.0, seed=7):
    """At prayer on the chapel step: sitting back on her heels, head bowed,
    hands together under her chin, the lantern on the floor at her right;
    rocking forward over her hands and back."""
    s = math.sin(TAU * phi)
    return Pose(
        pelvis=(0.0, -0.06, 0.55),
        lean=14 + 4.0 * s, chest_lean=8 + 2.0 * s, neck_lean=26 + 3.0 * s, head_pitch=-26 - 4.0 * s, head_roll=8,
        legs_r=((0.10, 0.30, 0.07), (0.10, -0.17, 0.05), (0.10, -0.33, 0.03)),
        legs_l=((-0.10, 0.30, 0.07), (-0.10, -0.17, 0.05), (-0.10, -0.33, 0.03)),
        hand_r=(0.03, 0.26 + 0.035 * s, 1.00 - 0.03 * s), elbow_pole_r=(0.6, 0.0, 0.6), hand_r_up=(0.0, 0.3, 1.0), palm_r=(-1, 0, 0),
        hand_l=(-0.03, 0.26 + 0.035 * s, 1.00 - 0.03 * s), elbow_pole_l=(-0.6, 0.0, 0.6), hand_l_up=(0.0, 0.3, 1.0), palm_l=(1, 0, 0),
        curl_r=(30, 30, 30, 30, 20), curl_l=(30, 30, 30, 30, 20), spread_l=0, spread_r=0,
        lantern='floor', lantern_pos=(0.36, 0.22, 0.0),
        hem=0.02, r1=0.34, apron=0.20,
        seed=seed,
    )


RISE_FRAMES = 6


def rise(k, seed=7):
    """Getting up from prayer, frames 0..5 between kneel() and idle(): her
    right hand goes down to the lantern's bail, then she stands with it,
    the head coming up last."""
    t = (k + 1) / (RISE_FRAMES + 1)
    e = smooth(t)

    def L(a, b, u=e):
        return a + (b - a) * u

    def V(a, b, u=e):
        return tuple(x + (y - x) * u for x, y in zip(a, b))
    took = t > 0.42                     # the lantern has left the floor
    bail = (0.36, 0.22, 0.29)           # where her hand closes on it
    if not took:
        hand_r = V((0.03, 0.26, 1.00), bail, smooth(t / 0.42))
    else:
        hand_r = V(bail, (0.25, 0.19, 0.91), smooth((t - 0.42) / 0.58))
    up = smooth((t - 0.25) / 0.75)      # the body starts to rise once she has leant for the lantern
    head = smooth((t - 0.5) / 0.5)
    reach = math.sin(math.pi * min(t / 0.6, 1.0))        # leaning over to her right for it
    return Pose(
        pelvis=(0.02 * reach, L(-0.06, 0.0, up), L(0.55, 1.02, up)), pelvis_roll=-4 * reach,
        lean=L(14, 12) + 10 * reach, chest_lean=L(8, 6), chest_roll=-6 * reach,
        neck_lean=L(26, 22, head), head_pitch=L(-26, -4, head), head_roll=L(8, 26, head), head_yaw=L(0, 4, head),
        foot_r=(0.10, L(-0.17, 0.03, up), 0.0), foot_l=(-0.10, L(-0.17, -0.03, up), 0.0),
        hand_r=hand_r, elbow_pole_r=V((0.6, 0.0, 0.6), (0.6, -0.4, 1.2)),
        hand_r_up=V((0.0, 0.3, 1.0), (0.0, 0.0, 1.0)),
        curl_r=V((30, 30, 30, 30, 20), (70, 80, 85, 85, 40), smooth(t / 0.42)),
        hand_l=V((-0.03, 0.26, 1.00), (-0.26, 0.06, 0.52)), elbow_pole_l=V((-0.6, 0.0, 0.6), (-0.6, -0.3, 1.2)),
        curl_l=V((30, 30, 30, 30, 20), (12, 18, 24, 30, 10)), spread_l=L(0, 22), spread_r=L(0, 4),
        lantern='hand' if took else 'floor', lantern_pos=(0.36, 0.22, 0.0),
        lantern_swing=(L(8.0, 1.0), L(-5.0, 0.0)),
        hem=L(0.02, 0.27, up), r1=L(0.34, 0.26, up), apron=L(0.20, 0.60, up),
        seed=seed,
    )


DOOR_FRAMES = 4


def door(k, seed=7):
    """Pushing a door open with her free hand: reaching for it (0), her
    palm on it (1), leaning through the push (2), the arm falling away (3)."""
    r = (0.45, 0.85, 1.0, 0.5)[k]       # how far the arm is out
    lean = (2.0, 6.0, 12.0, 5.0)[k]     # her weight behind it
    low = (0.0, 0.0, 0.0, 0.45)[k]      # the hand dropping after the push
    e = smooth(r)
    return Pose(
        pelvis=(0.0, 0.03 * e, None), dip=-0.01 - 0.02 * e,
        lean=12 + lean, chest_yaw=10 * e, head_roll=26 - 8 * e, head_pitch=-4 - 4 * e, head_yaw=4,
        foot_r=(0.085, 0.03 - 0.05 * e, 0.0), foot_l=(-0.085, -0.03 + 0.16 * e, 0.0),
        hand_r=(0.26, 0.15, 0.91), lantern_swing=(1.0 - 6.0 * e, 2.0 * e),
        hand_l=(-0.26 + 0.12 * e, 0.06 + 0.52 * e, 0.52 + (0.80 - 0.5 * low) * e),
        elbow_pole_l=(-0.9, 0.0, 0.8), hand_l_up=(0.0, 0.5, 1.0),
        palm_l=(0.0, -1.0, 0.1), curl_l=(10, 8, 8, 10, 4), spread_l=18,
        seed=seed,
    )


ATTACK_FRAMES = 8


def attack(k, seed=7):
    """The lunge, seen from 0.75 tiles, in 8 frames: rearing (0) through
    reaching to on you (7). Frames 0 and 7 are the old first and last."""
    t = k / (ATTACK_FRAMES - 1)
    return Pose(
        pelvis=(0.0, 0.05 + 0.10 * t, None), dip=-0.04 - 0.10 * t,
        foot_r=(0.12, 0.10 + 0.10 * t, 0.0), foot_l=(-0.12, -0.18, 0.0),
        lean=22 + 18 * t, chest_lean=6 + 8 * t, neck_lean=6, head_pitch=-(22 + 18 * t + 6 + 8 * t + 6) + 18 - 4 * t,
        head_roll=10 - 8 * t, head_yaw=0,
        hand_r=(0.32, 0.30 + 0.20 * t, 1.45 + 0.02 * t), elbow_pole_r=(0.9, -0.2, 1.0),
        hand_r_up=(0.0, 0.2, 1.0), palm_r=(-1.0, 0.2, 0.0), curl_r=(85, 90, 90, 90, 50),
        lantern_swing=(-10 - 10 * t, 6),
        hand_l=(-0.24 + 0.04 * t, 0.42 + 0.28 * t, 1.50 - 0.04 * t), elbow_pole_l=(-0.9, 0.0, 1.0),
        hand_l_up=(0.0, 1.0, 0.3), palm_l=(0.0, -0.4, -1.0), curl_l=(18, 12, 10, 14, 4), spread_l=30,
        jaw=0.35 + 0.65 * t,
        sway=(0.0, -0.05), seed=seed, eye=0.0,
    )
