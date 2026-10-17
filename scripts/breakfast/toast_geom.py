"""The one bread slice: shared by the breakfast build (toast, toast_bitten) and Bernard's toast clips
(scripts/human/body_clips.py), so the slice in his hand and the one in his teeth are the same."""
import math

W, H, TH = 0.05, 0.055, 0.018            # half width, half height (before the domed top), thickness
CRUST, CRUMB = '#B5773D', '#EDD5A3'      # golden-brown crust rim, light crumb face
GRIP = (0.03, 0.05)                      # Grips/Right: the top edge right of centre, slice XY (z 0)
BITE_TURN = math.radians(-8)             # toast_bitten: the slice turned in its plane...
BITE_INSET = (-0.012, 0.008)             # ...its top-left corner moved to the origin, just into the mouth
BITE_Z = -0.018                          # slice centre plane in front of the lips


def outline(n):
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        x, y = math.cos(t) * W, math.sin(t) * H
        if y > 0.02:                                  # domed top with two shoulders
            y += 0.012 * abs(math.sin(2 * t))
        pts.append((x, y))
    return pts


def _turn(p):
    c, s = math.cos(BITE_TURN), math.sin(BITE_TURN)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


_TOP = max((_turn(p) for p in outline(96)), key=lambda q: q[1] - 0.9 * q[0])   # the clamped corner


def bitten(p):
    """Slice XY -> toast_bitten local XY (the clamped corner at the origin; hangs down to his right)."""
    q = _turn(p)
    return (q[0] - _TOP[0] + BITE_INSET[0], q[1] - _TOP[1] + BITE_INSET[1])
