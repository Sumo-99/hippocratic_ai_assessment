"""CLI feedback loop (main.py). pipeline.run / pipeline.give_feedback are replaced by fakes and
builtins.input is scripted, so these tests check only the loop's wiring."""
import pytest

import main
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


@pytest.mark.parametrize("answer", ["", "   ", "q", "Q", "quit", " QUIT ", "exit", "Exit",
                                    "done", "Done\n"])
def test_cli_quits_on_empty_or_quit_words(cli, capsys, answer):
    cli["answers"] = [answer]
    main.main(["a dragon"])
    assert cli["feedback_calls"] == []
    assert len(cli["prompts"]) == 1 and "Anything to change?" in cli["prompts"][0]
    assert "STORY-0" in capsys.readouterr().out


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
    cli["answers"] = ["make it gory", "make her braver", ""]

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
