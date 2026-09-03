"""
Argo FC Analytics — brand asset generator ("1b Broadsheet" direction)
Instrument Serif + Public Sans - warm ink/cream editorial palette.

PALETTE is a draft approximation of the broadsheet tokens.
To sync with config/theme.json, replace the hex values and re-run.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Wedge, Circle

PALETTE = {
    "ink":    "#221C17",
    "paper":  "#F4EDDF",
    "accent": "#A8402A",
    "ochre":  "#C09035",
    "muted":  "#8A7E6F",
}

FONT_DIR = Path("/home/claude/argo-brand/fonts")
SERIF        = fm.FontProperties(fname=FONT_DIR / "InstrumentSerif-Regular.ttf")
SERIF_ITALIC = fm.FontProperties(fname=FONT_DIR / "InstrumentSerif-Italic.ttf")
SANS         = fm.FontProperties(fname=FONT_DIR / "PublicSans-Regular.ttf")

plt.rcParams["svg.fonttype"] = "path"
OUT = Path("/home/claude/argo-brand/out"); OUT.mkdir(exist_ok=True)

# Wedge radii tuned so the accent (tallest) slice sits upper-right.
RADII = [0.72, 0.58, 0.82, 0.66, 0.90, 0.62, 0.76, 0.54, 0.96, 0.68]
ACCENT_IDX = 8

def draw_mark(ax, fg, accent, ring, cx=0.0, cy=0.0, scale=1.0,
              pad_deg=2.4, ring_lw=1.6, radii=None, accent_idx=None):
    radii = radii or RADII
    accent_idx = ACCENT_IDX if accent_idx is None else accent_idx
    step = 360.0 / len(radii)
    for i, r in enumerate(radii):
        t0 = 90 + i * step + pad_deg / 2
        t1 = 90 + (i + 1) * step - pad_deg / 2
        color = accent if i == accent_idx else fg
        ax.add_patch(Wedge((cx, cy), r * scale, t0, t1, facecolor=color, edgecolor="none"))
    ax.add_patch(Circle((cx, cy), 1.0 * scale, fill=False, edgecolor=ring, linewidth=ring_lw))

def masthead(fig, ax, x, y, size, color, gap_em=0.28):
    """Draw 'Argo FC' roman + 'Analytics' italic with measured spacing."""
    t1 = ax.text(x, y, "Argo FC", fontproperties=SERIF, fontsize=size,
                 color=color, ha="left", va="baseline")
    fig.canvas.draw()
    bb = t1.get_window_extent(fig.canvas.get_renderer())
    gap_px = size * fig.dpi / 72 * gap_em
    x2 = ax.transData.inverted().transform((bb.x1 + gap_px, 0))[0]
    t2 = ax.text(x2, y, "Analytics", fontproperties=SERIF_ITALIC, fontsize=size,
                 color=color, ha="left", va="baseline")
    fig.canvas.draw()
    return t1, t2

def save(fig, name, png_dpi=None):
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", pad_inches=0.02, transparent=True)
    if png_dpi:
        fig.savefig(OUT / f"{name}.png", bbox_inches="tight", pad_inches=0.02,
                    transparent=True, dpi=png_dpi)
    plt.close(fig)

def mode_colors(mode):
    if mode == "dark":
        return dict(fg=PALETTE["paper"], bg=PALETTE["ink"],
                    accent=PALETTE["accent"], muted="#B9AE9D")
    return dict(fg=PALETTE["ink"], bg=PALETTE["paper"],
                accent=PALETTE["accent"], muted=PALETTE["muted"])

# marks
for mode in ("dark", "light"):
    c = mode_colors(mode)
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.set_xlim(-1.12, 1.12); ax.set_ylim(-1.12, 1.12)
    ax.set_aspect("equal"); ax.axis("off")
    draw_mark(ax, c["fg"], c["accent"], c["fg"])
    save(fig, f"mark-{mode}", png_dpi=300)

# wordmarks
for mode in ("dark", "light"):
    c = mode_colors(mode)
    fig, ax = plt.subplots(figsize=(10.5, 1.9))
    ax.axis("off"); ax.set_xlim(0, 10.5); ax.set_ylim(0, 1.9)
    masthead(fig, ax, 0.05, 0.55, 84, c["fg"])
    save(fig, f"wordmark-{mode}", png_dpi=300)

    fig, ax = plt.subplots(figsize=(5.2, 1.9))
    ax.axis("off"); ax.set_xlim(0, 5.2); ax.set_ylim(0, 1.9)
    ax.text(0.05, 0.55, "Argo FC", fontproperties=SERIF, fontsize=84,
            color=c["fg"], ha="left", va="baseline")
    save(fig, f"wordmark-compact-{mode}", png_dpi=300)

# lockups
for mode in ("dark", "light"):
    c = mode_colors(mode)
    fig, ax = plt.subplots(figsize=(12.0, 2.5))
    ax.axis("off"); ax.set_xlim(0, 12.0); ax.set_ylim(-1.25, 1.25)
    ax.set_aspect("equal")
    draw_mark(ax, c["fg"], c["accent"], c["fg"], cx=1.05, cy=0.0, ring_lw=1.4)
    masthead(fig, ax, 2.55, -0.40, 86, c["fg"])
    save(fig, f"lockup-{mode}", png_dpi=300)

# favicon: 8 wedges, no hairline ring, accent upper-right
FAV_RADII = [0.74, 0.60, 0.88, 0.64, 0.78, 0.56, 0.92, 1.00]
c = mode_colors("dark")
fig, ax = plt.subplots(figsize=(3, 3))
ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3)
ax.set_aspect("equal"); ax.axis("off")
ax.add_patch(Circle((0, 0), 1.3, facecolor=c["bg"], edgecolor="none"))
step = 360 / len(FAV_RADII)
for i, r in enumerate(FAV_RADII):
    t0 = 90 + i * step + 4; t1 = 90 + (i + 1) * step - 4
    color = c["accent"] if i == 7 else c["fg"]
    ax.add_patch(Wedge((0, 0), r, t0, t1, facecolor=color, edgecolor="none"))
fig.savefig(OUT / "favicon.svg", bbox_inches="tight", pad_inches=0, transparent=True)
for px, name in [(512, "icon-512"), (180, "apple-touch-icon"), (32, "favicon-32")]:
    fig.set_size_inches(px / 100, px / 100)
    fig.savefig(OUT / f"{name}.png", dpi=100, bbox_inches="tight", pad_inches=0, transparent=True)
plt.close(fig)

# OG card 1200x630
c = mode_colors("dark")
fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
ax.set_xlim(0, 1200); ax.set_ylim(0, 630)
fig.patch.set_facecolor(c["bg"]); ax.set_facecolor(c["bg"])
ax.plot([80, 1120], [566, 566], color=c["fg"], lw=1.3)
ax.plot([80, 1120], [559, 559], color=c["fg"], lw=0.5)
ax.plot([80, 1120], [72, 72], color=c["fg"], lw=0.5)

axm = fig.add_axes([0.075, 0.335, 0.185, 0.185 * (1200 / 630)])
axm.set_xlim(-1.12, 1.12); axm.set_ylim(-1.12, 1.12)
axm.set_aspect("equal"); axm.axis("off")
draw_mark(axm, c["fg"], c["accent"], c["fg"], ring_lw=1.6)

masthead(fig, ax, 340, 310, 62, c["fg"])
ax.text(343, 252, "Player, team & league analysis across Europe's top five leagues",
        fontproperties=SANS, fontsize=19.5, color=c["muted"], ha="left", va="baseline")
fig.savefig(OUT / "og-card.png", dpi=100, facecolor=c["bg"])
plt.close(fig)
print("done:", len(list(OUT.iterdir())), "files")
