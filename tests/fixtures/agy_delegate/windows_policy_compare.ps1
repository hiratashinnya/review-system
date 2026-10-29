param([Parameter(Mandatory=$true)][string]$PolicyWorker)
$ErrorActionPreference = 'Stop'
try {
    . $PolicyWorker
    . (Join-Path (Split-Path -Parent $PolicyWorker) 'agy_live_probe_local.ps1')
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
        $left = ('{"value":' + $case.left + '}') | ConvertFrom-Json
        $right = ('{"value":' + $case.right + '}') | ConvertFrom-Json
        $actual = Same-JsonValue $left.value $right.value
        if ($actual -isnot [bool] -or $actual -ne $case.expected) { throw 'policy_compare_regression_failed' }
    }
    $before = [Text.Encoding]::UTF8.GetBytes('{"permissions":{"ask":[]},"other":{"a":1,"b":[]}}')
    $same = [Text.Encoding]::UTF8.GetBytes('{"other":{"b":[],"a":1},"permissions":{}}')
    $changed = [Text.Encoding]::UTF8.GetBytes('{"permissions":{},"other":{"a":2,"b":[]}}')
    $unknownCase = [Text.Encoding]::UTF8.GetBytes('{"Permissions":{},"other":{"a":1,"b":[]}}')
    if (!(Same-NonPermissions $before $same) -or (Same-NonPermissions $before $changed) -or (Same-NonPermissions $before $unknownCase)) { throw 'policy_compare_regression_failed' }
    $shape = NonPermissions-ChangeShape ([Text.Encoding]::UTF8.GetBytes('{"permissions":{},"useG1Credits":false,"private-key":"/private/before"}')) ([Text.Encoding]::UTF8.GetBytes('{"permissions":{},"private-key":"/private/after"}'))
    $encoded = $shape | ConvertTo-Json -Depth 8 -Compress
    if ($shape.unknown_changed_key_count -ne 1 -or @($shape.known_changes).Count -ne 1 -or !$shape.known_changes[0].before_is_false -or $shape.known_changes[0].after_present -or $encoded.Contains('private-key') -or $encoded.Contains('/private/')) { throw 'policy_compare_regression_failed' }
    $defaultCases = @(
        @{before='{"permissions":{},"useG1Credits":false}';after='{"permissions":{}}';expected=$true},
        @{before='{"permissions":{},"useG1Credits":true}';after='{"permissions":{}}';expected=$false},
        @{before='{"permissions":{},"useG1Credits":false}';after='{"permissions":{},"useG1Credits":"false"}';expected=$false},
        @{before='{"permissions":{},"useG1Credits":false,"other":1}';after='{"permissions":{},"other":2}';expected=$false},
        @{before='{"permissions":{},"useG1Credits":false,"model":""}';after='{"permissions":{}}';expected=$false},
        @{before='{"permissions":{}}';after='{"permissions":{},"useG1Credits":false}';expected=$false},
        @{before='{"permissions":{},"useG1Credits":null}';after='{"permissions":{}}';expected=$false},
        @{before='{"permissions":{},"useG1Credits":false}';after='{"permissions":{},"useG1Credits":null}';expected=$false},
        @{before='{"permissions":{},"useG1Credits":0}';after='{"permissions":{}}';expected=$false}
    )
    foreach ($case in $defaultCases) {
        $actual = Same-NonPermissions ([Text.Encoding]::UTF8.GetBytes($case.before)) ([Text.Encoding]::UTF8.GetBytes($case.after)) $true
        if ($actual -isnot [bool] -or $actual -ne $case.expected) { throw 'policy_compare_regression_failed' }
    }
    $creditCases = @(@{value=$false;expected=$true},@{value=$true;expected=$false},@{value='False';expected=$false},@{value='false';expected=$false},@{value=0;expected=$false},@{value=$null;expected=$false},@{value=@{};expected=$false},@{value=@();expected=$false})
    foreach ($case in $creditCases) { if ((G1-CreditsFalse $case.value) -ne $case.expected) { throw 'policy_compare_regression_failed' } }
    @{passed=$true;cases=(13 + $defaultCases.Count + $creditCases.Count);settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
} catch {
    @{passed=$false;reason='policy_compare_regression_failed';settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
    exit 2
}
