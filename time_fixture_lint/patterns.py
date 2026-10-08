"""Wall-clock boundaries and markers; rationale is in scanner-rationale.md."""
import re


FIXTURE_EXTS = (".yml", ".yaml", ".json")
FIXTURE_ROOT = "tests/fixtures"
PY_TEST_ROOT = "tests/unit"
PY_TEST_ROOTS = (PY_TEST_ROOT, "tests/jev_hooks", "tests/time_fixture_lint")

# wall clock と直接比較されうる境界値語彙（上限・下限どちらも含む。inert な
# created_at/fetched_at/completed_at は含めない。理由は scanner-rationale.md 参照）。
SUSPICIOUS_FIELD_RE = re.compile(
    r"(?i)\b(expires?_?at|approved_at|resets?_?at|expiry|deadline|valid_until|not_after|not_before)\b"
)

# `key: value` トークン（YAML の1行1フィールド・JSON の1行複数フィールドの両方に対応）。
# key はシングル/ダブルクォート/裸のいずれも許容し、value もシングル/ダブルクォート/裸の
# いずれかにマッチする（F-344-03：旧実装はダブルクォートと裸値しか想定していなかった）。
FIELD_TOKEN_RE = re.compile(
    r"['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*:\s*"
    r"(?:\"([^\"]*)\"|'([^']*)'|([^,}\s]+))"
)

# 値が ISO8601 絶対日付、または epoch 疑いの10桁整数か。
ABS_DATE_VALUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
EPOCH_VALUE_RE = re.compile(r"^\d{10}$")

# python test 内の裸の epoch 定数代入（例: `NOW = 1783760000`）。
BARE_EPOCH_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d{10})\b")

# patch(...) の対象文字列が clock 関連語を含む場合のみ保護マーカーとして数える
# （F-344-01：clock と無関係な patch() で保護済みと誤判定させない）。
_CLOCK_PATCH_TARGET = r"[\"'][^\"']*(?:datetime|\btime\b|clock|freeze)[^\"']*[\"']"

# clock を制御している証拠。参照箇所の保護スコープ内にいずれかがあれば「保護済み」とみなす。
PROTECTION_MARKER_RE = re.compile(
    r"unittest\.mock\.patch\(\s*" + _CLOCK_PATCH_TARGET + r"|"
    r"(?<![\w.])patch\(\s*" + _CLOCK_PATCH_TARGET + r"|"
    r"freeze_time\(|freezegun|now\s*=\s*datetime\(|wraps=datetime"
)

# 同一行で time.time() の相対式に包まれていれば安全（#302 で採用された修正パターン）。
RELATIVE_TIME_RE = re.compile(r"time\.time\(\)")
