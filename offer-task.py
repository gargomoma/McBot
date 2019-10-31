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
		calendarOffers = filter(lambda x: x[1].dateTo >= now, calendarOffers.items())

		currentOffers.update(calendarOffers)
	except ApiErrorException as e:
		if e.errorMessage != "KO (message was: Daily offer not found)":
			raise e

currentOffers = dict(filter(lambda x: 'prueba' not in x[1].name.lower(), currentOffers.items()))

if len(currentOffers) < config['minOfferCount']:
	sys.exit(0)

codeToId = dict()
offersById = dict()
for offer in currentOffers.values():
	publishedMessage = database.getOrCreateOffer(offer.id)
	authKey = secrets.token_hex(8)
	publishedMessage.addAuthKey(authKey)

	requiresAuth = offer.type == 1 and offer.level == 1
	offersById[offer.id] = {
		'type': offer.type,
		'name': offer.name,
		'image': offer.image,
		'authKeys': publishedMessage.authKeys,
		'requiresAuth': requiresAuth
	}

	codeToId[offer.normal.code] = str(offer.id)
	if offer.big:
		codeToId[offer.big.code] = str(offer.id)

with open(config['offerJson'], 'w') as f:
	json.dump({'codeToId': codeToId, 'offersById': offersById}, f)

isFirstMessage = True
for offer in currentOffers.values():
	publishedMessage = database.getOfferData(offer.id)

	# Only for calendar offers dates seems to matter.
	# Loyalty seem to be valid as long as they're listed in the API, even if expired.
	if offer.type != 7:
		inTime = True
	else:
		inTime = offer.dateFrom <= now

	def formatPrice(x):
		price = '%.02f' % x
		price = price.replace('.', strings['decimalSeparator'])
		return price

	chevronTags = {
		'name': offer.name,
		'typeBronze': offer.type == 1 and offer.level == 0,
		'typeSilver': offer.type == 1 and offer.level == 1,
		'typeGold': offer.type == 1 and offer.level == 2,
		'typeLoyalty': offer.type == 1 and offer.level in (0, 1, 2),
		'typeMcnific': offer.type == 7,
		'typeBlack': offer.type == 1 and offer.level == 3,
		'code': offer.normal.code,
		'mcAuto': offer.normal.mcAutoCode,
		'price': formatPrice(offer.normal.price),
		'fromDay': offer.dateFrom.day,
		'fromMonth': offer.dateFrom.month,
		'fromMonthName': strings['months'][offer.dateFrom.month - 1],
		'fromYear': offer.dateFrom.year,
		'toDay': offer.dateTo.day,
		'toMonth': offer.dateTo.month,
		'toMonthName': strings['months'][offer.dateTo.month - 1],
		'toYear': offer.dateTo.year,
		'isSingleDay': offer.dateFrom.date() == offer.dateTo.date(),
		'inTime': inTime
	}

	if offer.big is not None:
		chevronTags.update({
			'bigCode': offer.big.code,
			'bigMcAuto': offer.big.mcAutoCode,
			'bigPrice': formatPrice(offer.big.price)
		})
	else:
		chevronTags.update({
			'bigCode': None,
			'bigMcAuto': None,
			'bigPrice': None
		})

	offerText = chevron.render(strings['offer'], chevronTags)
	offerText = '[\u200B](%s)%s' % (offer.image, offerText)

	if offer.type == 1 and offer.level == 2 or not inTime:
		keyboardRows = []
	else:
		keyboardRows = [
			[
				{
					'text': chevron.render(strings['exchange']['normal'], chevronTags),
					'url': config['exchangeUrl'] % {'code': offer.normal.code, 'authKey': publishedMessage.getNewestAuthKey()}
				}
			]
		]

		if offer.big is not None:
			keyboardRows.append([
				{
					'text': chevron.render(strings['exchange']['big'], chevronTags),
					'url': config['exchangeUrl'] % {'code': offer.big.code, 'authKey': publishedMessage.getNewestAuthKey()}
				}
			])

	replyMarkup = {
		'inline_keyboard': keyboardRows
	}

	if publishedMessage.messageId is not None:
		if publishedMessage.text == offerText:
			print('Updating keyboard for %d: %s' % (offer.id, offer.name))
			data = {
				'chat_id': config['bot']['channel'],
				'message_id': publishedMessage.messageId,
				'reply_markup': replyMarkup
			}

			response = requests.post('https://api.telegram.org/bot%s/editMessageReplyMarkup' % config['bot']['token'], json=data).json()
		else:
			print('Updating text for %d: %s' % (offer.id, offer.name))
			data = {
				'chat_id': config['bot']['channel'],
				'message_id': publishedMessage.messageId,
				'text': offerText,
				'parse_mode': 'Markdown',
				'reply_markup': replyMarkup
			}

			response = requests.post('https://api.telegram.org/bot%s/editMessageText' % config['bot']['token'], json=data).json()

		if response['ok']:
			publishedMessage.text = offerText

		else:
			if response['description'] == 'Bad Request: message to edit not found':
				publishedMessage.messageId = None
			else:
				publishedMessage.popAuthKey()

	if publishedMessage.messageId is None:
		print('Publishing offer %d: %s' % (offer.id, offer.name))
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

for offerId in list(database.publishedOffers.keys() - currentOffers.keys()):
	message = database.getOfferData(offerId)
	print('Deleting offer %d' % (offerId))

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
