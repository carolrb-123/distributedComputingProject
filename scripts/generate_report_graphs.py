#!/usr/bin/env python3
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "figures"
EVAL = ROOT / "evaluation_results"


def read_json(path):
    with open(path) as f:
        return json.load(f)


def run_dirs(prefix):
    dirs = []
    for path in EVAL.glob(f"{prefix}_users*_threads*"):
        if path.is_dir():
            name = path.name
            users = int(name.split("_users", 1)[1].split("_threads", 1)[0])
            threads = int(name.split("_threads", 1)[1])
            dirs.append((users, threads, path))
    return sorted(dirs)


def metrics(prefix):
    rows = []
    for users, threads, path in run_dirs(prefix):
        summary = read_json(path / "metrics_summary.json")
        evidence = read_json(path / "run_evidence.json")
        admission = evidence.get("load_balancer", {}).get("admission", {})
        rows.append({
            "users": users,
            "threads": threads,
            "success_rate": summary["success_rate"] * 100,
            "failed": summary["failed_requests"],
            "throughput": summary["throughput_req_per_sec"],
            "avg_latency": summary["avg_latency_sec"],
            "p50": summary["p50_latency_sec"],
            "p99": summary["p99_latency_sec"],
            "admission_waits": admission.get("wait_count", 0),
            "admission_timeouts": admission.get("timeout_count", 0),
            "assignments": evidence.get("load_balancer", {}).get("assignment_counts", {}),
        })
    return rows


def gpu_summary(prefix):
    rows = []
    for users, threads, path in run_dirs(prefix):
        hist = path / "gpu_metrics_history.csv"
        max_util = max_mem = max_temp = max_power = 0
        samples = 0
        with open(hist) as f:
            for row in csv.DictReader(f):
                samples += 1
                max_util = max(max_util, int(float(row["gpu_utilization_percent"] or 0)))
                max_mem = max(max_mem, int(float(row["memory_used_mb"] or 0)))
                max_temp = max(max_temp, int(float(row["temperature_c"] or 0)))
                max_power = max(max_power, float(row["power_draw_w"] or 0))
        rows.append({
            "users": users,
            "threads": threads,
            "samples": samples,
            "max_util": max_util,
            "max_mem": max_mem,
            "max_temp": max_temp,
            "max_power": max_power,
        })
    return rows


def esc(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_header(width, height):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Arial,Helvetica,sans-serif;fill:#111827} .axis{stroke:#374151;stroke-width:1.2} .grid{stroke:#e5e7eb;stroke-width:1} .muted{fill:#6b7280;font-size:12px} .title{font-size:19px;font-weight:700} .label{font-size:13px;font-weight:600} .tick{font-size:11px;fill:#374151}",
        "</style>",
        '<rect width="100%" height="100%" fill="white"/>',
    ]


def line_chart(path, title, series, y_label, y_max=None, width=900, height=520):
    margin = {"left": 78, "right": 34, "top": 62, "bottom": 72}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    xs = sorted({x for item in series for x, _ in item["points"]})
    values = [y for item in series for _, y in item["points"]]
    y_max = y_max if y_max is not None else max(values) * 1.15 if values else 1
    y_max = max(y_max, 1)

    def x_pos(x):
        if len(xs) == 1:
            return margin["left"] + plot_w / 2
        return margin["left"] + xs.index(x) * plot_w / (len(xs) - 1)

    def y_pos(y):
        return margin["top"] + plot_h - (y / y_max) * plot_h

    parts = svg_header(width, height)
    parts.append(f'<text x="{margin["left"]}" y="34" class="title">{esc(title)}</text>')
    parts.append(f'<text x="22" y="{margin["top"] + plot_h / 2}" transform="rotate(-90 22 {margin["top"] + plot_h / 2})" class="label">{esc(y_label)}</text>')
    parts.append(f'<text x="{margin["left"] + plot_w / 2 - 62}" y="{height - 18}" class="label">Concurrent users</text>')

    for i in range(6):
        y = margin["top"] + i * plot_h / 5
        val = y_max - i * y_max / 5
        parts.append(f'<line x1="{margin["left"]}" y1="{y:.2f}" x2="{margin["left"] + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{margin["left"] - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">{val:.1f}</text>')

    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" class="axis"/>')
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" class="axis"/>')

    for x in xs:
        xp = x_pos(x)
        parts.append(f'<text x="{xp:.2f}" y="{margin["top"] + plot_h + 24}" text-anchor="middle" class="tick">{x}</text>')

    legend_x = margin["left"] + 10
    for idx, item in enumerate(series):
        color = item["color"]
        pts = " ".join(f"{x_pos(x):.2f},{y_pos(y):.2f}" for x, y in item["points"])
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3"/>')
        for x, y in item["points"]:
            parts.append(f'<circle cx="{x_pos(x):.2f}" cy="{y_pos(y):.2f}" r="4" fill="{color}"/>')
        ly = 52 + idx * 20
        parts.append(f'<rect x="{legend_x}" y="{ly - 10}" width="14" height="4" fill="{color}"/>')
        parts.append(f'<text x="{legend_x + 22}" y="{ly - 5}" class="muted">{esc(item["name"])}</text>')

    parts.append("</svg>")
    path.write_text("\n".join(parts))


