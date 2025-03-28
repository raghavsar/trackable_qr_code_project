# PowerShell script to run Caddy on Windows

# Check if Caddy is installed
try {
    $caddyVersion = caddy version
    Write-Host "Caddy version: $caddyVersion" -ForegroundColor Green
}
catch {
    Write-Host "Caddy not found. Please install Caddy first:" -ForegroundColor Red
    Write-Host "1. Visit https://caddyserver.com/download" -ForegroundColor Yellow
    Write-Host "2. Download the Windows version" -ForegroundColor Yellow
    Write-Host "3. Add it to your PATH" -ForegroundColor Yellow
    exit 1
}

# Check which Caddyfile to use
$mode = $args[0]
$caddyfilePath = ""

if ($mode -eq "prod") {
    $caddyfilePath = Join-Path $PSScriptRoot "Caddyfile"
    Write-Host "Using production Caddyfile" -ForegroundColor Yellow
}
else {
    $caddyfilePath = Join-Path $PSScriptRoot "Caddyfile.dev"
    Write-Host "Using development Caddyfile" -ForegroundColor Cyan
}

# Ensure Caddyfile exists
if (!(Test-Path $caddyfilePath)) {
    Write-Host "Caddyfile not found at: $caddyfilePath" -ForegroundColor Red
    exit 1
}

# Create logs directory if needed (for production)
if ($mode -eq "prod") {
    $logDir = "C:\var\log\caddy"
    if (!(Test-Path $logDir)) {
        Write-Host "Creating log directory: $logDir" -ForegroundColor Yellow
        New-Item -Path $logDir -ItemType Directory -Force
    }
}

# Run Caddy
Write-Host "Starting Caddy..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Cyan

try {
    # Run with the specified Caddyfile
    caddy run --config $caddyfilePath
}
catch {
    Write-Host "Error running Caddy: $_" -ForegroundColor Red
    exit 1
} 