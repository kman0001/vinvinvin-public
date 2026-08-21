import os
from datetime import datetime
from zoneinfo import ZoneInfo

from croniter import croniter


def get_timezone():
    return ZoneInfo(
        os.getenv(
            "TZ",
            "UTC"
        )
    )


def get_next_run(
    cron_expression: str
):
    now = datetime.now(
        get_timezone()
    )

    cron = croniter(
        cron_expression,
        now
    )

    return cron.get_next(
        datetime
    )