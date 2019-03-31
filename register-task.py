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

		mailparts = [unidecode(x[:random.randint(5, 8)]).lower() for x in nameparts]
		random.shuffle(mailparts)
		mailparts = mailparts[:2]

		mailparts.append(str(random.randint(1, 9999)))
		mail = random.choice(['.', '', '']).join(mailparts) + '@' + random.choice(names['mailHosts'])

		password = ''.join([random.choice(string.ascii_letters) for i in range(random.randint(6, 10))])

		phone = random.choice(('6', '7')) + str(random.randint(0, 99999999)).zfill(8)

		userData = UserData(name=name, email=mail, password=password, phone=phone)
		print('Trying ' + str(userData))

		fetcher = RegisterUserFetcher(endpoint=config['endpoints']['register'], userData=userData, proxy=config.get('proxy'))
		try:
			response = fetcher.fetch()
		except ApiErrorException as e:
			if e.errorCode == 800:
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

for i in range(config['register']['retries']):
	devInfo = DevInfoGenerator().random()

	response = requests.post(config['endpoints']['metrics'], json=devInfo, proxies=proxy)
	if not 'OK' in response.text:
		print('Metrics response failed: ' + response.text)
		time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))
		continue

	userData = register_random_user(config, names)
	if userData is None:
		print('Could not register any user!', file=sys.stderr)
		time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))
		continue

	authInfo.append({'email': userData.email, 'deviceId': devInfo['udid']})
	if len(authInfo) == config['register']['max']:
		break

	time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))

if len(authInfo) == 0:
	print('Failed to register any user!', file=sys.stderr)
	sys.exit(1)

with open(config['output'], 'w') as f:
	json.dump(authInfo, f)
