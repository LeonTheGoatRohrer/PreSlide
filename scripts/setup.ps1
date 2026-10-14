$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    @'
import ssl
from pathlib import Path
p=Path('data/runtime/windows-ca.pem');p.parent.mkdir(parents=True,exist_ok=True)
certs=[]
for store in ('ROOT','CA'):
    for cert,encoding,trust in ssl.enum_certificates(store):
        if encoding=='x509_asn': certs.append(ssl.DER_cert_to_PEM_cert(cert))
p.write_text(''.join(certs),encoding='ascii')
'@ | & ./.venv/Scripts/python.exe -
    & ./.venv/Scripts/python.exe -m pip install --cert data/runtime/windows-ca.pem -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    $savedCertPath = $env:NODE_EXTRA_CA_CERTS
    try {
        $env:NODE_EXTRA_CA_CERTS = (Resolve-Path data/runtime/windows-ca.pem).Path
        Push-Location -LiteralPath (Join-Path $projectRoot 'frontend')
        try {
            npm.cmd ci --ignore-scripts
            if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
            npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        } finally { Pop-Location }
    } finally { $env:NODE_EXTRA_CA_CERTS = $savedCertPath }
} finally { Pop-Location }
