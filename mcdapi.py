
import requests
import secrets
from collections import namedtuple
from datetime import datetime
from datetime import timedelta

Offer = namedtuple('Offer', ('id', 'name', 'type', 'level', 'image', 'dateFrom', 'dateTo', 'normal', 'big'))
OfferVariant = namedtuple('OfferVariant', ('code', 'mcAutoCode', 'price'))
UserData = namedtuple('UserData', ('name', 'email', 'password', 'phone', 'birthDate'))
LoginData = namedtuple('LoginData', ('deviceId', 'email', 'password'))

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
	def __init__(self, endpoint, proxy=None, cert=None):
		self.endpoint = endpoint
		self.session = requests.Session()
		self.session.headers.update({'Accept': 'application/json', 'User-Agent': 'okhttp/3.9.0'})
		if proxy is not None:
			self.session.proxies = {
					'http': proxy,
					'https': proxy
			}
		if cert is not None:
			self.session.cert = (cert['public'], cert['private'])

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
		return response

class SimplifiedOfferFetcher(Fetcher):

	def __init__(self, *args, **kwargs):
		if 'deviceId' in kwargs:
			self.deviceId = kwargs.pop('deviceId')
		else:
			self.deviceId = secrets.token_hex(8)

		super().__init__(*args, **kwargs)

	def _run(self):
		request = {
			'deviceId': self.deviceId
		}
		return self.session.post(self.endpoint, json=request)

	def _processOffer(self, offer, dateFrom, dateTo):
		normal = OfferVariant(
				code=offer['qrCode'],
				mcAutoCode=offer['checkoutCode'],
				price=float(offer['price'])
		)

		if offer.get('bigQrCode') != None:
			big = OfferVariant(
				code=offer['bigQrCode'],
				mcAutoCode=offer['bigCheckoutCode'],
				price=float(offer['bigPrice'])
			)
		else:
			big = None

		return Offer(
			id=int(offer['id']),
			name=offer['name'].strip(),
			type=offer['offerType'],
			level=offer.get('offerLevel'),
			image=offer['imageDetail'],
			dateFrom=dateFrom,
			dateTo=dateTo,
			normal=normal,
			big=big
		)

class SimplifiedLoyaltyOfferFetcher(SimplifiedOfferFetcher):
	END_OF_DAY = timedelta(days=1, seconds=-1)

	def _processResponse(self, response):
		processed = dict()

		for offer in response['offers']:
			dateFrom = self._parseDate(offer['dateFrom'])
			dateTo = self._parseDate(offer['dateTo'], True)
			offer = self._processOffer(offer, dateFrom, dateTo)
			processed[offer.id] = offer

		return processed

	def _parseDate(self, date, isEnd=False):
		date = datetime.strptime(date, '%d/%m/%Y')
		if isEnd:
			date = date + SimplifiedLoyaltyOfferFetcher.END_OF_DAY
		return date

class SimplifiedCalendarOfferFetcher(SimplifiedOfferFetcher):
	def _processResponse(self, response):
		processed = dict()

		for promotion in response['offersPromotion']:
			dateFrom = self._parseTimestamp(promotion['dateFromOffer'])
			dateTo = self._parseTimestamp(promotion['dateToOffer'])
			offer = self._processOffer(promotion['offer'], dateFrom, dateTo)
			processed[offer.id] = offer

		return processed

	def _parseTimestamp(self, time):
		return datetime.strptime(time, '%Y-%m-%d %H:%M:%S')

class RegisterUserFetcher(Fetcher):
	def __init__(self, endpoint, userData, proxy=None, cert=None):
		super().__init__(endpoint=endpoint, proxy=proxy, cert=cert)
		self.userData = userData

	def _run(self):
		request = {
			"birthdate": self.userData.birthDate,
			"email": self.userData.email,
			"name": self.userData.name,
			"password": self.userData.password,
			"receiveEmail": False,
			"restaurants": []
		}
		return self.session.post(self.endpoint, json=request)

class LoginUserFetcher(Fetcher):
	def __init__(self, endpoint, loginData, proxy=None, cert=None):
		super().__init__(endpoint=endpoint, proxy=proxy, cert=cert)
		self.loginData = loginData

	def _run(self):
		request = {
			'deviceId': self.loginData.deviceId,
			'email': self.loginData.email,
			'password': self.loginData.password,
			'socialId': None,
			'socialToken': None,
			'socialType': None
		}
		return self.session.post(self.endpoint, json=request)
