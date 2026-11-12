"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

"""
import argparse
import asyncio
import json

from storyteller import config, pipeline

example_requests = "A story about a girl named Alice and her best friend Bob, who happens to be a cat."


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Tell a bedtime story for ages 5-10.")
    p.add_argument("request", nargs="?", help="what the story should be about "
                                              "(asked for interactively if omitted)")
    p.add_argument("--baseline", action="store_true",
                   help="one plain model call with just the request (the original behaviour)")
    p.add_argument("--verbose", action="store_true",
                   help="also print category, each round's pass/fail, timings, cost, trace path")
    return p.parse_args(argv)


def print_details(trace_path: str) -> None:
    """Summarise a run from its trace file, so the CLI shows exactly what was recorded."""
    with open(trace_path) as f:
        t = json.load(f)
    print("\n--- details ---")
    if "spec" in t:
        print(f"category: {t['spec']['category']}")
    if "versions" in t:
        print(f"revisions: {len(t['versions']) - 1} (max {config.MAX_ROUNDS})")
        for v in t["versions"]:
            print(f"  round {v['round']}: hard failures {v['evaluation']['hard_failures'] or 'none'}, "
                  f"soft failures {v['evaluation']['soft_failures'] or 'none'}")
    final = t.get("final", {})
    if "round" in final:
        print(f"kept round: {final['round']}")
    if "all_passed" in final:
        print(f"final: {'PASS' if final['all_passed'] else 'FAIL'} "
              f"(hard failures: {final['hard_failures'] or 'none'}, "
              f"soft failures: {final['soft_failures'] or 'none'})")
    else:
        print(f"final: {final.get('status', '-')}")
    print("timings (s): " + ", ".join(f"{k}={v:.2f}" for k, v in t["timings"].items()))
    print(f"total cost: ${t['total_cost_usd']:.4f}")
    print(f"trace: {trace_path}")


def main(argv=None):
    args = parse_args(argv)
    request = args.request or input("What kind of story do you want to hear? ")

    if args.baseline:
        print(asyncio.run(pipeline.baseline(request)))
        return

    result = asyncio.run(pipeline.run(request))
    print(result.story if result.story is not None else result.message)
    if args.verbose and result.trace_path:
        print_details(result.trace_path)
    # TODO(user-feedback): ask the listener what they thought and offer a revised story.


if __name__ == "__main__":
    main()
