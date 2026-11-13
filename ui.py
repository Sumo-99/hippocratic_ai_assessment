"""Everything about how the CLI looks, in one place: the banner, prompts, the story scroll and
its unfolding, the night-sky loading scene, messages, --verbose details and the goodbye.

main.py decides what happens; this file only decides how it looks. Nothing in storyteller/
imports it. Everything is indented two spaces and fits 76 columns. Colour and animation only
run on a terminal; NO_COLOR turns colour off and NO_ANIMATION turns animation off."""
import asyncio
import codecs
import json
import os
import re
import sys
import textwrap
import time

# ---- preferences --------------------------------------------------------------------------

WIDTH = 76               # the widest line anything prints
INDENT = "  "
PROMPT = INDENT + "› "
SCROLL_WIDTH = 66        # inside the scroll's side bars; the whole scroll is 76 columns
SCROLL_PAD = 3           # spaces between the side bars and the text
UNFOLD_SECONDS = 1.5     # how long the scroll takes to unroll
SKY_WIDTH = 46           # the loading scene's width
SKY_FRAME_SECONDS = 0.15
STAR_PHASES = "·✧✦✧"     # one star's twinkle, frame by frame


def _colour_on() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _animate_on(stream) -> bool:
    return stream.isatty() and not os.environ.get("NO_ANIMATION")


