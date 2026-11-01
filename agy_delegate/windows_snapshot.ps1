function Snapshot-Hash($Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Snapshot-TextHash($Value) { return Snapshot-Hash ([Text.Encoding]::UTF8.GetBytes([string]$Value)) }
function Test-GatewayVariableNames($Names) {
    return @($Names | Where-Object { $_ -like 'AGY_LLM_GATEWAY_*' }).Count -gt 0
}
function Require-PlainAncestors($Path) {
    $current = $Path
    while ($current -and !(Test-Path -LiteralPath $current)) { $current = Split-Path -Parent $current }
    if (!$current) { throw 'snapshot_ancestor_unverified' }
    while ($current) {
        $item = Get-Item -LiteralPath $current -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'snapshot_reparse_rejected' }
        $parent = Split-Path -Parent $current
        if ($parent -ceq $current) { break }
        $current = $parent
    }
}
function Read-SettingsFingerprint($Path) {
    Require-PlainAncestors $Path
    if (!(Test-Path -LiteralPath $Path)) { return @{exists=$false;sha256=$null;acl_sha256=$null;owner_sha256=$null} }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer -or $item.Length -gt 1048576) { throw 'snapshot_file_invalid' }
    $held = [IO.File]::Open($Path, 'Open', 'Read', 'Read')
    try {
        if ($held.Length -gt 1048576) { throw 'snapshot_file_invalid' }
        $before = Get-Acl -LiteralPath $Path
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $digest = ([BitConverter]::ToString($sha.ComputeHash($held))).Replace('-','').ToLowerInvariant() }
        finally { $sha.Dispose() }
        $after = Get-Acl -LiteralPath $Path
        $owner = $before.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if ($before.Sddl -cne $after.Sddl -or $owner -cne $after.GetOwner([Security.Principal.SecurityIdentifier]).Value) { throw 'snapshot_acl_changed' }
        return @{exists=$true;sha256=$digest;acl_sha256=(Snapshot-TextHash $before.Sddl);owner_sha256=(Snapshot-TextHash $owner)}
    } finally { $held.Dispose() }
}
function Require-SameFingerprints($First, $Second) {
    foreach ($label in @('global','project','shared')) {
        foreach ($key in @('exists','sha256','acl_sha256','owner_sha256')) {
            if ($First[$label][$key] -cne $Second[$label][$key]) { throw 'snapshot_files_changed' }
        }
    }
}
