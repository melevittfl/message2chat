from flask import Flask, request, abort
import os
from operator import itemgetter
import pylibmc
import requests


app = Flask(__name__)
app.config['DEBUG'] = os.environ.get("DEBUG", "True")

servers = os.environ.get('MEMCACHIER_SERVERS', '').split(',')
user = os.environ.get('MEMCACHIER_USERNAME', None)
password = os.environ.get('MEMCACHIER_PASSWORD', None)

cache = pylibmc.Client(servers,
                       binary=True,
                       username=user,
                       password=password)


chatbot_url = os.environ.get('CHATBOT_URL', None)

nexmo_key = os.environ.get('NEXMO_API_KEY', None)
nexmo_secret = os.environ.get('NEXMO_API_SECRET', None)
nexmo_number = os.environ.get('NEXMO_NUMBER')
nexmo_url = 'https://rest.nexmo.com/sms/json?'


def get_bot_response(sms, number, total_parts=None):
    r = requests.post(chatbot_url, json={'message': sms})
    app.logger.debug(r.text)

    chat_reply = r.json()
    app.logger.debug(chat_reply['reply'])

    params = {
        'api_key': nexmo_key,
        'api_secret': nexmo_secret,
        'to': number,
        'from': nexmo_number,
        'text': chat_reply['reply']
    }

    requests.get(nexmo_url, params=params)


def search_parts(list_of_parts, part_to_check):
    """
    Given a list of parts, checks to see if it exists already
    Returns The part found if the part to check is already in the list
    """
    return next((part for part in list_of_parts if part['part'] == part_to_check), None)


@app.route('/fdchat')  # From Nexmo.com
def message2():
    app.logger.debug(request)

    if (not request.args.get('to')) or (not request.args.get('msisdn')) or (not request.args.get('text')):
        app.logger.debug("Received something that wasn't an sms")
        abort(404)

    number = request.args.get(u"msisdn")
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
                get_bot_response(sms_message, number, total_parts=concat_total)
            else:
                cache.set(concat_reference, sms_parts)

        else:
            print(u"Cache entry not found")
            sms_message_part = {u"part": concat_part, u"text": text}
            sms_parts = [sms_message_part]
            cache.set(concat_reference, sms_parts)
    else:
        get_bot_response(request.args.get(u'text'), number)

    return u"<html><body>OK</body></html>", 200


if __name__ == '__main__':
    app.run()
