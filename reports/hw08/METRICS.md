| Failure scenario | Before fix explaiantions | After fix explainations |
|---|---|---|
| Duplicate delivery | same correlation_id processed twice, 2 drafts sent | replay skipped duplicate, 1 draft sent |
| Consumer killed mid-work | offset 7 auto-committed where lag 0, never redelivered, message lost | offset 13 not committed where lab 1, redelivered after restart, and then commit LAG 0 |
| Poison message | writer crashed JSONDecodeError, next task blocked until manual restart | 3 retries, moved to s0932_dead_letter, next task processed |
| Two partitions/two consumers | no key so lodash and requests out of order| key = package name: all packages in order|