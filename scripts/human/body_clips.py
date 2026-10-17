"""The Human's full-body and upper-body clips (Character rig v1), authored as poses (pose.py) and baked to keys.
Angles: Godot euler degrees in the character's rest frame. Arms: +X raises forward, -X back; Right arm +Z out
(Left -Z out). Spine/Head -X bends forward. LowerLeg -X bends the knee, Foot -X points the toes.
"""
import math

from mathutils import Matrix, Vector

import rig as R

import lib
import pose as PZ

HIPS = Vector((0, 0.84, 0))


def tip(theta, pivot=(0, 0.02, -0.14)):
    """Hips placement for the whole body tipped forward by theta (degrees) about a floor line through `pivot`."""
    p = Vector(pivot)
    r = lib.rot((-theta, 0, 0))
    return (p + r @ (HIPS - p), (-theta, 0, 0))


def arms(fwd_l, out_l, fwd_r, out_r, elbow=0.0):
    """Upper-arm swing for both arms (+fwd forward, +out away from the body) and elbow bend (+ bends)."""
    return {'LeftUpperArm': (fwd_l, 0, -out_l), 'RightUpperArm': (fwd_r, 0, out_r),
            'LeftLowerArm': (elbow, 0, 0), 'RightLowerArm': (elbow, 0, 0)}


def merge(*ds):
    out = {}
    for d in ds:
        out.update(d)
    return out


def faceplant():
    """Tips forward stiff as a plank, arms flung back, face first into the floor; heels kick up, then settle prone."""
    toes = {'LeftFoot': (-20, 0, 0), 'RightFoot': (-20, 0, 0)}         # up on the toes (grounded)
    flat = {'LeftFoot': (-70, 0, 0), 'RightFoot': (-70, 0, 0)}

    def knees(a):
        return {'LeftLowerLeg': (-a, 0, 0), 'RightLowerLeg': (-a, 0, 0)}
    return [
        (0, {'rot': merge(arms(5, 20, 5, 20), {'Spine': (-4, 0, 0)})}),
        (6, {'hips': tip(10), 'rot': merge(arms(-30, 25, -25, 30, 10), {'Head': (8, 0, 0)}, toes), 'ground': True}),
        (12, {'hips': tip(30), 'rot': merge(arms(-55, 30, -50, 35, 5), {'Head': (18, 0, 0)}, toes), 'ground': True}),
        (18, {'hips': tip(62), 'rot': merge(arms(-70, 25, -70, 25), {'Head': (22, 0, 0)}, flat)}),
        (22, {'hips': tip(84), 'rot': merge(arms(-75, 20, -75, 20), {'Head': (15, 0, 0)}, flat)}),
        (24, {'hips': tip(90), 'rot': merge(arms(-70, 18, -70, 18), {'Head': (2, 0, 0)}, flat), 'ground': True}),
        (28, {'hips': tip(90), 'lift': 0.03, 'rot': merge(arms(-55, 20, -55, 20, 15), {'Head': (5, 0, 0)}, flat,
                                                          knees(65)), 'ground': True}),
        (34, {'hips': tip(90), 'rot': merge(arms(-20, 22, -20, 22, 10), {'Head': (3, 0, 0)}, flat, knees(35)),
              'ground': True}),
        (42, {'hips': tip(90), 'rot': merge(arms(0, 12, 0, 12, 5), {'Head': (3, 0, 0)}, flat, knees(5)),
              'ground': True}),
        (48, {'hips': tip(90), 'rot': merge(arms(0, 10, 0, 10, 5), {'Head': (3, 0, 0)}, flat, knees(5)),
              'ground': True}),
    ]


# The tub in Seat space (bathroom `tub` prop: Seat on the outer rim edge, -Z toward the room, rim at y 0).
TUB = [((-0.85, -0.55, 0.0), (0.85, 0.0, 0.09)), ((-0.85, -0.55, 0.71), (0.85, 0.0, 0.8)),
       ((-0.85, -0.55, 0.0), (-0.76, 0.0, 0.8)), ((0.76, -0.55, 0.0), (0.85, 0.0, 0.8)),
       ((-0.85, -0.55, 0.0), (0.85, -0.425, 0.8)), ((-3, -1.5, -3), (3, -0.55, 3))]     # + the room floor


