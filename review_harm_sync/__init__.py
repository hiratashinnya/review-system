"""Generate and verify the Claude preload from the harm criteria source."""
from hashlib import sha256
from pathlib import Path

SOURCE = Path('.ai/skills/review-harm/SKILL.md')
TARGET = Path('.claude/skills/review-harm/SKILL.md')


def generated(root: Path) -> str:
    source = (root / SOURCE).read_text(encoding='utf-8')
    body = source.split('---', 2)[2].strip()
    digest = sha256(source.encode('utf-8')).hexdigest()
    return ('---\nname: review-harm\ndescription: Review finding harm criteria.\n'
            'user-invocable: false\n---\n\n'
            f'<!-- generated from {SOURCE}; sha256: {digest} -->\n\n{body}\n')


def check(root: Path) -> list[str]:
    try:
        return [] if (root / TARGET).read_text(encoding='utf-8') == generated(root) else [str(TARGET)]
    except (OSError, UnicodeError, IndexError):
        return [str(TARGET)]


def render(root: Path) -> None:
    output = generated(root)
    (root / TARGET).parent.mkdir(parents=True, exist_ok=True)
    (root / TARGET).write_text(output, encoding='utf-8')
