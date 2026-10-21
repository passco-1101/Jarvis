import argparse
import logging
import sys

from . import client, config, server


def setup_logging():
    config.LOG_DIR.mkdir(exist_ok=True)
    handlers = [logging.FileHandler(config.LOG_DIR / "jarvis.log", encoding="utf-8")]
    if sys.stderr:  # pythonw has no stderr, so this only applies when run from a console
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)


def build_parser():
    parser = argparse.ArgumentParser(prog="jarvis", description="Local PC assistant.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve", help="run the Jarvis daemon in this window")
    send = sub.add_parser("send", help="send a request, e.g. send open the downloads folder")
    send.add_argument("text", nargs="+")
    sub.add_parser("status", help="check that the daemon is running")
    sub.add_parser("pending", help="list commands waiting for approval")
    approve = sub.add_parser("approve", help="run a pending command")
    approve.add_argument("id")
    deny = sub.add_parser("deny", help="discard a pending command")
    deny.add_argument("id")
    return parser


def show(result):
    if result.get("status") == "pending":
        print(f"Needs your approval ({result['reason']}):\n  {result['command']}")
        print(f"Approve with: python -m jarvis approve {result['id']}")
        return
    if result.get("answer"):
        print(result["answer"])
    if result.get("command"):
        print(f"> {result['command']}")
    if result.get("output"):
        print(result["output"])
    if result.get("status") == "error" and not result.get("output"):
        print("Error.")


def main(argv=None):
    if sys.stdout:  # pythonw has no stdout
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)

    if args.cmd == "serve":
        setup_logging()
        try:
            server.serve(config.load(create_token=True))
        except OSError as exc:
            logging.error("could not start: %s (is Jarvis already running?)", exc)
            return 1
        return 0

    settings = config.load()
    if args.cmd == "send":
        show(client.call(settings, "POST", "/command", {"text": " ".join(args.text)}))
    elif args.cmd == "status":
        print(client.call(settings, "GET", "/status")["status"])
    elif args.cmd == "pending":
        items = client.call(settings, "GET", "/pending")["pending"]
        for item in items:
            print(f"{item['id']}  {item['command']}  ({item['reason']})")
        if not items:
            print("Nothing pending.")
    elif args.cmd == "approve":
        show(client.call(settings, "POST", f"/approve/{args.id}"))
    elif args.cmd == "deny":
        show(client.call(settings, "POST", f"/deny/{args.id}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
