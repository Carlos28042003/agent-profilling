| run | concurrency | tasks | accuracy | llm_calls | ttft_mean_s | ttft_p50_s | ttft_p95_s | task_p50_s | task_p95_s | tasks_per_min | gen_tokens_per_s | prompt_tokens | prefill_tokens_computed | prefill_s_server | cache_hit_% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gsm8k-cache-on | 1 | 100 | 0.5 | 421 | 2.48 | 2.41 | 2.7 | 12.41 | 27.16 | 4.65 | 15.12 | 338589 | 13418 | 173.58 | 96.04 |
| gsm8k-cache-off | 1 | 100 | 0.52 | 414 | 6.96 | 6.66 | 8.97 | 26.9 | 68.81 | 1.83 | 5.73 | 330612 | 330612 | 2028.88 | 0.0 |
