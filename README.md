# API Performance Tester — GUIDE ✅

Short guide for using `sirius.py` to run simple API performance tests and produce a summary.

---

## History

This tool was built to address a specific need: **simpler API testing with detailed metrics**. Many existing load testing tools are either too complex (requiring extensive setup and configuration) or too simplistic (providing only basic metrics without percentiles or time-series data).

I needed a lightweight, command-line tool that could:
- Run quick ad-hoc API performance tests without ceremony
- Provide comprehensive statistical analysis (percentiles, standard deviation, tail latency)
- Export results in multiple formats (JSON, CSV, HTML) for further analysis
- Generate visual reports without requiring separate tools

The result is this single-file Python script that balances simplicity with depth. It's designed for developers and QA engineers who want to quickly validate API performance, identify bottlenecks, and generate reports for stakeholders—all with a single command.

Additionally, this project serves as an experiment in building desktop applications using **Qt & PyQt**. The GUI version (under development in the `gui/` folder) explores modern Python desktop UI development, demonstrating how to create intuitive interfaces for technical tools while maintaining the powerful command-line core.

---

## Requirements

- Python 3.8+
- Install dependency:

```bash
pip install -r requirements.txt
```

---

## What it does

- Sends N HTTP requests to a target URL with configurable concurrency and timeout.
- Collects per-request latency and status code, then prints a concise summary or exports it to JSON.

---

## Usage

Basic command:

```bash
python sirius.py -u <URL> [-b '<BODY>'] -n <NUMBER_OF_REQUESTS> -c <CONCURRENCY_LEVEL> [--summary-export <OUT.json>]
```

Options (common):

- `-u, --url` (required): Target URL
- `-b, --body`: Request body (string or JSON). If valid JSON, Content-Type is set to `application/json` automatically.
- `-n, --num`: Number of requests (default: 100)
- `-c, --concurrency`: Concurrency level (default: 10)
- `--summary-export`: Path to write summary JSON
- `-m, --method`: HTTP method (auto-uses POST if `-b` supplied; otherwise GET)
- `-H, --header`: Custom header, repeatable (e.g., `-H "Authorization: Bearer TOKEN"`)
- `-t, --timeout`: Timeout per request in seconds (default: 30)
- `--request-log`: Write per-request CSV log to file (CSV). Columns: index,start_epoch,start_rel_s,status,ok,time_s,bytes,error
- `--timeseries-export`: Write per-second time series JSON to file (JSON)
- `--summary-csv`: Write a one-row summary CSV file
- `--timeseries-csv`: Write per-second time series CSV
- `--plot-timeseries`: Save a PNG plot of the time series (requires `matplotlib`)
- `--html-report`: Write a self-contained HTML report (interactive chart via Chart.js, includes download links for CSV/JSON/PNG when present)

---

## Examples

Print summary to console:

```bash
python sirius.py -u https://httpbin.org/post -b '{"foo": "bar"}' -n 200 -c 20
```

Save summary as JSON:

```bash
python sirius.py -u https://httpbin.org/post -b '{"foo": "bar"}' -n 200 -c 20 --summary-export out.json
```

Save per-request CSV log:

```bash
python sirius.py -u https://httpbin.org/post -b '{"foo": "bar"}' -n 200 -c 20 --request-log requests.csv
```

Save per-second time series (JSON):

```bash
python sirius.py -u https://httpbin.org/post -b '{"foo": "bar"}' -n 200 -c 20 --timeseries-export timeseries.json
```

Save time series as CSV and summary CSV:

```bash
python sirius.py -u https://httpbin.org/post -b '{"foo": "bar"}' -n 200 -c 20 --timeseries-csv timeseries.csv --summary-csv summary.csv
```

Save a PNG plot of the time series (requires matplotlib):

```bash
python sirius.py -u https://httpbin.org/post -b '{"foo": "bar"}' -n 200 -c 20 --timeseries-export timeseries.json --plot-timeseries timeseries.png
```

Generate an interactive HTML report (includes embedded Chart.js chart):

```bash
python sirius.py -u https://httpbin.org/post -b '{"foo": "bar"}' -n 200 -c 20 --request-log requests.csv --timeseries-export timeseries.json --summary-export summary.json --timeseries-csv timeseries.csv --summary-csv summary.csv --plot-timeseries timeseries.png --html-report report.html
```

With headers:

```bash
python sirius.py -u https://example.com/api -b '{"a":1}' -H "Authorization: Bearer TOKEN" -H "X-Env: prod"
```

---

## Request log & time series format

- Request log (`--request-log` CSV): columns are `index`, `start_epoch` (unix epoch), `start_rel_s` (seconds since test start), `status`, `ok`, `time_s` (latency seconds), `time_ms` (latency milliseconds, 3-decimal places), `bytes`, `error`.
- Time series (`--timeseries-export` JSON): contains `timeseries` array of objects per second:
  - `second` (relative second index), `start_epoch` (bucket epoch), `count`, `successes`, `failures`, `requests_per_second`, `avg_latency_s`, `avg_latency_ms`, `p50_s`, `p50_ms`, `p90_s`, `p90_ms`, `status_counts`.

Notes: The report prints and CSVs include millisecond statistics (`*_ms`) rounded to 3 decimal places.

---

## What the summary contains

- total_requests, successful_requests, failed_requests
- total_duration_s, requests_per_second
- latency metrics (min/mean/median/max/stdev) and percentiles (p50/p90/p95/p99)
- counts per status code

When `--summary-export` is used, a JSON file containing `summary` and `total_time_s` will be written.

---

## Tips & Caveats

