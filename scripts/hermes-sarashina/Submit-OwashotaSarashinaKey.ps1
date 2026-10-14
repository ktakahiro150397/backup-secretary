param([string]$EnvFile = (Join-Path $PSScriptRoot 'owashota-sarashina\.env'))
$ErrorActionPreference = 'Stop'
$sshExecutable = (Get-Command ssh.exe -ErrorAction Stop).Source
$sarashinaSecure = $null
$sarashinaPtr = [IntPtr]::Zero
$sarashinaPayload = $null
$sarashinaFileText = $null
$sarashinaFileKey = $null
try {
    # The owner's approved switch permits this helper to transfer the existing key.
    # Never output its value or put it in command arguments, diagnostics, or Git.
    $sarashinaEnvPath = $EnvFile
    $sarashinaFileText = [IO.File]::ReadAllText($sarashinaEnvPath)
    $sarashinaLines = @($sarashinaFileText -split '\r?\n' | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
    if ($sarashinaLines.Count -ne 1 -or $sarashinaLines[0] -notmatch '^\s*SARASHINA_API_KEY\s*=\s*(.*?)\s*$') {
        throw 'The dedicated .env must contain one SARASHINA_API_KEY assignment. Its contents were not printed.'
    }
    $sarashinaFileKey = $Matches[1]
    $Matches.Clear()
    if ($sarashinaFileKey.Length -ge 2 -and (($sarashinaFileKey.StartsWith('"') -and $sarashinaFileKey.EndsWith('"')) -or ($sarashinaFileKey.StartsWith("'") -and $sarashinaFileKey.EndsWith("'")))) {
        $sarashinaFileKey = $sarashinaFileKey.Substring(1, $sarashinaFileKey.Length - 2)
    }
    if ([string]::IsNullOrWhiteSpace($sarashinaFileKey)) { throw 'The key assignment is empty.' }
    $sarashinaPayload = @{ sarashina_api_key = $sarashinaFileKey } | ConvertTo-Json -Compress
    $sarashinaPayload | & $sshExecutable -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=8 yanelmoserver 'docker exec -i --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python /opt/data/sarashina-support/key_entry.py submit --approved-context'
    if ($LASTEXITCODE -ne 0) { throw 'Task handoff was not acknowledged. Do not repeat it until status is checked.' }
} finally {
    $sarashinaPayload = $null
    $sarashinaFileKey = $null
    $sarashinaFileText = $null
    $sarashinaLines = $null
    if ($sarashinaPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($sarashinaPtr) }
    if ($null -ne $sarashinaSecure) { $sarashinaSecure.Dispose() }
}
