import psycopg2
import sys
from spcControl import (
        email_error,
        get_config,
        )
from datetime import datetime
from time import sleep, timezone
import traceback
from psycopg2.tz import FixedOffsetTimezone
try:
    monitor_config_file = sys.argv[1]
except IndexError:
    monitor_config_file = "./monitor.ini"

monitor_config = get_config(monitor_config_file)


def _poll_database(chamber):
    try:
        con = psycopg2.connect(
                host=monitor_config.get("Postgres", "Host"),
                port=monitor_config.getint("Postgres", "Port"),
                user=monitor_config.get("Postgres", "User"),
                password=monitor_config.get("Postgres", "Pass"),
                )
        cur = con.cursor()
        statement = monitor_config.get("Postgres", "SelectLogPassesStatement")
        cur.execute(statement, (chamber,))
        result = list(cur)
        cur.close()
        con.close()
        return result
    except Exception as e:
        traceback_text = traceback.format_exc()
        if monitor_config.getboolean("Monitor", "Debug"):
            print(traceback_text)
        email_error("Error polling database", traceback_text, monitor_config_file)


def main():
    chamber_str = monitor_config.get("Monitor", "ChambersToMonitor")
    chambers = chamber_str.strip().split(",")

    chamber_interval_str = monitor_config.get("Monitor", "ChamberIntervals")
    chamber_intervals = chamber_interval_str.strip().split(",")

    chamber_dict = {}
    for chamber, interval in zip(chambers, chamber_intervals):
        chamber_dict[chamber] = int(interval)

    while True:
        offset_min = int(-timezone/60)  # from time import timezone
        local_now = datetime.now().replace(
                tzinfo=FixedOffsetTimezone(offset=offset_min, name="chamber"),
                )
        for chamber, interval in chamber_dict.items():
            result = _poll_database(chamber)
            if result is None:
                # An error occured in _poll_database, wait 5 sec and retry
                print("%s: SQL error, retrying" %
                        (datetime.now().isoformat(),))
                sleep(5)
                break
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
                    print("%s: Chamber %s OK" %
                            (datetime.now().isoformat(), chamber))
            except IndexError:
                error = "Chamber %s FAIL:\nNo database log records for chamber" % chamber
            if error is not None:
                print(error)
                subject = "Conviron monitoring error in chamber %s" % chamber
                email_error(subject, error, monitor_config_file)
                sleep(monitor_config.getint("Monitor", "SleepInterval"))
