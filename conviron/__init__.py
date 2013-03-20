from configparser import ConfigParser
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib



def get_config(filename):
    """Returns a ConfigParser which has read the given filename. If filename is
    not given, uses CONFIG_FILE."""
    # If the config file is specified on the command line, use it
    if filename is not None:
        config_file = filename
    else:
        config_file = CONFIG_FILE

    parser = ConfigParser()
    try:
        parser.readfp(open(config_file))
    except AttributeError:
        parser.read_file(open(config_file))
    return parser



def email_error(subject, message, config_file="./conviron.ini"):
    """Borrows heavily from http://kutuma.blogspot.com.au/2007/08/
    sending-emails-via-gmail-with-python.html
    """
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

