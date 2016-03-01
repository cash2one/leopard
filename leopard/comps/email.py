import logging
from email.mime.text import MIMEText
from smtplib import SMTP, SMTPException
from leopard.core.config import get_config

config = get_config(__name__)

context = {}

logger = logging.getLogger(__name__)

def get_smtp():
    smtp = SMTP()
    code, message = smtp.connect(config['HOST'])
    while code != 220:
        logger.error('Something went wrong when connect to smtp server, code: {}, message: {}'.format(code, message))
    logger.info('Connected to smtp server, code: {}, message: {}'.format(code, message))
    try:
        smtp.login(config['EMAIL'], config['PASSWORD'])
    except SMTPException as e:
        logger.error('Something went wrong when login to smtp server, error: {}'.format(e))

    return smtp 


def send(title, content, *, to_email):
    from_email = config['EMAIL']
    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = title
    msg['From'] = from_email
    msg['To'] = to_email

    smtp = get_smtp()
    try:
        smtp.sendmail(from_email, to_email, msg.as_string())
    except SMTPException as e:
        logger.error('Something went wrong while sending an email, error: {}'.format(e))
    else:
        logger.info('Send an email to {}, title: "{}"'.format(to_email, title))
    finally:
        shutdown(smtp)


def shutdown(smtp):
    if smtp:
        smtp.quit()
        logger.info('Connection closed')
