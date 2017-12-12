import hashlib
import zlib

from plugin import *


class crypto_hashes(plugin):
    def __init__(self, bot):
        if 'dsaWithSHA' not in hashlib.algorithms_available: del crypto_hashes.dsaWithSHA
        if 'blake2s' not in hashlib.algorithms_available: del crypto_hashes.blake2s
        if 'md4' not in hashlib.algorithms_available: del crypto_hashes.md4
        if 'ecdsa-with-SHA1' not in hashlib.algorithms_available: del crypto_hashes.ecdsa_with_SHA1
        if 'dsaEncryption' not in hashlib.algorithms_available: del crypto_hashes.dsaEncryption
        if 'whirlpool' not in hashlib.algorithms_available: del crypto_hashes.whirlpool
        if 'ripemd160' not in hashlib.algorithms_available: del crypto_hashes.ripemd160

        super().__init__(bot)

    @doc('computes sha1 of utf-8 encoded msg')
    @command
    def sha1(self, msg, **kwargs):
        self.bot.say(hashlib.sha1(msg.encode()).hexdigest())

    @doc('computes sha3_512 of utf-8 encoded msg')
    @command
    def sha3(self, msg, **kwargs):
        self.bot.say(hashlib.sha3_512(msg.encode()).hexdigest())

    @doc('computes sha224 of utf-8 encoded msg')
    @command
    def sha224(self, msg, **kwargs):
        self.bot.say(hashlib.sha224(msg.encode()).hexdigest())

    @doc('computes sha256 of utf-8 encoded msg')
    @command
    def sha256(self, msg, **kwargs):
        self.bot.say(hashlib.sha256(msg.encode()).hexdigest())

    @doc('computes sha384 of utf-8 encoded msg')
    @command
    def sha384(self, msg, **kwargs):
        self.bot.say(hashlib.sha384(msg.encode()).hexdigest())

    @doc('computes sha512 of utf-8 encoded msg')
    @command
    def sha512(self, msg, **kwargs):
        self.bot.say(hashlib.sha512(msg.encode()).hexdigest())

    @doc('computes sha3_224 of utf-8 encoded msg')
    @command
    def sha3_224(self, msg, **kwargs):
        self.bot.say(hashlib.sha3_224(msg.encode()).hexdigest())

    @doc('computes sha3_256 of utf-8 encoded msg')
    @command
    def sha3_256(self, msg, **kwargs):
        self.bot.say(hashlib.sha3_256(msg.encode()).hexdigest())

    @doc('computes sha3_384 of utf-8 encoded msg')
    @command
    def sha3_384(self, msg, **kwargs):
        self.bot.say(hashlib.sha3_384(msg.encode()).hexdigest())

    @doc('computes sha3_512 of utf-8 encoded msg')
    @command
    def sha3_512(self, msg, **kwargs):
        self.bot.say(hashlib.sha3_512(msg.encode()).hexdigest())

    @doc('computes md5 of utf-8 encoded msg')
    @command
    def md5(self, msg, **kwargs):
        self.bot.say(hashlib.md5(msg.encode()).hexdigest())

    @doc('computes blake2b of utf-8 encoded msg')
    @command
    def blake2b(self, msg, **kwargs):
        self.bot.say(hashlib.blake2b(msg.encode()).hexdigest())

    @doc('computes crc32 of utf-8 encoded msg')
    @command
    def crc32(self, msg, **kwargs):
        self.bot.say(zlib.crc32(msg.encode()))

    @doc('computes adler32 of utf-8 encoded msg')
    @command
    def adler32(self, msg, **kwargs):
        self.bot.say(zlib.adler32(msg.encode()))

    @doc('computes ripemd160 of utf-8 encoded msg')
    @command
    def ripemd160(self, msg, **kwargs):
        h = hashlib.new('ripemd160')
        h.update(msg.encode())
        self.bot.say(h.hexdigest())

    @doc('computes whirlpool of utf-8 encoded msg')
    @command
    def whirlpool(self, msg, **kwargs):
        h = hashlib.new('whirlpool')
        h.update(msg.encode())
        self.bot.say(h.hexdigest())

    @doc('computes dsaEncryption of utf-8 encoded msg')
    @command
    def dsaEncryption(self, msg, **kwargs):
        h = hashlib.new('dsaEncryption')
        h.update(msg.encode())
        self.bot.say(h.hexdigest())

    @doc('computes ecdsa-with-SHA1 of utf-8 encoded msg')
    @command
    def ecdsa_with_SHA1(self, msg, **kwargs):
        h = hashlib.new('ecdsa-with-SHA1')
        h.update(msg.encode())
        self.bot.say(h.hexdigest())

    @doc('computes md4 of utf-8 encoded msg')
    @command
    def md4(self, msg, **kwargs):
        h = hashlib.new('md4')
        h.update(msg.encode())
        self.bot.say(h.hexdigest())

    @doc('computes blake2s of utf-8 encoded msg')
    @command
    def blake2s(self, msg, **kwargs):
        h = hashlib.new('blake2s')
        h.update(msg.encode())
        self.bot.say(h.hexdigest())

    @doc('computes dsaWithSHA of utf-8 encoded msg')
    @command
    def dsaWithSHA(self, msg, **kwargs):
        h = hashlib.new('dsaWithSHA')
        h.update(msg.encode())
        self.bot.say(h.hexdigest())
