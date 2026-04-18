#!/usr/bin/env python3
"""
Plot GPU and scheduler time-series data from vLLM benchmarks.
Produces publication-quality PDF figures.

Usage:
    python plot_timeseries.py <timeseries_dir_or_file> [--output <output.pdf>]
"""

import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from collections import defaultdict
from scipy import interpolate

# Publication-quality settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'serif'],
    'font.size': 13,
    'axes.titlesize': 14,
    'axes.labelsize': 13,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
    'figure.titlesize': 15,
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'lines.linewidth': 1.2,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
})

# Color palette — one color per NODE (colorblind-friendly, high contrast)
NODE_PLOT_COLORS = [
    '#0072B2',  # Blue   — Node 0
    '#D55E00',  # Orange — Node 1
    '#009E73',  # Green  — Node 2
    '#CC79A7',  # Pink   — Node 3
    '#E69F00',  # Amber  — Node 4
    '#56B4E9',  # Sky    — Node 5
]

# Markers — one per GPU index within a node (visually distinct shapes)
GPU_MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X', 'h']

# Scheduler / queue colors
COLORS = {
    'avg': '#333333',
    'running': '#0072B2',
    'waiting': '#D55E00',
    'swapped': '#009E73',
}

# Colors per node (used for node-average plots)
NODE_COLORS = ['#2E86AB', '#FF6B35', '#2E8B57', '#A23B72', '#F18F01', '#8B008B']


def gpu_style(gpu_id):
    """Return (color, marker, label) for a gpu_id like 'node0_gpu1' or 'gpu0'.

    Color encodes the node, marker encodes the GPU index within the node.
    """
    if gpu_id.startswith('node'):
        parts = gpu_id.split('_')
        node_num = int(parts[0][4:])
        gpu_num = int(parts[1][3:])
        color = NODE_PLOT_COLORS[node_num % len(NODE_PLOT_COLORS)]
        marker = GPU_MARKERS[gpu_num % len(GPU_MARKERS)]
        label = f'N{node_num}:G{gpu_num}'
    else:
        gpu_num = int(gpu_id[3:])
        color = NODE_PLOT_COLORS[gpu_num % len(NODE_PLOT_COLORS)]
        marker = GPU_MARKERS[0]
        label = f'GPU {gpu_num}'
    return color, marker, label


def load_timeseries(path: Path) -> list[dict]:
    """Load timeseries data from file or directory."""
    experiments = []

    if path.is_file():
        with open(path) as f:
            experiments.append(json.load(f))
    elif path.is_dir():
        for json_file in sorted(path.glob('timeseries_*.json')):
            with open(json_file) as f:
                experiments.append(json.load(f))

    return experiments


def extract_gpu_data(gpu_timeseries: list[dict]) -> dict:
    """
    Extract GPU metrics into arrays for plotting.
    
    Handles the case where different GPUs are sampled at different times.
    Each GPU metric gets its own time series (only times when that GPU was sampled).
    """
    if not gpu_timeseries:
        return {}

    # First pass: collect all unique metric keys
    all_keys = set()
    for sample in gpu_timeseries:
        for key in sample.keys():
            if key != 't':
                all_keys.add(key)
    
    # Second pass: extract data per metric (each metric has its own time series)
    data = {}
    for key in all_keys:
        times = []
        values = []
        for sample in gpu_timeseries:
            if key in sample:
                times.append(sample['t'])
                values.append(sample[key])
        if times:  # Only add if we have data
            data[key] = {
                'time': np.array(times),
                'value': np.array(values)
            }
    
    # Also create a unified time array for backward compatibility (all unique times)
    all_times = sorted(set(sample['t'] for sample in gpu_timeseries))
    data['_all_times'] = np.array(all_times)
    
    return data


def extract_scheduler_data(scheduler_timeseries: list[dict]) -> dict:
    """Extract scheduler metrics into arrays for plotting."""
    if not scheduler_timeseries:
        return {}

    data = defaultdict(list)

    for sample in scheduler_timeseries:
        data['time'].append(sample['t'])
        for key, value in sample.items():
            if key != 't':
                data[key].append(value)

    return {k: np.array(v) for k, v in data.items()}


