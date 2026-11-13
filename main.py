"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

"""
import argparse
import asyncio
import re

import ui  # how the CLI looks; this file is only what happens
from storyteller import config, pipeline
from storyteller.llm import LLMError
from ui import read_feedback, with_spinner

example_requests = "A story about a girl named Alice and her best friend Bob, who happens to be a cat."

QUIT_WORDS = {"q", "quit", "exit", "done", "stop", "no", "nope", "no thanks", "nothing",
              "thats all"}
FEEDBACK_ERROR = "Sorry, something went wrong making that change. Please try again."


def is_quit(answer: str) -> bool:
    """A quit word or a plain "no" (any case, punctuation ignored): each would otherwise run a
    paid revision of a story the user is happy with. A blank answer is not a quit; the loop
    just asks again."""
    return re.sub(r"[^\w\s]", "", answer.lower()).strip() in QUIT_WORDS


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Tell a bedtime story for ages 5-10.")
    p.add_argument("request", nargs="?", help="what the story should be about "
                                              "(asked for interactively if omitted)")
    p.add_argument("--baseline", action="store_true",
                   help="one plain model call with just the request (the original behaviour)")
    p.add_argument("--verbose", action="store_true",
                   help="also print category, each round's pass/fail, timings, cost, trace path")
    return p.parse_args(argv)


def show(result, verbose: bool, caption: str = "Your story") -> None:
    ui.show(result, verbose, caption)
    if verbose and result.trace_path:
        print_details(result.trace_path)


def print_details(trace_path: str) -> None:
    ui.details(trace_path, config.MAX_ROUNDS)


def main(argv=None):
    args = parse_args(argv)
    ui.banner()
    if args.request:
        request = args.request
        ui.show_request(request)
    else:
        request = ui.ask_request()

    if args.baseline:
        story = asyncio.run(with_spinner(pipeline.baseline(request), "Writing a plain story"))
        print()
        ui.story(story, "Baseline: one plain model call")
        return

    try:
        result = asyncio.run(with_spinner(pipeline.run(request), "Writing your story"))
        show(result, args.verbose)

        # The feedback loop: there is always a session, and feedback is offered while it holds
        # a delivered story. Each answer is one more turn; a rejected or failed turn returns the
        # last good session unchanged.
        session = result.session
        while session.story is not None:
            ui.feedback_hint()
            try:
                answer = read_feedback(ui.PROMPT)
            except EOFError:  # Ctrl-D ends the conversation like exit
                break
            if answer is None or is_quit(answer):  # Esc, or exit / a quit word
                break
            answer = answer.strip()
            if not answer:  # Enter on an empty line: just ask again
                continue
            print()
            try:
                result = asyncio.run(with_spinner(pipeline.give_feedback(session, answer),
                                                  "Revising your story"))
            except LLMError:
                # DECISION: an upstream failure on one change keeps the conversation and the
                # last good story; the turn's trace is already written by the pipeline.
                ui.message(FEEDBACK_ERROR)
                continue
            show(result, args.verbose, caption=f"Revised · {answer}")
            session = result.session
    except KeyboardInterrupt:  # Ctrl-C ends the conversation quietly
        print()
    ui.goodbye()


if __name__ == "__main__":
    main()
