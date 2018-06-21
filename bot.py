#!/usr/bin/env python3

import argparse
import chevron
import dateutil.tz
import os
import requests
from database import Database
from database import PublishedMessage
from datetime import datetime
from imagebuilder import ImageBuilder
from mcdapi import ApiException
from mcdapi import OfferType
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
imageBuilder = ImageBuilder()

defaultDeadline = datetime.strptime(config['time']['defaultDeadline'], '%H:%M:%S').time()
print(defaultDeadline)

currentOffers = SimplifiedLoyaltyOfferFetcher(config['endpoints']['loyaltyOffers'], defaultDeadline).fetch()
currentOffers.update(SimplifiedCalendarOfferFetcher(config['endpoints']['calendarOffers']).fetch())

now = datetime.now(dateutil.tz.gettz(config['time']['timezone'])).replace(tzinfo=None)
currentOffers = OrderedSet(filter(lambda x: x.dateFrom <= now and x.dateTo >= now, currentOffers))

offerDiff = database.diffOffers(currentOffers)

for offer in offerDiff.new:
	imageId = os.urandom(16).hex()
	fileName = config['images']['folder'].format(id=imageId)
	imageBuilder.build(offer).save(fileName)
	imageUrl = config['images']['url'].format(id=imageId)

	price = '%.02f' % offer.price
	price = price.replace('.', strings['decimalSeparator'])

	offerText = chevron.render(strings['offer'], {
			'name': offer.name,
			'typeBronze': offer.type is OfferType.BRONZE,
			'typeSilver': offer.type is OfferType.SILVER,
			'typeGold': offer.type is OfferType.GOLD,
			'typeLoyalty': offer.type in (OfferType.BRONZE, OfferType.SILVER, OfferType.GOLD),
			'typeMcnific': offer.type is OfferType.MCNIFIC,
			'typeBlack': offer.type is OfferType.BLACK,
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
	})
	offerText = '[\u200B](%s)%s' % (imageUrl, offerText)

	data = {
		'chat_id': config['bot']['channel'],
		'text': offerText,
		'parse_mode': 'Markdown'
	}

	response = requests.post('https://api.telegram.org/bot%s/sendMessage' % config['bot']['token'], data=data).json()
	if response['ok']:
		publishedMessage = PublishedMessage(config['bot']['channel'], response['result']['message_id'], imageId)
		database.putPublishedOffer(offer, publishedMessage)

for offer in offerDiff.deleted:
	message = database.getOfferData(offer)

	data = {
		'chat_id': message.chatId,
		'message_id': message.messageId,
		'text': strings['offerExpired'],
		'parse_mode': 'Markdown'
	}

	response = requests.post('https://api.telegram.org/bot%s/editMessageText' % config['bot']['token'], data=data).json()
	if response['ok'] or response['description'] in ('Bad Request: message is not modified', 'Bad Request: message to edit not found'):
		try:
			os.unlink(config['images']['folder'].format(id=message.imageId))
		except:
			pass

		database.deletePublishedOffer(offer)

database.save(config['database'])
