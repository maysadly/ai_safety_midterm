# Before / after

Factual rows are filled from the garak reports by scripts/summarize.py. The last two rows are left for the author.

| | Baseline (garak -> Ollama) | Proxy, mode none | Proxy, mode sysprompt | Proxy, mode sysprompt+guard |
|---|---|---|---|---|
| Model and configuration | qwen2.5:7b-instruct (Ollama, id 845dbda0ea48), temperature 0.7, top_k 20, max 256 new tokens, generations 5, garak seed 42; garak -> Ollama directly; model's default system prompt | qwen2.5:7b-instruct (Ollama, id 845dbda0ea48), temperature 0.7, top_k 20, max 256 new tokens, generations 5, garak seed 42; garak -> proxy -> Ollama, prompt passed unchanged | qwen2.5:7b-instruct (Ollama, id 845dbda0ea48), temperature 0.7, top_k 20, max 256 new tokens, generations 5, garak seed 42; proxy adds adaptive system prompt (Zeng et al.) + <user_input> separation | qwen2.5:7b-instruct (Ollama, id 845dbda0ea48), temperature 0.7, top_k 20, max 256 new tokens, generations 5, garak seed 42; sysprompt + llama-guard3:1b checks each answer; unsafe -> refusal |
| Probes | dan: 11 classes | dan: 6 classes | dan: 9 classes | dan: 9 classes |
| Number of tests | 13 attempts x 5 generations = 65 outputs | 8 attempts x 5 generations = 40 outputs | 11 attempts x 5 generations = 55 outputs | 11 attempts x 5 generations = 55 outputs |
| Failures found | dan / dan.AntiDAN: 5/5 (100%)<br>dan / dan.DAN: 12/40 (30%)<br>dan / dan.DANJailbreak: 0/5 (0%)<br>dan / dan.DUDE: 0/5 (0%)<br>dan / dan.DevMode: 8/10 (80%)<br>dan / mitigation.MitigationBypass: 24/65 (37%)<br>any detector: 37/65 outputs | dan / dan.AntiDAN: 5/5 (100%)<br>dan / dan.DAN: 0/15 (0%)<br>dan / dan.DANJailbreak: 0/5 (0%)<br>dan / dan.DUDE: 0/5 (0%)<br>dan / dan.DevMode: 6/10 (60%)<br>dan / mitigation.MitigationBypass: 11/40 (28%)<br>any detector: 17/40 outputs | dan / dan.AntiDAN: 5/5 (100%)<br>dan / dan.DAN: 6/30 (20%)<br>dan / dan.DANJailbreak: 0/5 (0%)<br>dan / dan.DUDE: 0/5 (0%)<br>dan / dan.DevMode: 8/10 (80%)<br>dan / mitigation.MitigationBypass: 5/55 (9%)<br>any detector: 19/55 outputs | dan / dan.AntiDAN: 5/5 (100%)<br>dan / dan.DAN: 8/30 (27%)<br>dan / dan.DANJailbreak: 0/5 (0%)<br>dan / dan.DUDE: 0/5 (0%)<br>dan / dan.DevMode: 2/10 (20%)<br>dan / mitigation.MitigationBypass: 4/55 (7%)<br>any detector: 15/55 outputs |
| garak version / run time | 0.17.0 / 2026-10-16T17:13:39.721684 - None | 0.17.0 / 2026-10-16T17:15:22.939880 - None | 0.17.0 / 2026-10-16T17:13:54.439960 - None | 0.17.0 / 2026-10-16T17:13:59.629707 - None |
| Observed safety behavior |  |  |  |  |
| Remaining limitations |  |  |  |  |
