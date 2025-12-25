from __future__ import annotations

import multiprocessing

from zdp.app import run


def main() -> int:
    multiprocessing.freeze_support()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