def extract_node_avg_timeseries(gpu_timeseries: list[dict]) -> dict:
    """
    Compute per-node average of sm_pct and membw_pct at each timestep.
    Returns {node_id: {'time': np.array, 'sm_pct': np.array, 'membw_pct': np.array}}
    """
    if not gpu_timeseries:
        return {}

    # Discover node ids and their GPU keys from the first sample
    node_sm_keys = defaultdict(list)
    node_bw_keys = defaultdict(list)
    for key in gpu_timeseries[0].keys():
        if key == 't':
            continue
        if key.startswith('node') and '_gpu' in key:
            parts = key.split('_')
            node_id = int(parts[0][4:])
            if key.endswith('_sm_pct'):
                node_sm_keys[node_id].append(key)
            elif key.endswith('_membw_pct'):
                node_bw_keys[node_id].append(key)

    node_ids = sorted(set(node_sm_keys) | set(node_bw_keys))
    if not node_ids:
        return {}

    result = {n: {'time': [], 'sm_pct': [], 'membw_pct': []} for n in node_ids}

    for sample in gpu_timeseries:
        t = sample['t']
        for n in node_ids:
            sm_vals = [sample[k] for k in node_sm_keys[n] if k in sample]
            bw_vals = [sample[k] for k in node_bw_keys[n] if k in sample]
            result[n]['time'].append(t)
            result[n]['sm_pct'].append(np.mean(sm_vals) if sm_vals else np.nan)
            result[n]['membw_pct'].append(np.mean(bw_vals) if bw_vals else np.nan)

    raw = {n: {k: np.array(v) for k, v in d.items()} for n, d in result.items()}

    # Apply 30-second centered rolling average for smoothing
    WINDOW_SEC = 10.0
    for n, d in raw.items():
        t = d['time']
        for metric in ('sm_pct', 'membw_pct'):
            vals = d[metric]
            smoothed = np.empty_like(vals)
            for i in range(len(t)):
                mask = np.abs(t - t[i]) <= WINDOW_SEC / 2
                smoothed[i] = np.nanmean(vals[mask])
            d[metric] = smoothed

    return raw


def get_gpu_identifiers(gpu_data: dict) -> list[str]:
    """
    Extract unique GPU identifiers from data keys.

    Handles both formats:
    - Old single-node: gpu0_sm_pct, gpu1_sm_pct -> ['gpu0', 'gpu1']
    - New multi-node: node0_gpu0_sm_pct, node1_gpu0_sm_pct -> ['node0_gpu0', 'node1_gpu0']

    Returns sorted list of GPU identifiers.
    """
    gpu_ids = set()
    for key in gpu_data.keys():
        if key == '_all_times' or key == 'time':
            continue
        # Check for node-prefixed format: node0_gpu0_metric
        if key.startswith('node') and '_gpu' in key:
            parts = key.split('_')
            if len(parts) >= 3:
                gpu_id = f"{parts[0]}_{parts[1]}"  # e.g., "node0_gpu0"
                gpu_ids.add(gpu_id)
        # Check for old format: gpu0_metric
        elif key.startswith('gpu') and '_' in key:
            gpu_id = key.split('_')[0]  # e.g., "gpu0"
            gpu_ids.add(gpu_id)

    # Sort: by node first (if present), then by GPU number
    def sort_key(gpu_id):
        if gpu_id.startswith('node'):
            parts = gpu_id.split('_')
            node_num = int(parts[0][4:])  # Extract number from "node0"
            gpu_num = int(parts[1][3:])   # Extract number from "gpu0"
            return (node_num, gpu_num)
        else:
            return (0, int(gpu_id[3:]))   # Single node: sort by GPU number

    return sorted(gpu_ids, key=sort_key)


def get_num_gpus(gpu_data: dict) -> int:
    """Determine number of GPUs from data keys (legacy compatibility)."""
    return len(get_gpu_identifiers(gpu_data))


