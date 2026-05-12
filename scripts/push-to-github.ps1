# Run from the kalshi-polymarket-arb directory (same folder as this file's parent).
# PowerShell: cd ...\kalshi-polymarket-arb; .\scripts\push-to-github.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path .git)) {
  git init
}

git add -A
$st = git status --porcelain
if ($st) {
  git commit -m "Initial commit: Kalshi x Polymarket arbitrage stack"
} else {
  Write-Host "Nothing to commit (clean tree)."
}

git branch -M main

git remote remove origin 2>$null
git remote add origin "https://github.com/jsciochetti-cyber/KP-Arbitrage.git"

git push -u origin main
