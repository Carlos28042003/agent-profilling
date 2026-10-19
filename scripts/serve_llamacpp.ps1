param(
    [int]$Parallel = 1,
    [int]$CtxPerSlot = 8192,
    [int]$Unified = 0,
    [string]$LlamaDir = "$env:USERPROFILE\tools\llama.cpp-b11719",
    [string]$Model = "$env:USERPROFILE\.ollama\models\blobs\sha256-dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff"
)
if ($Unified -gt 0) { $kv = @("-c", $Unified, "-kvu") } else { $kv = @("-c", ($Parallel * $CtxPerSlot)) }
& "$LlamaDir\llama-server.exe" -m $Model --port 8080 -ngl 99 @kv -np $Parallel `
    -fa on -ctk q8_0 -ctv q8_0 --jinja --metrics
