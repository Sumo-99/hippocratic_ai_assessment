"""CLI feedback loop (main.py). pipeline.run / pipeline.give_feedback are replaced by fakes and
builtins.input is scripted, so these tests check only the loop's wiring."""
import pytest

import main
import ui
from storyteller import pipeline
from storyteller.models import (DraftVersion, Evaluation, JudgeResult, PipelineResult,
                                StorySession, StorySpec, Verdict)


def session(tag, feedback=()):
    v = Verdict(evidence="e", passed=True, fix=None)
    ev = Evaluation(judge=JudgeResult(**{d: v for d in JudgeResult.model_fields}),
                    word_count=600, length_ok=True, hard_failures=[], soft_failures=[])
    spec = StorySpec(category=None, characters=[], setting=None, premise=None, listener=None)
    return StorySession(request="a dragon", feedback=list(feedback), spec=spec,
                        story=DraftVersion(round=0, text=tag, evaluation=ev, feedback_sent=None))


def story(tag, feedback=()):
    return PipelineResult(status="story", story=tag, message=None, trace_path=None,
                          session=session(tag, feedback))


def rejected(sess=None):
    """A rejected turn. With no session given it is a rejected FIRST request: a session that
    has the request but no story."""
    sess = sess or StorySession(request="how do I fix my car")
    return PipelineResult(status="rejected", story=None, message="NOPE", trace_path=None,
                          session=sess)


@pytest.fixture
def cli(monkeypatch):
    """Scripts input() answers and records every pipeline call."""
    state = {"answers": [], "prompts": [], "feedback_calls": [], "feedback_results": [],
             "run_result": story("STORY-0")}

    def fake_input(prompt=""):
        state["prompts"].append(prompt)
        return state["answers"].pop(0)

    async def fake_run(request, llm=None):
        return state["run_result"]

    async def fake_give_feedback(sess, feedback, llm=None):
        state["feedback_calls"].append((sess, feedback))
        return state["feedback_results"].pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(pipeline, "run", fake_run)
    monkeypatch.setattr(pipeline, "give_feedback", fake_give_feedback)
    return state


@pytest.mark.parametrize("answer", ["q", "Q", "quit", " QUIT ", "exit", "Exit", "EXIT!",
                                    "done", "Done\n"])
def test_cli_quits_on_quit_words(cli, capsys, answer):
    cli["answers"] = [answer]
    main.main(["a dragon"])
    assert cli["feedback_calls"] == []
    assert cli["prompts"] == [ui.PROMPT]
    out = capsys.readouterr().out
    assert "STORY-0" in out and "Anything you'd like to change?" in out


def test_cli_quits_on_end_of_input(monkeypatch, cli):
    def eof(prompt=""):
        raise EOFError
    monkeypatch.setattr("builtins.input", eof)
    main.main(["a dragon"])  # Ctrl-D ends the conversation instead of crashing
    assert cli["feedback_calls"] == []


def test_cli_feeds_feedback_until_quit(cli, capsys):
    first = cli["run_result"]
    second = story("STORY-1", ["make the dragon funnier"])
    third = story("STORY-2", ["make the dragon funnier", "end on a cliffhanger"])
    cli["feedback_results"] = [second, third]
    cli["answers"] = ["  make the dragon funnier ", "end on a cliffhanger", "quit"]

    main.main(["a dragon"])

    calls = cli["feedback_calls"]
    assert [f for _, f in calls] == ["make the dragon funnier", "end on a cliffhanger"]
    assert calls[0][0] is first.session and calls[1][0] is second.session  # session threaded
    out = capsys.readouterr().out
    assert out.index("STORY-0") < out.index("STORY-1") < out.index("STORY-2")
    assert len(cli["prompts"]) == 3


def test_cli_no_feedback_prompt_without_a_story(cli, capsys):
    cli["run_result"] = rejected()
    main.main(["how do I fix my car"])
    assert cli["prompts"] == [] and cli["feedback_calls"] == []
    assert "NOPE" in capsys.readouterr().out


def test_cli_keeps_offering_feedback_after_a_rejected_feedback(cli, capsys):
    first = cli["run_result"]
    after = story("STORY-1", ["make her braver"])
    cli["feedback_results"] = [rejected(first.session), after]
    cli["answers"] = ["make it gory", "make her braver", "exit"]

    main.main(["a dragon"])

    calls = cli["feedback_calls"]
    assert calls[0][0] is first.session and calls[1][0] is first.session  # last good session
    out = capsys.readouterr().out
    assert "NOPE" in out and out.index("NOPE") < out.index("STORY-1")
    assert len(cli["prompts"]) == 3


