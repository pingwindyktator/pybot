import requests
import urllib.parse
import xml.etree.ElementTree

from plugin import *


class wolfram_alpha(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.logger = logging.getLogger(__name__)
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
        self.logger.info(f'{sender_nick} asked wolfram alpha "{msg}"')

        ask = urllib.parse.quote(msg)
        raw_response = requests.get(self.full_req % (ask, self.config['api_key'])).content.decode('utf-8')
        xml_root = xml.etree.ElementTree.fromstring(raw_response)
        answers = []

        if xml_root.attrib['error'] == 'true':  # wa error
            error_msg = xml_root.find('error').find('msg').text
            self.logger.warning(f'wolfram alpha error: {error_msg}')
            self.bot.say(error_msg)
            return

        if xml_root.attrib['success'] == 'false':  # no response
            self.logger.debug('******* NO DATA PARSED FROM WA RESPONSE *******')
            self.logger.debug(raw_response)
            self.logger.debug('***********************************************')
            self.bot.say(f'no data available for "{msg}"')
            return

        for pod in xml_root.findall('pod'):
            if pod.attrib['error'] == 'true': continue  # wa error
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
            self.logger.debug('******* NO DATA PARSED FROM WA RESPONSE *******')
            self.logger.debug(raw_response)
            self.logger.debug('***********************************************')
            self.bot.say(f'no data available for "{msg}"')
            return

        answers = sorted(answers)

        for it in range(0, len(answers)):
            if it > 0 and not answers[it].primary: break
            prefix = color.orange(f'[{answers[it].title}] ')
            for subpod in answers[it].subpods:
                result = prefix
                if subpod.title:
                    result = result + subpod.title + ': '

                result = result + subpod.plaintext
                self.bot.say(result)

    class wa_subpod:
        def __init__(self, plaintext, title=''):
            self.title = title.strip()
            self.plaintext = plaintext.strip().replace('  ', ' ').replace('\n', ' :: ').replace('\t', ' ').replace('|', '-')

    class wa_pod:
        def __init__(self, title, position, subpods, primary=False):
            self.title = title.strip()
            self.position = position
            self.subpods = subpods
            self.primary = primary

        def __lt__(self, other):
            if self.primary and not other.primary: return True
            if other.primary and not self.primary: return False
            return self.position < other.position
