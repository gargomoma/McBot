
import requests
from collections import namedtuple
from datetime import datetime

LoyaltyOffer = namedtuple('LoyaltyOffer', ('name', 'big', 'code', 'mcAutoCode', 'price', 'image', 'dateFrom', 'dateTo'))

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
	def _processOffer(self, processed, offer):
		processed.add(LoyaltyOffer(
				name=offer['name'].strip(),
				big=False,
				code=offer['qrCode'],
				mcAutoCode=offer['checkoutCode'],
				price=float(offer['price']),
				image=offer['imageDetail'],
				dateFrom=self._parseDate(offer['dateFrom']),
				dateTo=self._parseDate(offer['dateTo'])
		))

		if 'bigQrCode' in offer:
			processed.add(LoyaltyOffer(
					name=offer['name'].strip(),
					big=True,
					code=offer['bigQrCode'],
					mcAutoCode=offer['bigCheckoutCode'],
					price=float(offer['bigPrice']),
					image=offer['imageDetail'],
					dateFrom=self._parseDate(offer['dateFrom']),
					dateTo=self._parseDate(offer['dateTo'])
			))

	def _parseDate(self, date):
		return datetime.strptime(date, '%d/%m/%Y').date()

class SimplifiedLoyaltyOfferFetcher(SimplifiedOfferFetcher):
	def _processResponse(self, response):
		processed = set()

		for offer in response['offers']:
			self._processOffer(processed, offer)

		return processed

class SimplifiedCalendarOfferFetcher(SimplifiedOfferFetcher):
	def _processResponse(self, response):
		processed = set()

		for promotion in response['offersPromotion']:
			self._processOffer(processed, promotion['offer'])

		return processed
