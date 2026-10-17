param(
    [string]$ProtectedKey = '.verification/launch-l5-2026-10-14/owner-key.dpapi',
    [string]$OutputFile = '.verification/owner-access.txt'
)

$ErrorActionPreference = 'Stop'
$accessRoot = Split-Path $PSScriptRoot -Parent
Push-Location $accessRoot
try {
    # Recovery is deliberately local: never publish, log or embed the owner key.
    git check-ignore --quiet -- $OutputFile
    if ($LASTEXITCODE -ne 0) { throw 'The output must be ignored by Git.' }
    $accessDestination = [IO.Path]::GetFullPath((Join-Path $accessRoot $OutputFile))
    if (-not $accessDestination.StartsWith($accessRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'The output must remain inside this repository.'
    }
    if (-not (Test-Path -LiteralPath $ProtectedKey)) {
        throw 'No protected owner key found. Use the key configured as RESEARCH_API_KEY by your deployment operator.'
    }
    $accessSecure = Get-Content -Raw -LiteralPath $ProtectedKey | ConvertTo-SecureString
    $accessCredential = [Management.Automation.PSCredential]::new('owner', $accessSecure)
    $accessPlaintext = $accessCredential.GetNetworkCredential().Password
    New-Item -ItemType Directory -Force (Split-Path $accessDestination -Parent) | Out-Null
    Set-Content -LiteralPath $accessDestination -Encoding utf8 -Value @"
PRIVATE OWNER ACCESS - keep this file local; never upload it or commit it.

Workspace: https://stochastic-market-simulator.fly.dev/
Also supported: https://stochastic-market-simulator.vercel.app/

Private workspace key:
$accessPlaintext

Click 'Unlock private workspace', paste the key, and click 'Unlock workspace'.
It unlocks all private tabs, including the Risk Labs. Lock or refresh to clear it.
This is not a broker password. There is no broker connection.
"@
    $accessIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls.exe $accessDestination /inheritance:r /grant:r "${accessIdentity}:(R,W)" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the recovery file to the current Windows user.' }
    Write-Output "Private owner instructions saved locally: $accessDestination"
} finally {
    Remove-Variable accessPlaintext,accessCredential,accessSecure -ErrorAction SilentlyContinue
    Pop-Location
}
