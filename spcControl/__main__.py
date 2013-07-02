from time import strptime, sleep, mktime, time
import datetime
import csv
import socket
import sys
import time
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


def _email_traceback(traceback):
    message_text = "Error on chamber %i\n" % \
            config.getint("Global", "Chamber")
    message_text += traceback
    subject = "Conviron Error (Chamber %i)" % \
            config.getint("Global", "Chamber")
    email_error(subject, message_text)


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
        _email_traceback(traceback_text)


def communicate_line(line):
    """This processes each line, and handles any errors which they create
    elegantly.
    """
    global timepoint_count
    timepoint_count += 1
    if config.getboolean("Global", "Debug"):
        print("Csv line is:", line)
    now = datetime.datetime.now()
    log_str = "Running timepoint %i at %s" % (timepoint_count, now)
    print(log_str, end='... ')
    chamber_num = config.get("Global", "Chamber")
    sys.stdout.flush()  # flush to force buffering, so above is printed
    try:
        if config.getboolean("Conviron", "Use"):
            chamber.communicate(line)
        if config.getboolean("Heliospectra", "Use"):
            heliospectra.communicate(line)
        print("Success")
        log_tuple = (chamber_num, "FALSE", log_str)
    except Exception as e:
        print("FAIL")
        if config.getboolean("Global", "Debug"):
            traceback.print_exception(*sys.exc_info())
        traceback_text = traceback.format_exc()
        _email_traceback(traceback_text)
        log_tuple = (chamber_num, "TRUE", "%s\n%s" % (log_str, traceback_text))
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
        print("ERROR: csv file must exist\n"
                "Usage:\n"
                "\tpython3 -m spcControl <csv_file> [<ini.file>]"
                )
        exit(-1)

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
        first_time = datetime.datetime.fromtimestamp(
                mktime(strptime(
                    date_time, config.get("Global", "CsvDateFormat")
                    ))
                )
    except ValueError:
        # If an error occurs in this block, there's something wrong with the
        # csv file, so we don't want to catch it.
        first_line = next(csv_reader)
        date_time = first_line[datefield] + " " + first_line[timefield]
        first_time = datetime.datetime.fromtimestamp(
                mktime(strptime(
                    date_time,
                    config.get("Global", "CsvDateFormat")
                    ))
                )
    if config.getboolean("Global", "Debug"):
        print("First time in file is:", first_time)

    ## Find current time in CSV file ##
    now = datetime.datetime.now()
    # use a window of 10 in
    timedelta = datetime.timedelta(minutes=10)

    # Check if file starts too far into the future
    if first_time > now + timedelta:
        raise ValueError("The file starts too far into the future.")
    line = []  # Make the line variable local to the main() function

    # Read through the file to find the current date and time
    while not first_time < now < first_time + timedelta:
        try:
            line = next(csv_reader)
        except StopIteration:
            raise ValueError(
                    "No date in the CSV file matches the current time."
                    )
        date_time = line[datefield] + " " + line[timefield]
        first_time = datetime.datetime.fromtimestamp(
                mktime(strptime(
                    date_time, config.get("Global", "CsvDateFormat")
                    ))
                )

    # Run the first line
    prev_run_length = 0
    start = time.time()
    communicate_line(line)
    prev_run_length = time.time() - start
    previous_time = first_time

    # Loop through the rest of the lines, running each one
    for line in csv_reader:
        date_time = line[datefield] + " " + line[timefield]
        csv_time = datetime.datetime.fromtimestamp(
                mktime(strptime(
                    date_time,
                    config.get("Global", "CsvDateFormat")
                    ))
                )
        diff = csv_time - previous_time 
        wait_sec = max(
                diff.days * 24 * 60 * 60 + diff.seconds - prev_run_length,
                0  # We don't want to wait a negative number of seconds
                )
        if config.getboolean("Global", "Debug"):
            print("Waiting %i secs." % wait_sec)
        sleep(wait_sec)
        start = time.time()
        communicate_line(line)
        prev_run_length = time.time() - start
        previous_time = csv_time

main()
