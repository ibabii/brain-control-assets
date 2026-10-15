"""The Human's full-body and upper-body clips (Character rig v1), authored as poses (pose.py) and baked to keys.
Angles: Godot euler degrees in the character's rest frame. Arms: +X raises forward, -X back; Right arm +Z out
(Left -Z out). Spine/Head -X bends forward. LowerLeg -X bends the knee, Foot -X points the toes.
"""
import math

from mathutils import Matrix, Vector

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
       ((-0.85, -0.55, 0.0), (0.85, -0.425, 0.8))]


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


FULL = {'faceplant': faceplant, 'sit_tub': sit_tub, 'get_up_back': get_up_back, 'get_up_front': get_up_front}
BOXES = {'sit_tub': TUB}
