**前提条件**: `config.yaml` に `trace_scope.include` および `trace_scope.exclude` が設定されている
**入力/トリガ**: ファイルパスが include glob に一致し、かつ exclude glob にも一致する
**期待動作**: exclude が include より優先されるため、そのファイルを out-of-graph として検証対象から除外する
