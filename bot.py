
import argparse
import telegram.utils.request
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
fetcher = SimplifiedLoyaltyOfferFetcher(config['endpoints']['loyaltyOffers'])
imageBuilder = ImageBuilder()

pos = 0
for offer in fetcher.fetch():
	fileName = config['images']['folder'].format(file=str(pos))
	imageBuilder.build(offer).save(fileName)

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
	print(offerText)
	pos = pos + 1

	#bot.sendMessage(-1001294091205, '[\u200B](https://xn--6o8h.cf/bitmap4.jpg)This is just a test', ParseMode.MARKDOWN)


