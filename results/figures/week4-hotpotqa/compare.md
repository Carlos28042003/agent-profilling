| run | concurrency | tasks | accuracy | llm_calls | ttft_mean_s | ttft_p50_s | ttft_p95_s | task_p50_s | task_p95_s | tasks_per_min | gen_tokens_per_s | prompt_tokens | prefill_tokens_computed | prefill_s_server | cache_hit_% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hotpotqa-cache-on | 1 | 100 | 0.11 | 729 | 3.06 | 2.77 | 4.18 | 34.55 | 42.15 | 1.83 | 8.06 | 915925 | 83187 | 717.19 | 90.92 |
| hotpotqa-cache-off | 1 | 100 | 0.15 | 721 | 9.2 | 9.06 | 13.4 | 81.84 | 102.01 | 0.77 | 3.31 | 896456 | 896456 | 5133.54 | 0.0 |