def sit_tub():
    """Lands wedged in the tub (back on the far rim, knees hooked over the near rim, feet dangling), arms flung out,
    then settles with the hands on the thighs and holds."""
    def p(dy, lean, head, kick, hands):
        ik = {}
        for s in (-1, 1):
            n = 'Left' if s < 0 else 'Right'
            ik[n + 'Leg'] = ((0.11 * s, -0.07 + kick * (1 if s > 0 else -0.5), -0.25), (0.11 * s, 0.6, -0.1))
            if hands:
                ik[n + 'Arm'] = ((0.16 * s, 0.17, 0.2), (0.55 * s, 0.25, 0.55))
        return {'hips': ((0, -0.11 + dy, 0.31), (lean, 0, 0)), 'ik': ik,
                'rot': merge(arms(-25, 70, -25, 70, 35), {'Spine': (-8, 0, 0), 'Chest': (-10, 0, 0),
                                                          'Head': (head, 0, 0), 'LeftFoot': (-25, 0, 0),
                                                          'RightFoot': (-25, 0, 0)})}
    return [(0, p(0.05, 50, -20, 0.0, False)), (8, p(-0.01, 62, -30, 0.03, False)), (20, p(0.0, 60, -26, 0.0, True)),
            (40, p(0.005, 59, -25, 0.02, True)), (60, p(0.0, 60, -26, 0.0, True))]


def climb_out_tub():
    """From sit_tub's end: sits up and grabs the near rim, swings the right leg out to the floor, hauls over, brings
    the left leg out and stands in front of the tub facing the room. Seat space (root = tub Seat, floor at -0.55)."""
    fl = -0.55
    rim_hands = {'LeftArm': ((-0.28, 0.045, 0.05), (-0.7, 0.3, 0.4)), 'RightArm': ((0.28, 0.045, 0.05), (0.7, 0.3, 0.4))}
    hooked = {}
    for s in (-1, 1):
        n = 'Left' if s < 0 else 'Right'
        hooked[n + 'Leg'] = ((0.11 * s, -0.07, -0.25), (0.11 * s, 0.6, -0.1))
    end = sit_tub()[-1][1]
    return [
        (0, end),
        (14, {'hips': ((0, -0.16, 0.3), (18, 0, 0)), 'ik': merge(hooked, rim_hands), 'world': palms(),
              'rot': {'Spine': (-10, 0, 0), 'Head': (-8, 0, 0)}}),
        (26, {'hips': ((0, 0.06, 0.2), (-22, 0, 0)), 'ik': merge(rim_hands, {
            'LeftLeg': hooked['LeftLeg'], 'RightLeg': ((0.16, 0.1, -0.28), (0.3, 0.9, -0.5))}),
              'world': merge(palms(), {'RightFoot': (-20, -20, 0)}), 'rot': {'Head': (15, 0, 0)}}),
        (36, {'hips': ((0, 0.12, 0.02), (-35, 0, 0)), 'ik': merge(rim_hands, {
            'LeftLeg': ((-0.11, 0.0, -0.2), (-0.11, 0.8, -0.3)), 'RightLeg': ((0.16, fl + ANK, -0.3), (0.3, 0.2, -0.8))}),
              'world': merge(palms(), {'RightFoot': (0, -20, 0)}), 'rot': {'Head': (20, 0, 0)}}),
        (44, {'hips': ((0, 0.1, -0.12), (-40, 0, 0)), 'ik': merge(rim_hands, {
            'LeftLeg': ((-0.13, 0.12, -0.2), (-0.3, 0.8, -0.6)), 'RightLeg': ((0.16, fl + ANK, -0.3), (0.3, 0.2, -0.8))}),
              'world': merge(palms(), {'RightFoot': (0, -20, 0), 'LeftFoot': (-30, 0, 0)}), 'rot': {'Head': (20, 0, 0)}}),
        (54, {'hips': ((0, fl + 0.7, -0.3), (-24, 0, 0)), 'ik': {
            'LeftLeg': ((-0.13, fl + ANK, -0.34), (-0.13, 0.2, -1.0)), 'RightLeg': ((0.16, fl + ANK, -0.3), (0.3, 0.2, -0.9)),
            'LeftArm': ((-0.18, fl + 0.62, -0.5), (-0.6, 0.3, 0)), 'RightArm': ((0.2, fl + 0.62, -0.5), (0.6, 0.3, 0))},
              'world': {'RightFoot': (0, -20, 0), 'LeftFoot': (0, 0, 0)}, 'rot': {'Head': (12, 0, 0)}}),
        (66, {'hips': ((0, fl + 0.83, -0.32), (-3, 0, 0)), 'ik': {
            'LeftLeg': ((-0.135, fl + ANK, -0.32), (-0.135, 0.2, -1.0)), 'RightLeg': ((0.135, fl + ANK, -0.32), (0.135, 0.2, -1.0))},
              'world': FLAT, 'rot': arms(3, 6, 3, 6, 8)}),
    ]


