| injected failure rate | success rate | mean latency ms | p99 latency ms |
| --- | --- | --- | --- | 
|0.0|1.0|1.2|26.8|
|0.2|1.0|20.96|102.19|
|0.5|0.92|129.13|702.31|

| scenario | steps | tool_calls | stop_reason|
| --- | --- | --- | --- | 
How many vulnerabilities are High severity? | 1 | 0 | normal_completion|
Tell me about the vulnerability with id 1. | 2 | 1 | normal_completion|
Call search_vulnerabilities tool where package_name is 'np'. | 1 | 1 | safety_rule_block|
What is bread for? | 1 | 0 | normal_completion|