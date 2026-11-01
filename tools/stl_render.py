"""Render an STL to PNG from several viewpoints using matplotlib.

Usage: python tools/stl_render.py <file.stl> <out.png> [zoom]
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def draw(ax, mesh, elev, azim, title):
    tris = mesh.triangles
    normals = mesh.face_normals
    light = np.array([0.4, 0.5, 0.75])
    light = light / np.linalg.norm(light)
    shade = np.clip(normals @ light, 0.15, 1.0)
    colors = np.stack([0.35 * shade + 0.12, 0.55 * shade + 0.18, 0.75 * shade + 0.2, np.ones(len(tris))], axis=1)
    pc = Poly3DCollection(tris, facecolors=colors, edgecolors="none")
    ax.add_collection3d(pc)
    lo, hi = mesh.bounds
    ctr = (lo + hi) / 2
    r = 0.55 * float(np.max(hi - lo))
    ax.set_xlim(ctr[0] - r, ctr[0] + r)
    ax.set_ylim(ctr[1] - r, ctr[1] + r)
    ax.set_zlim(ctr[2] - r, ctr[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=8)


def main():
    path, out = sys.argv[1], sys.argv[2]
    mesh = trimesh.load(path, force="mesh")
    views = [(20, -60), (20, 120), (-25, -60), (89, -90)]
    fig = plt.figure(figsize=(12, 10), dpi=110)
    for i, (elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        draw(ax, mesh, elev, azim, f"elev {elev} azim {azim}")
    fig.suptitle(path.split("/")[-1].split("\\")[-1], fontsize=10)
    fig.tight_layout()
    fig.savefig(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
