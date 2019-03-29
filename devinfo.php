<?php

function devinfo_random() {
	$manufacturers = [
		'Samsung',
		'Apple',
		'Huawei',
		'Nokia',
		'Sony',
		'LG',
		'HTC',
		'Motorola',
		'Acer',
		'bq',
		'BIRD',
		'BlackBerry',
		'Dell',
		'Coolpad',
		'Google',
		'Honor',
		'Kyocera',
		'Karbonn'
	];

	$resolutions = [
		[1280, 720],
		[1920, 1080],
		[800, 480],
		[854, 480],
		[960, 540],
		[1024, 600],
		[1280, 800],
		[2560, 1440]
	];

	$apis = [
		'5.0 (21)',
		'5.0.1 (21)',
		'5.0.2 (21)',
		'5.1 (22)',
		'5.1.1 (22)',
		'6.0 (23)',
		'6.0.1 (23)',
		'7.0 (24)',
		'7.1 (25)',
		'7.1.1 (25)',
		'7.1.2 (25)',
		'8.0 (26)',
		'8.1 (27)'
	];

	$resolution = $resolutions[mt_rand(0, count($resolutions) - 1)];

	$model = chr(mt_rand(0x41, 0x5A));
	if (mt_rand(0, 5) <= 1) {
		$model .= chr(mt_rand(0x41, 0x5A));
	}
	$model .= mt_rand(1, 9);

	return array(
		'SDKVersion' => '6.1.10',
		'appVersion' => '6.5.1',
		'dateTime' => date('c'),
		'device' => $manufacturers[mt_rand(0, count($manufacturers) - 1)],
		'id' => '3976',
		'installReferrer' => '',
		'isFirstRun' => '1',
		'language' => 'ES',
		'mcc' => '214',
		'mnc' => '0' . mt_rand(1, 9),
		'model' => $model,
		'notificationId' => '',
		'pixelHeight' => $resolution[0],
		'pixelWidth' => $resolution[1],
		'runningSecs' => 0,
		'status' => 'start',
		'udid' => bin2hex(random_bytes(8)),
		'userDoc' => '',
		'userIdGA' => '',
		'version' => $apis[mt_rand(0, count($apis) - 1)]
	);
}

?>
