"""サイドカー（{slug}.yaml）＋配置パスの機械検証（stdlib のみ・参照実装）。

Sub-A の受け入れ条件「サンプルが schema 検証を通る」を満たすための最小検証器。
YAML 読取は既存 ``docidx/nodeyaml.py``（新フォーマットでも流用予定・Sub-C）を再利用する。

検証内容（schema/sidecar.schema.json ＋ FORMAT.md と一致）:
  - 必須キー title/version/edges、未知キー禁止（additionalProperties:false）。
  - version は x.y.z、edge は無名（to 非空必須・ref_version は x.y・note のみ許容）。
  - condition ∈ config.yml condition_vocab（任意・非テスタブルは省略）。
  - **配置パス** nodes/<stage>/<type>/[<status>/]{slug}.md（+ .yaml）: stage/type/status が既知集合。
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
# lifecycle を持つ型のみ status サブディレクトリを取る（他型は status なし）。
STATUS_DIRS = {
    "fnd": {"open", "resolved"},
    "q": {"open", "decided", "deferred", "closed"},
    "dd": {"decided", "closed"},
}
# 正準 meta-schema フィールド（labels/scheduled/condition/suppress・TR の result/log_ref）＋
# コーパス実使用の carrier（canonicalization 保留）。id/type/status はサイドカーに持たない。
_ALLOWED_TOP = {"title", "version", "condition", "labels", "scheduled",
                "suppress", "result", "log_ref", "carrier", "edges"}
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
    if "suppress" in data and not isinstance(data["suppress"], list):
        errs.append("suppress は配列であること（ルール番号のリスト）")
    if "result" in data and data["result"] not in _RESULTS:
        errs.append(f"result 不正（PASS|FAIL）: {data['result']!r}")
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


def validate_path(md: Path, root: Path) -> tuple[list[str], list[str]]:
    """(errors, warnings)。md は nodes/<stage>/<type>/[<status>/]{slug}.md。"""
    errs: list[str] = []
    warns: list[str] = []
    rel = md.relative_to(root).parts  # ("nodes", stage, type, [status], file)
    if rel[0] != "nodes":
        errs.append("nodes/ 配下でない")
        return errs, warns
    parts = rel[1:-1]  # stage, type, [status]
    if len(parts) < 2:
        errs.append(f"stage/type ディレクトリ不足: {'/'.join(rel)}")
        return errs, warns
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
    return errs, warns


def validate_node(md: Path, root: Path) -> list[str]:
    """1ノード（md＋同名 yaml）を検証し、'ERROR:'/'WARN:' 行のリストを返す。"""
    out: list[str] = []
    yaml = md.with_suffix(".yaml")
    if not yaml.exists():
        return [f"ERROR: サイドカー欠落: {yaml.name}"]
    try:
        data = nodeyaml.parse(yaml.read_text("utf-8"))
    except Exception as ex:  # noqa: BLE001
        return [f"ERROR: yaml パース失敗: {ex}"]
    for e in validate_sidecar(data):
        out.append(f"ERROR: {e}")
    p_err, p_warn = validate_path(md, root)
    out += [f"ERROR: {e}" for e in p_err]
    out += [f"WARN: {w}" for w in p_warn]
    # id 一貫性: stem == slugify(title)
    if "title" in data:
        want = slugify(str(data["title"]))
        if md.stem != want:
            out.append(f"WARN: stem≠slugify(title): stem={md.stem!r} slugify={want!r}")
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent
    mds = sorted((root / "nodes").rglob("*.md"))
    total_err = 0
    for md in mds:
        msgs = validate_node(md, root)
        errs = [m for m in msgs if m.startswith("ERROR")]
        total_err += len(errs)
        status = "OK" if not errs else "NG"
        print(f"[{status}] {md.relative_to(root)}")
        for m in msgs:
            print(f"    {m}")
    print(f"\n{len(mds)} ノード / エラー {total_err} 件")
    return 1 if total_err else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
