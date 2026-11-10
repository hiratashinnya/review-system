import sys

from .cli import main
from .reviewer_cli import register as register_reviewer
from .owner_cli import register as register_owner
from .handoff_cli import register as register_handoff

if __name__ == "__main__":
    sys.exit(main(extra_registrars=(register_reviewer, register_owner, register_handoff)))