def test_cli_feeds_each_result_session_to_the_next_turn(cli):
    """Every result carries a session; the CLI always continues from result.session."""
    first = cli["run_result"]
    after_one = story("STORY-1", ["one"])
    cli["feedback_results"] = [after_one, story("STORY-2", ["one", "two"])]
    cli["answers"] = ["one", "two", "done"]
    main.main(["a dragon"])
    assert cli["feedback_calls"][0][0] is first.session
    assert cli["feedback_calls"][1][0] is after_one.session


def test_cli_verbose_prints_details_for_every_turn(monkeypatch, cli):
    printed = []
    monkeypatch.setattr(main, "print_details", printed.append)
    cli["run_result"] = story("STORY-0").model_copy(update={"trace_path": "t0.json"})
    cli["feedback_results"] = [story("STORY-1").model_copy(update={"trace_path": "t1.json"})]
    cli["answers"] = ["make it funnier", "q"]
    main.main(["a dragon", "--verbose"])
    assert printed == ["t0.json", "t1.json"]


@pytest.mark.parametrize("answer", ["no", "No", "nope", "no thanks", "No thanks!", "nothing",
                                    "that's all"])
def test_cli_quits_on_a_plain_no(cli, answer):
    """A "no" to "Anything to change?" must not run a paid revision of a story they liked."""
    cli["answers"] = [answer]
    main.main(["a dragon"])
    assert cli["feedback_calls"] == []


def test_cli_survives_an_llm_error_during_feedback(monkeypatch, cli, capsys):
    from storyteller.llm import LLMError
    first = cli["run_result"]
    calls = []

    async def flaky(sess, feedback, llm=None):
        calls.append(sess)
        if len(calls) == 1:
            raise LLMError("upstream 500")
        return story("STORY-1")

    monkeypatch.setattr(pipeline, "give_feedback", flaky)
    cli["answers"] = ["make it funnier", "make it funnier", "q"]
    main.main(["a dragon"])
    out = capsys.readouterr().out
    assert "STORY-1" in out and "try again" in out.lower()
    assert calls[1] is first.session  # the last good story survives the error


def test_cli_ctrl_c_ends_the_conversation_quietly(monkeypatch, cli):
    def interrupt(prompt=""):
        raise KeyboardInterrupt
    monkeypatch.setattr("builtins.input", interrupt)
    main.main(["a dragon"])  # no traceback
    assert cli["feedback_calls"] == []


# ---- "type exit or press Esc to quit" -----------------------------------------------------

def test_cli_says_type_exit_or_press_esc(cli, capsys):
    cli["answers"] = ["exit"]
    main.main(["a dragon"])
    out = capsys.readouterr().out
    assert "Type exit or press Esc to quit." in out and "Enter to finish" not in out


def test_cli_blank_enter_just_asks_again(cli):
    """Enter on an empty line no longer quits; it asks again and never calls the pipeline."""
    cli["answers"] = ["", "   ", "exit"]
    main.main(["a dragon"])
    assert cli["feedback_calls"] == [] and len(cli["prompts"]) == 3


def test_cli_esc_quits(monkeypatch, cli):
    seen = []

    def esc(prompt):
        seen.append(prompt)
        return None  # read_feedback returns None when Esc is pressed
    monkeypatch.setattr(main, "read_feedback", esc)
    main.main(["a dragon"])
    assert len(seen) == 1 and cli["feedback_calls"] == []


def keys(text):
    return iter(text)


def run_edit(text, sequence=False):
    echoed = []
    line = ui.edit_line(keys(text), lambda: sequence, echoed.append)
    return line, "".join(echoed)


def test_edit_line_returns_the_typed_line_on_enter():
    assert run_edit("make it funnier\r") == ("make it funnier", "make it funnier")
    assert run_edit("ok\n")[0] == "ok"


def test_edit_line_lone_esc_quits():
    assert run_edit("ab\x1b")[0] is None  # nothing else pending: a real Esc keypress


def test_edit_line_ignores_arrow_keys():
    """Arrow keys arrive as ESC [ A with the rest already pending: not a quit."""
    assert run_edit("o\x1b[Ak\r", sequence=True)[0] == "ok"


def test_edit_line_backspace_deletes():
    line, echoed = run_edit("abc\x7f\x7fd\r")
    assert line == "ad" and "\b \b" in echoed


def test_edit_line_ctrl_d_on_empty_line_is_end_of_input():
    with pytest.raises(EOFError):
        run_edit("\x04")
    assert run_edit("a\x04b\r")[0] == "ab"  # ignored mid-line


