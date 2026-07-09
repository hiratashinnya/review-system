"""サイドカー（{slug}.yaml）＋配置パスの機械検証（stdlib のみ・参照実装）。

Sub-A の受け入れ条件「サンプルが schema 検証を通る」を満たすための最小検証器。
YAML 読取は既存 ``docidx/nodeyaml.py``（新フォーマットでも流用予定・Sub-C）を再利用する。

検証内容（schema/sidecar.schema.json ＋ FORMAT.md と一致）:
  - 必須キー title/version/edges、未知キー禁止（additionalProperties:false）。
  - version は x.y.z、edge は無名（to 非空必須・ref_version は x.y・note のみ許容）。
  - condition ∈ config.yml condition_vocab（任意・非テスタブルは省略）。
  - **配置パス** nodes/<stage>/<type>/[<status>/]{slug}.yaml: stage/type/status が既知集合。
  - **本文ポリシー** required/shared/none に従う同名 .md または body_ref。
  - **id 一貫性**: ファイル stem（slug）== slugify(title)（不一致は warning）。

型横断の存在確認（edge.to の解決）・グローバル一意は本器の責務ではない（meta.json/グラフ照会＝Sub-C、
一意 fail-close＝reconciliation-validator/Sub-D）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root（docidx 用）
from docidx import nodeyaml  # noqa: E402

from slugify import slugify  # noqa: E402  # 同ディレクトリ

# 以下 3 集合は config.yml（layout / status_dirs）を正本とし、それと一致させて直書きしている。
# 検証器が config.yml を直接読む配線は Sub-E #74（それまで本コメントで整合を担保）。
STAGES = {"01-why", "02-what", "03-analysis", "05-design", "04-verification"}
TYPE_DIRS = {
    "val", "sr", "fr", "nfr", "spec", "actor", "i", "o", "d", "p", "e", "term",
    "orc", "ds", "mod", "dm", "port", "prs", "scm", "cfg", "prompt",
    "td", "tc", "tr", "verify", "fnd", "dd", "q", "pend",
}
BODY_POLICY = {
    "required": {
        "val", "sr", "fr", "nfr", "spec", "actor", "i", "o", "d", "p", "e", "term",
        "orc", "ds", "mod", "dm", "port", "prs", "scm", "cfg", "prompt",
        "tr", "verify", "fnd", "dd", "q", "pend",
    },
    "shared": {"td"},
    "none": {"tc", "src"},
}
# lifecycle を持つ型のみ status サブディレクトリを取る（他型は status なし）。
STATUS_DIRS = {
    "fnd": {"open", "resolved"},
    "q": {"open", "decided", "deferred", "closed"},
    "dd": {"decided", "closed"},
    "pend": {"open", "resolved", "deferred"},
}
# 正準 meta-schema フィールド（labels/scheduled/condition・TR の result/log_ref）＋
# コーパス実使用の carrier（canonicalization 保留）。id/type/status はサイドカーに持たない。
_ALLOWED_TOP = {"title", "version", "condition", "labels", "scheduled",
                "result", "log_ref", "carrier", "body_ref.file", "body_ref.anchor", "edges"}
_ALLOWED_EDGE = {"to", "ref_version", "note"}  # 無名依存辺（kind なし）
_VER = re.compile(r"^\d+\.\d+\.\d+$")
_REFVER = re.compile(r"^\d+\.\d+$")
# config.yml condition_vocab と一致（傘性は condition でなく構造から導出＝ここに umbrella は無い）。
_CONDITIONS = {"normal", "boundary", "empty", "failure", "error"}
_RESULTS = {"PASS", "FAIL"}


def validate_sidecar(data: dict) -> list[str]:
    errs: list[str] = []
    for k in data:
        if k not in _ALLOWED_TOP:
            errs.append(f"未知キー: {k!r}")
    for req in ("title", "version", "edges"):
        if req not in data:
            errs.append(f"必須キー欠落: {req!r}")
    if "title" in data and not str(data["title"]).strip():
        errs.append("title が空")
    if "version" in data and not _VER.match(str(data["version"])):
        errs.append(f"version が x.y.z でない: {data['version']!r}")
    if "condition" in data and data["condition"] not in _CONDITIONS:
        errs.append(f"condition 不正: {data['condition']!r}")
    if "labels" in data and not isinstance(data["labels"], list):
        errs.append("labels は配列であること")
    if "result" in data and data["result"] not in _RESULTS:
        errs.append(f"result 不正（PASS|FAIL）: {data['result']!r}")
    if "body_ref.file" in data and not str(data["body_ref.file"]).strip():
        errs.append("body_ref.file が非空必須")
    if "body_ref.anchor" in data and "body_ref.file" not in data:
        errs.append("body_ref.anchor は body_ref.file と併用すること")
    if "edges" in data:
        if not isinstance(data["edges"], list):
            errs.append("edges は配列であること")
        else:
            for j, e in enumerate(data["edges"]):
                if not isinstance(e, dict) or not str(e.get("to", "")).strip():
                    errs.append(f"edges[{j}]: to が非空必須")
                    continue
                for k in e:
                    if k not in _ALLOWED_EDGE:
                        errs.append(f"edges[{j}]: 未知キー {k!r}（無名依存辺は to/ref_version/note のみ）")
                if "ref_version" in e and not _REFVER.match(str(e["ref_version"])):
                    errs.append(f"edges[{j}].ref_version が x.y でない: {e['ref_version']!r}")
    return errs


def body_policy_for(typ: str) -> str:
    for policy, types in BODY_POLICY.items():
        if typ in types:
            return policy
    return "required"


def _body_ref_path(yaml: Path, root: Path, data: dict) -> Path | None:
    if not str(data.get("body_ref.file", "") or "").strip():
        return None
    raw = Path(str(data["body_ref.file"]))
    if raw.is_absolute():
        return raw
    root_rel = root / raw
    if root_rel.exists():
        return root_rel
    return yaml.parent / raw


def validate_body_policy(yaml: Path, root: Path, typ: str, data: dict) -> list[str]:
    errs: list[str] = []
    policy = body_policy_for(typ)
    same_stem = yaml.with_suffix(".md")
    ref_path = _body_ref_path(yaml, root, data)
    if policy == "required":
        if "body_ref.file" in data or "body_ref.anchor" in data:
            errs.append(f"type {typ!r} は body_ref.* を持たない（body_policy=required）")
        if not same_stem.exists():
            errs.append(f"本文 .md 欠落（body_policy=required）: {same_stem.name}")
    elif policy == "shared":
        if ref_path is None and not same_stem.exists():
            errs.append("本文参照欠落（body_policy=shared）: body_ref.file または同名 .md が必要")
        if ref_path is not None and not ref_path.exists():
            errs.append(f"body_ref.file が存在しない: {ref_path}")
    elif policy == "none":
        if "body_ref.file" in data or "body_ref.anchor" in data:
            errs.append(f"type {typ!r} は body_ref.* を持たない（body_policy=none）")
    return errs


def validate_path(yaml: Path, root: Path) -> tuple[list[str], list[str], str]:
    """(errors, warnings, type)。yaml は nodes/<stage>/<type>/[<status>/]{slug}.yaml。"""
    errs: list[str] = []
    warns: list[str] = []
    rel = yaml.relative_to(root).parts  # ("nodes", stage, type, [status], file)
    if rel[0] != "nodes":
        errs.append("nodes/ 配下でない")
        return errs, warns, ""
    parts = rel[1:-1]  # stage, type, [status]
    if len(parts) < 2:
        errs.append(f"stage/type ディレクトリ不足: {'/'.join(rel)}")
        return errs, warns, ""
    stage, typ = parts[0], parts[1]
    if stage not in STAGES:
        errs.append(f"未知 stage: {stage!r}")
    if typ not in TYPE_DIRS:
        errs.append(f"未知 type: {typ!r}")
    if len(parts) == 3:
        status = parts[2]
        allowed = STATUS_DIRS.get(typ)
        if allowed is None:
            errs.append(f"type {typ!r} は status サブディレクトリを取らない: {status!r}")
        elif status not in allowed:
            errs.append(f"type {typ!r} の未知 status: {status!r}（許容 {sorted(allowed)}）")
    elif typ in STATUS_DIRS:
        errs.append(f"type {typ!r} は status サブディレクトリ必須（{sorted(STATUS_DIRS[typ])}）")
    return errs, warns, typ


def validate_node(yaml: Path, root: Path) -> list[str]:
    """1ノード（正本 yaml＋型別本文）を検証し、'ERROR:'/'WARN:' 行のリストを返す。"""
    out: list[str] = []
    try:
        data = nodeyaml.parse(yaml.read_text("utf-8"))
    except Exception as ex:  # noqa: BLE001
        return [f"ERROR: yaml パース失敗: {ex}"]
    for e in validate_sidecar(data):
        out.append(f"ERROR: {e}")
    p_err, p_warn, typ = validate_path(yaml, root)
    out += [f"ERROR: {e}" for e in p_err]
    out += [f"WARN: {w}" for w in p_warn]
    if typ:
        out += [f"ERROR: {e}" for e in validate_body_policy(yaml, root, typ, data)]
    # id 一貫性: stem == slugify(title)
    if "title" in data:
        want = slugify(str(data["title"]))
        if yaml.stem != want:
            out.append(f"WARN: stem≠slugify(title): stem={yaml.stem!r} slugify={want!r}")
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent
    yamls = sorted((root / "nodes").rglob("*.yaml"))
    total_err = 0
    for yaml in yamls:
        msgs = validate_node(yaml, root)
        errs = [m for m in msgs if m.startswith("ERROR")]
        total_err += len(errs)
        status = "OK" if not errs else "NG"
        print(f"[{status}] {yaml.relative_to(root)}")
        for m in msgs:
            print(f"    {m}")
    print(f"\n{len(yamls)} ノード / エラー {total_err} 件")
    return 1 if total_err else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
