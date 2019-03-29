
import requests
import secrets
from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from orderedset import OrderedSet

Offer = namedtuple('Offer', ('id', 'name', 'type', 'level', 'big', 'code', 'mcAutoCode', 'price', 'image', 'dateFrom', 'dateTo'))

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
	def __init__(self, endpoint, proxy=None):
		self.endpoint = endpoint
		self.session = requests.Session()
		self.session.headers.update({'accept': 'application/json'})
		if proxy is not None:
			self.session.proxies = {
					'http': proxy,
					'https': proxy
			}

	def fetch(self):
		try:
			response = self._run()
		except Exception as e:
			raise ApiException('Cannot fetch from endpoint') from e

		try:
			response = response.json()
		except Exception as e:
			raise ApiException('Unable to parse JSON: ' + response.text) from e

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

	def _run(self):
		request = {
			'deviceId': secrets.token_hex(16),
		}
		return self.session.post(self.endpoint, json=request)

	def _processOffer(self, processed, offer, dateFrom, dateTo):
		processed.add(Offer(
				id=offer['id'],
				name=offer['name'].strip(),
				type=offer['offerType'],
				level=offer.get('offerLevel'),
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
					id=offer['id'],
					name=offer['name'].strip(),
					type=offer['offerType'],
					level=offer.get('offerLevel'),
					big=True,
					code=offer['bigQrCode'],
					mcAutoCode=offer['bigCheckoutCode'],
					price=float(offer['bigPrice']),
					image=offer['imageDetail'],
					dateFrom=dateFrom,
					dateTo=dateTo
			))

class SimplifiedLoyaltyOfferFetcher(SimplifiedOfferFetcher):
	END_OF_DAY = timedelta(days=1, seconds=-1)

	def _processResponse(self, response):
		processed = OrderedSet()

		for offer in response['offers']:
			dateFrom = self._parseDate(offer['dateFrom'])
			dateTo = self._parseDate(offer['dateTo'], True)
			self._processOffer(processed, offer, dateFrom, dateTo)

		return processed

	def _parseDate(self, date, isEnd=False):
		date = datetime.strptime(date, '%d/%m/%Y')
		if isEnd:
			date = date + SimplifiedLoyaltyOfferFetcher.END_OF_DAY
		return date

class SimplifiedCalendarOfferFetcher(SimplifiedOfferFetcher):
	def _processResponse(self, response):
		processed = OrderedSet()

		for promotion in response['offersPromotion']:
			dateFrom = self._parseTimestamp(promotion['dateFromOffer'])
			dateTo = self._parseTimestamp(promotion['dateToOffer'])

			self._processOffer(processed, promotion['offer'], dateFrom, dateTo)

		return processed

	def _parseTimestamp(self, time):
		return datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
