[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputZip,

    [Parameter(Mandatory = $true)]
    [string]$SnapshotLabel
)

$ErrorActionPreference = "Stop"

if ($SnapshotLabel -notmatch "^[A-Za-z0-9_-]+$") {
    throw "SnapshotLabel must contain only letters, numbers, underscores, and hyphens."
}

try {
    $inputZipItem = Get-Item -LiteralPath $InputZip -ErrorAction Stop
}
catch {
    throw "InputZip was not found: $InputZip"
}

if ($inputZipItem.PSIsContainer -or $inputZipItem.Extension -ine ".zip") {
    throw "InputZip must be a .zip file: $InputZip"
}

try {
    $zipArchive = [System.IO.Compression.ZipFile]::OpenRead($inputZipItem.FullName)
    $zipArchive.Dispose()
}
catch {
    throw "InputZip is not a readable ZIP archive: $($inputZipItem.FullName)"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Project virtual-environment Python was not found: $pythonPath. Run the setup steps in README.md first."
}

$bronzeDir = Join-Path $projectRoot "data\bronze\$SnapshotLabel"
$silverDir = Join-Path $projectRoot "data\silver\$SnapshotLabel"
$goldDatabase = Join-Path $projectRoot "data\gold\nppes_provider_directory.duckdb"
$manifestDir = Join-Path $projectRoot "data\gold\manifests"
$manifestPath = Join-Path $manifestDir "$SnapshotLabel.json"
$bronzeParquet = Join-Path $bronzeDir "$($inputZipItem.BaseName)_massachusetts.parquet"

$ingestScript = Join-Path $projectRoot "src\ingest.py"
$transformScript = Join-Path $projectRoot "src\transform.py"
$loadScript = Join-Path $projectRoot "src\load.py"
$manifestScript = Join-Path $projectRoot "src\run_manifest.py"

function Invoke-PipelineStage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Stage,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Write-Host "Running $Stage..."
    & $pythonPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Stage failed with exit code $LASTEXITCODE."
    }
}

Invoke-PipelineStage -Stage "Bronze ingestion" -Arguments @(
    $ingestScript,
    $inputZipItem.FullName,
    $bronzeDir
)

if (-not (Test-Path -LiteralPath $bronzeParquet -PathType Leaf)) {
    throw "Bronze ingestion completed but the expected Parquet file was not found: $bronzeParquet"
}

Invoke-PipelineStage -Stage "Silver transformation" -Arguments @(
    $transformScript,
    $bronzeParquet,
    $silverDir
)

Invoke-PipelineStage -Stage "Gold DuckDB load" -Arguments @(
    $loadScript,
    $silverDir,
    $goldDatabase
)

Invoke-PipelineStage -Stage "Gold run-manifest creation" -Arguments @(
    $manifestScript,
    "--snapshot-label",
    $SnapshotLabel,
    "--source-zip",
    $inputZipItem.FullName,
    "--bronze-dir",
    $bronzeDir,
    "--silver-dir",
    $silverDir,
    "--gold-database",
    $goldDatabase,
    "--manifest-dir",
    $manifestDir
)

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Manifest creation completed but the expected manifest was not found: $manifestPath"
}

Write-Host ""
Write-Host "Snapshot pipeline completed: $SnapshotLabel"
Write-Host "Bronze: $bronzeDir"
Write-Host "Silver: $silverDir"
Write-Host "Gold:   $goldDatabase"
Write-Host "Manifest: $manifestPath"
