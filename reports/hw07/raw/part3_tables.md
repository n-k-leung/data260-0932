| Setting | Mean prompt tokens/turn | Mean latency (ms) | Probe quality (1-5) |
| --- | --- | --- | --- |
| N4 | 859.4 | 20955 | 4.6 |
| N12 | 825.0 | 20389 | 4.6 |
| N30 | 886.8 | 21343 | 4.2 |
| COMPRESS | 868.5 | 21739 | 4.6 |

Compression vs N12: token savings = -5.3%,probe quality change = +0.00

Cost of 10000 x 30-turn conversations(input $1.0/M, output $5.0/M):
| Setting | Probe quality | Input tokens | Output tokens | Cost (USD) | Role |
| --- | --- | --- | --- | --- | --- |
| N4 | 4.6 | 257,820,000 |102,060,000 | $768.12 |  |
| N12 | 4.6 | 247,500,000 |101,850,000 | $756.75 | BEST |
| N30 | 4.2 | 266,040,000 |99,960,000 | $765.84 |  |
| COMPRESS | 4.6 | 260,550,000 |104,100,000 | $781.05 | WORST |