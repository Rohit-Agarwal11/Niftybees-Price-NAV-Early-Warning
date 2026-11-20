"""Create the paper's information-timing and operational-workload figure."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

fig, ax = plt.subplots(figsize=(11, 3.2))
ax.set_xlim(0, 11); ax.set_ylim(0, 3); ax.axis("off")
items = [
    (0.3, "Market close\nDate t", "ETF, index, VIX\nand liquidity known"),
    (3.0, "Official NAV\nDate t", "Post-NAV screen\n(stipulated 11 p.m.)"),
    (5.7, "Risk ranking", "Score all dates; review\nhighest-ranked 10%"),
    (8.4, "Next session\nDate t+1", "Observe absolute gap\nand abnormal event"),
]
for x, title, body in items:
    box = FancyBboxPatch((x, .65), 2.1, 1.55, boxstyle="round,pad=.04,rounding_size=.08",
                         facecolor="#F4F7FB", edgecolor="#1F4E78", linewidth=1.4)
    ax.add_patch(box)
    ax.text(x + 1.05, 1.72, title, ha="center", va="center", fontsize=10.5, weight="bold", color="#1F4E78")
    ax.text(x + 1.05, 1.08, body, ha="center", va="center", fontsize=9)
for x in [2.42, 5.12, 7.82]:
    ax.add_patch(FancyArrowPatch((x, 1.43), (x + .48, 1.43), arrowstyle="-|>",
                                 mutation_scale=13, color="#5B6573", linewidth=1.3))
ax.text(5.5, .25, "Observed pooled workload: 72 reviews across 3 held-out years (about 24 per year), detecting 19 of 65 events",
        ha="center", va="center", fontsize=9.5, color="#333333")
fig.tight_layout()
fig.savefig(FIG / "ETF_Operational_Timeline.png", dpi=220, bbox_inches="tight")
plt.close(fig)
print(FIG / "ETF_Operational_Timeline.png")
