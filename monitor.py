import psycopg2
import sys
from conviron import (
        get_config,
        CONFIG_FILE,
        email_error,
        )
from datetime import datetime

try:
    config_file = sys.argv[1]
except IndexError:
    config_file = CONFIG_FILE

config = get_config(config_file)
try:
    monitor_config_file = sys.argv[2]
except IndexError:
    monitor_config_file = "./monitor.ini"

monitor_config = get_config(monitor_config_file)


def _poll_database(chamber):
    con = psycopg2.connect(
            host=config.get("Postgres", "Host"),
            port=config.getint("Postgres", "Port"),
            user=config.get("Postgres", "User"),
            password=config.get("Postgres", "Pass"),
            )
    cur = con.cursor()
    statement = monitor_config.get("Postgres", "SelectLogPassesStatement")
    cur.execute(statement, chamber)
    result = list(cur)
    cur.close()
    con.close()
    return result


def main():
    chamber_str = monitor_config.get("Monitor", "ChambersToMonitor")
    chambers = chamber_str.strip().split(",")

    chamber_interval_str = monitor_config.get("Monitor", "ChamberIntervals")
    chamber_intervals = chamber_interval_str.strip().split(",")

    chamber_dict = {}
    for chamber, interval in zip(chambers, chamber_intervals):
        chamber_dict[chamber] = int(interval)

    while True:
        local_now = datetime.now().replace(
                tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=660, name=None),
                )
        for chamber, interval in chamber_dict.items():
            result = _poll_database(chamber)
            error = None
            try:
                last_good_result = result[0][0]
                time_diff = local_now - last_good_result
                sec_since_good_result = time_diff.days * 24 * 60 * 60 + \
                        time_diff.seconds
                if sec_since_good_result > interval:
                    error = "Chamber %s FAIL:\nToo long since good ping: %i > %i" % \
                            (chamber, sec_since_good_result, interval,)
                else:
                    print("Chamber %s OK" % chamber)
            except IndexError:
                error = "Chamber %s FAIL:\nNo database log records for chamber" % chamber
            if error is not None:
                print(error)
                email_error(error)


if __name__ == "__main__":
    main()