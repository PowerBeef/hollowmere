import os
import sys, time
from rig import Pose
from view import shoot, sheet
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'build', 'preview'); os.makedirs(SP, exist_ok=True)
def run(name, poses, views=(0, 45, 90, 135, 180), ss=2, scale=3, **kw):
    t = time.time()
    f = [shoot(p, v, ss=ss, **kw) for p in poses for v in views]
    sheet(f, f'{SP}/{name}.png', scale)
    print(name, f'{time.time() - t:.1f}s')
if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else 'sis', [Pose()])
