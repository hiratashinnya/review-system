**前提条件**: `config.yaml` に `trace_scope.include` および `trace_scope.exclude`（glob）が設定されている
**入力/トリガ**: ファイルパスが include glob に一致し、exclude glob に一致しない
**期待動作**: そのファイルを in-graph として扱い、検証対象に含める
