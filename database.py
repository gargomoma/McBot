
import pickle
from collections import namedtuple

OfferDiff = namedtuple('OfferDiff', ('new', 'deleted'))
PublishedMessage = namedtuple('PublishedMessage', ('chatId', 'messageId', 'imageId'))

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
		self.modified = False
		self.publishedOffers = dict()

	def diffOffers(self, current):
		new = current - self.publishedOffers.keys()
		deleted = self.publishedOffers.keys() - current
		return OfferDiff(new, deleted)

	def putPublishedOffer(self, offer, data):
		self.publishedOffers[offer] = data
		self.modified = True

	def deletePublishedOffer(self, offer):
		del self.publishedOffers[offer]
		self.modified = True

	def save(self, path):
		if self.modified:
			with open(path, 'wb') as f:
				pickle.dump(self, f)
			self.modified = False
