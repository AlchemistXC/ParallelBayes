param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$Output,
    [Parameter(Mandatory=$true)][string]$Rscript
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'Native Windows is required.'
}
if (Test-Path -LiteralPath $Output) {
    throw 'Output directory already exists; choose a new attempt directory.'
}
if (!(Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Native Python executable does not exist.'
}
if (!(Test-Path -LiteralPath $Rscript -PathType Leaf)) {
    throw 'Rscript executable does not exist.'
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$dest = (New-Item -ItemType Directory -Path $Output).FullName
$before = Get-Location
try {
    Set-Location $root
    $commit = (& git rev-parse HEAD | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve Git commit.' }
    $status = @(& git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Git status.' }
    $drives = @(Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace)
    $metadata = @{
        started_utc = [DateTime]::UtcNow.ToString('o')
        source_commit = $commit
        worktree_status = $status
        python_path = (Resolve-Path $Python).Path
        machine = $env:COMPUTERNAME
        os = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture)
        cpu = @(Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors)
        disks = $drives
        scope = 'framework and metadata only; no sampler calls'
    }
    $metadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $dest 'metadata.json') -Encoding UTF8
    & $Python -B scripts/prospective_plan/inventory.py (Join-Path $dest 'inventory.json')
    $inventoryExit = $LASTEXITCODE
    & $Python -B scripts/prospective_plan/qualification_inventory.py (Join-Path $dest 'qualification-inventory.json')
    $qualificationExit = $LASTEXITCODE
    & $Python -B scripts/prospective_plan/probe_dependencies.py --rscript $Rscript --output (Join-Path $dest 'dependencies.json')
    $dependenciesExit = $LASTEXITCODE
    & $Python -B scripts/windows/probe_environment.py --require-windows --require-cuda --output (Join-Path $dest 'framework.json')
    $frameworkExit = $LASTEXITCODE
    $files = Get-ChildItem -LiteralPath $dest -File | Where-Object Name -ne 'sha256.json'
    $hashes = @($files | ForEach-Object {
        @{ name = $_.Name; bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
    @{ inventory_exit = $inventoryExit; qualification_exit = $qualificationExit; dependencies_exit = $dependenciesExit; framework_exit = $frameworkExit; files = $hashes } |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $dest 'sha256.json') -Encoding UTF8
    if ($inventoryExit -ne 0 -or $qualificationExit -ne 0 -or $dependenciesExit -ne 0 -or $frameworkExit -ne 0) {
        throw "Preflight failed. Inventory exit=$inventoryExit; qualification exit=$qualificationExit; dependencies exit=$dependenciesExit; framework exit=$frameworkExit."
    }
    Write-Output "Framework and metadata preflight passed. Evidence: $dest"
} finally {
    Set-Location $before
}
