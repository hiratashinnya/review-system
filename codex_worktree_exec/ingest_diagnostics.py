"""karte reviewer 取り込み結果から返却する拒否理由を整形する。"""

REJECTION_LINE_LIMIT = 8
REJECTION_CHAR_LIMIT = 1000


def rejection_detail(lines: list[str], rejected: list[int]) -> str:
    """拒否理由と各理由に続く箇条書きを、全体上限内で整形する。

    省略数は、表示できなかった行数を数える。
    """
    blocks = []
    for position, start in enumerate(rejected):
        end = rejected[position + 1] if position + 1 < len(rejected) else len(lines)
        block = [lines[start].strip()]
        for line in lines[start + 1:end]:
            if not line.startswith("  - "):
                break
            block.append(line.strip())
        blocks.append(block)
    all_lines = [line for block in blocks for line in block]
    full_detail = "\n".join(all_lines)
    if len(all_lines) <= REJECTION_LINE_LIMIT and len(full_detail) <= REJECTION_CHAR_LIMIT:
        return full_detail
    shown: list[str] = []
    omitted = sum(len(block) for block in blocks)
    while blocks:
        suffix = f"\n…ほか {omitted} 件" if omitted else ""
        room = REJECTION_LINE_LIMIT - len(shown) - bool(suffix)
        if room <= 0:
            break
        block = blocks[0]
        candidate = block[:room]
        text = "\n".join((*shown, *candidate))
        while len(text) + len(suffix) > REJECTION_CHAR_LIMIT and len(candidate) > 1:
            if candidate[-1].startswith("- "):
                prefix = "\n".join((*shown, *candidate[:-1]))
                remaining = omitted - len(candidate)
                final_suffix = f"\n…ほか {remaining} 件" if remaining else ""
                available = REJECTION_CHAR_LIMIT - len(prefix) - 1 - len(final_suffix) - 1
                if available >= 4:
                    shown.extend(candidate[:-1])
                    last = candidate[-1]
                    shown.append(last if len(last) <= available + 1 else last[:available].rstrip() + "…")
                    detail = "\n".join(shown) + final_suffix
                    return detail
            candidate.pop()
            text = "\n".join((*shown, *candidate))
        if len(text) + len(suffix) <= REJECTION_CHAR_LIMIT:
            shown.extend(candidate)
            omitted -= len(candidate)
            if len(candidate) == len(block):
                blocks.pop(0)
                continue
            blocks[0] = block[len(candidate):]
            break
        if not shown:
            omitted_after_header = omitted - 1
            suffix = f"\n…ほか {omitted_after_header} 件" if omitted_after_header else ""
            available = REJECTION_CHAR_LIMIT - len(suffix) - 1
            return block[0][:available].rstrip() + "…" + suffix
        break
    suffix = f"\n…ほか {omitted} 件" if omitted else ""
    while len(shown) + bool(suffix) > REJECTION_LINE_LIMIT:
        shown.pop()
    detail = "\n".join(shown) + suffix
    if len(detail) > REJECTION_CHAR_LIMIT:
        detail = detail[:REJECTION_CHAR_LIMIT - 1].rstrip() + "…"
    return detail