def bar_chart(path, title, labels, values, y_label, color="#2563eb", width=900, height=520):
    margin = {"left": 82, "right": 36, "top": 62, "bottom": 82}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    y_max = max(values) * 1.18 if values else 1
    y_max = max(y_max, 1)
    gap = 16
    bar_w = (plot_w - gap * (len(values) + 1)) / max(len(values), 1)

    def y_pos(y):
        return margin["top"] + plot_h - (y / y_max) * plot_h

    parts = svg_header(width, height)
    parts.append(f'<text x="{margin["left"]}" y="34" class="title">{esc(title)}</text>')
    parts.append(f'<text x="22" y="{margin["top"] + plot_h / 2}" transform="rotate(-90 22 {margin["top"] + plot_h / 2})" class="label">{esc(y_label)}</text>')
    for i in range(6):
        y = margin["top"] + i * plot_h / 5
        val = y_max - i * y_max / 5
        parts.append(f'<line x1="{margin["left"]}" y1="{y:.2f}" x2="{margin["left"] + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{margin["left"] - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">{val:.1f}</text>')
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" class="axis"/>')
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" class="axis"/>')
    for i, (label, val) in enumerate(zip(labels, values)):
        x = margin["left"] + gap + i * (bar_w + gap)
        y = y_pos(val)
        h = margin["top"] + plot_h - y
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" fill="{color}"/>')
        parts.append(f'<text x="{x + bar_w / 2:.2f}" y="{y - 6:.2f}" text-anchor="middle" class="tick">{val:.1f}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.2f}" y="{margin["top"] + plot_h + 24}" text-anchor="middle" class="tick">{esc(label)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def grouped_bar_chart(path, title, labels, groups, y_label, width=960, height=540):
    colors = ["#2563eb", "#dc2626", "#059669"]
    margin = {"left": 82, "right": 36, "top": 72, "bottom": 90}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    y_max = max(v for group in groups for v in group["values"]) * 1.18
    gap = 22
    group_w = (plot_w - gap * (len(labels) + 1)) / len(labels)
    bar_w = group_w / len(groups)

    def y_pos(y):
        return margin["top"] + plot_h - (y / y_max) * plot_h

    parts = svg_header(width, height)
    parts.append(f'<text x="{margin["left"]}" y="34" class="title">{esc(title)}</text>')
    parts.append(f'<text x="22" y="{margin["top"] + plot_h / 2}" transform="rotate(-90 22 {margin["top"] + plot_h / 2})" class="label">{esc(y_label)}</text>')
    for i in range(6):
        y = margin["top"] + i * plot_h / 5
        val = y_max - i * y_max / 5
        parts.append(f'<line x1="{margin["left"]}" y1="{y:.2f}" x2="{margin["left"] + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{margin["left"] - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">{val:.1f}</text>')
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" class="axis"/>')
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" class="axis"/>')
    for gi, group in enumerate(groups):
        lx = margin["left"] + 8 + gi * 150
        parts.append(f'<rect x="{lx}" y="48" width="14" height="8" fill="{colors[gi % len(colors)]}"/>')
        parts.append(f'<text x="{lx + 20}" y="56" class="muted">{esc(group["name"])}</text>')
    for i, label in enumerate(labels):
        base = margin["left"] + gap + i * (group_w + gap)
        for gi, group in enumerate(groups):
            val = group["values"][i]
            x = base + gi * bar_w
            y = y_pos(val)
            h = margin["top"] + plot_h - y
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w - 2:.2f}" height="{h:.2f}" fill="{colors[gi % len(colors)]}"/>')
        parts.append(f'<text x="{base + group_w / 2:.2f}" y="{margin["top"] + plot_h + 24}" text-anchor="middle" class="tick">{esc(label)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def latency_cdf(path, run_dir, width=900, height=520):
    latencies = []
    with open(run_dir / "latencies.csv") as f:
        for row in csv.DictReader(f):
            latencies.append(float(row["latency_seconds"]))
    latencies.sort()
    points = [(lat, (i + 1) / len(latencies) * 100) for i, lat in enumerate(latencies)]
    max_x = max(latencies) * 1.05 if latencies else 1
    margin = {"left": 78, "right": 34, "top": 62, "bottom": 72}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]

    def x_pos(x):
        return margin["left"] + (x / max_x) * plot_w

    def y_pos(y):
        return margin["top"] + plot_h - (y / 100) * plot_h

    parts = svg_header(width, height)
    parts.append(f'<text x="{margin["left"]}" y="34" class="title">Latency CDF for 1000-Request Six-Worker Run</text>')
    parts.append(f'<text x="22" y="{margin["top"] + plot_h / 2}" transform="rotate(-90 22 {margin["top"] + plot_h / 2})" class="label">Completed requests (%)</text>')
    parts.append(f'<text x="{margin["left"] + plot_w / 2 - 45}" y="{height - 18}" class="label">Latency (s)</text>')
    for i in range(6):
        y = margin["top"] + i * plot_h / 5
        val = 100 - i * 20
        parts.append(f'<line x1="{margin["left"]}" y1="{y:.2f}" x2="{margin["left"] + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{margin["left"] - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">{val}</text>')
    for i in range(6):
        x = margin["left"] + i * plot_w / 5
        val = i * max_x / 5
        parts.append(f'<text x="{x:.2f}" y="{margin["top"] + plot_h + 24}" text-anchor="middle" class="tick">{val:.0f}</text>')
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" class="axis"/>')
    parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" class="axis"/>')
    pts = " ".join(f"{x_pos(x):.2f},{y_pos(y):.2f}" for x, y in points)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="#7c3aed" stroke-width="3"/>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def architecture_svg(path):
    width, height = 1000, 520
    parts = svg_header(width, height)
    parts.append('<text x="70" y="40" class="title">Distributed AI Inference System Architecture</text>')
    boxes = [
        (70, 110, 150, 72, "Load Test Clients", "#dbeafe"),
        (275, 110, 150, 72, "Scheduler", "#dcfce7"),
        (480, 110, 170, 72, "Adaptive Load Balancer", "#fef3c7"),
        (725, 62, 190, 52, "Thunder GPU Worker 0", "#f3e8ff"),
        (725, 124, 190, 52, "Thunder GPU Worker 1", "#f3e8ff"),
        (725, 186, 190, 52, "Thunder GPU Worker 2", "#f3e8ff"),
        (725, 248, 190, 52, "Thunder GPU Worker 3", "#f3e8ff"),
        (725, 310, 190, 52, "Thunder GPU Worker 4", "#f3e8ff"),
        (725, 372, 190, 52, "Thunder GPU Worker 5", "#f3e8ff"),
        (275, 300, 150, 70, "RAG / FAISS", "#e0f2fe"),
        (480, 300, 170, 70, "Metrics + Evidence", "#fee2e2"),
    ]
    for x, y, w, h, label, fill in boxes:
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="#374151" stroke-width="1.2"/>')
        parts.append(f'<text x="{x+w/2}" y="{y+h/2+4}" text-anchor="middle" class="label">{esc(label)}</text>')
    arrows = [
        (220, 146, 275, 146),
        (425, 146, 480, 146),
        (650, 146, 725, 88),
        (650, 146, 725, 150),
        (650, 146, 725, 212),
        (650, 146, 725, 274),
        (650, 146, 725, 336),
        (650, 146, 725, 398),
        (350, 182, 350, 300),
        (565, 182, 565, 300),
    ]
    parts.append('<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#374151"/></marker></defs>')
    for x1, y1, x2, y2 in arrows:
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#374151" stroke-width="2" marker-end="url(#arrow)"/>')
    parts.append('<text x="70" y="472" class="muted">Each worker is a real Thunder Compute A6000 VM running Ollama; GPU metrics are polled through per-node metrics agents.</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def write_summary_csv(rows6, gpu_rows):
    out = ROOT / "report" / "evaluation_summary_table.csv"
    gpu_by_users = {r["users"]: r for r in gpu_rows}
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "users", "threads", "success_rate_percent", "failed_requests",
            "throughput_req_per_sec", "avg_latency_sec", "p50_latency_sec",
            "p99_latency_sec", "admission_waits", "admission_timeouts",
            "max_gpu_util_percent", "max_gpu_mem_mb", "max_gpu_temp_c",
            "max_gpu_power_w",
        ])
        for row in rows6:
            gpu = gpu_by_users[row["users"]]
            writer.writerow([
                row["users"], row["threads"], f'{row["success_rate"]:.1f}',
                row["failed"], f'{row["throughput"]:.3f}',
                f'{row["avg_latency"]:.3f}', f'{row["p50"]:.3f}',
                f'{row["p99"]:.3f}', row["admission_waits"],
                row["admission_timeouts"], gpu["max_util"], gpu["max_mem"],
                gpu["max_temp"], f'{gpu["max_power"]:.2f}',
            ])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows2 = metrics("final_eval_2workers")
    rows6 = metrics("final_eval_6workers")
    gpu6 = gpu_summary("final_eval_6workers")
    write_summary_csv(rows6, gpu6)

    users = [row["users"] for row in rows6]
    two_by_user = {row["users"]: row for row in rows2}
    six_by_user = {row["users"]: row for row in rows6}

    line_chart(
        OUT / "success_rate_scaling.svg",
        "Success Rate: Two Workers vs Six Workers",
        [
            {"name": "2 workers", "color": "#dc2626", "points": [(u, two_by_user[u]["success_rate"]) for u in users]},
            {"name": "6 workers", "color": "#2563eb", "points": [(u, six_by_user[u]["success_rate"]) for u in users]},
        ],
        "Success rate (%)",
        y_max=105,
    )
    line_chart(
        OUT / "throughput_scaling.svg",
        "Throughput Scaling with Six Thunder Workers",
        [
            {"name": "2 workers", "color": "#dc2626", "points": [(u, two_by_user[u]["throughput"]) for u in users]},
            {"name": "6 workers", "color": "#2563eb", "points": [(u, six_by_user[u]["throughput"]) for u in users]},
        ],
        "Requests / second",
    )
    grouped_bar_chart(
        OUT / "latency_summary_6workers.svg",
        "Latency Distribution Summary for Six-Worker Evaluation",
        [str(u) for u in users],
        [
            {"name": "p50", "values": [six_by_user[u]["p50"] for u in users]},
            {"name": "average", "values": [six_by_user[u]["avg_latency"] for u in users]},
            {"name": "p99", "values": [six_by_user[u]["p99"] for u in users]},
        ],
        "Latency (s)",
    )
    assign = six_by_user[1000]["assignments"]
    worker_ids = [str(i) for i in range(6)]
    bar_chart(
        OUT / "worker_assignments_1000.svg",
        "Load-Balancer Assignments in 1000-Request Run",
        [f"W{i}" for i in worker_ids],
        [float(assign.get(i, assign.get(str(i), 0))) for i in worker_ids],
        "Assigned requests",
        color="#059669",
    )
    bar_chart(
        OUT / "admission_backpressure.svg",
        "Admission Backpressure Events Under Load",
        [str(u) for u in users],
        [float(six_by_user[u]["admission_waits"]) for u in users],
        "Requests that waited",
        color="#7c3aed",
    )
    grouped_bar_chart(
        OUT / "gpu_summary_6workers.svg",
        "GPU Telemetry Maxima During Six-Worker Evaluation",
        [str(r["users"]) for r in gpu6],
        [
            {"name": "GPU util (%)", "values": [r["max_util"] for r in gpu6]},
            {"name": "Temp (C)", "values": [r["max_temp"] for r in gpu6]},
            {"name": "Power (W)", "values": [r["max_power"] for r in gpu6]},
        ],
        "Value",
    )
    latency_cdf(OUT / "latency_cdf_1000.svg", EVAL / "final_eval_6workers_users1000_threads120")
    architecture_svg(OUT / "architecture.svg")
    print(f"Wrote report figures to {OUT}")


if __name__ == "__main__":
    main()
