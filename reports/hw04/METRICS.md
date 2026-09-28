| Page size | Version | p50 (ms) | p95 (ms) | p99 (ms) | SQL stmts/req |
|---|---|---|---|---|---|
| 10 | naive | 8.63 |17.58 | 18.08 | 11 |
| 10 | fixed | 4.61 | 4.95 | 5.18 | 1 |
| 50 | naive | 26.15 | 29.56 | 57.69 | 51 |
| 50 | fixed | 5.78 | 6.51 | 6.74 | 1 |
| 200 | naive | 98.95 | 127.4 | 135.56 | 201 |
| 200 | fixed | 10.23 | 14.25 | 49.59 | 1 |


config | accuracy | faithfulness | format_compliance | robustness
['A', 0.5, 0.0, 'n/a', 0.0]
['B', 0.5, 0.5, 'n/a', 0.0]
['C', 0.5, 0.5, 1.0, 1.0]