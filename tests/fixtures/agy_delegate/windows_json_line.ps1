$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
try {
    $line = [Console]::In.ReadLine()
    $value = $line | ConvertFrom-Json
    @{parsed=$true;nonce_matches=($value.nonce -ceq 'synthetic-nonce');settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
} catch {
    @{parsed=$false;nonce_matches=$false;settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
}