ANK = 0.095                       # ankle joint height when the foot is flat
FLAT = {'LeftFoot': (0, 0, 0), 'RightFoot': (0, 0, 0)}          # world: soles on the floor


def palm_down(s, fingers=-1):
    """World turn for a hand flat on the floor, fingers toward -Z (fingers=-1) or +Z (1); s = -1 left, 1 right."""
    return lib.rot((0, 0, 90 * s)) @ lib.rot((-90 * fingers, 0, 0))


def palms(fingers=-1):
    return {'LeftHand': palm_down(-1, fingers), 'RightHand': palm_down(1, fingers)}


def stand_feet(zl=0.0, zr=0.0, x=0.135):
    return {'LeftLeg': ((-x, ANK, zl), (-x, 0.5, zl - 0.6)), 'RightLeg': ((x, ANK, zr), (x, 0.5, zr - 0.6))}


def get_up_front():
    """From prone (faceplant's end, Hips over the origin): push up, onto all fours, right foot forward, stand."""
    flat_prone = {'LeftFoot': (-70, 0, 0), 'RightFoot': (-70, 0, 0)}
    kneel = {}
    for s in (-1, 1):
        n = 'Left' if s < 0 else 'Right'
        kneel[n + 'Leg'] = ((0.1 * s, 0.08, 0.5), (0.1 * s, -0.5, -0.3))
    hands_floor = {'LeftArm': ((-0.27, 0.045, -0.42), (-0.6, 0.5, -0.1)), 'RightArm': ((0.27, 0.045, -0.42), (0.6, 0.5, -0.1))}
    back_feet = {'LeftFoot': (180, 0, 0), 'RightFoot': (180, 0, 0)}
    return [
        (0, {'hips': ((0, 0.2, 0), (-90, 0, 0)), 'rot': merge(arms(0, 10, 0, 10, 5), {'Head': (3, 0, 0)}, flat_prone),
             'ground': True}),
        (10, {'hips': ((0, 0.2, 0), (-90, 0, 0)), 'ik': hands_floor, 'world': palms(),
              'rot': merge({'Head': (12, 0, 0)}, flat_prone), 'ground': True}),
        (20, {'hips': ((0, 0.2, 0.02), (-72, 0, 0)), 'ik': hands_floor, 'world': palms(),
              'rot': merge({'Head': (25, 0, 0)}, flat_prone), 'ground': True}),
        (32, {'hips': ((0, 0.5, 0.16), (-95, 0, 0)), 'ik': merge(hands_floor, kneel), 'world': palms(),
              'rot': merge({'Head': (30, 0, 0), 'Chest': (8, 0, 0)}, back_feet), 'ground': True}),
        (44, {'hips': ((0, 0.52, 0.14), (-55, 0, 0)),
              'ik': merge({'LeftLeg': kneel['LeftLeg'], 'RightLeg': ((0.13, ANK, -0.12), (0.13, 0.8, -0.8)),
                           'RightArm': ((0.16, 0.5, -0.16), (0.6, 0.6, 0.2)), 'LeftArm': ((-0.1, 0.5, -0.12), (-0.6, 0.6, 0.2))}),
              'rot': {'Head': (25, 0, 0), 'LeftFoot': (180, 0, 0)}, 'world': {'RightFoot': (0, 0, 0)}}),
        (56, {'hips': ((0, 0.72, 0.04), (-28, 0, 0)), 'ik': merge(stand_feet(0.06, -0.06),
              {'RightArm': ((0.2, 0.66, -0.22), (0.6, 0.8, 0.2)), 'LeftArm': ((-0.2, 0.7, -0.2), (-0.6, 0.8, 0.2))}),
              'rot': {'Head': (18, 0, 0)}, 'world': FLAT}),
        (66, {'hips': ((0, 0.83, 0), (-4, 0, 0)), 'ik': stand_feet(), 'rot': arms(3, 6, 3, 6, 8), 'world': FLAT}),
        (74, {'rot': {}}),
    ]


