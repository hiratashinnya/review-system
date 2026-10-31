import sys

from .cli import main
from .reviewer_cli import register

if __name__ == "__main__":
    sys.exit(main(extra_registrars=(register,)))
