import pythonwhois

from contextlib import suppress
from pythonwhois.shared import WhoisException
from plugin import *


class whois(plugin):
    def __init__(self, bot):
        super().__init__(bot)

    @command
    @doc('gets whois info')
    def whois(self, sender_nick, msg, **kwargs):
        domain = msg.strip().lower()
        self.logger.info(f'{sender_nick} whoised {domain}')

        try:
            data = pythonwhois.get_whois(domain, normalized=True)
        except WhoisException:
            self.bot.say(f'no match for {domain}')
            return
        except:
            self.bot.say(f'no info for {domain}')
            return

        result = []

        with suppress(KeyError):
            result.append(['Registrar', format(data['registrar'][0])])

        with suppress(KeyError):
            result.append(['Registered', format(data['creation_date'][0].strftime('%d-%m-%Y'))])

        with suppress(KeyError):
            result.append(['Expires', format(data['expiration_date'][0].strftime('%d-%m-%Y'))])

        if data['contacts']['registrant']:
            result.append(['Registrant', self.build_contact_str(data, 'registrant')])

        if data['contacts']['admin']:
            result.append(['Admin', self.build_contact_str(data, 'admin')])

        if not result:
            self.bot.say(f'no info for {domain}')

        for i in result:
            self.bot.say(f'{i[0]}: {i[1]}')

    def build_contact_str(self, _data, contact):
        if not _data['contacts'][contact]: return None

        data = _data['contacts'][contact]
        result = data['name']

        info = []
        for field in ['email', 'phone']:
            if field in data and data[field]: info.append(data[field])
        info = ', '.join(info)

        if info: result += f' ({info})'

        for field in ['city', 'street', 'postalcode', 'country']:
            if field in data and data[field]: result += f', {data[field]}'

        return result
