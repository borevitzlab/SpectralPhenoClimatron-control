from __future__ import print_function
from time import strptime, sleep, mktime, time
import datetime
import csv
from conviron import get_config


def communicate_line(line):
    """This processes each line, and """
    print("Communicating:", line)


def main():
    """Main event loop. This just handles the files, and passes lines to be
    processed to communicate_line()
    """
    config = get_config()
   
    # open the CSV file, and make the csv reader
    csv_fh = open(config.get("Global", "CsvFilePath"))
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
        print(first_time)

    ## Find current time in CSV file ##
    now = datetime.datetime.now()
    # use a window of 10 in
    timedelta = datetime.timedelta(minutes=10)

    # Check if file starts too far into the future
    if first_time > now + timedelta:
        raise ValueError("The file starts too far into the future.")
    line = [] # Make the line variable local to the main() function

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
    
    if config.getboolean("Global", "Debug"):
        print(line)

    # Run the first line
    communicate_line(line)
    previous_time = first_time

    # Loop through the rest of the lines, running each one
    for line in csv_reader:
        date_time = line[datefield] + " " + line[timefield]
        time = datetime.datetime.fromtimestamp(
                mktime(strptime(
                    date_time,
                    config.get("Global", "CsvDateFormat")
                    ))
                )
        timediff = time - previous_time
        wait_sec = timediff.days * 24 * 60 * 60 + timediff.seconds
        if config.getboolean("Global", "Debug"):
            print("Waiting %i secs." % wait_sec)
        #sleep(wait_sec)
        communicate_line(line)
        previous_time = time

main()