def get_up_back():
    """From supine (Hips over the origin): sit up, scoot back pulling the feet in, crouch over the feet, stand."""
    hands_back = {'LeftArm': ((-0.24, 0.045, 0.5), (-0.6, 0.4, 0.2)), 'RightArm': ((0.24, 0.045, 0.5), (0.6, 0.4, 0.2))}
    legs_long = {}
    for s in (-1, 1):
        n = 'Left' if s < 0 else 'Right'
        legs_long[n + 'Leg'] = ((0.13 * s, 0.115, -0.62), (0.13 * s, 0.7, -0.3))
    toes_up = {'LeftFoot': (15, 0, 0), 'RightFoot': (15, 0, 0)}
    return [
        (0, {'hips': ((0, 0.2, 0), (90, 0, 0)), 'rot': merge(arms(0, 15, 0, 15, 5), {'Head': (-8, 0, 0)}, toes_up),
             'ground': True}),
        (12, {'hips': ((0, 0.15, 0.06), (35, 0, 0)), 'ik': merge(legs_long, hands_back), 'world': palms(1),
              'rot': merge({'Spine': (-10, 0, 0), 'Head': (-15, 0, 0)}, toes_up), 'ground': True}),
        (24, {'hips': ((0, 0.15, 0.3), (12, 0, 0)), 'ik': merge(stand_feet(-0.06, -0.02), hands_back),
              'world': merge(palms(1), FLAT), 'rot': {'Spine': (-12, 0, 0), 'Chest': (-8, 0, 0), 'Head': (-10, 0, 0)}}),
        (36, {'hips': ((0, 0.42, 0.12), (-45, 0, 0)), 'ik': merge(stand_feet(-0.04, 0.0),
              {'LeftArm': ((-0.18, 0.42, -0.2), (-0.6, 0.6, 0.3)), 'RightArm': ((0.18, 0.42, -0.2), (0.6, 0.6, 0.3))}),
              'rot': {'Spine': (-10, 0, 0), 'Head': (25, 0, 0)}, 'world': FLAT}),
        (48, {'hips': ((0, 0.68, 0.06), (-22, 0, 0)), 'ik': merge(stand_feet(-0.02, 0.0),
              {'LeftArm': ((-0.2, 0.62, -0.18), (-0.6, 0.8, 0.3)), 'RightArm': ((0.2, 0.62, -0.18), (0.6, 0.8, 0.3))}),
              'rot': {'Head': (12, 0, 0)}, 'world': FLAT}),
        (60, {'hips': ((0, 0.83, 0), (-3, 0, 0)), 'ik': stand_feet(), 'rot': arms(3, 6, 3, 6, 8), 'world': FLAT}),
        (68, {'rot': {}}),
    ]


def stumble():
    """Trips on the right foot: lurches forward over three scrambling steps, arms windmilling; ends off-balance
    forward (chain into faceplant, or blend back to idle). The Hips travel forward about 0.6 m (json `end`)."""
    def feet(lz, ly, rz, ry, lt=0, rt=0):
        ly, ry = ly + 0.0016 * abs(lt), ry + 0.0016 * abs(rt)          # a tilted foot rides on its heel or toes
        return ({'LeftLeg': ((-0.135, ANK + ly, lz), (-0.135, 0.6, lz - 0.6)),
                 'RightLeg': ((0.135, ANK + ry, rz), (0.135, 0.6, rz - 0.6))},
                {'LeftFoot': (lt, 0, 0), 'RightFoot': (rt, 0, 0)})

    def k(hips, pitch, f, arm, head=10, spine=-8):
        ik, w = f
        return {'hips': (hips, (pitch, 0, 0)), 'ik': ik, 'world': w,
                'rot': merge(arm, {'Spine': (spine, 0, 0), 'Head': (head, 0, 0)})}
    return [
        (0, k((0, 0.83, 0), 0, feet(0, 0, 0, 0), arms(3, 6, 3, 6, 8), 0, 0)),
        (5, k((0, 0.82, -0.1), -16, feet(-0.06, 0.12, 0.06, 0, -25, 10), arms(25, 60, 15, 65, 20), 20)),
        (11, k((0, 0.8, -0.26), -26, feet(-0.36, 0, 0.08, 0.06, 10, -25), arms(120, 40, -40, 50, 30), 24)),
        (17, k((0, 0.81, -0.42), -26, feet(-0.32, 0.08, -0.56, 0, -20, 10), arms(-40, 50, 130, 40, 30), 22)),
        (23, k((0, 0.78, -0.58), -36, feet(-0.74, 0, -0.46, 0.06, 8, -30), arms(140, 70, 70, 80, 20), 28, -12)),
        (30, k((0, 0.78, -0.72), -42, feet(-0.66, 0.03, -0.8, 0.02, 0, -10), arms(60, 85, 150, 60, 15), 32, -14)),
        (36, k((0, 0.76, -0.86), -50, feet(-0.7, 0.06, -0.8, 0, -30, 0), arms(110, 90, 90, 90, 10), 36, -16)),
    ]


