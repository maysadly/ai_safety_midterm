# Latency per stage

From `results/midterm/chat_log.jsonl` (bot, guard, total per /api/chat request, measured inside the app on the pod, requests one at a time) and `results/midterm/attacks/attempts.jsonl` (judge). Percentiles: numpy linear interpolation.

| requests | n | bot model p50 / p95 (ms) | guard p50 / p95 (ms) | total p50 / p95 (ms) |
|---|---|---|---|---|
| M0/M2 runner | 180 | 1846 / 6507 | 182 / 386 | 2097 / 6764 |
| M1 garak | 480 | 790 / 7109 | 178 / 303 | 908 / 7398 |
| judge (G3/G4 scoring, not part of the chatbot) | 90 | - | - | 2120 / 2730 |
