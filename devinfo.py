
from datetime import datetime, timezone
import random as random_class
import secrets
import string

class DevInfoGenerator:
	MANUFACTURERS = [
		'Samsung',
		'Apple',
		'Huawei',
		'Nokia',
		'Sony',
		'LG',
		'HTC',
		'Motorola',
		'Acer',
		'bq',
		'BIRD',
		'BlackBerry',
		'Dell',
		'Coolpad',
		'Google',
		'Honor',
		'Kyocera',
		'Karbonn'
	];

	RESOLUTIONS = [
		(1280, 720),
		(1920, 1080),
		(800, 480),
		(854, 480),
		(960, 540),
		(1024, 600),
		(1280, 800),
		(2560, 1440)
	];

	API_VERSION = [
		'5.0 (21)',
		'5.0.1 (21)',
		'5.0.2 (21)',
		'5.1 (22)',
		'5.1.1 (22)',
		'6.0 (23)',
		'6.0.1 (23)',
		'7.0 (24)',
		'7.1 (25)',
		'7.1.1 (25)',
		'7.1.2 (25)',
		'8.0 (26)',
		'8.1 (27)'
	];

	def __init__(self, sdkVersion=None, appVersion=None):
		self.sdkVersion = sdkVersion
		self.appVersion = appVersion

	def random(self):
		model = random_class.choice(string.ascii_uppercase)
		if random_class.randint(0, 3) == 0:
			model += random_class.choice(string.ascii_uppercase)
		model += random_class.choice(string.digits)

		now = datetime.utcnow().replace(tzinfo=timezone.utc,microsecond=0).isoformat()
		resolution = random_class.choice(self.RESOLUTIONS)

		return {
			'SDKVersion': self.sdkVersion or '6.1.10',
			'appVersion': self.appVersion or '6.5.1',
			'dateTime': now,
			'device': random_class.choice(self.MANUFACTURERS),
			'id': '3976',
			'installReferrer': '',
			'isFirstRun': '1',
			'language': 'ES',
			'mcc': '214',
			'mnc': '%02i' % random_class.randint(1, 9),
			'model': model,
			'notificationId': '',
			'pixelHeight': resolution[0],
			'pixelWidth': resolution[1],
			'runningSecs': 0,
			'status': 'start',
			'udid': secrets.token_hex(8),
			'userDoc': '',
			'userIdGA': '',
			'version': random_class.choice(self.API_VERSION)
		}
