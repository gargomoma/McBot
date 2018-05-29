#!/usr/bin/env python3

import argparse
import telegram.utils.request
import os
from database import Database, PublishedMessage
from mcdapi import ApiException, SimplifiedLoyaltyOfferFetcher
from imagebuilder import ImageBuilder
from ruamel import yaml
from telegram import Bot, ParseMode

parser = argparse.ArgumentParser(description='Updates McDonalds offers')
parser.add_argument('config', help='YAML configuration', type=argparse.FileType('r'))
args = parser.parse_args()

config = yaml.safe_load(args.config)
with open(config['strings']) as f:
	strings = yaml.safe_load(f)

bot = Bot(token=config['bot']['token'], request=telegram.utils.request.Request(8))
database = Database.loadOrCreate(config['database'])
imageBuilder = ImageBuilder()

currentOffers = SimplifiedLoyaltyOfferFetcher(config['endpoints']['loyaltyOffers']).fetch()
offerDiff = database.diffOffers(currentOffers)

for offer in offerDiff.new:
	imageId = os.urandom(16).hex()
	fileName = config['images']['folder'].format(id=imageId)
	imageBuilder.build(offer).save(fileName)
	imageUrl = config['images']['url'].format(id=imageId)

	productName = offer.name
	if offer.big:
		productName = strings['big'].format(name=productName)

	price = '%.02f' % offer.price
	price = price.replace('.', strings['decimalSeparator'])

	offerText = strings['offer'].format(
			name=productName,
			code=offer.code,
			mcAutoCode=offer.mcAutoCode,
			price=price,
			fromDay=offer.dateFrom.day,
			fromMonth=offer.dateFrom.month,
			fromMonthName=strings['months'][offer.dateFrom.month],
			fromYear=offer.dateFrom.year,
			toDay=offer.dateTo.day,
			toMonth=offer.dateTo.month,
			toMonthName=strings['months'][offer.dateTo.month],
			toYear=offer.dateTo.year
	)
	offerText = '[\u200B](%s)%s' % (imageUrl, offerText)

	response = bot.sendMessage(config['bot']['channel'], offerText, ParseMode.MARKDOWN)
	publishedMessage = PublishedMessage(config['bot']['channel'], response['message_id'], imageId)
	database.putPublishedOffer(offer, publishedMessage)

database.save(config['database'])