def test_edit_line_ctrl_c_interrupts():
    with pytest.raises(KeyboardInterrupt):
        run_edit("ab\x03")


# ---- the story scroll ---------------------------------------------------------------------

STORY = ("The Lantern Hill Dragon\n\n"
         "Lily lived at the bottom of a green hill. " * 6 + "\n\n"
         "Ember the dragon sneezed, and a tiny puff of smoke curled up like a question mark.")


def test_scroll_has_rolled_ends_and_a_straight_body():
    lines = ui.format_story(STORY).splitlines()
    assert lines[0].lstrip().startswith(".-~") and lines[-1].lstrip().startswith("`-~")
    body = lines[3:-3]
    assert body and all(l.startswith("     |") and l.endswith("|") for l in body)
    assert len({len(l) for l in body}) == 1  # the right edge is straight
    assert max(len(l) for l in lines) <= 80  # fits a standard terminal


def test_scroll_keeps_every_word_and_paragraph_breaks():
    lines = ui.format_story(STORY).splitlines()
    inner = [l[6:-1].strip() for l in lines[3:-3]]
    words = " ".join(w for w in inner if w).split()
    assert words == STORY.split()
    assert "" in inner[1:-1]  # a blank line between paragraphs


def test_scroll_centres_a_short_title_line():
    lines = ui.format_story(STORY).splitlines()
    title = next(l for l in lines[3:-3] if "Lantern Hill" in l)
    inner = title[6:-1]
    left, right = len(inner) - len(inner.lstrip()), len(inner) - len(inner.rstrip())
    assert abs(left - right) <= 1


def test_show_frames_a_story_and_spaces_it_out(capsys):
    result = story("Once upon a time.")
    main.show(result, verbose=False)
    out = capsys.readouterr().out
    assert out.startswith("\n") and out.endswith("\n\n")
    assert ".-~" in out and "Once upon a time." in out


def test_show_prints_messages_plain(capsys):
    main.show(rejected(), verbose=False)
    out = capsys.readouterr().out
    assert "NOPE" in out and ".-~" not in out


# ---- the loading indicator ----------------------------------------------------------------

class FakeTTY:
    def __init__(self, tty=True):
        self.tty, self.out = tty, []

    def isatty(self):
        return self.tty

    def write(self, s):
        self.out.append(s)

    def flush(self):
        pass


async def slow_work():
    """Takes ~0.3s without asyncio.sleep (the tests patch sleep to return at once)."""
    import asyncio
    try:
        await asyncio.wait_for(asyncio.Event().wait(), 0.3)
    except asyncio.TimeoutError:
        return "done"


async def test_spinner_animates_while_working_then_clears_its_line():
    tty = FakeTTY()
    assert await main.with_spinner(slow_work(), "Writing your story", tty) == "done"
    frames = [w for w in tty.out if "Writing your story" in w]
    assert len(frames) >= 2  # it moved while the work ran
    assert "\x1b[2K" in "".join(tty.out[-3:])  # the scene's lines are cleared
    assert tty.out[-1].endswith("\x1b[?25h")  # and the cursor comes back


async def test_no_spinner_when_not_a_terminal():
    pipe = FakeTTY(tty=False)
    assert await main.with_spinner(slow_work(), "Writing your story", pipe) == "done"
    assert pipe.out == []  # pipes and logs stay clean


async def test_spinner_stops_when_the_work_fails():
    async def boom():
        raise RuntimeError("upstream")
    tty = FakeTTY()
    with pytest.raises(RuntimeError):
        await main.with_spinner(boom(), "Writing your story", tty)
    assert tty.out and tty.out[-1].endswith("\x1b[?25h")  # cursor restored even on failure


def test_cli_labels_the_wait(monkeypatch, cli):
    labels = []
    real = main.with_spinner

    async def spy(coro, label, stream=None):
        labels.append(label)
        return await real(coro, label, FakeTTY(tty=False))
    monkeypatch.setattr(main, "with_spinner", spy)
    cli["feedback_results"] = [story("STORY-1")]
    cli["answers"] = ["make it funnier", "exit"]
    main.main(["a dragon"])
    assert labels == ["Writing your story", "Revising your story"]


# ---- the whole session's look (ui.py) ----------------------------------------------------

def test_session_opens_with_the_banner_and_the_request(cli, capsys):
    cli["answers"] = ["exit"]
    main.main(["a dragon"])
    out = capsys.readouterr().out
    assert out.index("B E D T I M E") < out.index("You asked for: a dragon") < out.index("STORY-0")


