doc-system v2 の `config.yml` 操作を支援する Codex custom agent の PROMPT ノード。実体＝`.codex/agents/doc-system-config-operator.toml`、補助手順＝`.agents/skills/doc-system-config/SKILL.md`。GitHub issue #140 の doc_system 側範囲を担い、review_system 側への横展開は issue #141 に残す。
**バージョン**: 1.0
**目的**: `doc-system-v2/config.yml` の作成・解説・変更時に、FORMAT/config/schema/dsv2 と対応する SPEC/SCM/CFG/PROMPT ノードの根拠を照合し、config だけが先行する変更を防ぐ。
**入力変数**: `change_request`／`target_config_key`／`related_issue`／`scope_boundary`／`validation_commands`。既定の `scope_boundary` は doc-system 側のみで、review_system 側 config 操作は #141 として除外する。
**出力形式**: 変更対象ファイル、config key、対応ノード、実行検証、#141 へ残す横展開事項を列挙する。corpus ノード著作が必要な場合は AGENTS.md の authoring pipeline へ委譲する。
**注意事項**: `config.yml` の接続規則・対象集合・語彙を変更する場合は SPEC/SCM/CFG の根拠を先に確認する。根拠が無い場合は勝手に config だけを変更せず停止する。`.claude/` には配置しない。carrier=agent（Codex custom agent・issue #140）。**辺の ref_version**: `config.yml が PROMPT ノードカバレッジ対象 skill 集合を宣言する` "0.2"、SPEC-61 傘 "0.1"。
