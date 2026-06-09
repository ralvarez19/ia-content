# Arranca el backend en 0.0.0.0:8000 y deja regla de firewall.
# Uso: .\start_backend.ps1
#
# - Detecta y muestra las IPs LAN que tu celular debería usar.
# - Crea la regla de firewall si no existe y estás en sesión admin.
# - Arranca uvicorn con --host 0.0.0.0 (no 127.0.0.1).

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "=== ia-content backend ===" -ForegroundColor Cyan

# IPs LAN
$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -match '^(192\.168|10\.|172\.(1[6-9]|2\d|3[01]))' -and
        $_.PrefixOrigin -ne 'WellKnown' -and
        $_.InterfaceAlias -notmatch 'vEthernet'
    }
Write-Host "IPs LAN disponibles:" -ForegroundColor Yellow
foreach ($ip in $ips) {
    Write-Host "  http://$($ip.IPAddress):8000  ($($ip.InterfaceAlias))"
}

# Firewall (silencioso si no es admin)
$rule = Get-NetFirewallRule -DisplayName 'ia-content backend' -ErrorAction SilentlyContinue
if (-not $rule) {
    try {
        New-NetFirewallRule -DisplayName 'ia-content backend' `
            -Direction Inbound -LocalPort 8000 -Protocol TCP `
            -Action Allow -Profile Private | Out-Null
        Write-Host "Regla de firewall creada (8000/tcp, perfil Privado)" -ForegroundColor Green
    } catch {
        Write-Host "No pude crear la regla de firewall (necesita PowerShell Admin)." -ForegroundColor Yellow
        Write-Host "Si el celular no conecta, abrí PowerShell como admin y corré:" -ForegroundColor Yellow
        Write-Host "  New-NetFirewallRule -DisplayName 'ia-content backend' -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private"
    }
} else {
    Write-Host "Regla de firewall ya existía: OK" -ForegroundColor Green
}

# Venv si existe
if (Test-Path .\.venv\Scripts\Activate.ps1) {
    Write-Host "Activando .venv" -ForegroundColor Gray
    . .\.venv\Scripts\Activate.ps1
}

Write-Host ""
Write-Host "Arrancando uvicorn en 0.0.0.0:8000..." -ForegroundColor Cyan
Write-Host "(Ctrl+C para parar)`n"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