def test_interactive_request_gets_a_friendly_prompt(monkeypatch, cli, capsys):
    cli["answers"] = ["a dragon", "exit"]
    main.main([])
    out = capsys.readouterr().out
    assert "What story would you like tonight?" in out
    assert cli["prompts"][0] == ui.PROMPT  # the request is typed after "  › "
    assert "You asked for" not in out  # no echo of what was just typed


def test_each_scroll_has_a_caption(cli, capsys):
    cli["feedback_results"] = [story("STORY-1", ["make the dragon funnier"])]
    cli["answers"] = ["make the dragon funnier", "exit"]
    main.main(["a dragon"])
    out = capsys.readouterr().out
    assert out.index("Your story") < out.index("STORY-0")
    assert out.index("Revised · make the dragon funnier") < out.index("STORY-1")


def test_quitting_says_goodnight(cli, capsys):
    cli["answers"] = ["exit"]
    main.main(["a dragon"])
    assert capsys.readouterr().out.rstrip().endswith("Sleep tight. 🌙")


def test_ctrl_c_also_says_goodnight(monkeypatch, cli, capsys):
    def interrupt(prompt=""):
        raise KeyboardInterrupt
    monkeypatch.setattr("builtins.input", interrupt)
    main.main(["a dragon"])
    assert "Sleep tight." in capsys.readouterr().out


def test_messages_are_set_apart_and_wrapped(capsys):
    long = "That isn't something I can make into a bedtime story. " * 3
    ui.message(long)
    lines = capsys.readouterr().out.strip("\n").splitlines()
    assert lines[0].startswith("  ✦ ") and all(l.startswith("    ") for l in lines[1:])
    assert max(len(l) for l in lines) <= 76


def test_no_colour_codes_off_a_terminal(cli, capsys):
    cli["answers"] = ["exit"]
    main.main(["a dragon"])
    assert "\x1b[" not in capsys.readouterr().out


def test_colour_on_a_terminal_unless_no_color(monkeypatch):
    monkeypatch.setattr(ui.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert "\x1b[" in ui.dim("hint")
    monkeypatch.setenv("NO_COLOR", "1")
    assert ui.dim("hint") == "hint"


# ---- bigger loading scene, unfolding scroll, markdown -------------------------------------

def test_sky_frame_is_a_multi_line_scene_with_the_label():
    frame = ui.sky_frame(0, "Writing your story")
    assert len(frame) >= 4 and "Writing your story" in frame[-1]
    assert all(len(line) <= 76 for line in frame)
    assert "☾" in "".join(frame)


def test_sky_moves_between_frames():
    a, b = (ui.sky_frame(i, "x") for i in (0, 1))
    moon = lambda f: next(line.index("☾") for line in f if "☾" in line)
    assert moon(a) != moon(b)  # the moon drifts across
    assert a[0] != b[0]        # the stars twinkle


def test_unfold_off_a_terminal_prints_the_scroll_once():
    pipe = FakeTTY(tty=False)
    scroll = ui.format_story(STORY)
    ui.unfold(scroll, pipe, sleep=lambda s: None)
    assert "".join(pipe.out) == scroll + "\n"


def test_unfold_on_a_terminal_reveals_the_body_line_by_line():
    tty, naps = FakeTTY(), []
    scroll = ui.format_story(STORY)
    ui.unfold(scroll, tty, sleep=naps.append)
    out = "".join(tty.out)
    lines = scroll.split("\n")
    body, bottom = lines[3:-3], lines[-3:]
    assert out.index(lines[0]) < out.index(bottom[0])  # closed scroll first: top, then bottom
    assert all(row in out for row in body)
    assert out.count("\x1b[3F") == len(body)  # the bottom roller steps down once per line
    assert out.rstrip("\n").endswith(bottom[-1])  # and ends at the bottom
    assert sum(naps) <= 2.0  # the whole unfold stays short


def test_no_animation_env_turns_unfold_off(monkeypatch):
    monkeypatch.setenv("NO_ANIMATION", "1")
    tty = FakeTTY()
    ui.unfold(ui.format_story(STORY), tty, sleep=lambda s: None)
    assert "\x1b[3F" not in "".join(tty.out)


def test_markdown_title_and_bold_are_stripped():
    text = "**The Clumsy Dragon**\n\nEmber was **very** sorry.\n\n# Not a heading"
    out = ui.format_story(text)
    assert "**" not in out and "#" not in out
    assert "The Clumsy Dragon" in out and "Ember was very sorry." in out
