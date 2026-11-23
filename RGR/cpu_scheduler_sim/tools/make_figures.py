"""
Генерація графічних матеріалів записки: діаграми Ганта, графіки експериментів, знімки CLI.
Запуск з кореня проєкту: python tools/make_figures.py  (потрібні matplotlib та Pillow).
Знімки консолі створюються з РЕАЛЬНОГО виводу команд, а не малюються вручну.
"""

import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib                                           # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                             # noqa: E402
from PIL import Image, ImageDraw, ImageFont                 # noqa: E402

from cpu_scheduler import FIFOScheduler, RoundRobinScheduler, load_workload   # noqa: E402

OUT = os.path.join("docs", "fig")
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
PALETTE = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN]
INK, MUTED, GRID = "#1a1a19", "#6b6a63", "#e3e2dc"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False})


def draw_gantt(ax, result, pid_colors, title):
    for seg in result.segments:
        if seg.kind == "RUN":
            ax.barh(0, seg.duration, left=seg.start, height=0.6, color=pid_colors[seg.pid],
                    edgecolor="white", linewidth=1.5)
            if seg.duration >= 2:
                ax.text(seg.start + seg.duration / 2, 0, seg.pid, ha="center", va="center",
                        color="white", fontsize=9, fontweight="bold")
        elif seg.kind == "IDLE":
            ax.barh(0, seg.duration, left=seg.start, height=0.6, color="#f4f4f1",
                    edgecolor=MUTED, hatch="///", linewidth=0.8)
            ax.text(seg.start + seg.duration / 2, 0, "idle", ha="center", va="center",
                    color=INK, fontsize=9, bbox=dict(facecolor="white", edgecolor="none", pad=1))
        else:
            ax.barh(0, seg.duration, left=seg.start, height=0.6, color="#3a3a38",
                    edgecolor="white", linewidth=0.5)
    ax.set_yticks([])
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_xlim(result.start_time, result.end_time)
    ax.spines["left"].set_visible(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_gantt_compare():
    workload = load_workload("data/workload_basic.txt")
    colors = {p.pid: PALETTE[i] for i, p in enumerate(workload)}
    fifo, rr = FIFOScheduler().schedule(workload), RoundRobinScheduler(4).schedule(workload)
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 3.2), sharex=True)
    draw_gantt(axes[0], fifo, colors, f"FIFO: середнє очікування W = {fifo.avg_waiting:.2f}")
    draw_gantt(axes[1], rr, colors, f"Round Robin, q = 4: середнє очікування W = {rr.avg_waiting:.2f}")
    axes[1].set_xlabel("Час, умовні одиниці (мс)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "gantt_compare.png"), dpi=200)
    plt.close(fig)


def fig_gantt_mixed():
    workload = load_workload("data/workload_mixed.txt")
    colors = {p.pid: PALETTE[i] for i, p in enumerate(workload)}
    res = RoundRobinScheduler(4, 1).schedule(workload)
    fig, ax = plt.subplots(figsize=(7.2, 1.7))
    draw_gantt(ax, res, colors, "Round Robin, q = 4, σ = 1: чорні блоки — перемикання контексту, штрихування — простій")
    ax.set_xlabel("Час, умовні одиниці (мс)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "gantt_mixed.png"), dpi=200)
    plt.close(fig)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def fig_benchmark():
    rows = read_csv("results/benchmark.csv")
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    series = {}
    for name, color, marker in (("FIFO", BLUE, "o"), ("RR", ORANGE, "s")):
        pts = [(int(r["n"]), float(r["seconds"])) for r in rows if r["algorithm"] == name]
        series[name] = pts
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, marker=marker,
                markersize=6, linewidth=2, markeredgecolor="white", markeredgewidth=1.2)
    n0, t0 = series["FIFO"][0]
    ns = [p[0] for p in series["FIFO"]]
    ax.plot(ns, [t0 * n / n0 * 0.45 for n in ns], color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(ns[-1], series["FIFO"][-1][1] * 0.55, "FIFO", color=INK, ha="right", fontsize=10)
    ax.text(ns[-1], series["RR"][-1][1] * 1.25, "Round Robin (q = 4)", color=INK, ha="right", fontsize=10)
    ax.text(ns[3], t0 * ns[3] / n0 * 0.45 * 0.5, "еталон O(n)", color=MUTED, fontsize=9)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Кількість процесів n"); ax.set_ylabel("Час прогону, с")
    ax.grid(True, color=GRID, linewidth=0.8, which="both"); ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "benchmark.png"), dpi=200)
    plt.close(fig)


