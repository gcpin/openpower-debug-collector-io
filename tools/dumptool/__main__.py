"""Entry point for running dumptool as a module with python -m dumptool.cli"""

from dumptool.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
