
import pickle
import secrets
from collections import namedtuple

OfferDiff = namedtuple('OfferDiff', ('new', 'deleted'))

class PublishedMessage:
	def __init__(self, messageId=None, authKeys=None):
		self.messageId = messageId
		self.authKeys = authKeys or list()

	def addAuthKey(self, authKey=None):
		if authKey is None:
			authKey = secrets.token_hex(8)
		if len(self.authKeys) > 5:
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

	def diffOffers(self, current):
		new = current - self.publishedOffers.keys()
		deleted = self.publishedOffers.keys() - current
		return OfferDiff(new, deleted)

	def putPublishedOffer(self, offer, data):
		self.publishedOffers[offer] = data

	def getOfferData(self, offer):
		return self.publishedOffers[offer]

	def getOrCreateOffer(self, offer):
		data = self.publishedOffers.get(offer)
		if data is None:
			data = PublishedMessage()
			self.publishedOffers[offer] = data
		return data

	def deletePublishedOffer(self, offer):
		del self.publishedOffers[offer]

	def save(self, path):
		with open(path, 'wb') as f:
			pickle.dump(self, f)
