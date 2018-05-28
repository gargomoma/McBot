
import PIL.Image
import requests
import qrcode

class ImageBuilder:
	def __init__(self):
		self.imageCache = dict()

	def build(self, offer):
		productPicture = self._getOrFetch(offer.image)
		qrCode = qrcode.make(offer.code).resize((510, 510))
		image = PIL.Image.new('RGB', (1260, 510))
		image.paste(qrCode)
		image.paste(productPicture, (510, 0))
		return image

	def _getOrFetch(self, url):
		img = self.imageCache.get(url)

		if img is None:
			img = PIL.Image.open(requests.get(url, stream=True).raw)
			img = img.resize((750, 510), PIL.Image.BICUBIC)
			self.imageCache[url] = img

		return img
