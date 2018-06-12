
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
			img = self._coverResize(img, (750, 510))
			self.imageCache[url] = img

		return img

	def _coverResize(self, image, target, resample=PIL.Image.BICUBIC):
		imageSize = image.size
		imageRatio = imageSize[0] / imageSize[1]
		targetRatio = target[0] / target[1]

		# Image is taller than it should
		if imageRatio < targetRatio:
			croppedHeight = imageSize[0] / targetRatio
			box = (0, imageSize[1] / 2 - croppedHeight / 2, imageSize[0], imageSize[1] / 2 + croppedHeight / 2)

		# Image is wider than it should
		else:
			croppedWidth = imageSize[1] * targetRatio
			box = (imageSize[0] / 2 - croppedWidth / 2, 0, imageSize[0] / 2 + croppedWidth / 2, imageSize[1])

		return image.resize(target, resample=resample, box=box)
