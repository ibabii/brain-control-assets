"""Brain-fold enclosure: a rounded room whose inner surface is displaced by a tileable fold height field."""
import math

import bmesh
import numpy as np
from mathutils import Vector

import folds
import lib

# Plan shape: superellipse around the seat. Back wall z = ZC - B, side walls x = +-A.
# Near-circular around the eye so every wall faces the camera (no grazing smear).
A, B, ZC, P = 1.68, 1.72, 0.75, 2.0
Y0, Y1 = 0.62, 2.75
TILE = 1.9          # metres per height-field tile
DEPTH = 0.13        # fold height
STEP = 0.017        # grid spacing

GROOVE, BASE, TOP = '#9A4038', '#EE8E7A', '#FBB7A2'


def _plan(theta):
    s, c = math.sin(theta), math.cos(theta)
    x = A * math.copysign(abs(s) ** (2 / P), s)
    z = ZC - B * math.copysign(abs(c) ** (2 / P), c)
    return x, z


def _lean(y):
    """Walls curve inward toward the top, like the inside of a skull, and flare out at desk level."""
    t = min(max((y - 1.9) / (Y1 - 1.9), 0), 1)
    b = min(max((1.3 - y) / 0.6, 0), 1)
    return (1 - 0.32 * t * t) * (1 + 0.18 * b * b)


def inside(p):
    k = _lean(p[1])
    return (abs(p[0] / (A * k)) ** P + abs((p[2] - ZC) / (B * k)) ** P) < 1


def wall_hit(px, py, gap=0.1):
    """Point just in front of the (undisplaced) wall along the camera ray through concept pixel (px, py)."""
    d = lib.ray(px, py)
    t = 0.3
    while inside(lib.CAM + d * t) and t < 6:
        t += 0.01
    return lib.CAM + d * (t - gap), t - gap


def _sample(h, u, v):
    n = h.shape[0]
    x, y = (u % 1) * n, (v % 1) * n
    x0, y0 = int(x) % n, int(y) % n
    x1, y1 = (x0 + 1) % n, (y0 + 1) % n
    fx, fy = x - int(x), y - int(y)
    return (h[y0, x0] * (1 - fx) * (1 - fy) + h[y0, x1] * fx * (1 - fy) + h[y1, x0] * (1 - fx) * fy
            + h[y1, x1] * fx * fy)


def albedo(h):
    """Fold colour with baked stylised shading: soft top-left key plus occlusion in the grooves."""
    g, b, t = (np.array([lib.linear(c) for c in lib.srgb(x)]) for x in (GROOVE, BASE, TOP))
    s = np.clip(h / 0.7, 0, 1)[..., None] ** 1.5
    col = g * (1 - s) + b * s
    s2 = np.clip((h - 0.75) / 0.25, 0, 1)[..., None]
    col = col * (1 - s2) + t * s2
    # Height-field normal (rows run top-down here, so +row = down).
    k = 7.0
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * k
    dy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * k
    n = np.stack([-dx, -dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    light = np.array([-0.45, 0.6, 0.66])
    light /= np.linalg.norm(light)
    lambert = np.clip((n * light).sum(-1), 0, 1)
    cavity = np.clip(h - folds.blur(h, 6) + 0.5, 0, 1)          # <0.5 in grooves
    shade = (0.62 + 0.5 * lambert) * (0.55 + 0.9 * cavity)
    col *= np.clip(shade, 0.35, 1.35)[..., None]
    noise = folds.blur(np.random.default_rng(3).random(h.shape), 8)
    col *= (0.95 + 0.1 * (noise - noise.min()) / (np.ptp(noise) + 1e-6))[..., None]
    srgb = np.where(col <= 0.0031308, col * 12.92, 1.055 * np.power(np.clip(col, 0, None), 1 / 2.4) - 0.055)
    return np.clip(srgb, 0, 1)


def build(parent):
    h = folds.fold_height(seed=7)
    tex = lib.image_from_array('BrainFolds', albedo(h)[::-1])   # image rows run bottom-up in UV space
    material = lib.mat('BrainFolds', BASE, rough=0.5, image=tex)

    thetas = np.linspace(-math.radians(128), math.radians(128), 700)
    plan = [_plan(t) for t in thetas]
    arc = [0.0]
    for (x0, z0), (x1, z1) in zip(plan, plan[1:]):
        arc.append(arc[-1] + math.hypot(x1 - x0, z1 - z0))
    total = arc[-1]
    cols = int(total / STEP)
    rows = int((Y1 - Y0) / STEP)
    sel = np.interp(np.linspace(0, total, cols + 1), arc, np.arange(len(arc)))

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    grid = []
    for r in range(rows + 1):
        y = Y0 + (Y1 - Y0) * r / rows
        k = _lean(y)
        row = []
        for c in range(cols + 1):
            i = sel[c]
            i0 = int(min(i, len(plan) - 2))
            f = i - i0
            x = (plan[i0][0] * (1 - f) + plan[i0 + 1][0] * f) * k
            z = ZC + ((plan[i0][1] * (1 - f) + plan[i0 + 1][1] * f) - ZC) * k
            u, v = total * c / cols / TILE, y / TILE
            inward = Vector((-x, 0, ZC - z)).normalized()
            p = Vector((x, y, z)) + inward * (DEPTH * _sample(h, u, v))
            row.append((bm.verts.new(p), (u, v)))
        grid.append(row)
    for r in range(rows):
        for c in range(cols):
            quad = [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]]
            face = bm.faces.new([q[0] for q in quad])
            for loop, q in zip(face.loops, quad):
                loop[uv].uv = q[1]
    bm.normal_update()
    for f in bm.faces:            # face the room
        centre = f.calc_center_median()
        if f.normal.dot(Vector((-centre.x, 0, ZC - centre.z))) < 0:
            f.normal_flip()
    return lib.from_bmesh('BrainFolds', bm, material, parent, pivot=(0, 0, 0), smooth=True)