def brush_loop(rig):
    """Right arm brushing the front teeth: bristles at the mouth (Foam), handle out to the right, palm toward the
    face; one side-to-side stroke cycle in 0.5 s. Keys the right arm and hand only (upper layer)."""
    import pose as PZ
    mouth = Vector(PZ.MARKERS['Foam']['pos'])
    gx = Vector((-0.78, 0.08, 0.62)).normalized()                  # grip -> bristles: from front-right into the mouth
    gy = Vector((0, 0.25, -1))                                     # back of the hand forward, bristles to the teeth
    gy = (gy - gx * gy.dot(gx)).normalized()
    basis = Matrix((gx, gy, gx.cross(gy))).transposed()
    fingers = R.finger_pose(1, 'grip')
    keys = []
    for f in (0, 4, 8, 11, 15):
        a = math.sin(2 * math.pi * f / 15)
        head = mouth + Vector((0.025 * a, -0.008 + 0.005 * abs(a), -0.022))      # bristles scrub side to side
        b = lib.rot((0, 5 * a, 0)) @ basis
        pos = head - (b @ Vector((1, 0, 0))) * 0.17 - (b @ Vector((0, 1, 0))) * 0.01
        wrist, turn = PZ.grip(rig, 1, pos, b)
        keys.append((f, {'ik': {'RightArm': (wrist, (0.6, 1.0, 0.3))}, 'world': {'RightHand': turn},
                         'local': fingers}))
    return keys


def sit_floor():
    """Plops down on the floor from standing: squat, bump, legs shoot out, then sits leaning back on the hands
    (hold the last frame). The Hips end 0.2 m behind the start (json end)."""
    hands_back = {'LeftArm': ((-0.24, 0.045, 0.5), (-0.6, 0.4, 0.2)), 'RightArm': ((0.24, 0.045, 0.5), (0.6, 0.4, 0.2))}
    legs = {}
    for s in (-1, 1):
        n = 'Left' if s < 0 else 'Right'
        legs[n + 'Leg'] = ((0.14 * s, 0.115, -0.5), (0.14 * s, 0.7, -0.2))
    toes_up = {'LeftFoot': (15, 0, 0), 'RightFoot': (15, 0, 0)}
    return [
        (0, {'hips': ((0, 0.83, 0), (-2, 0, 0)), 'ik': stand_feet(), 'world': FLAT, 'rot': arms(3, 6, 3, 6, 8)}),
        (8, {'hips': ((0, 0.5, 0.12), (-25, 0, 0)), 'ik': stand_feet(), 'world': FLAT,
             'rot': merge(arms(45, 20, 45, 20, 20), {'Head': (10, 0, 0)})}),
        (13, {'hips': ((0, 0.16, 0.2), (15, 0, 0)), 'ik': legs, 'world': toes_up, 'ground': True,
              'rot': merge(arms(60, 45, 60, 45, 10), {'Head': (-15, 0, 0), 'Spine': (-5, 0, 0)})}),
        (17, {'hips': ((0, 0.16, 0.2), (8, 0, 0)), 'ik': legs, 'world': toes_up, 'ground': True, 'lift': 0.03,
              'rot': merge(arms(30, 40, 30, 40, 10), {'Head': (5, 0, 0)})}),
        (24, {'hips': ((0, 0.16, 0.2), (30, 0, 0)), 'ik': merge(legs, hands_back), 'world': merge(palms(1), toes_up),
              'ground': True, 'rot': {'Spine': (-10, 0, 0), 'Head': (-15, 0, 0)}}),
        (40, {'hips': ((0, 0.16, 0.2), (28, 0, 0)), 'ik': merge(legs, hands_back), 'world': merge(palms(1), toes_up),
              'ground': True, 'rot': {'Spine': (-10, 0, 0), 'Head': (-12, 0, 0)}}),
    ]


WALK = {'stride': 1.0, 'cycle': 1.0, 'speed': 1.0}       # m per full cycle (two steps), s, m/s


def _foot(phase, side):
    """Ankle (z, lift, pitch) of one foot at gait phase in [0, 1): stance first half (left), swing second half."""
    half = WALK['stride'] / 4                               # foot travels +-half around the hips
    u = (phase + (0.0 if side < 0 else 0.5)) % 1.0
    if u < 0.5:                                             # stance: slides back under the body at walk speed
        v = u / 0.5
        z = -half + 2 * half * v
        pitch = 15 * max(0.0, 1 - v / 0.15) - 25 * max(0.0, (v - 0.75) / 0.25)   # heel strike .. push-off
        lift = 0.0
    else:                                                   # swing: forward and up
        v = (u - 0.5) / 0.5
        e = v * v * (3 - 2 * v)
        z = half - 2 * half * e
        pitch = -25 + 40 * e
        lift = 0.07 * math.sin(math.pi * v)
    y = ANK + lift + (0.15 * math.sin(math.radians(-pitch)) if pitch < 0 else 0.06 * math.sin(math.radians(pitch)))
    return z, y, pitch


