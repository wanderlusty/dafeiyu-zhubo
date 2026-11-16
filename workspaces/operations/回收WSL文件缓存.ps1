$ErrorActionPreference = 'Stop'
# Model weights are already resident in the voice workers. Reclaim only Linux
# file cache; this does not stop either model or change any voice setting.
& wsl.exe -u root --exec sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
if ($LASTEXITCODE -ne 0) { throw 'WSL file cache reclaim failed' }
Write-Output 'WSL file cache reclaimed; voice models remain loaded.'
