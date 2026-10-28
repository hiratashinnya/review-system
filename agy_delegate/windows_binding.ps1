$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$phase = 'read_request'
$nonce = $null
try {
    . (Join-Path $PSScriptRoot 'windows_snapshot.ps1')
    $line = [Console]::In.ReadLine()
    if (!$line -or $line.Length -gt 8192) { throw 'request_invalid' }
    $request = $line | ConvertFrom-Json
    if (@($request.PSObject.Properties).Count -ne 3 -or @($request.PSObject.Properties | Where-Object { $_.Name -cnotin @('nonce','native_executable','native_workspace') }).Count -or $request.nonce -cnotmatch '^[0-9a-f]{32}$' -or $request.native_executable -isnot [string] -or $request.native_workspace -isnot [string] -or $request.native_workspace -cnotmatch '^//wsl\.localhost/[A-Za-z0-9_.-]+/') { throw 'request_invalid' }
    $nonce = $request.nonce
    $phase = 'bind_windows_identity'
    $profile = $env:USERPROFILE
    $exe = [IO.Path]::GetFullPath((Get-Command agy.exe -ErrorAction Stop).Source)
    if ($exe -cne [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'agy/bin/agy.exe')) -or $exe -cne [IO.Path]::GetFullPath($request.native_executable)) { throw 'executable_binding_mismatch' }
    if ($env:AGY_CLI_DISABLE_AUTO_UPDATE -cne 'true') { throw 'update_environment_unverified' }
    Require-PlainAncestors $exe
    if ((Get-Item -LiteralPath $exe -Force).Length -gt 268435456) { throw 'executable_unbounded' }
    $exeBefore = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    $principal = ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value + "`0" + $profile + "`0" + $env:LOCALAPPDATA + "`0" + $env:HOME)
    $paths = @{global=(Join-Path $profile '.gemini/antigravity-cli/settings.json');project=(Join-Path $profile '.gemini/config/projects/default-cli-project.json');shared=(Join-Path $profile '.gemini/config/config.json')}
    $first = @{}; $second = @{}
    foreach ($label in @('global','project','shared')) { $phase = 'first_' + $label; $first[$label] = Read-SettingsFingerprint $paths[$label] }
    foreach ($label in @('global','project','shared')) { $phase = 'second_' + $label; $second[$label] = Read-SettingsFingerprint $paths[$label] }
    Require-SameFingerprints $first $second
    $phase = 'verify_windows_binding'
    if ($exeBefore -cne (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'executable_changed' }
    $admin = Join-Path $env:ProgramData 'Antigravity/admin_settings.json'
    Require-PlainAncestors $admin
    $gatewayEnvironment = Test-GatewayVariableNames ([Environment]::GetEnvironmentVariables().Keys)
    @{ok=$true;nonce=$nonce;windows_os_sha256=(Snapshot-TextHash ([Environment]::OSVersion.VersionString));windows_principal_sha256=(Snapshot-TextHash $principal);executable_sha256=$exeBefore;files=$first;admin_gateway_candidate_absent=(!(Test-Path -LiteralPath $admin));gateway_environment_present=$gatewayEnvironment;update_disabled_for_child=$true;os_cwd_observed=$false;settings_writes=0;agy_launches=0} | ConvertTo-Json -Depth 8 -Compress
} catch {
    @{ok=$false;nonce=$nonce;reason='cohort_windows_binding_unverified';phase=$phase;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
    exit 2
}
