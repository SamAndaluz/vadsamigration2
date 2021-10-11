from base64 import b64decode
from base64 import b64encode
from Crypto import Random
from Crypto.Cipher import AES
import random
from binascii import hexlify, unhexlify

block_size = AES.block_size

import logging
_logger = logging.getLogger(__name__)

class AESCrypto:
	def __init__(self, key):
		self.key = key
        # "35841EF124C3D42B7B4137488D3052DA"
		self.bs = 16

	def _unpadPKCS5(self, s):
		return s[0:-ord(s[-1])]

	def _padPKCS5(self, s):
		return s + (
		    self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

	def encrypt(self, raw):
		padded_plain_text = self._padPKCS5(raw)
		iv = Random.new().read(AES.block_size)
		key = self.key
		cipher = AES.new(key.encode("utf8"), AES.MODE_CBC, iv)
		ivEncoded = b64encode(iv)
		dataEncoded = b64encode(cipher.encrypt(padded_plain_text.encode("utf8")))
		#return b64encode(dataEncoded)
		return b64encode(dataEncoded+':'.encode("utf8")+ivEncoded)
	
	def encrypt2(self, raw):
		raw = self._padPKCS5(raw)
		iv = Random.new().read(AES.block_size)
		key = unhexlify(self.key)
		cipher = AES.new(key, AES.MODE_CBC, iv)
		return b64encode(iv + cipher.encrypt(raw.encode()))

	def decrypt(self, enc):
		unpad = lambda s : s[:-s[-1]]
		enc = b64decode(enc)
		iv = enc[0:16]
		key = unhexlify(self.key)
		dipher = AES.new(key, AES.MODE_CBC, iv)
		decrypted = dipher.decrypt(enc)
		clean = unpad(decrypted).decode('latin-1')
		new_string = clean.split('<')
		to_remove = new_string[0]
		clean = clean.replace(to_remove, '')
		return clean

	def decrypt2(self, enc):
		enc = b64decode(enc)
		dataArr = enc.split(b":")
		iv = b64decode(dataArr[1])
		enc = b64decode(dataArr[0])
		key = self.key
		cipher = AES.new(key.encode("utf8"), AES.MODE_CBC, iv)
		return self._unpadPKCS5(cipher.decrypt(enc).decode('utf-8'))
