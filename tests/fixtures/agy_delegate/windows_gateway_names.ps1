$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot '../../../agy_delegate/windows_snapshot.ps1')
    $cases = @(
        @{names=@('AGY_LLM_GATEWAY_URL');expected=$true},
        @{names=@('agy_llm_gateway_url');expected=$true},
        @{names=@('Agy_Llm_Gateway_Model');expected=$true},
        @{names=@('OTHER','agy_llm_gateway_url');expected=$true},
        @{names=@('AGY_LLM_GATEWAY_');expected=$true},
        @{names=@('AGY_LLM_GATEWAY');expected=$false},
        @{names=@('OTHER');expected=$false},
        @{names=@();expected=$false}
    )
    foreach ($case in $cases) {
        $actual = Test-GatewayVariableNames $case.names
        if ($actual -isnot [bool] -or $actual -ne $case.expected) { throw 'gateway_names_regression_failed' }
    }
    @{passed=$true;cases=$cases.Count;settings_reads=0;settings_writes=0;agy_launches=0;environment_values_read=0} | ConvertTo-Json -Compress
} catch {
    @{reason='gateway_names_regression_failed';settings_reads=0;settings_writes=0;agy_launches=0;environment_values_read=0} | ConvertTo-Json -Compress
    exit 2
}