def plot_experiment(exp_data: dict, output_path: Path):
    """Create a multi-panel figure for one experiment."""

    gpu_timeseries_raw = exp_data.get('gpu_timeseries', [])
    gpu_data = extract_gpu_data(gpu_timeseries_raw)
    node_avg_data = extract_node_avg_timeseries(gpu_timeseries_raw)
    scheduler_data = extract_scheduler_data(exp_data.get('scheduler_timeseries', []))

    config = exp_data.get('config', {})
    exp_id = exp_data.get('exp_id', 'unknown')
    elapsed = exp_data.get('elapsed_time', 0)
    
    # Get result record from results.json in the same directory
    instance_type = None
    gpu_type = None
    result_record = {}
    try:
        results_json_path = output_path.parent / 'results.json'
        if results_json_path.exists():
            with open(results_json_path, 'r') as f:
                results_data = json.load(f)
                if isinstance(results_data, list) and len(results_data) > 0:
                    # Find matching experiment by exp_id, or fall back to first
                    result_record = results_data[0]
                    for r in results_data:
                        if r.get('exp_id') == exp_id:
                            result_record = r
                            break
                elif isinstance(results_data, dict):
                    result_record = results_data

                instance_type = result_record.get('instance_type')
                gpu_type = result_record.get('gpu_type')

                # If gpu_type not found, infer from instance_type
                if not gpu_type and instance_type:
                    instance_str = instance_type.lower()
                    if 'g6e' in instance_str:
                        gpu_type = 'L40S'
                    elif 'g6' in instance_str and 'g6e' not in instance_str:
                        gpu_type = 'L4'
                    elif 'g5' in instance_str:
                        gpu_type = 'A10G'
                    elif 'p4d' in instance_str:
                        gpu_type = 'A100_40gb'
                    elif 'p4de' in instance_str:
                        gpu_type = 'A100_80gb'
    except Exception:
        pass

    # Determine what to plot
    has_gpu = bool(gpu_data)
    has_scheduler = bool(scheduler_data)
    has_kv_cache = 'kv_cache_util_pct' in scheduler_data if scheduler_data else False
    has_queues = any(k in scheduler_data for k in ['running', 'waiting', 'swapped']) if scheduler_data else False
    has_throughput = 'tps_total' in scheduler_data if scheduler_data else False
    gpu_ids = get_gpu_identifiers(gpu_data) if has_gpu else []
    num_gpus = len(gpu_ids)

    # Calculate number of subplots needed
    # 1. Node-average SM Utilization (if >1 node)
    # 2. Node-average Memory BW Utilization (if >1 node)
    # 3. Throughput (tok/s, if available)
    # 4. KV Cache Utilization (if available)
    # 5. Scheduler Queues (if available)

    has_node_avg = bool(node_avg_data) and len(node_avg_data) > 1  # only useful with >1 node
    has_summary = bool(result_record) and result_record.get('status') == 'success'
    num_plots = 0
    if has_node_avg:
        num_plots += 2  # node-avg SM and node-avg Mem BW
    if has_throughput:
        num_plots += 1
    if has_kv_cache:
        num_plots += 1
    if has_queues:
        num_plots += 1
    if has_summary:
        num_plots += 1  # text summary panel

    # Create figure — summary panel gets 2× height so text fits without overlap
    SUMMARY_RATIO = 1
    height_ratios = []
    if has_summary:
        height_ratios.append(SUMMARY_RATIO)
    height_ratios += [1] * (num_plots - (1 if has_summary else 0))

    fig_height = 3.0 * (num_plots - (1 if has_summary else 0)) + (3.0 * SUMMARY_RATIO if has_summary else 0)
    fig, axes = plt.subplots(num_plots, 1, figsize=(10, fig_height),
                             gridspec_kw={'height_ratios': height_ratios})

    if num_plots == 1:
        axes = [axes]

    # Get all times to determine time unit and calculate GPU time
    all_times = gpu_data.get('_all_times', np.array([]))
    if len(all_times) == 0 and gpu_data:
        # Fallback: get times from first available metric
        for key, value in gpu_data.items():
            if isinstance(value, dict) and 'time' in value:
                all_times = value['time']
                break
    
    # Calculate GPU monitoring time span
    gpu_time = 0.0
    if len(all_times) > 0:
        gpu_time = all_times[-1] - all_times[0] if len(all_times) > 1 else 0.0

    # Title with experiment configuration
    model_name = config.get('model', 'Unknown').split('/')[-1]
    title_parts = [model_name]
    title_parts.append(f"TP={config.get('tp', '?')}, PP={config.get('pp', '?')}, Input={config.get('max_input_length', '?')}, Output={config.get('max_output_length', '?')}")
    title_parts.append(f"Instance={instance_type}, GPU={gpu_type}")
    title = "\n".join(title_parts)
    fig.suptitle(title, y=0.995)

    ax_idx = 0

    # Convert time to minutes if > 120 seconds
    time_unit = 's'
    time_divisor = 1
    if len(all_times) > 0 and all_times[-1] > 120:
        time_unit = 'min'
        time_divisor = 60

    # Precompute KV-full regions (in plot time units) for cross-panel shading
    kv_full_regions = []
    kv_full_pct = 0.0
    if has_scheduler and 'kv_cache_util_pct' in scheduler_data:
        kv_pct = scheduler_data['kv_cache_util_pct']
        sched_time_raw = scheduler_data.get('time', np.array([]))
        sched_time_scaled = sched_time_raw / time_divisor
        kv_full_mask = kv_pct >= 99.0
        kv_full_pct = np.sum(kv_full_mask) / len(kv_full_mask) * 100 if len(kv_full_mask) > 0 else 0
        # Find contiguous runs
        in_region = False
        region_start = None
        for i in range(len(kv_full_mask)):
            if kv_full_mask[i] and not in_region:
                region_start = sched_time_scaled[i]
                in_region = True
            elif not kv_full_mask[i] and in_region:
                kv_full_regions.append((region_start, sched_time_scaled[i]))
                in_region = False
        if in_region:
            kv_full_regions.append((region_start, sched_time_scaled[-1]))

    def _shade_kv_full(ax, zorder=0):
        """Shade KV-full regions on any axis. Returns a legend handle (or None)."""
        for (t0, t1) in kv_full_regions:
            ax.axvspan(t0, t1, alpha=0.10, color='#DC143C', zorder=zorder)
        if kv_full_regions:
            return ax.axvspan(0, 0, alpha=0.10, color='#DC143C', label='KV full', zorder=zorder)
        return None

    # Helper: plot one GPU metric across all GPUs
    def _plot_gpu_metric(ax, gpu_ids, gpu_data, metric_suffix, time_divisor):
        """Plot a metric for all GPUs with randomized z-order.
        Returns (all_vals, legend_handles)."""
        all_points = []  # (time, value, color, marker)
        legend_entries = []  # (gpu_id, color, marker, label) in original order

        for gpu_id in gpu_ids:
            key = f'{gpu_id}_{metric_suffix}'
            if key in gpu_data and isinstance(gpu_data[key], dict):
                metric_data = gpu_data[key]
                time_arr = metric_data['time']
                values = metric_data['value']
                time_plot = time_arr / time_divisor
                color, marker, label = gpu_style(gpu_id)
                legend_entries.append((color, marker, label))
                for t, v in zip(time_plot, values):
                    all_points.append((t, v, color, marker))

        if not all_points:
            return [], []

        # Shuffle all points so no single GPU consistently renders on top
        rng = np.random.default_rng(seed=42)
        idxs = np.arange(len(all_points))
        rng.shuffle(idxs)
        all_points = [all_points[i] for i in idxs]

        # Group by marker (scatter requires uniform marker per call)
        marker_groups = defaultdict(lambda: {'times': [], 'values': [], 'colors': []})
        for t, v, color, marker in all_points:
            marker_groups[marker]['times'].append(t)
            marker_groups[marker]['values'].append(v)
            marker_groups[marker]['colors'].append(color)

        for marker, data in marker_groups.items():
            ax.scatter(data['times'], data['values'],
                       edgecolors=data['colors'], facecolors='none',
                       marker=marker, s=30, alpha=0.35, linewidths=1.2)

        # Proxy artists for the legend (one per GPU, in original order)
        legend_handles = [
            ax.scatter([], [], edgecolors=color, facecolors='none',
                       marker=marker, s=30, linewidths=1.2, label=label)
            for color, marker, label in legend_entries
        ]

        all_vals = [p[1] for p in all_points]
        return all_vals, legend_handles

    # Legend layout for per-GPU panels:
    # Group by GPU-index-within-node → ncol=num_nodes, reorder handles so each
    # row = same GPU index across nodes (N0:G0, N1:G0, N2:G0 / N0:G1, N1:G1, ...).
    if gpu_ids and gpu_ids[0].startswith('node'):
        _num_nodes = len(set(g.split('_')[0] for g in gpu_ids))
        _gpus_per_node = len(gpu_ids) // _num_nodes if _num_nodes else len(gpu_ids)
        legend_ncol = _num_nodes
    else:
        _num_nodes = 1
        _gpus_per_node = num_gpus
        legend_ncol = min(num_gpus, 6)


    # --- Summary Panel (from results.json) — rendered first ---
    if has_summary:
        ax = axes[ax_idx]
        ax.axis('off')

        r = result_record
        elapsed_s = r.get('elapsed_time', 0)
        elapsed_str = f'{int(elapsed_s//60)}m {elapsed_s%60:.0f}s' if elapsed_s >= 60 else f'{elapsed_s:.1f}s'

        send_all = r.get('benchmark_send_all', False)
        concurrency = r.get('benchmark_target_concurrency', '?')
        mode_str = 'send-all' if send_all else 'rate-limited'

        # Two rows × two columns layout
        rows_data = [
            [
                ('Throughput', [
                    # ('Total tok/s', f'{r.get("total_tokens_per_sec", 0):,.1f}'),
                    ('Prefill tok/s', f'{r.get("input_tokens_per_sec", 0):,.1f}'),
                    ('Decode tok/s', f'{r.get("output_tokens_per_sec", 0):,.1f}'),
                    ('Requests/sec', f'{r.get("requests_per_sec", 0):.3f}'),
                ]),
                ('Cost & Time', [
                    ('Elapsed', elapsed_str),
                    ('Cost', f'${r.get("cost_for_run_usd", 0):.2f}'),
                    ('Tok/dollar', f'{r.get("tokens_per_dollar", 0):,.0f}'),
                    ('$/1M tok', f'{r.get("cost_per_1m_tokens_total_usd", "N/A"):.2f}'),
                ]),
            ],
            [
                ('Benchmark Config', [
                    ('Mode', mode_str),
                    # ('Concurrency', f'{concurrency}'),
                    ('Requests', f'{r.get("benchmark_num_requests", "?")}'),
                    ('Preemptions', f'{r.get("num_preemptions", 0)}'),
                ]),
                ('GPU Utilization (avg)', [
                    ('SM util', f'{r.get("avg_sm_util_pct", 0):.0f}%'),
                    ('Mem BW util', f'{r.get("avg_mem_bw_util_pct", 0):.0f}%'),
                    ('Mem util', f'{r.get("avg_mem_util_pct", 0):.0f}%'),
                    ('Nodes', f'{r.get("gpu_monitor_num_nodes", "?")}'),
                ]),
            ],
        ]

        # 4-column single-row layout — each section is a title + monospace body block
        # Flatten rows_data into a single list of 4 sections
        all_sections = [sec for row in rows_data for sec in row]
        col_x = [0.02, 0.27, 0.52, 0.77]
        y_top = 0.92
        pad = 15  # label column width for monospace alignment

        for col_idx, (section_title, items) in enumerate(all_sections):
            cx = col_x[col_idx]
            ax.text(cx, y_top, section_title,
                    fontsize=12, fontweight='bold', color='#1a1a1a',
                    transform=ax.transAxes, va='top')
            body = '\n'.join(f'{label:<{pad}}{value}' for label, value in items)
            ax.text(cx, y_top - 0.22, body,
                    fontsize=11, color='#333333',
                    transform=ax.transAxes, va='top',
                    fontfamily='monospace')

        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_edgecolor('#cccccc')
            spine.set_linewidth(0.8)
        ax.set_facecolor('#f8f8f8')
        ax_idx += 1

    def _add_gpu_legends(ax, handles, kv_h):
        """GPU legend above the axes; KV full as a separate corner legend."""
        gpu_leg = ax.legend(handles=handles,
                            loc='upper center', bbox_to_anchor=(0.5, 2.30),
                            ncol=legend_ncol, framealpha=0.9,
                            handletextpad=0.3, columnspacing=0.8)
        ax.add_artist(gpu_leg)
        if kv_h:
            ax.legend(handles=[kv_h], loc='upper right', framealpha=0.9,
                      handlelength=1.2, handletextpad=0.4)

    # --- Node-average SM and Memory BW Utilization ---
    if has_node_avg:
        for metric_key, ylabel, title_str in [
            ('sm_pct', 'Avg SM Util. (%)\nper Node', 'Average SM Utilization per Node'),
            ('membw_pct', 'Avg Mem BW Util. (%)\nper Node', 'Average Memory Bandwidth Utilization per Node'),
        ]:
            ax = axes[ax_idx]
            kv_h = _shade_kv_full(ax)
            node_handles = []
            for node_id, nd in sorted(node_avg_data.items()):
                t_plot = nd['time'] / time_divisor
                color = NODE_PLOT_COLORS[node_id % len(NODE_PLOT_COLORS)]
                line, = ax.plot(t_plot, nd[metric_key],
                                color=color, linewidth=1.5, alpha=0.9,
                                label=f'Node {node_id}')
                node_handles.append(line)
            if kv_h:
                node_handles.append(kv_h)
            ax.set_ylabel(ylabel)
            ax.set_xlabel(f'Time ({time_unit})')
            ax.set_ylim(-5, 105)
            ax.yaxis.set_major_locator(ticker.MultipleLocator(25))
            ax.grid(True, alpha=0.3)
            ax.set_title(title_str, pad=2)
            ax.legend(handles=node_handles, loc='upper right', framealpha=0.9)
            ax_idx += 1

    # --- Throughput (tok/s) ---
    if has_throughput:
        ax = axes[ax_idx]
        sched_time = scheduler_data.get('time', np.array([]))
        sched_time_plot = sched_time / time_divisor

        tps_total = scheduler_data.get('tps_total', np.array([]))
        tps_prefill = scheduler_data.get('tps_prefill', np.array([]))
        tps_decode = scheduler_data.get('tps_decode', np.array([]))

        kv_h = _shade_kv_full(ax)

        # Interleave prefill/decode points randomly so neither always renders on top
        tps_points = (
            [(t, v, '#2E8B57', 'prefill') for t, v in zip(sched_time_plot, tps_prefill)] +
            [(t, v, '#F18F01', 'decode') for t, v in zip(sched_time_plot, tps_decode)]
        )
        rng = np.random.default_rng(seed=42)
        rng.shuffle(tps_points)
        t_arr = [p[0] for p in tps_points]
        v_arr = [p[1] for p in tps_points]
        c_arr = [p[2] for p in tps_points]
        ax.scatter(t_arr, v_arr, c=c_arr, alpha=0.35, s=15)
        sc_prefill = ax.scatter([], [], color='#2E8B57', alpha=0.35, s=15, label='Prefill tok/s')
        sc_decode  = ax.scatter([], [], color='#F18F01', alpha=0.35, s=15, label='Decode tok/s')

        ax.set_title('Throughput (tok/s)', pad=2)
        ax.set_ylabel('Throughput (tok/s)')
        ax.set_xlabel(f'Time ({time_unit})')
        ax.grid(True, alpha=0.3)
        tps_handles = [sc_prefill, sc_decode]
        if kv_h:
            tps_handles.append(kv_h)
        ax.legend(handles=tps_handles, loc='upper right', framealpha=0.9)
        ax_idx += 1

    # --- KV Cache Utilization ---
    if has_kv_cache:
        ax = axes[ax_idx]
        sched_time = scheduler_data.get('time', np.array([]))
        sched_time_plot = sched_time / time_divisor

        kv_h = _shade_kv_full(ax, zorder=3)
        line_kv, = ax.plot(sched_time_plot, scheduler_data['kv_cache_util_pct'],
                           color='#E69F00', linewidth=1.5, label='KV Cache Util.')
        ax.fill_between(sched_time_plot, 0, scheduler_data['kv_cache_util_pct'],
                        alpha=0.3, color='#E69F00')

        ax.set_title('KV Cache Utilization', pad=2)
        ax.set_ylabel('KV Cache Util. (%)')
        ax.set_xlabel(f'Time ({time_unit})')
        ax.set_ylim(-5, 105)
        ax.yaxis.set_major_locator(ticker.MultipleLocator(25))
        ax.grid(True, alpha=0.3)
        kv_handles = [line_kv]
        if kv_h:
            kv_handles.append(kv_h)
        ax.legend(handles=kv_handles, loc='lower right', framealpha=0.9)
        ax_idx += 1

    # --- Scheduler Queues ---
    if has_queues:
        ax = axes[ax_idx]
        sched_time = scheduler_data.get('time', np.array([]))
        sched_time_plot = sched_time / time_divisor

        kv_h = _shade_kv_full(ax)
        queue_handles = []
        if 'running' in scheduler_data:
            line, = ax.plot(sched_time_plot, scheduler_data['running'],
                            color=COLORS['running'], label='Running', linewidth=1.5)
            queue_handles.append(line)
        if 'waiting' in scheduler_data:
            line, = ax.plot(sched_time_plot, scheduler_data['waiting'],
                            color=COLORS['waiting'], label='Waiting', linewidth=1.5)
            queue_handles.append(line)
        if 'swapped' in scheduler_data:
            line, = ax.plot(sched_time_plot, scheduler_data['swapped'],
                            color=COLORS['swapped'], label='Swapped', linewidth=1.5)
            queue_handles.append(line)
        if kv_h:
            queue_handles.append(kv_h)

        ax.set_title('Scheduler Queue Depth', pad=2)
        ax.set_ylabel('Queue Depth')
        ax.set_xlabel(f'Time ({time_unit})')
        ax.grid(True, alpha=0.3)
        ax.legend(handles=queue_handles, loc='upper right', framealpha=0.9)
        ax_idx += 1

    # Adjust layout — more vertical space between subplots for legends
    plt.tight_layout()
    plt.subplots_adjust(top=0.92, hspace=0.6)

    # Save figure
    fig.savefig(output_path, format='pdf', bbox_inches='tight')
    fig.savefig(output_path.with_suffix('.png'), format='png', bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {output_path}")


def plot_all_experiments(experiments: list[dict], output_path: Path):
    """Create a combined figure with all experiments, or individual files."""

    if len(experiments) == 1:
        plot_experiment(experiments[0], output_path)
        return

    # Multiple experiments: create one PDF per experiment
    output_dir = output_path.parent
    base_name = output_path.stem

    for exp in experiments:
        exp_id = exp.get('exp_id', 'unknown')
        exp_output = output_dir / f"{base_name}_{exp_id}.pdf"
        plot_experiment(exp, exp_output)

    print(f"\nGenerated {len(experiments)} PDF files in {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Plot GPU and scheduler time-series from vLLM benchmarks')
    parser.add_argument('input', type=Path,
                       help='Timeseries JSON file or directory containing timeseries files')
    parser.add_argument('--output', '-o', type=Path, default=None,
                       help='Output PDF path (default: timeseries_plot.pdf)')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} does not exist")
        return 1

    # Default output path
    if args.output is None:
        if args.input.is_file():
            args.output = args.input.with_suffix('.pdf')
        else:
            args.output = args.input / 'timeseries_plot.pdf'

    # Load data
    experiments = load_timeseries(args.input)

    if not experiments:
        print(f"Error: No timeseries data found in {args.input}")
        return 1

    print(f"Loaded {len(experiments)} experiment(s)")

    # Plot
    plot_all_experiments(experiments, args.output)

    return 0


if __name__ == '__main__':
    exit(main())
