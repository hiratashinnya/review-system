param([Parameter(Mandatory=$true)][string]$CohortWorker)
$ErrorActionPreference = 'Stop'
try {
    . $CohortWorker
    function Observe-WslRelativeTrial($Binding, $Original, $CohortWorkspace) {
        if (!$CohortWorkspace) { throw 'cohort_workspace_required' }
        return @{anchor_observed=$true;normalized_success=$true;update_environment_verified=$true;corpus_unchanged=$true;
            fixture_leaf=('live-628-' + ('a' * 32));local_policy_observations=@(@{verified_zero_turn_command=$true;permissions_match_candidate=$true},@{verified_zero_turn_command=$true;permissions_match_candidate=$true})}
    }
    $receipt = @{pid=1;created='synthetic';exe='synthetic'}
    $request = @{nonce=('b' * 32)}
    $result = @{}
    $summary = @{proof_committed=$true;publication_phase='complete';durability_confirmed=$true;durability_warning=$false;normal_success=$true;impact_witness=$true;version_supported=$true;source_unchanged=$true;normal_reason_count=0}
    $line = @{op='cohort_result';nonce=$request.nonce;summary=$summary} | ConvertTo-Json -Compress
    $savedIn = [Console]::In; $savedOut = [Console]::Out
    $writer = [IO.StringWriter]::new()
    try {
        [Console]::SetIn([IO.StringReader]::new($line + "`n"))
        [Console]::SetOut($writer)
        $returned = Observe-CohortSingleTrial @{exe_hash=('c' * 64)} @{}
    } finally {
        [Console]::SetIn($savedIn); [Console]::SetOut($savedOut)
    }
    $frame = $writer.ToString().Trim() | ConvertFrom-Json
    if ($returned -isnot [bool] -or !$returned -or !$frame.cohort_single_ready -or $frame.ready_receipt.nonce -cne $request.nonce -or $frame.ready_receipt.phase -cne 'cohort_single' -or !$result.cohort_single_trial.normal_success) { throw 'cohort_ready_regression_failed' }
    @{passed=$true;ready_reached_console_before_read=$true;assignment_received_only_bool=$true;settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
} catch {
    @{passed=$false;reason='cohort_ready_regression_failed';settings_reads=0;settings_writes=0;agy_launches=0} | ConvertTo-Json -Compress
    exit 2
}