def walk_loop():
    """In-place walk, one cycle (left step, right step). The feet slide back at WALK speed while planted; gameplay
    moves the root at that speed so they stick to the floor."""
    n = round(WALK['cycle'] * 30)
    keys = []
    for f in range(0, n + 1, 2):
        ph = f / n
        c, sn = math.cos(2 * math.pi * ph), math.sin(2 * math.pi * ph)
        ik, world = {}, {}
        for s in (-1, 1):
            nm = 'Left' if s < 0 else 'Right'
            z, y, pitch = _foot(ph, s)
            ik[nm + 'Leg'] = ((0.12 * s, y, z), (0.12 * s, 0.5, z - 0.6))
            world[nm + 'Foot'] = (pitch, 0, 0)
        hips = ((-0.015 * sn, 0.795 - 0.012 * math.cos(4 * math.pi * ph), 0), (-3, -5 * c, 2 * sn))
        rot = merge(arms(-20 * c, 4, 20 * c, 4, 14), {'Chest': (0, 8 * c, 0), 'Head': (3, -3 * c, 0),
                                                      'Spine': (-2, 0, -1.5 * sn)})
        keys.append((f, {'hips': hips, 'ik': ik, 'world': world, 'rot': rot}))
    return keys


def _turn(sign):
    """90 degrees in place in two steps, leading with the foot on the turning side (sign +1 = left)."""
    lead, trail = (-1, 1) if sign > 0 else (1, -1)

    def foot(s, yaw):
        r = lib.rot((0, yaw, 0))
        p = r @ Vector((0.135 * s, ANK, 0))
        return (p, p + r @ Vector((0, 0.4, -0.6)))

    def k(yaw_hips, yaw_lead, yaw_trail, dip=0.0):
        ik, world = {}, {}
        for s, yaw in ((lead, yaw_lead), (trail, yaw_trail)):
            nm = 'Left' if s < 0 else 'Right'
            ik[nm + 'Leg'] = foot(s, yaw)
            world[nm + 'Foot'] = (0, yaw, 0)
        return {'hips': ((0, 0.83 - dip, 0), (-2, yaw_hips, 0)), 'ik': ik, 'world': world,
                'rot': merge(arms(3, 8, 3, 8, 10), {'Head': (0, 10 * sign, 0)})}
    t = 90 * sign
    return [(0, k(0, 0, 0)), (8, k(0.4 * t, 0.55 * t, 0, 0.02)), (16, k(0.8 * t, 0.55 * t, t, 0.02)),
            (22, k(t, t, t, 0.01)), (28, k(t, t, t))]


def turn_L():
    return _turn(1)


def turn_R():
    return _turn(-1)


def step():
    """One short step forward (0.3 m): left, then the right foot joins. The Hips end 0.3 m forward (json end)."""
    def k(zl, zr, zh, dip=0.0, pitch=-2):
        return {'hips': ((0, 0.83 - dip, zh), (pitch, 0, 0)), 'ik': stand_feet(zl, zr), 'world': FLAT,
                'rot': arms(3 - 12 * (zl - zr) / 0.3, 6, 3 + 12 * (zl - zr) / 0.3, 6, 10)}
    return [(0, k(0, 0, 0)), (12, k(-0.3, 0, -0.15, 0.025, -4)), (22, k(-0.3, -0.3, -0.3, 0.01)),
            (30, k(-0.3, -0.3, -0.3))]


def brace():
    """Braces for an impact ahead: hands up and forward, palms out, elbows soft, knees giving a little. Holds the end
    pose (a target pose for the active ragdoll, M2)."""
    def palm_out(s):
        return lib.rot((90, 0, 0)) @ palm_down(s)

    def k(dip, spine, head, arm, hands=None):
        return {'hips': ((0, 0.83 - dip, 0.02 * dip / 0.04), (-4 * dip / 0.04, 0, 0)), 'ik': stand_feet(),
                'world': merge(FLAT, hands or {}), 'rot': merge(arm, {'Spine': (spine, 0, 0), 'Head': (head, 0, 0)})}
    out = {'LeftHand': palm_out(-1), 'RightHand': palm_out(1)}
    return [(0, k(0, 0, 0, arms(3, 6, 3, 6, 8))),
            (4, k(0.03, -6, 6, arms(55, 20, 55, 20, 40))),
            (8, k(0.04, -10, 10, arms(78, 16, 78, 16, 25), out)),
            (16, k(0.04, -10, 10, arms(78, 16, 78, 16, 25), out))]


FULL_EXTRA = {'stumble': stumble, 'climb_out_tub': climb_out_tub, 'walk_loop': walk_loop, 'turn_L': turn_L,
              'turn_R': turn_R, 'step': step, 'sit_floor': sit_floor, 'brace': brace}
