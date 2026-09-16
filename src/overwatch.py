#!/usr/bin/python3
"""Keep Overwatch at the highest refresh without pinning monitor or workspace."""
import os
import re
import sys
from pathlib import Path

SETTINGS = Path(
    str(Path.home()) + "/.local/share/Steam/steamapps/compatdata/2357570/pfx/"
    "drive_c/users/steamuser/Documents/Overwatch/Settings/Settings_v0.ini"
)

RENDER = {
    "FrameRateCap": os.environ.get("JOGARDUO_FPS", "120"),
    "UseCustomFrameRates": "1",
    "FullScreenRefresh": os.environ.get("JOGARDUO_FPS", "120"),
    "WindowedRefresh": os.environ.get("JOGARDUO_FPS", "120"),
    "WindowedFullscreen": "1",
    "WindowMode": "1",
    "ShowFPSCounter": "1",
}


def _upsert_section(text: str, header: str, values: dict[str, str]) -> str:
    if header not in text:
        block = header + "\n" + "".join(f'{k} = "{v}"\n' for k, v in values.items()) + "\n"
        return text.rstrip() + "\n\n" + block
    start = text.index(header)
    nxt = re.search(r"\n\[", text[start + len(header) :])
    end = start + len(header) + nxt.start() if nxt else len(text)
    body = text[start:end]
    for key, value in values.items():
        line = f'{key} = "{value}"'
        if re.search(rf"^{re.escape(key)}\s*=", body, re.M):
            body = re.sub(rf"^{re.escape(key)}\s*=\s*\".*?\"", line, body, count=1, flags=re.M)
        else:
            body = body.rstrip() + "\n" + line + "\n"
    return text[:start] + body + text[end:]


def patch_display() -> None:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    text = SETTINGS.read_text() if SETTINGS.exists() else ""
    text = _upsert_section(text, "[Render.13]", RENDER)
    SETTINGS.write_text(text)


if __name__ == "__main__":
    patch_display()
    if sys.argv[1:] == ["--patch-only"]:
        sys.exit(0)
    # Proton/DXVK otherwise compiles pipelines on ~all 16 threads and the
    # menu looks like a 70% CPU game. Windows never does this work.
    os.environ["DXVK_MAX_COMPILER_THREADS"] = "2"
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: ow-pc %command%")
    if "--tank_Locale" not in args:
        args += ["--tank_Locale", "ptBR"]
    os.execvp(args[0], args)