- Use a reasonable concurrency and request count to avoid unintended load on production systems.
- For accurate high-load testing, run from a machine with sufficient network and CPU resources.
- The script is simple and not a full-featured load tester (no ramp-up, no complex scenarios, no connection pooling beyond aiohttp defaults).
- Plotting requires `matplotlib`; install it with `pip install matplotlib` if you want PNG output.
- Consider more advanced tools (e.g., k6, Locust) for complex or long-running test scenarios.

---

## Troubleshooting

- If you see network errors or timeouts, increase `-t/--timeout` and/or reduce concurrency.
- If many requests fail with connection errors, check rate limits, firewalls, or server-side protections.

---

## Want more?

If you want CSV export, request-level logs, histogram outputs, or integration with CI, tell me which features you'd like and I'll add them.

---

## APPENDIX: Reporting Metrics Explained

This section provides detailed descriptions of all statistical metrics included in the performance report.

### Basic Counts

- **total_requests**: Total number of HTTP requests sent during the test.
- **successful_requests**: Number of requests that received a 2xx or 3xx HTTP status code (considered successful).
- **failed_requests**: Number of requests that failed (4xx, 5xx status codes, network errors, or timeouts).

### Duration & Throughput

- **total_duration_s / total_duration_ms**: Total elapsed time from the start of the first request to the completion of the last request, in seconds or milliseconds.
- **requests_per_second (RPS)**: Throughput metric calculated as `total_requests / total_duration_s`. Indicates how many requests the API handled per second during the test.

### Latency Metrics (Response Time)

All latency metrics measure the time from when a request is sent until the response is fully received. Values are provided in both seconds (`*_s`) and milliseconds (`*_ms`, rounded to 3 decimal places).

- **min**: Minimum (fastest) latency observed across all requests. Represents the best-case response time.
  
- **max**: Maximum (slowest) latency observed across all requests. Represents the worst-case response time. Useful for identifying outliers or spikes.

- **mean**: Arithmetic mean (average) latency across all requests. Calculated as the sum of all latencies divided by the number of requests. Can be skewed by outliers.

- **median**: Middle value when all latencies are sorted. 50% of requests were faster than this value, and 50% were slower. Less sensitive to outliers than the mean.

- **stdev**: Standard deviation of latencies. Measures the variability or spread of response times around the mean. A high stdev indicates inconsistent performance; a low stdev indicates stable response times.

### Percentiles (p50, p90, p95, p99)

Percentiles indicate the latency value below which a given percentage of requests fall. They are extremely valuable for understanding the distribution of response times and identifying tail latency.

- **p50 (50th percentile)**: Same as the median. 50% of requests completed faster than this latency. This is a good indicator of "typical" performance.

- **p90 (90th percentile)**: 90% of requests completed faster than this latency. Only 10% of requests were slower. Useful for understanding the experience of the "slower" users.

- **p95 (95th percentile)**: 95% of requests completed faster than this latency. Only 5% of requests were slower. A common SLA (Service Level Agreement) metric.

- **p99 (99th percentile)**: 99% of requests completed faster than this latency. Only 1% of requests were slower. Critical for understanding tail latency and worst-case user experience.

**Why percentiles matter**: Unlike mean, percentiles are not affected by extreme outliers. A single very slow request won't significantly impact p50 or p90, making them more reliable for understanding real-world performance. High p95 or p99 values relative to p50 indicate inconsistent performance or occasional severe slowdowns.

### Status Code Distribution

- **status_counts**: A dictionary/object showing the count of each HTTP status code received (e.g., `{200: 150, 404: 5, 500: 2}`). Useful for identifying error patterns:
  - **2xx**: Success (e.g., 200 OK, 201 Created)
  - **3xx**: Redirection (e.g., 301, 302)
  - **4xx**: Client errors (e.g., 400 Bad Request, 404 Not Found, 429 Too Many Requests)
  - **5xx**: Server errors (e.g., 500 Internal Server Error, 503 Service Unavailable)

### Time Series Data (Per-Second Buckets)

When using `--timeseries-export` or `--timeseries-csv`, the tool aggregates request data into per-second buckets:

- **second**: Relative second index (0 = first second of the test, 1 = second second, etc.).
- **start_epoch**: Unix epoch timestamp for the start of this second bucket.
- **count**: Total number of requests that started in this second.
- **successes / failures**: Breakdown of successful vs. failed requests in this second.
- **requests_per_second**: Same as `count` (number of requests in this second).
- **avg_latency_s / avg_latency_ms**: Average latency for requests that started in this second.
- **p50_s / p50_ms, p90_s / p90_ms**: 50th and 90th percentile latencies for requests in this second.
- **status_counts**: HTTP status code distribution for this second.

### Request-Level Log (CSV)

When using `--request-log`, each row represents a single request:

- **index**: Sequential request number (0, 1, 2, ...).
- **start_epoch**: Unix epoch timestamp when the request was sent.
- **start_rel_s**: Relative time (in seconds) since the test started when this request was sent.
- **status**: HTTP status code received (or null if the request failed).
- **ok**: Boolean indicating if the request was successful (2xx or 3xx status).
- **time_s / time_ms**: Latency for this specific request in seconds or milliseconds.
- **bytes**: Size of the response body in bytes.
- **error**: Error message if the request failed (network error, timeout, etc.).

### Interpreting Results

**Good performance characteristics:**
- Low mean and median latency
- Small stdev (consistent response times)
- p95 and p99 close to p50 (no tail latency)
- High requests_per_second
- Few or no failed requests

**Warning signs:**
- p99 >> p50 (significant tail latency, some users experience slow responses)
- High stdev (inconsistent, unpredictable performance)
- Increasing latency over time in time series (potential resource exhaustion, memory leak)
- High failure rate (>1-5% depending on SLA)
- 429 status codes (rate limiting, reduce concurrency or request rate)
- 5xx status codes (server-side issues, investigate backend)

---

License: MIT

---

Version: 0.0.1
