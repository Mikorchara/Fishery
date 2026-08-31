"""性能基准测试结果可视化 — 从 bench_output/bench_full_result.json 生成图表。"""
import json, sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT = "bench_output/bench_full_result.json"
OUT_DIR = "bench_output"
DPI = 150

# 中文字体
for fn in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        matplotlib.font_manager.findfont(fn, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [fn, "DejaVu Sans"]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"font.size": 14, "axes.titlesize": 18, "axes.labelsize": 16,
                     "legend.fontsize": 11, "figure.dpi": DPI, "savefig.dpi": DPI,
                     "savefig.bbox": "tight"})


def load():
    with open(INPUT, encoding="utf-8") as f:
        return json.load(f)


# 颜色
def color_for(name):
    if "ema" in name.lower(): return "#1f77b4" if "无增强" in name or "+SAM2" in name else "#aec7e8"
    if "seam" in name.lower(): return "#2ca02c" if "无增强" in name or "+SAM2" in name else "#98df8a"
    if "onnx" in name.lower(): return "#d62728" if "无增强" in name else "#ff9896"
    if "seg" in name.lower(): return "#9467bd" if "无增强" in name else "#c5b0d5"
    if "bifpn" in name.lower(): return "#8c564b" if "无增强" in name else "#c49c94"
    return "#999"


# ---- 图1: 延迟柱状图 (增强前后对比) ----
def plot_enhance_bars(data):
    models = ["fish_detect_ema", "fish_detect_seam", "fish_onnx",
              "fish_seg", "fish_seg_nano", "fish_seg_yolo11",
              "fish_seg_nano_onnx", "fish_seg_yolo11_onnx", "fish_bifpn"]
    labels = ["EMA", "SEAM", "ONNX(det)", "SEG", "SEG-Nano", "YOLO11",
              "SEG-Nano\nONNX", "YOLO11\nONNX", "BiFPN"]

    means_off = [data[f"{m} 无增强"]["latency_ms_mean"] if f"{m} 无增强" in data else 0 for m in models]
    means_on = [data[f"{m} +增强"]["latency_ms_mean"] if f"{m} +增强" in data else 0 for m in models]

    x = np.arange(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.bar(x - w/2, means_off, w, label="无增强", color="#1f77b4", edgecolor="white")
    ax.bar(x + w/2, means_on, w, label="+WWE-UIE 增强", color="#ff7f0e", edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel("延迟 (ms)")
    ax.set_title("各模型增强前后延迟对比")
    ax.legend(); ax.grid(True, alpha=0.3, axis="y")
    for bar in ax.patches:
        h = bar.get_height()
        if h > 0: ax.text(bar.get_x()+bar.get_width()/2, h+1, f"{h:.0f}", ha="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig1_enhance_bars.png")
    plt.close(fig)
    print("  [OK] fig1_enhance_bars.png")


# ---- 图2: FPS 总览 (横向柱状) ----
def plot_fps_overview(data):
    items = sorted(data.items(), key=lambda x: -x[1]['fps'])
    labels = [k for k, v in items]
    fps = [v['fps'] for _, v in items]

    fig, ax = plt.subplots(figsize=(14, 8))
    colors = [color_for(k) for k in labels]
    y_pos = range(len(labels))
    ax.barh(y_pos, fps, color=colors, edgecolor="white")
    ax.set_yticks(y_pos); ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("FPS")
    ax.set_title("各配置吞吐量对比 (FPS)")
    ax.grid(True, alpha=0.3, axis="x")
    for i, v in enumerate(fps):
        ax.text(v+0.5, i, f"{v:.1f}", va="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig2_fps_overview.png")
    plt.close(fig)
    print("  [OK] fig2_fps_overview.png")


# ---- 图3: 检测模型延迟时序 (上:无增强, 下:增强) ----
def plot_latency_ts(data):
    base_models = ["fish_detect_ema", "fish_detect_seam",
                   "fish_seg", "fish_seg_nano", "fish_seg_yolo11", "fish_bifpn"]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    for mk in base_models:
        k = f"{mk} 无增强"
        if k in data:
            fs = data[k]["frames"]
            ax1.plot([f["frame"] for f in fs], [f["latency_ms"] for f in fs],
                     linewidth=0.7, label=mk, alpha=0.75, color=color_for(k))
    ax1.set_ylabel("延迟 (ms)"); ax1.set_title("纯检测延迟时序 (无增强)")
    ax1.legend(ncol=3, fontsize=11); ax1.grid(True, alpha=0.3); ax1.set_ylim(bottom=0)

    for mk in base_models:
        k = f"{mk} +增强"
        if k in data:
            fs = data[k]["frames"]
            ax2.plot([f["frame"] for f in fs], [f["latency_ms"] for f in fs],
                     linewidth=0.7, label=mk, alpha=0.75, color=color_for(k))
    ax2.set_xlabel("帧"); ax2.set_ylabel("延迟 (ms)")
    ax2.set_title("检测 + WWE-UIE 增强延迟时序")
    ax2.legend(ncol=3, fontsize=11); ax2.grid(True, alpha=0.3); ax2.set_ylim(bottom=0)

    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig3_latency_ts.png")
    plt.close(fig)
    print("  [OK] fig3_latency_ts.png")


# ---- 图4: 检出数对比 ----
def plot_detections(data):
    models = [k for k in data if "无增强" in k and "data" not in k]
    models = sorted(models, key=lambda k: data[k].get("det_mean", 0), reverse=True)
    dets = [data[m].get("det_mean", 0) for m in models]
    stds = [data[m].get("det_std", 0) for m in models]

    fig, ax = plt.subplots(figsize=(14, 5))
    x = np.arange(len(models))
    colors = [color_for(m) for m in models]
    bars = ax.bar(x, dets, color=colors, edgecolor="white", yerr=stds, capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace(" 无增强","") for m in models], fontsize=12, rotation=45)
    ax.set_ylabel("平均检出数")
    ax.set_title("各模型平均检测数量 (无增强)")
    ax.grid(True, alpha=0.3, axis="y")
    for b, d in zip(bars, dets):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.3, f"{d:.1f}", ha="center", fontsize=12)
    fig.tight_layout()
    fig.savefig(f"{OUT_DIR}/fig4_detections.png")
    plt.close(fig)
    print("  [OK] fig4_detections.png")


def main():
    if len(sys.argv) > 1:
        global INPUT; INPUT = sys.argv[1]
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"读取: {INPUT}")
    data = load()
    print(f"共 {len(data)} 组配置\n")

    plot_enhance_bars(data)
    plot_fps_overview(data)
    plot_latency_ts(data)
    plot_detections(data)
    print("\n完成")


if __name__ == "__main__":
    main()
