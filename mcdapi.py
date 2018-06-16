
import requests
from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from enum import Enum

Offer = namedtuple('Offer', ('name', 'type', 'big', 'code', 'mcAutoCode', 'price', 'image', 'dateFrom', 'dateTo'))

class OfferType(Enum):
	BRONZE = 1
	SILVER = 2
	GOLD = 3
	MCNIFIC = 4
	BLACK = 5

	@staticmethod
	def fromInts(type, level=None):
		if type == 1:
			if level == 0:
				return OfferType.BRONZE
			if level == 1:
				return OfferType.SILVER
			if level == 2:
				return OfferType.GOLD
			if level == 3:
				return OfferType.BLACK
		elif type == 7:
			return OfferType.MCNIFIC

		raise ValueError()

class ApiException(Exception):
	pass

class ApiErrorException(ApiException):
	def __init__(self, errorCode, errorMessage):
		super().__init__('API replied with an error (code: %s, message: %s)' % (errorCode, errorMessage))
		self.errorCode = errorCode
		self.errorMessage = errorMessage

class InvalidJsonResponse(ApiException):
	def __init__(self, json, msg=None):
		if msg is None:
			super().__init__('API replied with non-standard JSON (%s)' % repr(json))
		else:
			super().__init__(msg)

		self.json = json

class Fetcher:
	def __init__(self, endpoint):
		self.endpoint = endpoint
		self.session = requests.Session()
		self.session.headers.update({'accept': 'application/json'})

	def fetch(self):
		try:
			response = self.session.get(self.endpoint)
		except Exception as e:
			raise ApiException('Cannot fetch from endpoint') from e

		try:
			response = response.json()
		except Exception as e:
			raise ApiException('Unable to parse JSON') from e

		try:
			if response['code'] != 100 or response['msg'] != 'OK':
				raise ApiErrorException(response['code'], response['msg'])

			response = response['response']
		except KeyError as e:
			raise InvalidJsonResponse(response) from e

		try:
			return self._processResponse(response)
		except Exception as e:
			raise InvalidJsonResponse(response) from e

	def _processResponse(self, response):
		raise NotImplementedError()

class SimplifiedOfferFetcher(Fetcher):

	def _processOffer(self, processed, offer, dateFrom, dateTo):
		try:
			type = OfferType.fromInts(offer['offerType'], offer.get('offerLevel'))
		except ValueError:
			return

		processed.add(Offer(
				name=offer['name'].strip(),
				type=type,
				big=False,
				code=offer['qrCode'],
				mcAutoCode=offer['checkoutCode'],
				price=float(offer['price']),
				image=offer['imageDetail'],
				dateFrom=dateFrom,
				dateTo=dateTo
		))

		if 'bigQrCode' in offer:
			processed.add(Offer(
					name=offer['name'].strip(),
					type=type,
					big=True,
					code=offer['bigQrCode'],
					mcAutoCode=offer['bigCheckoutCode'],
					price=float(offer['bigPrice']),
					image=offer['imageDetail'],
					dateFrom=dateFrom,
					dateTo=dateTo
			))

class SimplifiedLoyaltyOfferFetcher(SimplifiedOfferFetcher):
	SECOND_TD = timedelta(seconds=1)

	def __init__(self, endpoint, deadlineTime):
		super().__init__(endpoint)
		self.deadlineTime = deadlineTime

	def _processResponse(self, response):
		processed = set()

		for offer in response['offers']:
			dateFrom = self._parseDate(offer['dateFrom'])
			dateTo = self._parseDate(offer['dateTo'], True)
			self._processOffer(processed, offer, dateFrom, dateTo)

		return processed

	def _parseDate(self, date, isEnd=False):
		date = datetime.strptime(date, '%d/%m/%Y').date()
		time = datetime.combine(date, self.deadlineTime)
		if isEnd:
			time = time - SimplifiedLoyaltyOfferFetcher.SECOND_TD
		return time

class SimplifiedCalendarOfferFetcher(SimplifiedOfferFetcher):
	def _processResponse(self, response):
		processed = set()

		for promotion in response['offersPromotion']:
			dateFrom = self._parseTimestamp(promotion['dateFromOffer'])
			dateTo = self._parseTimestamp(promotion['dateToOffer'])

			self._processOffer(processed, promotion['offer'], dateFrom, dateTo)

		return processed

	def _parseTimestamp(self, time):
		return datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
