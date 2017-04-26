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

        ask = self.parse_to_url(msg)
        raw_response = requests.get(self.full_req % (ask, self.key)).content.decode('utf-8')
        xml_root = xml.etree.ElementTree.fromstring(raw_response)
        answers = []

        if xml_root.attrib['error'] == 'true':  # wa error
            error_msg = xml_root.find('error').find('msg').text
            self.logger.warning('wolfram alpha error: %s' % error_msg)
            self.bot.say(error_msg)
            return

        if xml_root.attrib['success'] == 'false':  # no response
            self.bot.say('no data available for "%s"' % msg)
            return

        for pod in xml_root.findall('pod'):
            if pod.attrib['error'] == 'true': continue
            title = pod.attrib['title']
            primary = 'primary' in pod.attrib and pod.attrib['primary'] == 'true'
            position = int(pod.attrib['position'])
            subpods = []

            for subpod in pod.findall('subpod'):
                plaintext = subpod.find('plaintext').text
                subtitle = subpod.attrib['title']
                if not plaintext: continue
                subpods.append(self.wa_subpod(plaintext, subtitle))

            answers.append(self.wa_pod(title, position, subpods, primary))

        if not answers:
            self.bot.say('no data available for "%s"' % msg)
            return

        answers = sorted(answers)
        prefix = color.orange('[%s] ' % answers[0].title)

        for subpod in answers[0].subpods:
            result = prefix
            if subpod.title:
                result = result + subpod.title + ': '

            result = result + subpod.plaintext
            self.bot.say(result)

    class wa_subpod:
        def __init__(self, plaintext, title=''):
            self.title = title.strip()
            self.plaintext = plaintext.strip().replace('  ', ' ')

    class wa_pod:
        def __init__(self, title, position, subpods, primary=False):
            self.title = title.strip()
            self.position = position
            self.subpods = subpods
            self.primary = primary

        def __lt__(self, other):
            if self.primary: return True
            if other.primary: return False
            return self.position < other.position

    @staticmethod
    def parse_to_url(str):
        return urllib.parse.quote(str)
