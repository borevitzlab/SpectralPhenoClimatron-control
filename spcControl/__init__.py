from configparser import ConfigParser
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib


def get_config_file():
    try:
        config_file = sys.argv[2]
        with open(config_file) as fh:
            pass  # we can open it
    except (IndexError, IOError):
        config_file = "./chamber.ini"  # Default file name
    return config_file


def get_config(config_file):
    """Returns a ConfigParser which has read the given filename. If filename is
    not given, uses get_config_file()."""
    # If the config file is specified on the command line, use it

    parser = ConfigParser()
    try:
        parser.readfp(open(config_file))
    except AttributeError:
        parser.read_file(open(config_file))
    return parser



def email_error(subject, message, config_file=""):
    """Borrows heavily from http://kutuma.blogspot.com.au/2007/08/
    sending-emails-via-gmail-with-python.html
    """

    if not os.path.exists(config_file):
        config_file = get_config_file()

    config = get_config(config_file)
    try:
        msg = MIMEMultipart()
        msg["From"] = config.get("Global", "GmailUser")
        msg["To"] = config.get("Global", "EmailRecipient")
        msg["Subject"] = subject
        msg.attach(MIMEText(message))

        gmail = smtplib.SMTP("smtp.gmail.com", 587)
        gmail.ehlo()
        gmail.starttls()
        gmail.ehlo()
        gmail.login(
                config.get("Global", "GmailUser"),
                config.get("Global", "GmailPass")
            )
        gmail.sendmail(
                config.get("Global", "GmailUser"),
                config.get("Global", "EmailRecipient"),
                msg.as_string()
                )
        gmail.close()
    except:
        pass

