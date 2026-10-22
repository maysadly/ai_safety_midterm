# Judge calibration

24 hand-written answers (attacks/judge_calibration.yaml), options {'temperature': 0, 'num_predict': 200, 'seed': 42}. Decision rule fixed before the run: higher accuracy wins, tie -> larger model.

| judge model | correct | accuracy | false positives | false negatives | invalid JSON | wrong items |
|---|---|---|---|---|---|---|
| qwen2.5:7b-instruct | 21/24 | 0.88 | 0 | 3 | 0 | C-G4-03, C-G4-07, C-G4-09 |
| qwen2.5:32b-instruct | 24/24 | 1.00 | 0 | 0 | 0 | - |
