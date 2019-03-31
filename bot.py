#!/usr/bin/env python3

import argparse
import chevron
import csv
import dateutil.tz
import json
import os
import random
import requests
import sys
import secrets
import string
import time
from database import Database
from database import PublishedMessage
from datetime import datetime
from devinfo import DevInfoGenerator
from mcdapi import ApiException
from mcdapi import ApiErrorException
from mcdapi import SimplifiedLoyaltyOfferFetcher
from mcdapi import SimplifiedCalendarOfferFetcher
from mcdapi import RegisterUserFetcher
from mcdapi import UserData
from orderedset import OrderedSet
from ruamel import yaml
from unidecode import unidecode
from util import random_string

def register_random_user(config, strings):
	for i in range(config['register']['retries']):
		nameparts = [random.choice(strings['names']['given']), random.choice(strings['names']['last'])]
		if random.randint(0, 1) == 1:
			nameparts.append(random.choice(strings['names']['last']))

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
		mail = random.choice(['.', '', '']).join(mailparts) + '@' + random.choice(strings['mailHosts'])

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

parser = argparse.ArgumentParser(description='Updates McDonalds offers')
parser.add_argument('config', help='YAML configuration', type=argparse.FileType('r'))
args = parser.parse_args()

config = yaml.safe_load(args.config)
with open(config['strings']) as f:
	strings = yaml.safe_load(f)

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

	userData = register_random_user(config, strings)
	if userData is None:
		print('Could not register any user!', file=sys.stderr)
		time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))
		continue

	authInfo.append({'email': userData.email, 'deviceId': devInfo['udid']})
	if len(authInfo) == config['register']['max']:
		break

	time.sleep(random.randint(config['register']['delay']['min'], config['register']['delay']['max']))

database = Database.loadOrCreate(config['database'])

currentOffers = SimplifiedLoyaltyOfferFetcher(config['endpoints']['loyaltyOffers'], config.get('proxy')).fetch()

try:
	calendarOffers = SimplifiedCalendarOfferFetcher(config['endpoints']['calendarOffers'], config.get('proxy')).fetch()

	now = datetime.now(dateutil.tz.gettz(config['time']['timezone'])).replace(tzinfo=None)
	calendarOffers = filter(lambda x: x.dateFrom <= now and x.dateTo >= now, calendarOffers)

	currentOffers.update(calendarOffers)
except ApiErrorException as e:
	if e.errorMessage != "KO (message was: Daily offer not found)":
		raise e

currentOffers = OrderedSet(filter(lambda x: 'prueba' not in x.name.lower(), currentOffers))

if len(currentOffers) < config['minOfferCount']:
	sys.exit(0)

offersByCode = dict()
for offer in currentOffers:
	publishedMessage = database.getOrCreateOffer(offer)
	authKey = random_string(8)
	publishedMessage.addAuthKey(authKey)

	requiresAuth = offer.type == 1 and offer.level in (1, 2)
	offersByCode[offer.code] = {
		'id': offer.id,
		'type': offer.type,
		'name': offer.name,
		'image': offer.image,
		'authKeys': publishedMessage.authKeys,
		'requiresAuth': requiresAuth
	}

with open(config['offerJson'], 'w') as f:
	jsoninfo = {
		'offers': offersByCode,
		'auth': authInfo
	}
	json.dump(jsoninfo, f)

isFirstMessage = True
for offer in currentOffers:
	publishedMessage = database.getOfferData(offer)

	if offer.type == 1 and offer.level == 2:
		replyMarkup = {
			'inline_keyboard': []
		}
	else:
		replyMarkup = {
			'inline_keyboard': [
				[
					{
						'text': strings['exchangeText'],
						'url': config['exchangeUrl'] % {'code': offer.code, 'authKey': publishedMessage.getNewestAuthKey()}
					}
				]
			]
		}

	if publishedMessage.messageId is None:
		price = '%.02f' % offer.price
		price = price.replace('.', strings['decimalSeparator'])

		offerText = chevron.render(strings['offer'], {
				'name': offer.name,
				'typeBronze': offer.type == 1 and offer.level == 0,
				'typeSilver': offer.type == 1 and offer.level == 1,
				'typeGold': offer.type == 1 and offer.level == 2,
				'typeLoyalty': offer.type == 1 and offer.level in (0, 1, 2),
				'typeMcnific': offer.type == 7,
				'typeBlack': offer.type == 1 and offer.level == 3,
				'big': offer.big,
				'code': offer.code,
				'mcAutoCode': offer.mcAutoCode,
				'price': price,
				'fromDay': offer.dateFrom.day,
				'fromMonth': offer.dateFrom.month,
				'fromMonthName': strings['months'][offer.dateFrom.month - 1],
				'fromYear': offer.dateFrom.year,
				'toDay': offer.dateTo.day,
				'toMonth': offer.dateTo.month,
				'toMonthName': strings['months'][offer.dateTo.month - 1],
				'toYear': offer.dateTo.year
		})
		offerText = '[\u200B](%s)%s' % (offer.image, offerText)

		data = {
			'chat_id': config['bot']['channel'],
			'text': offerText,
			'parse_mode': 'Markdown',
			'disable_notification': not isFirstMessage,
			'reply_markup': replyMarkup
		}

		response = requests.post('https://api.telegram.org/bot%s/sendMessage' % config['bot']['token'], json=data).json()
		if response['ok']:
			publishedMessage.messageId = response['result']['message_id']
		else:
			publishedMessage.popAuthKey()

		isFirstMessage = False
	else:
		data = {
			'chat_id': config['bot']['channel'],
			'message_id': publishedMessage.messageId,
			'reply_markup': replyMarkup
		}

		response = requests.post('https://api.telegram.org/bot%s/editMessageReplyMarkup' % config['bot']['token'], json=data).json()
		if not response['ok']:
			publishedMessage.popAuthKey()

for offer in list(database.publishedOffers.keys() - currentOffers):
	message = database.getOfferData(offer)

	data = {
		'chat_id': config['bot']['channel'],
		'message_id': message.messageId
	}
	response = requests.post('https://api.telegram.org/bot%s/deleteMessage' % config['bot']['token'], json=data).json()
	deleted = response['ok']

	if not deleted:
		data = {
			'chat_id': config['bot']['channel'],
			'message_id': message.messageId,
			'text': strings['offerExpired'],
			'parse_mode': 'Markdown'
		}

		response = requests.post('https://api.telegram.org/bot%s/editMessageText' % config['bot']['token'], json=data).json()
		deleted = response['ok'] or response['description'] in ('Bad Request: message is not modified', 'Bad Request: message to edit not found')

	if deleted:
		database.deletePublishedOffer(offer)

database.save(config['database'])

if 'userCountFile' in config:
	params = {
		'chat_id': config['bot']['channel']
	}
	response = requests.get('https://api.telegram.org/bot%s/getChatMembersCount' % config['bot']['token'], params=params).json()
	if response['ok']:
		with open(config['userCountFile'], 'a+', newline='') as f:
			now = datetime.utcnow().isoformat() + 'Z'
			writer = csv.writer(f)
			writer.writerow([now, response['result']])
