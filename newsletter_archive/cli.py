import argparse
from .logging_conf import configure_logging, get_logger

log = get_logger("cli")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="archive", description="Newsletter brand archive")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="fetch new emails from Gmail and process them")
    sub.add_parser("build", help="render the static site from SQLite")
    sub.add_parser("backfill", help="dedup existing images into R2")
    m = sub.add_parser("migrate", help="import existing docs/ archives into SQLite")
    m.add_argument("--reingest", action="store_true", help="re-fetch from Gmail for true headers")
    b = sub.add_parser("brand", help="manage brands")
    bsub = b.add_subparsers(dest="action", required=True)
    sc = bsub.add_parser("set-category")
    sc.add_argument("key"); sc.add_argument("value")
    mg = bsub.add_parser("merge")
    mg.add_argument("key"); mg.add_argument("value")
    return p


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    log.info("command", extra={"command": args.command})
    raise SystemExit(
        f"'{args.command}' not implemented yet (Wave 1 skeleton)."
    )


if __name__ == "__main__":
    main()
