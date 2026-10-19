# guidance_sync の正本選択と生成境界

`guidance_sync/sources.py` の `NON_GUIDANCE_SHARED_DIRS` は、非活性の共有記録が常時読込 guidance の正本になることを防ぐためにある。値は `ai_layout.NON_ACTIVE_SHARED_DIRS` から末尾 `/` を付けて導出する。source path に対して `str.startswith` で判定するため、末尾の区切りを含める。

`.ai/guidance` はこの一覧に含めない。述語は「guidance source にしてはならない」であり、`TARGETS` は正規の `.ai/guidance/platforms/*.md` から構成される。一方、`asset_parity.inventory.NON_NORMATIVE_SHARED_DIRS` は「parity seed にしてはならない」という逆の述語を持ち、`.ai/guidance` を加える。この二つの定数は同じ概念ではなく、共通の一覧へ統合しない。

生成物の本文へ共通 guidance を inline するため、`rendered_bytes` は `NON_GUIDANCE_SHARED_DIRS` を直接用いない。これを拒否リストへ加えると、唯一正当な guidance source tree まで拒否されるためである。marker 書式は `asset_parity.inlining` に互換のため複製され、`tests/unit/test_asset_parity_inlining_marker.py` で一致を検査する。
