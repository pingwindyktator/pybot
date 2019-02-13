import random
import requests

from datetime import timedelta
from plugin import *


class foass(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.unsupported_endpoints = ['/version']
        self.supported_args = {
            'behavior': 'this shit',
            'thing': 'thing',
            'language': 'programming',
            'name': None,
            'from': None,
            'tool': 'google',
            'company': None
        }
        self.must_have_args = ['name']
        assert all((arg in self.supported_args for arg in self.must_have_args))
        self.endpoints = self.get_all_endpoints()

    @utils.timed_lru_cache(expiration=timedelta(hours=24))
    def get_all_endpoints(self):
        endpoints = requests.get('http://www.foaas.com/operations').json()
        endpoints = [r['url'] for r in endpoints if ':' in r['url']]
        endpoints = [r for r in endpoints if r not in self.unsupported_endpoints]
        endpoints = list(set(endpoints))
        _endpoints = endpoints.copy()

        for response in endpoints:
            args = re.findall(r':[^/]+', response)
            if any((arg[1:] not in self.supported_args.keys() for arg in args)):
                _endpoints.remove(response)

            elif not all((f':{arg}' in args for arg in self.must_have_args)):
                _endpoints.remove(response)

        endpoints = _endpoints

        for i in range(0, len(endpoints)):
            for arg in self.supported_args.keys():
                endpoints[i] = endpoints[i].replace(f':{arg}', '{%s}' % arg)

        return endpoints

    def prepare_endpoint(self, endpoint, victim):
        self.supported_args['name'] = victim
        self.supported_args['company'] = victim

        return endpoint.format(**self.supported_args)

    def get_response(self, endpoint):
        response = requests.get(r'https://foaas.com%s' % endpoint, headers={"Accept": "text/plain"}, timeout=10).content.decode()
        response = re.sub(r' - %s$' % str(self.supported_args['from']), '', response)
        return response

    @command
    @doc('respond <nickname>: respond to <nickname>')
    def respond(self, sender_nick, args, **kwargs):
        if not args: return
        nickname = irc_nickname(args[0])
        self.logger.info(f'{sender_nick} responds {nickname}')

        endpoints = self.get_all_endpoints()
        endpoint = self.prepare_endpoint(random.choice(endpoints), nickname)
        response = self.get_response(endpoint)
        if not response.startswith(sender_nick):
            response[0].upper()

        self.bot.say(response)
