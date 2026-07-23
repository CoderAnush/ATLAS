# Fetch Linux binaries used by Compose image builds (run on the host).
# Usage: pwsh scripts/dev/fetch-binaries.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Bin = Join-Path $Root "infrastructure/docker/bin"
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
$ProgressPreference = "SilentlyContinue"

Write-Host "Downloading MinIO..."
curl.exe -L --retry 5 -o (Join-Path $Bin "minio") "https://dl.min.io/server/minio/release/linux-amd64/minio"
Write-Host "Downloading mc..."
curl.exe -L --retry 5 -o (Join-Path $Bin "mc") "https://dl.min.io/client/mc/release/linux-amd64/mc"
Write-Host "Downloading Prometheus..."
curl.exe -L --retry 5 -o (Join-Path $Bin "prometheus.tar.gz") "https://github.com/prometheus/prometheus/releases/download/v2.54.1/prometheus-2.54.1.linux-amd64.tar.gz"
Write-Host "Downloading Grafana..."
curl.exe -L --retry 5 -o (Join-Path $Bin "grafana.tar.gz") "https://dl.grafana.com/oss/release/grafana-11.2.2.linux-amd64.tar.gz"
Get-ChildItem $Bin | Format-Table Name, Length
Write-Host "Done. Binaries are gitignored; required before docker compose build of minio/prometheus/grafana."
