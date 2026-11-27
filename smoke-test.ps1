$ErrorActionPreference = 'Stop'
function Check-Native { if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" } }
docker compose up --build -d
Check-Native
$ready = $false
for ($i=0; $i -lt 60; $i++) {
    try { $r = Invoke-RestMethod http://localhost:8000/health; if ($r.status -eq 'ok') { $ready = $true; break } } catch {}
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw 'API did not become healthy. Inspect docker compose logs.' }
docker compose exec -T api python -m src.ingest data/companies_demo.csv data/fsa_demo.csv
Check-Native
$found = $false
for ($i=0; $i -lt 60; $i++) {
    $matches = @(Invoke-RestMethod 'http://localhost:8000/business?name=ABC&postcode=TN9%201AB')
    if (@($matches | Where-Object { $_.company_id -eq 'C1' -and $_.fsa_id -eq 'F1' }).Count -eq 1) { $found = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $found) { throw 'Demo match not returned. Inspect worker and queue logs.' }
Write-Host 'Docker demo smoke test passed. Synthetic data only.'
