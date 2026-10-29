param([Parameter(Mandatory=$true)][string]$PolicyWorker)
$ErrorActionPreference = 'Stop'
try {
    . $PolicyWorker
    $cases = @(
        @{left='{"a":1,"b":[]}';right='{"b":[],"a":1}';expected=$true},
        @{left='{}';right='{}';expected=$true},
        @{left='[1,2]';right='[2,1]';expected=$false},
        @{left='[]';right='null';expected=$false},
        @{left='"Value"';right='"value"';expected=$false},
        @{left='{"a":1}';right='{"A":1}';expected=$false},
        @{left='true';right='1';expected=$false},
        @{left='{"a":null}';right='{}';expected=$false},
        @{left='1';right='1.0';expected=$false}
    )
    foreach ($case in $cases) {
        $actual = Same-JsonValue ($case.left | ConvertFrom-Json) ($case.right | ConvertFrom-Json)
        if ($actual -isnot [bool] -or $actual -ne $case.expected) { throw 'policy_compare_regression_failed' }
    }
    $before = [Text.Encoding]::UTF8.GetBytes('{"permissions":{"ask":[]},"other":{"a":1,"b":[]}}')
    $same = [Text.Encoding]::UTF8.GetBytes('{"other":{"b":[],"a":1},"permissions":{}}')
    $changed = [Text.Encoding]::UTF8.GetBytes('{"permissions":{},"other":{"a":2,"b":[]}}')
    $unknownCase = [Text.Encoding]::UTF8.GetBytes('{"Permissions":{},"other":{"a":1,"b":[]}}')
    if (!(Same-NonPermissions $before $same) -or (Same-NonPermissions $before $changed) -or (Same-NonPermissions $before $unknownCase)) { throw 'policy_compare_regression_failed' }
    @{passed=$true;cases=12;settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
} catch {
    @{passed=$false;reason='policy_compare_regression_failed';settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
    exit 2
}
