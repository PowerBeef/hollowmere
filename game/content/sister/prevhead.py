# SPDX-License-Identifier: MIT
import os
import sys
from rig import Pose
from view import shoot, sheet
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'build', 'preview'); os.makedirs(SP, exist_ok=True)
def heads(name, pose, views=(0, 35, 90), dist=1.6):
    f = [shoot(pose, v, dist=dist, W=200, H=200, ss=2, plane_bottom=1.45, plane_w=0.55, plane_h=0.55, eye=1.75) for v in views]
    sheet(f, f'{SP}/{name}.png', 2)
if __name__ == '__main__':
    heads(sys.argv[1], Pose())
