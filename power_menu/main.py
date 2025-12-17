#!/usr/bin/env python3
import subprocess


def run_fuzzel(prompt: str, items: list[str]) -> str:
    result = subprocess.run(
        ["fuzzel", "--dmenu", "--index", "-p", prompt],
        input="\n".join(items),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


actions = [
    (
        "Lock",
        [
            "sh",
            "-lc",
            "command -v hyprlock >/dev/null && exec hyprlock",
        ],
        "system-lock-screen-symbolic",
    ),
    (
        "Sleep",
        ["systemctl", "suspend"],
        "weather-clear-night-symbolic",
    ),
    ("Logout", ["hyprctl", "dispatch", "exit"], "system-log-out-symbolic"),
    (
        "Reboot",
        ["systemctl", "reboot"],
        "system-reboot-symbolic",
    ),
    ("Shutdown", ["systemctl", "poweroff"], "system-shutdown-symbolic"),
]

items = [f"{label}\0icon\x1f{icon}" for label, _cmd, icon in actions]

choice = run_fuzzel("System: ", items)
if not choice or not choice.isdigit():
    raise SystemExit(0)

subprocess.run(actions[int(choice)][1], check=False)
