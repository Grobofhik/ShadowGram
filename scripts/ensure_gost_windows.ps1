param(
    [Parameter(Mandatory = $true)]
    [string]$GostUrl,

    [Parameter(Mandatory = $true)]
    [string]$ChecksumsUrl,

    [Parameter(Mandatory = $true)]
    [string]$AssetName,

    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$ChecksumsPath,

    [Parameter(Mandatory = $true)]
    [string]$ExtractDir,

    [Parameter(Mandatory = $true)]
    [string]$TargetPath
)

$ErrorActionPreference = "Stop"

$archiveDir = Split-Path -Parent $ArchivePath
$targetDir = Split-Path -Parent $TargetPath

if ($archiveDir) {
    New-Item -ItemType Directory -Force -Path $archiveDir | Out-Null
}
if ($targetDir) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
}

Invoke-WebRequest -Uri $GostUrl -OutFile $ArchivePath
Invoke-WebRequest -Uri $ChecksumsUrl -OutFile $ChecksumsPath

$expected = Get-Content $ChecksumsPath |
    Where-Object { $_ -match ("  " + [regex]::Escape($AssetName) + "$") } |
    ForEach-Object { ($_ -split "\s+")[0] } |
    Select-Object -First 1

if (-not $expected) {
    throw "Unable to find checksum for $AssetName"
}

$actual = (Get-FileHash -Algorithm SHA256 $ArchivePath).Hash.ToLowerInvariant()
if ($actual -ne $expected.ToLowerInvariant()) {
    throw "SHA256 mismatch for $AssetName: expected $expected, got $actual"
}

if (Test-Path $ExtractDir) {
    Remove-Item -Recurse -Force $ExtractDir
}

Expand-Archive -LiteralPath $ArchivePath -DestinationPath $ExtractDir -Force

$source = Get-ChildItem -Path $ExtractDir -Recurse -Filter "gost.exe" |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $source) {
    throw "gost.exe not found in downloaded archive"
}

Copy-Item -LiteralPath $source -Destination $TargetPath -Force
