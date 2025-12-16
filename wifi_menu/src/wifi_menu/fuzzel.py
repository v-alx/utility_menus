from __future__ import annotations
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class Choice:
    index: int
    text: str


class UI:
    def __init__(self, *, anchor: str = "top-right") -> None:
        self._anchor = anchor

    def _run(
        self, input_text: str | None, args: list[str]
    ) -> subprocess.CompletedProcess[str]:
        cmd = ["fuzzel", "--dmenu", "-a", self._anchor, *args]
        return subprocess.run(cmd, input=input_text, text=True, capture_output=True)

    def choose(self, items: list[str], *, lines: int | None = None) -> Optional[Choice]:
        if not items:
            return None
        shown_lines = lines if lines is not None else min(len(items), 30)
        res = self._run("\n".join(items), ["-l", str(shown_lines)])
        if res.returncode != 0:
            return None
        picked = res.stdout.rstrip("\n")
        if not picked:
            return None

        idx = next((i for i, s in enumerate(items) if s == picked))
        return Choice(index=idx, text=picked)

    def prompt_password(self) -> Optional[str]:
        res = self._run(
            None,
            ["--prompt-only=Password: ", "--password", "--cache=/dev/null"],
        )
        if res.returncode != 0:
            return None
        password = res.stdout.strip()
        return password or None


# TODO: configure nofity-send and find how to disble nm notifs