def fig_quantum():
    rows = read_csv("results/quantum_study.csv")
    fifo = rows[0]
    rr = [r for r in rows[1:] if r["algorithm"] == "RR" and int(r["quantum"]) <= 30]
    q = [int(r["quantum"]) for r in rr]
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.3))
    ax = axes[0]
    ax.plot(q, [float(r["avg_waiting"]) for r in rr], color=BLUE, marker="o", markersize=4, linewidth=2)
    ax.plot(q, [float(r["avg_response"]) for r in rr], color=ORANGE, marker="s", markersize=4, linewidth=2)
    ax.axhline(float(fifo["avg_waiting"]), color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(30, float(fifo["avg_waiting"]) + 12, "FIFO: W = R", color=MUTED, ha="right", fontsize=8.5)
    ax.text(6, float(rr[5]["avg_waiting"]) + 25, "W (очікування)", color=INK, fontsize=9)
    ax.text(10, float(rr[9]["avg_response"]) - 55, "R (відгук)", color=INK, fontsize=9)
    ax.set_title("а) Середні часи, од. часу", loc="left", fontsize=10)
    ax = axes[1]
    ax.plot(q, [float(r["utilization_percent"]) for r in rr], color=BLUE, marker="o", markersize=4, linewidth=2)
    ax.axhline(float(fifo["utilization_percent"]), color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(30, float(fifo["utilization_percent"]) - 4, "FIFO", color=MUTED, ha="right", fontsize=8.5)
    ax.set_ylim(40, 100)
    ax.set_title("б) Завантаження CPU U, %", loc="left", fontsize=10)
    ax = axes[2]
    ax.plot(q, [int(r["context_switches"]) for r in rr], color=ORANGE, marker="s", markersize=4, linewidth=2)
    ax.axhline(int(fifo["context_switches"]), color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(30, int(fifo["context_switches"]) + 12, "FIFO", color=MUTED, ha="right", fontsize=8.5)
    ax.set_title("в) Кількість перемикань CS", loc="left", fontsize=10)
    for ax in axes:
        ax.set_xlabel("Квант часу q")
        ax.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "quantum_study.png"), dpi=200)
    plt.close(fig)


# --- Знімки консолі з реального виводу -------------------------------------------------------

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 17)
BOLD = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 17)


def run_capture(args):
    proc = subprocess.run([sys.executable, "cli_main.py", *args], capture_output=True, text=True,
                          encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return proc.stdout.rstrip("\n"), proc.stderr.rstrip("\n"), proc.returncode


def terminal_image(blocks, name):
    """blocks: список (команда, вивід, код). Малює темне вікно терміналу."""
    lines = []
    for cmd, out, err, code in blocks:
        lines.append(("cmd", "$ python cli_main.py " + " ".join(cmd)))
        for text in out.splitlines():
            lines.append(("out", text))
        for text in err.splitlines():
            lines.append(("err", text))
        lines.append(("code", f"[код завершення: {code}]") if code else ("code", ""))
        lines.append(("out", ""))
    while lines and lines[-1][1] == "":
        lines.pop()
    char_w = FONT.getlength("M")
    width = int(max(len(t) for _, t in lines) * char_w + 40)
    height = 24 * len(lines) + 70
    img = Image.new("RGB", (width, height), "#1e1f22")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 34], fill="#2b2d30")
    for i, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        draw.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=color)
    draw.text((width // 2 - 60, 8), "Термінал — РГР", font=FONT, fill="#9da0a8")
    y = 48
    palette = {"cmd": "#7ee787", "out": "#d4d7dd", "err": "#ff8a80", "code": "#ffd479"}
    for kind, text in lines:
        draw.text((20, y), text, font=BOLD if kind == "cmd" else FONT, fill=palette[kind])
        y += 24
    img.save(os.path.join(OUT, name))


def fig_cli():
    cmd1 = ["run", "--input", "data/workload_basic.txt", "--algo", "rr", "--quantum", "4", "--gantt"]
    out, err, code = run_capture(cmd1)
    terminal_image([(cmd1, out, err, code)], "cli_run.png")

    cmd2 = ["compare", "--input", "data/workload_mixed.txt", "--quanta", "1,2,4,8,100", "--switch-cost", "1"]
    out, err, code = run_capture(cmd2)
    terminal_image([(cmd2, out, err, code)], "cli_compare.png")

    blocks = []
    for cmd in (["run", "--input", "data/bad_workload.txt"],
                ["run", "--input", "data/workload_basic.txt", "--quantum", "0"],
                ["run", "--input", "data/workload_basic.txt", "--quantum", "1", "--max-slices", "5"],
                ["run", "--input", "data/workload_basic.txt", "--json", "results"],
                ["run", "--input", "data/workload_basic.txt", "--oops"]):
        out, err, code = run_capture(cmd)
        err = "\n".join(line for line in err.splitlines() if not line.startswith("Довідка"))
        blocks.append((cmd, "", err, code))
    terminal_image(blocks, "cli_errors.png")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_gantt_compare(); fig_gantt_mixed(); fig_benchmark(); fig_quantum(); fig_cli()
    print("Готово:", sorted(f for f in os.listdir(OUT) if f.endswith(".png")))
