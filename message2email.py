from flask import Flask, request
import os
from postmark import PMMail
from operator import itemgetter
import pylibmc
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
app.config['DEBUG'] = os.environ.get("DEBUG", "True")

servers = os.environ.get('MEMCACHIER_SERVERS', '').split(',')
user = os.environ.get('MEMCACHIER_USERNAME', None)
password = os.environ.get('MEMCACHIER_PASSWORD', None)

cache = pylibmc.Client(servers,
                       binary=True,
                       username=user,
                       password=password)



def send_sms_email(sms, total_parts=None):
    pass
    # if total_parts:
    #     subject_line = "BT SMS sent as {0} parts".format(total_parts)
    # else:
    #     subject_line = "BT SMS sent as 1 part"
    #
    # email = PMMail(api_key=os.environ.get('POSTMARK_API_TOKEN'),
    #                subject=subject_line,
    #                sender="otptest@marklevitt.co.uk",
    #                to="asturg@visa.com",
    #                text_body=sms)
    # email.send()
    # print("Email sent")


def search_parts(list_of_parts, part_to_check):
    """
    Given a list of parts, checks to see if it exists already
    Returns The part found if the part to check is already in the list
    """
    return next((part for part in list_of_parts if part['part'] == part_to_check), None)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/message', methods=['POST'])  # From Twilio.com
def message():
    print(request)
    sms = request.form['Body']
    send_sms_email(sms)
    return """<?xml version="1.0" encoding="UTF-8"?><Response></Response>"""

@app.route('/messagepart')
def messagepart():
    print(request)
    text = request.args.get(u"text", u"Not Sent").encode('utf-8')
    if request.args.get(u'concat') == u"true":
        concat_total = request.args.get(u"concat-total")
        concat_reference = request.args.get(u"concat-ref")
        print(u"Got a multipart message")
        send_sms_email("[Nexmo Ref: {0}] ".format(concat_reference) + text, total_parts=concat_total)
    else:
        send_sms_email(text)

    return u"<html><body>OK</body></html>", 200


# @app.route('/message2')  # From Nexmo.com
# def message2():
#     print(request)
#     if request.args.get(u'concat') == u"true":
#         """We have one part of a multipart message. We need to
#          check the cache and see if we have another part already. If so,
#          concatinate the parts and send the e-mail
#          If not, store this message in the cache
#         """
#         print(u"Got part of a multi-part message")
#         concat_reference = request.args.get(u"concat-ref")
#         concat_total = request.args.get(u"concat-total")
#         concat_part = request.args.get(u"concat-part")
#         text = request.args.get(u"text", u"Not Sent").encode('utf-8')
#         print(text)
#
#         sms_parts = cache.get(concat_reference)
#         if sms_parts is not None:
#             """We've got an existing entry add this message"""
#             print(u"Found reference in the cache")
#
#             if search_parts(sms_parts, concat_part):
#                 print(u"Duplicate part received. Ignoring.")
#                 return u"<html><body>Duplicate Part</body></html>", 200
#
#             sms_parts.append({u"part": concat_part, u"text": text})
#
#             if len(sms_parts) == int(concat_total):
#                 """We've got all parts of the message"""
#                 print(u"All parts arrived")
#                 sms_message = ""
#                 for part in sorted(sms_parts, key=itemgetter(u'part')):
#                     sms_message += part[u'text']
#
#                 print(sms_message)
#                 cache.delete(concat_reference)
#                 send_sms_email(sms_message, total_parts=concat_total)
#             else:
#                 cache.set(concat_reference, sms_parts)
#
#         else:
#             print(u"Cache entry not found")
#             sms_message_part = {u"part": concat_part, u"text": text}
#             sms_parts = [sms_message_part]
#             cache.set(concat_reference, sms_parts)
#     else:
#         send_sms_email(request.args.get(u'text'))
#
#     return u"<html><body>OK</body></html>", 200


@app.route('/fdchat')  # From Nexmo.com
def message2():
    app.logger.debug(request)
    if request.args.get(u'concat') == u"true":
        """We have one part of a multipart message. We need to
         check the cache and see if we have another part already. If so,
         concatinate the parts and send the e-mail
         If not, store this message in the cache
        """
        app.logger.info(u"Got part of a multi-part message")
        concat_reference = request.args.get(u"concat-ref")
        concat_total = request.args.get(u"concat-total")
        concat_part = request.args.get(u"concat-part")
        text = request.args.get(u"text", u"Not Sent").encode('utf-8')
        app.logger.info(text)

        sms_parts = cache.get(concat_reference)
        if sms_parts is not None:
            """We've got an existing entry add this message"""
            app.logger.info(u"Found reference in the cache")

            if search_parts(sms_parts, concat_part):
                print(u"Duplicate part received. Ignoring.")
                return u"<html><body>Duplicate Part</body></html>", 200

            sms_parts.append({u"part": concat_part, u"text": text})

            if len(sms_parts) == int(concat_total):
                """We've got all parts of the message"""
                print(u"All parts arrived")
                sms_message = ""
                for part in sorted(sms_parts, key=itemgetter(u'part')):
                    sms_message += part[u'text']

                print(sms_message)
                cache.delete(concat_reference)
                send_sms_email(sms_message, total_parts=concat_total)
            else:
                cache.set(concat_reference, sms_parts)

        else:
            print(u"Cache entry not found")
            sms_message_part = {u"part": concat_part, u"text": text}
            sms_parts = [sms_message_part]
            cache.set(concat_reference, sms_parts)
    else:
        send_sms_email(request.args.get(u'text'))

    return u"<html><body>OK</body></html>", 200


if __name__ == '__main__':
    app.run()
