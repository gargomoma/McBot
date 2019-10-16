#!/usr/bin/env python3

import argparse
import json
import os
import random
import requests
import sys
import secrets
import string
import time
from devinfo import DevInfoGenerator
from mcdapi import ApiErrorException
from mcdapi import RegisterUserFetcher
from mcdapi import UserData
from mcdapi import LoginData
from mcdapi import LoginUserFetcher
from ruamel import yaml
from unidecode import unidecode

def register_random_user(config, names):
	for i in range(config['register']['retries']):
		nameparts = [random.choice(names['given']), random.choice(names['last'])]
		if random.randint(0, 1) == 1:
			nameparts.append(random.choice(names['last']))

		namecasing = random.randint(0, 2)
		if namecasing == 0:
			nameparts = [name.upper() for name in nameparts]
		elif namecasing == 1:
			nameparts = [name.lower() for name in nameparts]
		else:
			nameparts = [name.capitalize() for name in nameparts]
		name = ' '.join(nameparts)

		mailparts = [unidecode(x[:random.randint(3, 6)]).lower() for x in nameparts]
		random.shuffle(mailparts)
		mailparts = mailparts[:2]

		mailparts.append(str(random.randint(1, 9999)))
		mail = ''.join(mailparts) + '@' + random.choice(names['mailHosts'])

		password = ''.join([random.choice(string.ascii_letters) for i in range(random.randint(6, 10))])

		birthDate = '%04i-%02d' % (random.randint(1960, 2002), random.randint(1, 12))

		userData = UserData(name=name, email=mail, password=password, phone=None, birthDate=birthDate)
		print('Trying ' + str(userData))

		fetcher = RegisterUserFetcher(endpoint=config['endpoints']['register'], userData=userData, proxy=config.get('proxy'), cert=config.get('cert'))
		try:
			response = fetcher.fetch()
		except ApiErrorException as e:
			if e.errorCode // 100 == 8:
				continue
			raise e

		return userData
	return None

parser = argparse.ArgumentParser(description='Registers McDonalds accounts')
parser.add_argument('config', help='YAML configuration', type=argparse.FileType('r'))
args = parser.parse_args()

config = yaml.safe_load(args.config)
with open(config['names']) as f:
	names = yaml.safe_load(f)

authInfo = list()

proxy = config.get('proxy')
if proxy is not None:
	proxy = {
		'http': proxy,
		'https': proxy
	}

def rndb64(length):
	bytecount = (length * 4 + 2) // 3
	token = secrets.token_urlsafe(bytecount)
	return token[:length]

for i in range(config['register']['retries']):
	devInfo = DevInfoGenerator().random()

	params = {
		'udid': devInfo['udid'],
		'token': rndb64(11) + ':' + rndb64(140),
		'appId': '3976',
		'language': 'ES',
		'brand': devInfo['device'],
		'model': devInfo['model'],
		'deviceOS': 'ANDROID',
		'deviceOSVersion': devInfo['version'],
		'appVersion': devInfo['appVersion'],
		'latitude': random.uniform(38, 43),
		'longitude': random.uniform(-6.64, -1.04),
		'country': 'ES',
		'isTablet': '0',
		'SDKVersion': devInfo['SDKVersion'],
		'userIdGA': '',
		'userDoc': ''
	}
	response = requests.get('https://api3.mo2o.com/appPushNotifications/register-device.php', params=params, proxies=proxy)
	if not 'OK' in response.text:
		print('Device register failed: ' + response.text)
		time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))
		continue

	response = requests.post(config['endpoints']['metrics'], json=devInfo, proxies=proxy)
	if not 'OK' in response.text:
		print('Metrics response failed: ' + response.text)

	userData = register_random_user(config, names)
	if userData is None:
		print('Could not register any user!', file=sys.stderr)
		time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))
		continue

	loginData = LoginData(deviceId=devInfo['udid'], email=userData.email, password=userData.password)
	fetcher = LoginUserFetcher(endpoint=config['endpoints']['login'], loginData=loginData, proxy=config.get('proxy'), cert=config.get('cert'))
	print(fetcher.fetch())

	authInfo.append({'email': userData.email, 'dev': devInfo, 'cookies': fetcher.session.cookies.get_dict()})
	if len(authInfo) == config['register']['max']:
		break

	time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))

if len(authInfo) == 0:
	print('Failed to register any user!', file=sys.stderr)
	sys.exit(1)

with open(config['output'], 'w') as f:
	json.dump(authInfo, f)
