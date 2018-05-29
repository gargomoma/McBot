
import pickle
from collections import namedtuple

OfferDiff = namedtuple('OfferDiff', ('new', 'deleted'))
PublishedMessageV1 = namedtuple('PublishedMessageV1', ('chatId', 'messageId'))

class Database:
	@staticmethod
	def loadOrCreate(path):
		try:
			with open(path, 'rb') as f:
				db = pickle.load(f)
				return db.upgrade()
		except FileNotFoundError:
			return DatabaseV1()

	def __init__(self):
		self.modified = False

	def save(self, path):
		if self.modified:
			with open(path, 'wb') as f:
				pickle.dump(self, f)
			self.modified = False

	def upgrade(self):
		raise NotImplementedError()
		
class DatabaseV1(Database):
	def __init__(self):
		super().__init__()

		self.imageId = 0
		self.publishedOffers = dict()

	def nextImageId(self):
		self.imageId += 1
		self.modified = True
		return str(self.imageId)

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

	def upgrade(self):
		return self
