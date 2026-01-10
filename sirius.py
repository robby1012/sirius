#!/usr/bin/env python3
"""sirius.py

Simple async API performance tester and summary exporter.

Usage:
  python sirius.py -u <URL> -b '<BODY>' -n 100 -c 10 --summary-export out.json

Dependencies:
  pip install aiohttp

Author: Robby Sitanala

Version: 0.0.1
"""

from __future__ import annotations
import argparse
import asyncio
import csv
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime
from statistics import mean, median, stdev
from typing import Any, Dict, Iterable, List, Optional

try:
    import aiohttp
except Exception:
    aiohttp = None


def parse_headers(header_list: Optional[List[str]]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if not header_list:
        return headers
    for h in header_list:
        if ':' in h:
            k, v = h.split(':', 1)
            headers[k.strip()] = v.strip()
    return headers


def percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return float('nan')
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return d0 + d1


async def run_test(
    url: str,
    method: str,
    body: Optional[bytes],
    headers: Dict[str, str],
    total: int,
    concurrency: int,
    timeout: float,
) -> Dict[str, Any]:
    if aiohttp is None:
        raise RuntimeError("Missing dependency 'aiohttp'. Install with: pip install aiohttp")
    results: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(concurrency)
    timeout_cfg = aiohttp.ClientTimeout(total=timeout)

    connector = aiohttp.TCPConnector(limit=0)

    async with aiohttp.ClientSession(timeout=timeout_cfg, connector=connector) as session:
        # record a common start so we can compute relative start times
        start_all = time.perf_counter()

        async def do_request(i: int) -> None:
            nonlocal results
            async with sem:
                req_start_perf = time.perf_counter()
                req_start_epoch = time.time()
                try:
                    async with session.request(method, url, data=body, headers=headers) as resp:
                        payload = await resp.read()
                        elapsed = time.perf_counter() - req_start_perf
                        results.append({
                            'index': i,
                            'status': resp.status,
                            'time': elapsed,
                            'ok': 200 <= resp.status < 400,
                            'bytes': len(payload),
                            'start_epoch': req_start_epoch,
                            'start_rel_s': req_start_perf - start_all,
                        })
                except Exception as e:  # network/timeout
                    elapsed = time.perf_counter() - req_start_perf
                    results.append({'index': i, 'status': None, 'time': None, 'ok': False, 'error': str(e), 'start_epoch': req_start_epoch, 'start_rel_s': req_start_perf - start_all})

        tasks = [asyncio.create_task(do_request(i)) for i in range(total)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_all

    return {
        'results': results,
        'total_time': total_time,
    }


def summarize(results: List[Dict[str, Any]], total_time: float) -> Dict[str, Any]:
    total = len(results)
    successes = sum(1 for r in results if r.get('ok'))
    failures = total - successes
    times = sorted([r['time'] for r in results if r.get('time') is not None])
    status_counts = Counter(r['status'] for r in results if r.get('status') is not None)

    summary: Dict[str, Any] = {
        'total_requests': total,
        'successful_requests': successes,
        'failed_requests': failures,
        'total_duration_s': total_time,
        'requests_per_second': total / total_time if total_time > 0 else float('nan'),
        'status_counts': dict(status_counts),
    }

    if times:
        min_s = min(times)
        max_s = max(times)
        mean_s = mean(times)
        median_s = median(times)
        stdev_s = stdev(times) if len(times) > 1 else 0.0
        p50_s = percentile(times, 50)
        p90_s = percentile(times, 90)
        p95_s = percentile(times, 95)
        p99_s = percentile(times, 99)

        summary.update({
            'min_s': min_s,
            'max_s': max_s,
            'mean_s': mean_s,
            'median_s': median_s,
            'stdev_s': stdev_s,
            'p50_s': p50_s,
            'p90_s': p90_s,
            'p95_s': p95_s,
            'p99_s': p99_s,
            # Millisecond equivalents (rounded to 3 decimals)
            'min_ms': round(min_s * 1000.0, 3),
            'max_ms': round(max_s * 1000.0, 3),
            'mean_ms': round(mean_s * 1000.0, 3),
            'median_ms': round(median_s * 1000.0, 3),
            'stdev_ms': round(stdev_s * 1000.0, 3),
            'p50_ms': round(p50_s * 1000.0, 3),
            'p90_ms': round(p90_s * 1000.0, 3),
            'p95_ms': round(p95_s * 1000.0, 3),
            'p99_ms': round(p99_s * 1000.0, 3),
            'total_duration_ms': round(total_time * 1000.0, 3),
        })
    else:
        summary.update({
            'min_s': None,
            'max_s': None,
            'mean_s': None,
            'median_s': None,
            'stdev_s': None,
            'p50_s': None,
            'p90_s': None,
            'p95_s': None,
            'p99_s': None,
            'min_ms': None,
            'max_ms': None,
            'mean_ms': None,
            'median_ms': None,
            'stdev_ms': None,
            'p50_ms': None,
            'p90_ms': None,
            'p95_ms': None,
            'p99_ms': None,
            'total_duration_ms': round(total_time * 1000.0, 3),
        })

    return summary


def compute_time_series(results: List[Dict[str, Any]], total_time: float) -> List[Dict[str, Any]]:
    """Aggregate results into per-second buckets.

    Returns a list of dicts with keys: second (relative), start_epoch, count, successes, failures,
    requests_per_second, avg_latency_s, p50_s, p90_s, status_counts
    """
    if not results:
        return []
    # base epoch is the earliest request start
    epochs = [r['start_epoch'] for r in results if r.get('start_epoch') is not None]
    base_epoch = min(epochs) if epochs else time.time()

    buckets: Dict[int, Dict[str, Any]] = {}
    for r in results:
        rel = r.get('start_rel_s')
        if rel is None:
            continue
        sec = int(rel)
        b = buckets.setdefault(sec, {'count': 0, 'latencies': [], 'successes': 0, 'failures': 0, 'status_counts': {}})
        b['count'] += 1
        if r.get('time') is not None:
            b['latencies'].append(r['time'])
        if r.get('ok'):
            b['successes'] += 1
        else:
            b['failures'] += 1
        st = r.get('status')
        if st is not None:
            b['status_counts'][st] = b['status_counts'].get(st, 0) + 1

    series: List[Dict[str, Any]] = []
    max_sec = int(math.ceil(total_time)) if total_time and total_time > 0 else max(buckets.keys(), default=0)
    for s in range(0, max_sec + 1):
        b = buckets.get(s, {'count': 0, 'latencies': [], 'successes': 0, 'failures': 0, 'status_counts': {}})
        lats = sorted(b['latencies'])
        entry: Dict[str, Any] = {
            'second': s,
            'start_epoch': base_epoch + s,
            'count': b['count'],
            'successes': b['successes'],
            'failures': b['failures'],
            'requests_per_second': b['count'],
            'status_counts': b['status_counts'],
        }
        if lats:
            avg_s = mean(lats)
            p50_s = percentile(lats, 50)
            p90_s = percentile(lats, 90)
            entry.update({
                'avg_latency_s': avg_s,
                'p50_s': p50_s,
                'p90_s': p90_s,
                'avg_latency_ms': round(avg_s * 1000.0, 3),
                'p50_ms': round(p50_s * 1000.0, 3),
                'p90_ms': round(p90_s * 1000.0, 3),
            })
        else:
            entry.update({'avg_latency_s': None, 'p50_s': None, 'p90_s': None, 'avg_latency_ms': None, 'p50_ms': None, 'p90_ms': None})
        series.append(entry)
    return series


def write_request_log_csv(results: List[Dict[str, Any]], path: str) -> None:
    """Write per-request logs to a CSV file with a header."""
    fieldnames = ['index', 'start_epoch', 'start_rel_s', 'status', 'ok', 'time_s', 'time_ms', 'bytes', 'error']
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in sorted(results, key=lambda x: x.get('index', 0)):
            time_val = r.get('time')
            time_ms = round(time_val * 1000.0, 3) if time_val is not None else None
            writer.writerow({
                'index': r.get('index'),
                'start_epoch': r.get('start_epoch'),
                'start_rel_s': r.get('start_rel_s'),
                'status': r.get('status'),
                'ok': r.get('ok'),
                'time_s': time_val,
                'time_ms': time_ms,
                'bytes': r.get('bytes'),
                'error': r.get('error'),
            })


def write_summary_csv(summary: Dict[str, Any], path: str) -> None:
    """Write a one-row CSV summary."""
    # Flatten summary keys into columns
    fieldnames = sorted(k for k in summary.keys())
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        # ensure status_counts is JSON-serializable string
        row = dict(summary)
        if 'status_counts' in row:
            row['status_counts'] = json.dumps(row['status_counts'])
        writer.writerow(row)


def write_timeseries_csv(timeseries: List[Dict[str, Any]], path: str) -> None:
    """Write per-second time series to CSV."""
    fieldnames = ['second', 'start_epoch', 'count', 'successes', 'failures', 'requests_per_second', 'avg_latency_s', 'avg_latency_ms', 'p50_s', 'p50_ms', 'p90_s', 'p90_ms', 'status_counts']
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for e in timeseries:
            row = dict(e)
            # ensure ms fields are present
            row['avg_latency_ms'] = row.get('avg_latency_ms')
            row['p50_ms'] = row.get('p50_ms')
            row['p90_ms'] = row.get('p90_ms')
            row['status_counts'] = json.dumps(row.get('status_counts', {}))
            writer.writerow(row)


def plot_time_series(timeseries: List[Dict[str, Any]], path: str) -> None:
    """Plot requests/sec and avg latency over time and save to `path`.

    Requires matplotlib. If not installed, raises RuntimeError with install hint.
    """
    try:
        import matplotlib
        import matplotlib.pyplot as plt
    except Exception:
        raise RuntimeError("Missing dependency 'matplotlib'. Install with: pip install matplotlib")

    if not timeseries:
        raise ValueError("Empty timeseries")

    seconds = [e['second'] for e in timeseries]
    rps = [e.get('requests_per_second', 0) for e in timeseries]
    # prefer avg_latency_ms if present
    avg_lat = [e.get('avg_latency_ms') if e.get('avg_latency_ms') is not None else (e.get('avg_latency_s')*1000.0 if e.get('avg_latency_s') is not None else float('nan')) for e in timeseries]

    fig, ax1 = plt.subplots(figsize=(10, 4))
    ax1.bar(seconds, rps, color='C0', alpha=0.6, label='Requests/sec')
    ax1.set_xlabel('Second (relative)')
    ax1.set_ylabel('Requests/sec', color='C0')
    ax1.tick_params(axis='y', labelcolor='C0')

    ax2 = ax1.twinx()
    ax2.plot(seconds, avg_lat, color='C1', marker='o', label='Avg latency (ms)')
    ax2.set_ylabel('Avg latency (ms)', color='C1')
    ax2.tick_params(axis='y', labelcolor='C1')

    # Layout and save
    fig.tight_layout()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def generate_html_report(path: str, summary: Dict[str, Any], timeseries: List[Dict[str, Any]], request_log: Optional[str] = None, timeseries_json: Optional[str] = None, summary_json: Optional[str] = None, summary_csv: Optional[str] = None, timeseries_csv: Optional[str] = None, plot_png: Optional[str] = None) -> None:
    """Generate an interactive HTML report that includes:
    - Summary section (table)
    - Embedded timeseries JSON and Chart.js chart (requests/sec and avg latency)
    - Download links for provided CSV/JSON/PNG files
    """
    ts_json = json.dumps(timeseries)
    summary_json_str = json.dumps(summary)

    # Build HTML
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>API Performance Report</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; margin: 20px; }}
    .summary {{ margin-bottom: 20px; }}
    table.summary-table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
    table.summary-table td, table.summary-table th {{ border: 1px solid #ddd; padding: 8px; }}
    .links {{ margin: 12px 0; }}
    .chart {{ max-width: 900px; height: 360px; }}
  </style>
</head>
<body>
  <h1>API Performance Report</h1>
  <div class="summary">
    <h2>Summary</h2>
    <table class="summary-table">
"""

    # add summary rows
    for k, v in sorted(summary.items()):
        html += f"      <tr><th>{k}</th><td>{v}</td></tr>\n"

    html += "    </table>\n"

    # links
    html += "  <div class=\"links\">\n    <strong>Downloads:</strong> "
    links = []
    if summary_json:
        links.append(f'<a href="{os.path.basename(summary_json)}" download>{os.path.basename(summary_json)}</a>')
    if summary_csv:
        links.append(f'<a href="{os.path.basename(summary_csv)}" download>{os.path.basename(summary_csv)}</a>')
    if timeseries_json:
        links.append(f'<a href="{os.path.basename(timeseries_json)}" download>{os.path.basename(timeseries_json)}</a>')
    if timeseries_csv:
        links.append(f'<a href="{os.path.basename(timeseries_csv)}" download>{os.path.basename(timeseries_csv)}</a>')
    if request_log:
        links.append(f'<a href="{os.path.basename(request_log)}" download>{os.path.basename(request_log)}</a>')
    if plot_png:
        links.append(f'<a href="{os.path.basename(plot_png)}" download>{os.path.basename(plot_png)}</a>')

    html += ' | '.join(links) if links else 'None'
    html += "\n  </div>\n"

    # chart container
    html += "  <div class=\"chart\">\n    <canvas id=\"tsChart\"></canvas>\n  </div>\n"

    # include timeseries data
    html += f"  <script>\n    const TIMESERIES = {ts_json};\n    const ctx = document.getElementById('tsChart').getContext('2d');\n    const labels = TIMESERIES.map(e => e.second);\n    const rps = TIMESERIES.map(e => e.requests_per_second);\n    const avg = TIMESERIES.map(e => e.avg_latency_ms == null ? NaN : e.avg_latency_ms);\n\n    const chart = new Chart(ctx, {{\n      data: {{\n        labels: labels,\n        datasets: [{{ type: 'bar', label: 'Requests/sec', data: rps, yAxisID: 'y' }}, {{ type: 'line', label: 'Avg latency (ms)', data: avg, yAxisID: 'y1', borderColor: 'rgb(220, 80, 80)', backgroundColor: 'rgba(220,80,80,0.1)' }}]\n      }},\n      options: {{\n        responsive: true,\n        interaction: {{ mode: 'index', intersect: false }},\n        scales: {{\n          y: {{ position: 'left', title: {{ display: true, text: 'Requests/sec' }} }},\n          y1: {{ position: 'right', title: {{ display: true, text: 'Avg latency (ms)' }}, grid: {{ drawOnChartArea: false }} }}\n        }}\n      }}\n    }});\n  </script>\n"

    html += "</body>\n</html>"

    # write file
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)

    # copy referenced files to same directory as report if they exist and are not absolute
    report_dir = os.path.dirname(path) or '.'
    def try_copy(src):
        if not src:
            return
        if not os.path.exists(src):
            return
        dst = os.path.join(report_dir, os.path.basename(src))
        if os.path.abspath(src) != os.path.abspath(dst):
            try:
                with open(src, 'rb') as s, open(dst, 'wb') as d:
                    d.write(s.read())
            except Exception:
                pass

    try_copy(request_log)
    try_copy(timeseries_json)
    try_copy(summary_json)
    try_copy(summary_csv)
    try_copy(timeseries_csv)
    try_copy(plot_png)

    print(f"HTML report written to {path}")


def pretty_print(summary: Dict[str, Any]) -> None:
    print('\n=== API Performance Summary ===')
    print(f"Total requests: {summary['total_requests']}")
    print(f"Successful: {summary['successful_requests']}")
    print(f"Failed: {summary['failed_requests']}")
    print(f"Total duration: {summary.get('total_duration_ms', round(summary.get('total_duration_s', 0)*1000,3)):.3f} ms")
    rps = summary['requests_per_second']
    print(f"Requests/sec: {rps:.2f}")

    if summary['min_s'] is not None:
        print('\nLatency (ms):')
        print(f"  min: {summary['min_ms']:.3f}")
        print(f"  mean: {summary['mean_ms']:.3f}")
        print(f"  median: {summary['median_ms']:.3f}")
        print(f"  max: {summary['max_ms']:.3f}")
        print(f"  stdev: {summary['stdev_ms']:.3f}")
        print(f"  p50: {summary['p50_ms']:.3f}")
        print(f"  p90: {summary['p90_ms']:.3f}")
        print(f"  p95: {summary['p95_ms']:.3f}")
        print(f"  p99: {summary['p99_ms']:.3f}")

    print('\nStatus codes:')
    for st, cnt in sorted(summary['status_counts'].items()):
        print(f"  {st}: {cnt}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='API performance tester and summary exporter')
    parser.add_argument('-u', '--url', required=True, help='Target URL')
    parser.add_argument('-b', '--body', help='Request body (string or JSON)')
    parser.add_argument('-n', '--num', type=int, default=100, help='Number of requests to send (default 100)')
    parser.add_argument('-c', '--concurrency', type=int, default=10, help='Concurrency level (default 10)')
    parser.add_argument('--summary-export', help='Write summary JSON to file')
    parser.add_argument('-m', '--method', help='HTTP method (GET/POST/PUT/DELETE). Defaults to POST if -b provided else GET')
    parser.add_argument('-H', '--header', action='append', help='Custom header, repeatable, like "-H Content-Type: application/json"')
    parser.add_argument('-t', '--timeout', type=float, default=30.0, help='Request timeout in seconds (default 30)')
    parser.add_argument('--request-log', help='Write per-request CSV log to file (CSV). Columns: index,start_epoch,start_rel_s,status,ok,time_s,bytes,error')
    parser.add_argument('--timeseries-export', help='Write per-second time series JSON to file')
    parser.add_argument('--summary-csv', help='Write summary CSV (one-line summary)')
    parser.add_argument('--timeseries-csv', help='Write time series CSV (per-second rows)')
    parser.add_argument('--plot-timeseries', help='Save a PNG plot of the time series (requires matplotlib)')
    parser.add_argument('--html-report', help='Write an interactive HTML report (includes embedded timeseries chart via Chart.js)')
    args = parser.parse_args(argv)

    method = (args.method or ("POST" if args.body else "GET")).upper()

    if args.concurrency < 1:
        print('Concurrency must be >= 1', file=sys.stderr)
        return 2
    if args.num < 1:
        print('Number of requests must be >= 1', file=sys.stderr)
        return 2

    headers = parse_headers(args.header)

    body_bytes: Optional[bytes] = None
    if args.body is not None:
        # try to detect json
        try:
            js = json.loads(args.body)
            body_bytes = json.dumps(js).encode('utf-8')
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
        except Exception:
            body_bytes = args.body.encode('utf-8')

    # Cap concurrency to number of requests
    concurrency = min(args.concurrency, args.num)

    # Prefer asyncio.run where available; fall back to creating a new loop for compatibility
    try:
        res = asyncio.run(run_test(args.url, method, body_bytes, headers, args.num, concurrency, args.timeout))
    except RuntimeError:
        # fallback for environments where asyncio.run may fail due to loop policy
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(run_test(args.url, method, body_bytes, headers, args.num, concurrency, args.timeout))
        finally:
            try:
                loop.close()
            except Exception:
                pass

    summary = summarize(res['results'], res['total_time'])

    # optional: write per-request CSV log
    if getattr(args, 'request_log', None):
        write_request_log_csv(res['results'], args.request_log)
        print(f"Request log written to {args.request_log}")

    # optional: compute and write per-second timeseries
    ts: Optional[List[Dict[str, Any]]] = None
    if getattr(args, 'timeseries_export', None):
        ts = compute_time_series(res['results'], res['total_time'])
        with open(args.timeseries_export, 'w', encoding='utf-8') as fh:
            json.dump({'timeseries': ts, 'total_time_s': res['total_time']}, fh, indent=2)
        print(f"Time series written to {args.timeseries_export}")

    if getattr(args, 'summary_csv', None):
        write_summary_csv(summary, args.summary_csv)
        print(f"Summary CSV written to {args.summary_csv}")

    if getattr(args, 'timeseries_csv', None) and ts is not None:
        write_timeseries_csv(ts, args.timeseries_csv)
        print(f"Time series CSV written to {args.timeseries_csv}")

    if getattr(args, 'plot_timeseries', None) and ts is not None:
        try:
            plot_time_series(ts, args.plot_timeseries)
            print(f"Time series plot written to {args.plot_timeseries}")
        except Exception as e:
            print(f"Failed to create plot: {e}", file=sys.stderr)

    # optional: write HTML report
    if getattr(args, 'html_report', None):
        # ensure we have timeseries computed
        if ts is None:
            ts = compute_time_series(res['results'], res['total_time'])
        try:
            generate_html_report(args.html_report, summary, ts, request_log=args.request_log, timeseries_json=args.timeseries_export, summary_json=args.summary_export, summary_csv=args.summary_csv, timeseries_csv=args.timeseries_csv, plot_png=args.plot_timeseries)
        except Exception as e:
            print(f"Failed to write HTML report: {e}", file=sys.stderr)

    if args.summary_export:
        out = {
            'summary': summary,
            'total_time_s': res['total_time'],
        }
        # include timeseries in summary export if we computed it here but didn't write separate file
        if ts is not None and not getattr(args, 'timeseries_export', None):
            out['timeseries'] = ts
        with open(args.summary_export, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, indent=2)
        print(f"Summary written to {args.summary_export}")
    else:
        pretty_print(summary)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
