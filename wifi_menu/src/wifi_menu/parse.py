from __future__ import annotations


# for parsing nmcli escaped output (nmcli -e yes -f -t [fields])
def parse_connection_profile(line: str, maxsplit: int = -1) -> list[str]:
    parts: list[str] = []
    curr: list[str] = []

    splits = 0
    esc_char = "\\"
    separator = ":"

    size = len(line)
    it = 0
    while it < size:
        ch = line[it]

        if ch == esc_char and it + 1 < size:
            curr.append(line[it + 1])
            it += 2
            continue

        if ch == separator and (maxsplit < 0 or splits < maxsplit):
            parts.append("".join(curr))
            curr = []
            splits += 1
            it += 1
            continue

        curr.append(ch)
        it += 1

    parts.append("".join(curr))
    return parts
