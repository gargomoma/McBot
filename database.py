
import pickle
import secrets
from collections import namedtuple

OfferDiff = namedtuple('OfferDiff', ('new', 'deleted'))

class PublishedMessage:
	def __init__(self, text=None, messageId=None, authKeys=None):
		self.text = text
		self.messageId = messageId
		self.authKeys = authKeys or list()

	def addAuthKey(self, authKey=None):
		if authKey is None:
			authKey = secrets.token_hex(8)
		if len(self.authKeys) > 2:
			self.authKeys.pop(0)
		self.authKeys.append(authKey)

	def getNewestAuthKey(self):
		return self.authKeys[-1]

	def popAuthKey(self):
		if len(self.authKeys) > 0:
			self.authKeys.pop()

class Database:
	@staticmethod
	def loadOrCreate(path):
		try:
			with open(path, 'rb') as f:
				db = pickle.load(f)
				return db
		except FileNotFoundError:
			return Database()

	def __init__(self):
		self.publishedOffers = dict()

	def putPublishedOffer(self, offerId, data):
		self.publishedOffers[offerId] = data

	def getOfferData(self, offerId):
		return self.publishedOffers[offerId]

	def getOrCreateOffer(self, offerId):
		data = self.publishedOffers.get(offerId)
		if data is None:
			data = PublishedMessage()
			self.publishedOffers[offerId] = data
		return data

	def deletePublishedOffer(self, offerId):
		del self.publishedOffers[offerId]

	def save(self, path):
		with open(path, 'wb') as f:
			pickle.dump(self, f)
