# Core performance measurements

Measured on 2026-09-10, Python 3.14.6, Windows 11 (build 26200). Both synthetic TDG repositories
contain 3,000 tags and 222,780 source bytes. One has 300 files with 10 tags each; the other has three
files with 1,000 tags each. Each tag has a local ID, parent issue, body line, and following Python code.

| Operation | 300 small files (ms) | 3 large files (ms) |
| --- | ---: | ---: |
| Discovery | 7.961 | 0.373 |
| Uncached full scan | 400.945 | 352.037 |
| Warm full scan | 391.457 | 299.929 |
| Initial index refresh (one sample) | 596.561 | 401.013 |
| Warm index refresh | 64.423 | 7.021 |
| One-file change + refresh | 67.429 | 151.148 |
| ID lookup (one matching tag) | 0.574 | 0.586 |
| Tracker lookup (miss) | 0.512 | 0.542 |
| File lookup (10 / 1,000 results) | 0.915 | 12.288 |
| Batch update (10 / 100 tags) | 3.307 | 20.016 |

All repeated timings are medians: three runs for scans, refreshes, and batches; 200 for ID/tracker
queries; 30 for file queries. Initial refresh is a single sample against a new database. Queries
include opening/validating/closing a SQLite connection and constructing result records. Batch timings
exclude the preceding parse and include validation, serialization, flush, and file replacement.

“Uncached” clears the process-local token cache, not the operating system's filesystem cache. Warm
full scans still parse every file. The 32-source token cache cannot retain the entire 300-file fixture.
The benchmark runs locally without the test matrix running concurrently. These are synthetic timing
samples, not latency guarantees or claims about cold physical-disk performance.

## Refresh work

Both warm refreshes read/hash all 222,780 source bytes and parse zero files. Each one-file-change
refresh reads all selected files and parses exactly one. A changed large file contains 1,000 tags;
a changed small file contains 10. This explains why the large-file change is slower even though its
unchanged refresh is faster. File-query results likewise cost more when returning 1,000 records.

The raw JSON separates discovery, read/decode/hash, parsing, and storage durations. Complete refresh
also includes configuration/schema selection, connection management, bookkeeping, and transaction
setup; phase timings need not sum to the total, and medians are computed independently per field.
Initial refresh is more expensive than a fresh scan because it builds and stores the query snapshot.

Index files occupy approximately 4.3 MB for about 0.22 MB of source: records currently retain full
schema and source-span metadata in JSON. This is a deliberate simplicity/storage tradeoff, not a
compact storage claim. Schema deduplication is a possible later optimization if real workloads justify it.

## Complexity and consistency

Discovery scales with visited directory entries. Explicit directory exclusions prune traversal.
Refresh remains linear in selected source bytes to detect timestamp-preserving edits; changed-file
parsing and SQLite updates add work proportional to affected records. ID/tracker/file searches use
SQLite indexes (verified with EXPLAIN QUERY PLAN), plus the cost of materializing matching records.
No constant-time full-repository refresh is claimed.

Mutation computes source-line starts once, sorts disjoint spans, and reconstructs the file in one
pass. It still reads and rewrites the complete affected file. It is not an in-place database-page update.
Snapshot queries never rescan source; call refresh explicitly. Source fingerprints prevent stale
indexed records from overwriting changed files. A refresh transaction makes the database update
indivisible, but concurrent source edits can still produce a view gathered at different moments.

## Reproduce

```powershell
.venv/Scripts/python.exe -m tests.benchmark_core --output spec/core_performance.json
```

The script uses disposable temporary fixtures and verifies indexed results against fresh parsing.
It measures discovery, fresh scans, warm refreshes, lookups, one-file edits, and validated batch writes.
Machine-readable observations are in [core_performance.json](core_performance.json).
