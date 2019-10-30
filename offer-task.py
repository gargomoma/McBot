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
from mcdapi import ApiErrorException
from mcdapi import SimplifiedLoyaltyOfferFetcher
from mcdapi import SimplifiedCalendarOfferFetcher
from orderedset import OrderedSet
from ruamel import yaml

parser = argparse.ArgumentParser(description='Updates McDonalds offers')
parser.add_argument('config', help='YAML configuration', type=argparse.FileType('r'))
args = parser.parse_args()

config = yaml.safe_load(args.config)
with open(config['strings']) as f:
	strings = yaml.safe_load(f)

database = Database.loadOrCreate(config['database'])
now = datetime.now(dateutil.tz.gettz(config['time']['timezone'])).replace(tzinfo=None)

print('Fetching loyalty offers')
currentOffers = SimplifiedLoyaltyOfferFetcher(config['endpoints']['loyaltyOffers'], proxy=config.get('proxy'), cert=config.get('cert')).fetch()

for endpoint in ('dailyOffer', 'calendarOffers'):
	print('Fetching %s' % endpoint)
	try:
		calendarOffers = SimplifiedCalendarOfferFetcher(config['endpoints'][endpoint], config.get('proxy'), cert=config.get('cert')).fetch()
		calendarOffers = filter(lambda x: x.dateTo >= now, calendarOffers)

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
	authKey = secrets.token_hex(8)
	publishedMessage.addAuthKey(authKey)

	requiresAuth = offer.type == 1
	offersByCode[offer.code] = {
		'id': offer.id,
		'type': offer.type,
		'name': offer.name,
		'image': offer.image,
		'authKeys': publishedMessage.authKeys,
		'requiresAuth': requiresAuth
	}

with open(config['offerJson'], 'w') as f:
	json.dump(offersByCode, f)

isFirstMessage = True
for offer in currentOffers:
	publishedMessage = database.getOfferData(offer)

	# Only for calendar offers dates seems to matter.
	# Loyalty seem to be valid as long as they're listed in the API, even if expired.
	if offer.type != 7:
		inTime = True
	else:
		inTime = offer.dateFrom <= now

	if offer.type == 1 and offer.level == 2 or not inTime:
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

	if publishedMessage.messageId is not None:
		print('Updating offer %d: %s' % (offer.id, offer.name))
		data = {
			'chat_id': config['bot']['channel'],
			'message_id': publishedMessage.messageId,
			'reply_markup': replyMarkup
		}

		response = requests.post('https://api.telegram.org/bot%s/editMessageReplyMarkup' % config['bot']['token'], json=data).json()
		if not response['ok']:
			if response['description'] == 'Bad Request: message to edit not found':
				publishedMessage.messageId = None
			else:
				publishedMessage.popAuthKey()

	if publishedMessage.messageId is None:
		print('Publishing offer %d: %s' % (offer.id, offer.name))
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
				'toYear': offer.dateTo.year,
				'isSingleDay': offer.dateFrom.date() == offer.dateTo.date()
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

for offer in list(database.publishedOffers.keys() - currentOffers):
	message = database.getOfferData(offer)
	print('Deleting offer %d: %s' % (offer.id, offer.name))

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
