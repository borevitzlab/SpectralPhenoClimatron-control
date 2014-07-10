from __future__ import print_function
import csv
import datetime
import logging
import socket
import sys
from time import strptime, sleep, mktime, time
import traceback

from spcControl import (
        get_config_file,
        get_config,
        chamber,
        heliospectra,
        email_error,
        )


timepoint_count = 0
config = get_config(get_config_file())
LOG = logging.getLogger("spcControl")


def _log_to_postgres(log_tuple):
    try:
        import psycopg2
    except ImportError:
        return
    try:
        con = psycopg2.connect(
                host=config.get("Postgres", "Host"),
                port=config.getint("Postgres", "Port"),
                user=config.get("Postgres", "User"),
                password=config.get("Postgres", "Pass"),
                )
        cur = con.cursor()
        statement = config.get("Postgres", "InsertStatement")
        cur.execute(statement, log_tuple)
        con.commit()
        cur.close()
        con.close()
    except Exception as e:
        traceback_text = traceback.format_exc()
        LOG.warn("Can't connect to database to log")
        LOG.debug(traceback_text)


def communicate_line(line):
    """This processes each line, and handles any errors which they create
    elegantly.
    """
    global timepoint_count
    timepoint_count += 1
    LOG.debug("Csv line is: {0!s}".format(line))
    now = datetime.datetime.now().strftime("%d/%m/%y %H:%M")
    log_str = "Running timepoint {} at {}".format(timepoint_count, now)
    print(log_str, end='... ')
    chamber_num = config.get("Global", "Chamber")
    sys.stdout.flush()  # flush to force buffering, so above is printed
    step = ""
    try:
        if config.getboolean("Heliospectra", "Use"):
            step = "Update Heliospectra Lamps"
            heliospectra.communicate(line)
        if config.getboolean("Conviron", "Use"):
            step = "Update Conviron"
            chamber.communicate(line)
            step = "Log Conviron Conditions"
            chamber.log()
        LOG.info(log_str + " Success")
        print("Success")
        log_tuple = (chamber_num, "FALSE", log_str)
    except Exception as e:
        print("FAIL")
        traceback_text = traceback.format_exc()
        fail_msg = "Step {} Failed with traceback:\n{}".format(step,
                                                               traceback_text)
        LOG.error("Could not run timepoint {}\n{}".format(timepoint_count,
                                                          fail_msg))
        log_tuple = (chamber_num, "TRUE", "%s\n%s" % (log_str, traceback_text))
    if config.getboolean("Postgres", "Use"):
        _log_to_postgres(log_tuple)


def main():
    """Main event loop. This just handles the files, and passes lines to be
    processed to communicate_line()
    """
    # open the CSV file, and make the csv reader
    try:
        csv_file = sys.argv[1]
        csv_fh = open(csv_file)
    except (KeyError, IOError):
        print("ERROR: csv file must exist\n")
        print("Usage:")
        print("\tpython3 -m spcControl <csv_file> [<ini.file>]")
        exit(-1)
    # Prepare the CSV reader
    csv_reader = csv.reader(csv_fh, delimiter=',',
            quoting=csv.QUOTE_NONE)
    # Define these for short/easy reference later
    datefield = config.getint("GlobalCsvFields", "Date")
    timefield = config.getint("GlobalCsvFields", "Time")
    # Detect if the file has a header, by trying to get a date and time from
    # the first two field of the first row.
    try:
        first_line = next(csv_reader)
        date_time = first_line[datefield] + " " + first_line[timefield]
        # If this fails to strip the datetime from date_time, it raises a
        # ValueError, and means the first line isn't valid (i.e. probably a
        # header)
        first_time = datetime.datetime.strptime(
                date_time, config.get("Global", "CsvDateFormat"))
    except ValueError:
        try:
            # If an error occurs in this block, there's something wrong with
            # the csv file, so we don't want to catch it.
            first_line = next(csv_reader)
            date_time = first_line[datefield] + " " + first_line[timefield]
            first_time = datetime.datetime.strptime(
                    date_time, config.get("Global", "CsvDateFormat"))
        except ValueError:
            LOG.error("There's something wrong with the CSV file: " +
                    "{0!s} isn't a date in format '{1}'!".format(
                    date_time, config.get("Global", "CsvDateFormat")))
            exit(1)
    LOG.debug("First time in file is: {0!s}".format(first_time))
    # Find current time in CSV file
    now = datetime.datetime.now()
    timedelta = datetime.timedelta(minutes=config.getint("Global", "Interval"))
    # Check if file starts too far into the future
    if first_time > now + timedelta:
        LOG.error("The file starts too far into the future.")
        exit(2)
    # Make the line variable local to the main() function
    line = []
    # Read through the file to find the current date and time
    while not first_time < now < first_time + timedelta:
        try:
            line = next(csv_reader)
        except StopIteration:
            LOG.error("No date in the CSV file matches the current time.")
            exit(3)
        date_time = line[datefield] + " " + line[timefield]
        first_time = datetime.datetime.strptime(
                date_time, config.get("Global", "CsvDateFormat"))
    # Run the first line
    prev_run_length = 0
    start = time()
    communicate_line(line)
    prev_run_length = time() - start
    previous_time = first_time
    # Loop through the rest of the lines, running each one
    for line in csv_reader:
        date_time = line[datefield] + " " + line[timefield]
        csv_time = datetime.datetime.strptime(
                date_time, config.get("Global", "CsvDateFormat"))
        # Work out how long to wait
        diff = csv_time - previous_time
        diff_sec = diff.days * 24 * 60 * 60 + diff.seconds
        # We don't want to wait a negative number of seconds
        wait_sec = max(diff_sec - prev_run_length, 0)
        LOG.debug("Waiting %i secs." % wait_sec)
        # And wait that long
        sleep(wait_sec)
        # reset timer and run the line
        start = time()
        communicate_line(line)
        prev_run_length = time() - start
        previous_time = csv_time

if __name__ == "__main__":
    main()
