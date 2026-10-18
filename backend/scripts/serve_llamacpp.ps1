# Start llama.cpp's OpenAI-compatible server on port 8080 with Ollama's llama3.2:3b GGUF.
#   .\scripts\serve_llamacpp.ps1                 # 1 slot, 8192-token context
#   .\scripts\serve_llamacpp.ps1 -Parallel 4     # 4 slots (4 concurrent agents), 8192 tokens each
# Unload Ollama's copy first so both do not compete for GPU memory: ollama stop llama3.2:3b-ctx8k
param(
    [int]$Parallel = 1,
    [int]$CtxPerSlot = 8192,
    [string]$LlamaDir = "$env:USERPROFILE\tools\llama.cpp-b11719",
    [string]$Model = "$env:USERPROFILE\.ollama\models\blobs\sha256-dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff"
)
$ctx = $Parallel * $CtxPerSlot
# q8_0 KV cache halves KV memory so several slots fit in 4 GB; flash attention is required for it.
& "$LlamaDir\llama-server.exe" -m $Model --port 8080 -ngl 99 -c $ctx -np $Parallel `
    -fa on -ctk q8_0 -ctv q8_0 --jinja --metrics
