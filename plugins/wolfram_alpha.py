import requests
import urllib.parse
import xml.etree.ElementTree

from plugin import *


class wolfram_alpha(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
        self.key = '4EU37Y-TX9WJG3JH3'  # should be replaced with you'r personal API key
        self.short_req = r'https://api.wolframalpha.com/v1/result?i=%s&appid=%s'
        self.full_req = r'http://api.wolframalpha.com/v2/query?' \
                        r'input=%s' \
                        r'&appid=%s' \
                        r'&format=plaintext' \
                        r'&scantimeout=3.0' \
                        r'&podtimeout=4.0' \
                        r'&formattimeout=8.0' \
                        r'&parsetimeout=5.0' \
                        r'&excludepodid=SeriesRepresentations:*' \
                        r'&excludepodid=Illustration' \
                        r'&excludepodid=TypicalHumanComputationTimes' \
                        r'&excludepodid=NumberLine' \
                        r'&excludepodid=NumberName' \
                        r'&excludepodid=Input' \
                        r'&excludepodid=Sequence'
        self.url = 'https://www.wolframalpha.com/input/?i=%s'

    @command
    def wa(self, msg, sender_nick, **kwargs):
        self.logger.info('%s asked wolfram alpha "%s"' % (sender_nick, msg))
        self.bot.say(self.get_wa_response(msg))

        # response = color.orange('[Wolfram|Alpha] ') + response
        # if response.lower().strip() == ask.lower().strip():  # TODO more cases
        #     response = url % ask
        #
        # self.bot.say(response)

    def get_wa_response(self, msg):
        ask = self.parse_to_url(msg)
        error = r'http://api.wolframalpha.com/v2/query?input=mortgage'
        ok = self.full_req % (ask, self.key)
        raw_response = requests.get(ok).content.decode('utf-8')
        xml_root = xml.etree.ElementTree.fromstring(raw_response)
        print(raw_response)

        if xml_root.attrib['error'] == 'true':  # wa error
            return xml_root.find('error').find('msg').text

        if xml_root.attrib['success'] == 'false':  # no response
            return 'no data available'

        answers = {}  # answer_type -> answer
        # TODO maybe I should keep it sorted and take first answer?
        for pod in xml_root.findall('pod'):  # answers[a] = d
            if pod.attrib['error'] == 'true': continue
            answer_type = pod.attrib['title']
            answer = pod.find('subpod').find('plaintext').text  # TODO can be more subpods!
            if answer: answers[answer_type] = answer

        if not answers: return 'no data available'

        for answer_type, answer in answers.items():
            for subanswer in answer.split('\n'):
                subanswer = subanswer.replace('  ', ' ').replace(' |', ":")
                str = '[%s] %s' % (answer_type, subanswer)
                a = 42

        return ''

    @staticmethod
    def parse_to_url(str):
        return urllib.parse.quote(str)