UPPER = {'brush_loop': (brush_loop, 1)}
LOOPS = ['brush_loop', 'walk_loop']


def squat():
    """Deep squat and hold (character-system mock: poke-through check): heels down, knees forward and out, torso
    leaning in, arms forward for balance."""
    def k(h, z, lean, arm, knee_out=0.0):
        return {'hips': ((0, h, z), (-lean, 0, 0)), 'world': FLAT,
                'ik': {'LeftLeg': ((-0.16, ANK, 0.0), (-0.16 - knee_out, 0.6, -0.8)),
                       'RightLeg': ((0.16, ANK, 0.0), (0.16 + knee_out, 0.6, -0.8))},
                'rot': merge(arm, {'Spine': (-lean * 0.4, 0, 0), 'Head': (lean * 0.7, 0, 0)})}
    return [(0, k(0.83, 0, 0, arms(3, 6, 3, 6, 8))), (12, k(0.6, 0.06, 18, arms(40, 12, 40, 12, 15), 0.1)),
            (22, k(0.42, 0.12, 28, arms(75, 12, 75, 12, 20), 0.25)), (34, k(0.42, 0.12, 28, arms(75, 12, 75, 12, 20), 0.25))]



# --- NPC gestures (E00/E01 cast; Character.anim plays them by name). Torso layer: spine, neck, head, both arms and
# fingers only, so they play over a standing or a seated (sit_chair) body. Character space, -Z forward, +X = right.

def _fingers(kind_l='relaxed', kind_r='relaxed', point=False):
    f = merge(R.finger_pose(-1, kind_l), R.finger_pose(1, kind_r))
    if point:                                                       # index straight out of a fist
        for sg in ('Proximal', 'Intermediate', 'Distal'):
            f['RightIndex' + sg] = (0.0, 0.0, 0.0)
    return f


REST_ARMS = arms(3, 6, 3, 6, 8)


def _t(rot=None, ik=None, local=None):
    return {'rot': merge(REST_ARMS, rot or {}), 'ik': ik or {}, 'local': local or _fingers()}


def wave():
    """Friendly wave with the right hand: up beside the head, forearm swinging side to side 3 times, then down."""
    def up(dx, head=0):
        return _t({'Head': (0, 0, head), 'UpperChest': (0, 0, -2)},
                  {'RightArm': ((0.36 + dx, 1.6, -0.1), (0.62, 1.2, 0.25))}, _fingers(kind_r='spread'))
    return [(0, _t()), (8, up(0.0, 3)), (13, up(0.07, 4)), (18, up(-0.05, 4)), (23, up(0.07, 4)), (28, up(-0.05, 4)),
            (33, up(0.04, 3)), (40, up(0.0, 2)), (50, _t())]


def point():
    """Points ahead with the right index finger (arm straight out, a little to the right), holds, drops."""
    p = _t({'RightUpperArm': (82, 0, 14), 'RightLowerArm': (4, 0, 0), 'Head': (-4, 0, 0), 'UpperChest': (-3, 0, 0)},
           local=_fingers(kind_r='grip', point=True))
    return [(0, _t()), (8, p), (38, p), (48, _t())]


def throw():
    """Overhand throw with the right arm (the toast): wind back, whip forward and release, follow through."""
    return [(0, _t()),
            (9, _t({'RightUpperArm': (-35, 0, 85), 'RightLowerArm': (100, 0, 0), 'Spine': (4, 18, 0),
                    'UpperChest': (2, 10, 0), 'LeftUpperArm': (40, 0, -25), 'Head': (0, -10, 0)},
                   local=_fingers(kind_r='grip'))),
            (14, _t({'RightUpperArm': (115, 0, 25), 'RightLowerArm': (15, 0, 0), 'Spine': (-8, -16, 0),
                     'UpperChest': (-4, -8, 0), 'LeftUpperArm': (-10, 0, -20), 'Head': (-4, 6, 0)},
                    local=_fingers(kind_r='spread'))),
            (21, _t({'RightUpperArm': (70, 0, 10), 'RightLowerArm': (25, 0, 0), 'Spine': (-10, -12, 0),
                     'UpperChest': (-4, -6, 0), 'Head': (-4, 4, 0)})),
            (36, _t())]


