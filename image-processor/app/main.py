import time
from datetime import datetime

from app.config import load_config
from app.scheduler import get_next_run

config = load_config()

if config is None:
    raise SystemExit(1)

from app.processor.processor import process_images


def run_images(config, label):
    try:
        process_images(config)
    except Exception as exc:
        print(
            f"[ERROR] {label} image processing failed: {exc}",
            flush=True
        )


def main():

    config = load_config()

    if config is None:
        raise SystemExit(1)

    print(
        "Image processor scheduler started",
        flush=True
    )

    scheduler = config["scheduler"]

    print(
        "Running initial image processing",
        flush=True
    )
    run_images(config, "Initial")

    if not scheduler.get("enabled", False):
        print(
            "Scheduler disabled; initial run complete",
            flush=True
        )
        return

    while True:
        next_run = get_next_run(
            scheduler["cron"]
        )

        print(
            f"Next run: {next_run}",
            flush=True
        )

        now = datetime.now(
            next_run.tzinfo
        )

        wait_seconds = (
            next_run - now
        ).total_seconds()

        if wait_seconds > 0:
            time.sleep(wait_seconds)

        run_images(config, "Scheduled")


if __name__ == "__main__":
    main()