def _style(text: str, code: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if _colour_on() else text


def dim(text: str) -> str:
    return _style(text, "2")


def bold(text: str) -> str:
    return _style(text, "1")


def _plain(text: str) -> str:
    """text without colour codes, for measuring."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ---- the start ----------------------------------------------------------------------------

def banner() -> None:
    lines = ["☾   ·   ✦   ·   ☾", bold("B E D T I M E   S T O R I E S"),
             dim("stories for ages 5 to 10"), dim("·   ˚   ·   ˚   ·")]
    print("\n")
    for line in lines:
        print(" " * ((WIDTH - len(_plain(line))) // 2) + line)  # centred
    print("\n")


def ask_request() -> str:
    print(INDENT + bold("What story would you like tonight?"))
    print(INDENT + dim('A character, a place, a worry, anything at all. Or just "tell me a story".'))
    print()
    request = input(PROMPT)
    print()
    return request


def show_request(request: str) -> None:
    print(INDENT + dim("You asked for: ") + request + "\n")


# ---- the story scroll ---------------------------------------------------------------------

def _unmarkdown(text: str) -> str:
    """Models sometimes write the title as **Title** or # Title; a scroll shows plain text."""
    text = re.sub(r"\*\*|__", "", text)
    return re.sub(r"^\s*#+\s*", "", text)


def format_story(text: str, width: int = SCROLL_WIDTH) -> str:
    """The story inside a scroll: rolled ends at top and bottom, straight sides, wrapped text.
    Paragraphs stay apart; a short first line (the title) is centred."""
    text_width = width - 2 * SCROLL_PAD
    paragraphs = [_unmarkdown(" ".join(p.split())) for p in text.strip().split("\n\n")
                  if p.strip()]
    body = [""]
    for i, para in enumerate(paragraphs):
        if i == 0 and len(para) <= text_width and len(paragraphs) > 1:
            body.append(para.center(text_width).rstrip())  # the title line
        else:
            body.extend(textwrap.wrap(para, text_width))
        body.append("")

    def row(content: str) -> str:
        return "     |" + " " * SCROLL_PAD + content.ljust(text_width) + " " * SCROLL_PAD + "|"

    return "\n".join([
        "  .-" + "~" * (width + 4) + "-.",
        " (   ." + "-" * width + ".   )",
        "  `-'|" + " " * width + "|`-'",
        *[row(line) for line in body],
        "  .-.|" + " " * width + "|.-.",
        " (   `" + "-" * width + "'   )",
        "  `-" + "~" * (width + 4) + "-'",
    ])


def unfold(scroll: str, stream=None, sleep=time.sleep) -> None:
    """Print the scroll so it unrolls: the closed scroll (both rolled ends together) appears
    first, then the bottom roller steps down one line at a time, revealing the story."""
    stream = stream or sys.stdout
    if not _animate_on(stream):
        stream.write(scroll + "\n")
        return
    lines = scroll.split("\n")
    top, body, bottom = lines[:3], lines[3:-3], lines[-3:]
    for line in top + bottom:  # the closed scroll
        stream.write(line + "\n")
    stream.flush()
    sleep(0.3)
    step = min(0.04, (UNFOLD_SECONDS - 0.3) / max(len(body), 1))
    for row in body:
        stream.write(f"\x1b[{len(bottom)}F")  # back up to where the bottom roller starts
        stream.write("\x1b[2K" + row + "\n")  # one more line of the story...
        for line in bottom:                   # ...and the roller below it
            stream.write("\x1b[2K" + line + "\n")
        stream.flush()
        sleep(step)


def story(text: str, caption: str) -> None:
    """A caption, then the story unrolling in its scroll, with space around both."""
    print(INDENT + "✦ " + bold(caption) + "\n")
    sys.stdout.flush()
    unfold(format_story(text))
    print()


# ---- messages, feedback, details and goodbye ----------------------------------------------

def message(text: str) -> None:
    """A rejection, safety message or error: set apart and wrapped, never in a scroll."""
    print()
    print(textwrap.fill(" ".join(text.split()), WIDTH, initial_indent=INDENT + "✦ ",
                        subsequent_indent=INDENT + "  "))
    print()


def show(result, verbose: bool = False, caption: str = "Your story") -> None:
    """A story goes in its scroll under a caption; a message is set apart, never in a scroll."""
    if result.story is not None:
        print()
        story(result.story, caption)
    else:
        message(result.message)


def feedback_hint() -> None:
    print(INDENT + dim("─" * (WIDTH - len(INDENT))))
    print()
    print(INDENT + bold("Anything you'd like to change?") + " Just say it, for example")
    print(INDENT + dim('"make the dragon funnier" or "end on a cliffhanger".'))
    print(INDENT + dim("Type exit or press Esc to quit."))
    print()


def details(trace_path: str, max_rounds: int | None = None) -> None:
    """--verbose: a summary of the run read back from its trace file, dimmed and indented, so
    the CLI shows exactly what was recorded."""
    with open(trace_path) as f:
        t = json.load(f)
    lines = []
    if t.get("turn"):
        lines.append(f"feedback turn {t['turn']}: {t['feedback'][-1]!r}")
    if "spec" in t:
        lines.append(f"category: {t['spec']['category']}")
    if "versions" in t:
        cap = f" (max {max_rounds})" if max_rounds is not None else ""
        lines.append(f"revisions: {len(t['versions']) - 1}{cap}")
        for v in t["versions"]:
            lines.append(f"  round {v['round']}: hard failures "
                         f"{v['evaluation']['hard_failures'] or 'none'}, "
                         f"soft failures {v['evaluation']['soft_failures'] or 'none'}")
    final = t.get("final", {})
    if "round" in final:
        lines.append(f"kept round: {final['round']}")
    if "all_passed" in final:
        lines.append(f"final: {'PASS' if final['all_passed'] else 'FAIL'} "
                     f"(hard failures: {final['hard_failures'] or 'none'}, "
                     f"soft failures: {final['soft_failures'] or 'none'})")
    else:
        lines.append(f"final: {final.get('status', '-')}")
    lines.append("timings (s): " + ", ".join(f"{k}={v:.2f}" for k, v in t["timings"].items()))
    lines.append(f"total cost: ${t['total_cost_usd']:.4f}")
    lines.append(f"trace: {trace_path}")
    print(INDENT + dim("details"))
    for line in lines:
        print(INDENT + "  " + dim(line))
    print()


def goodbye() -> None:
    print("\n" + INDENT + "Sleep tight. 🌙" + "\n")


# ---- the loading scene --------------------------------------------------------------------

def sky_frame(i: int, label: str) -> list[str]:
    """Frame i of the loading scene: twinkling stars, a moon drifting across, and a quill
    line with the label. Every character is one column wide, so frames line up."""
    def stars(offset: int) -> str:
        row = [" "] * SKY_WIDTH
        for k, pos in enumerate(range(offset, SKY_WIDTH, 7)):
            row[pos] = STAR_PHASES[(i + k) % len(STAR_PHASES)]
        return "".join(row)

    sky = [" "] * SKY_WIDTH
    sky[i % SKY_WIDTH] = "☾"
    pad = INDENT * 2
    return [pad + stars(1), pad + "".join(sky), pad + stars(4), "",
            pad + "✎  " + label + "." * (i // 2 % 4)]


async def with_spinner(coro, label: str, stream=None):
    """Await `coro` while the night-sky scene plays above `label`, then clear it. Only on a
    terminal: piped or logged output gets no animation."""
    stream = stream or sys.stdout
    if not _animate_on(stream):
        return await coro
    done = asyncio.Event()
    height = len(sky_frame(0, label))

    async def play():
        i = 0
        stream.write("\x1b[?25l")  # hide the cursor while drawing
        while True:
            if i:
                stream.write(f"\x1b[{height}F")  # back to the scene's first line
            for line in sky_frame(i, label):
                stream.write("\x1b[2K" + line + "\n")
            stream.flush()
            try:  # wait one frame, or stop as soon as the work is done
                await asyncio.wait_for(done.wait(), SKY_FRAME_SECONDS)
                break
            except asyncio.TimeoutError:
                i += 1
        stream.write(f"\x1b[{height}F" + "\x1b[2K\n" * height + f"\x1b[{height}F")
        stream.write("\x1b[?25h")  # cursor back
        stream.flush()

    player = asyncio.create_task(play())
    try:
        return await coro
    finally:
        done.set()
        await player


# ---- reading feedback (Esc quits) ---------------------------------------------------------

ESC = "\x1b"


def edit_line(keys, is_sequence, echo) -> str | None:
    """Build one line from single keypresses. Returns the line on Enter, or None on Esc.

    keys: iterator of characters; is_sequence(): True if more bytes are already waiting right
    after an Esc, which means it began a key sequence (an arrow key), not an Esc keypress;
    echo(text): shows what was typed, since the terminal's own echo is off."""
    line = []
    for ch in keys:
        if ch in "\r\n":
            return "".join(line)
        if ch == ESC:
            if not is_sequence():
                return None  # a lone Esc: quit
            # Arrow and other special keys are ignored; there is no cursor movement.
            nxt = next(keys, "")
            if nxt in "[O":
                for c in keys:  # skip to the sequence's final byte (@ .. ~)
                    if "@" <= c <= "~":
                        break
        elif ch in "\x7f\b":
            if line:
                line.pop()
                echo("\b \b")
        elif ch == "\x03":
            raise KeyboardInterrupt
        elif ch == "\x04":
            if not line:
                raise EOFError
        elif ch.isprintable():
            line.append(ch)
            echo(ch)
    raise EOFError


def read_feedback(prompt: str = PROMPT) -> str | None:
    """One answer to the feedback prompt; None when the user pressed Esc.

    On a terminal, keys are read one at a time so a lone Esc can quit without Enter. Anywhere
    else (pipes, tests, Windows) it is plain input(), where typing exit still quits."""
    try:
        import select
        import termios
        import tty
    except ImportError:  # no termios (Windows)
        return input(prompt)
    if not sys.stdin.isatty():
        return input(prompt)
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    decoder = codecs.getincrementaldecoder("utf-8")()

    def keys():
        while True:
            ch = decoder.decode(os.read(fd, 1))
            if ch:
                yield ch

    def is_sequence():
        return bool(select.select([fd], [], [], 0.05)[0])

    def echo(text):
        sys.stdout.write(text)
        sys.stdout.flush()

    echo(prompt)
    try:
        tty.setcbreak(fd)  # no line buffering, no echo; Ctrl-C still interrupts
        return edit_line(keys(), is_sequence, echo)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        echo("\n")