def laugh():
    """Belly laugh: head thrown back, hands to the belly, shoulders bouncing; 2 s."""
    keys = [(0, _t())]
    hands = {'LeftArm': ((-0.1, 1.0, -0.21), (-0.4, 1.1, 0.2)), 'RightArm': ((0.1, 1.0, -0.21), (0.4, 1.1, 0.2))}
    for i, f in enumerate(range(6, 55, 4)):
        b = 1 if i % 2 else -1
        keys.append((f, _t({'Head': (14 + 3 * b, 0, 2 * b), 'UpperChest': (5 + 3 * b, 0, 0), 'Spine': (3, 0, 0),
                            'LeftShoulder': (0, 0, 2 * b), 'RightShoulder': (0, 0, -2 * b)}, hands)))
    keys.append((64, _t()))
    return keys


def facepalm():
    """Right palm to the forehead, head drops into it, a slow shake; then the hand comes down."""
    def k(shake):
        return _t({'Head': (-14, shake, 0), 'Neck': (-6, 0, 0), 'UpperChest': (-4, 0, 0)},
                  {'RightArm': ((0.04, 1.6, -0.25), (0.42, 1.15, -0.05))})
    return [(0, _t()), (8, k(0)), (16, k(-6)), (24, k(6)), (32, k(-4)), (40, k(0)), (52, _t())]


def concerned():
    """Worried: hands clasped at the chest, head tilted and a little forward, a small lean in; holds, settles."""
    c = _t({'Head': (-6, 0, 9), 'UpperChest': (-4, 0, 0)},
           {'LeftArm': ((-0.04, 1.13, -0.21), (-0.4, 1.0, 0.15)), 'RightArm': ((0.04, 1.13, -0.21), (0.4, 1.0, 0.15))},
           _fingers('grip', 'grip'))
    c2 = dict(c, rot=merge(c['rot'], {'Head': (-8, 0, 12)}))
    return [(0, _t()), (10, c), (30, c2), (46, c), (58, _t())]


def talk():
    """Talking hands: forearms up, palms opening and closing in alternation with a little head nod; 2 s (loops)."""
    def k(a):
        return _t({'LeftUpperArm': (28 + 10 * a, 0, -14), 'LeftLowerArm': (70 - 15 * a, 0, 0),
                   'RightUpperArm': (28 - 10 * a, 0, 14), 'RightLowerArm': (70 + 15 * a, 0, 0),
                   'Head': (3 * a, 2 * a, 0)}, local=_fingers('spread' if a > 0 else 'relaxed',
                                                         'relaxed' if a > 0 else 'spread'))
    return [(0, k(0)), (12, k(1)), (24, k(-1)), (36, k(1)), (48, k(-1)), (60, k(0))]


def sit_chair():
    """Sits on a chair (seat 0.45 m, the Hips over its middle): thighs level, shins down, feet flat a little ahead,
    hands on the thighs. A held pose; gestures play over it."""
    legs = {'LeftLeg': ((-0.13, ANK, -0.4), (-0.13, 0.6, -1.0)), 'RightLeg': ((0.13, ANK, -0.4), (0.13, 0.6, -1.0))}
    k = {'hips': ((0, 0.53, 0.04), (0, 0, 0)), 'ik': legs, 'world': FLAT,
         'rot': merge(arms(30, 10, 30, 10, 45), {'Spine': (-3, 0, 0)})}
    return [(0, k), (30, k)]


def sit_table():
    """sit_chair at a table (top 0.75 m, near edge ~0.15 m ahead of the Hips): a small lean in, both hands resting
    on the tabletop near a plate/mug. A held pose."""
    legs = {'LeftLeg': ((-0.13, ANK, -0.4), (-0.13, 0.6, -1.0)), 'RightLeg': ((0.13, ANK, -0.4), (0.13, 0.6, -1.0))}
    hands = {'LeftArm': ((-0.17, 0.79, -0.3), (-0.5, 0.75, 0.1)), 'RightArm': ((0.15, 0.79, -0.33), (0.45, 0.8, -0.1))}
    k = {'hips': ((0, 0.53, 0.04), (0, 0, 0)), 'ik': merge(legs, hands), 'world': FLAT,
         'rot': {'Spine': (-2, 0, 0), 'Chest': (-2, 0, 0), 'Head': (3, 0, 0)}, 'local': _fingers()}
    return [(0, k), (30, k)]


TORSO = {'wave': wave, 'point': point, 'throw': throw, 'laugh': laugh, 'facepalm': facepalm,
         'concerned': concerned, 'talk': talk}
LOOPS.append('talk')

MOCK = {'squat': squat}                 # character-system mock only (not in the shipped Human)


FULL = {'faceplant': faceplant, 'sit_tub': sit_tub, 'get_up_back': get_up_back, 'get_up_front': get_up_front,
        'sit_chair': sit_chair, 'sit_table': sit_table, **FULL_EXTRA}
BOXES = {'sit_tub': TUB, 'climb_out_tub': TUB}
