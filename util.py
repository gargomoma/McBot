
import os
import base64

def random_string(len):
	byteslen = ((len + 3) // 4) * 3
	return base64.urlsafe_b64encode(os.urandom(byteslen)).decode()[:len]
