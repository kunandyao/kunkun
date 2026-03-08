# Build frontend for DouyinCrawler
# Run from project root: .\build-frontend.ps1

$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "frontend"

$npmExe = $null
if (Get-Command npm -ErrorAction SilentlyContinue) { $npmExe = "npm" }
elseif (Test-Path "$env:ProgramFiles\nodejs\npm.cmd") { $npmExe = "$env:ProgramFiles\nodejs\npm.cmd" }
elseif (Test-Path "${env:ProgramFiles(x86)}\nodejs\npm.cmd") { $npmExe = "${env:ProgramFiles(x86)}\nodejs\npm.cmd" }
if (-not $npmExe) {
    Write-Host "Error: npm not found. Install Node.js from https://nodejs.org or restart terminal after install." -ForegroundColor Red
    exit 1
}
function Run-Npm { & $npmExe @args }

if (-not (Test-Path $frontend)) {
    Write-Host "Error: frontend folder not found." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Building frontend..." -ForegroundColor Cyan
Write-Host ""
Push-Location $frontend
try {
    if (-not (Test-Path "node_modules")) {
        if (Get-Command pnpm -ErrorAction SilentlyContinue) {
            pnpm install
        } else {
            Run-Npm install
        }
    }
    if (Get-Command pnpm -ErrorAction SilentlyContinue) {
        pnpm run build
    } else {
        Run-Npm run build
    }
    if (Test-Path "dist\index.html") {
        Write-Host ""
        Write-Host "Build OK. Run: python main.py" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "Build may have failed. Check output above." -ForegroundColor Yellow
        exit 1
    }
} finally {
    Pop-Location
}
