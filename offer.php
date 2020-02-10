<?php
error_reporting(~0); ini_set('display_errors', 1);
require_once('guid.php');
require_once('lang.php');
require_once('ip2location/IP2Location.php');
require_once('devinfo.php');
require_once('curlclient.php');

$error = null;

$offerData = json_decode(file_get_contents("codes.json"), true);
$offerId = @$_GET['id'];
$authKey = @$_GET['authKey'];
$offer = @$offerData[$offerId];

$regionOk = false;

// Try matching valid languages that are used only inside Spain
$uaLangs = language_header_parse();
$regionOk = count(array_intersect($uaLangs, array('es-es', 'ca', 'ca-es', 'gl', 'gl-es', 'eu', 'eu-es'))) > 0;

// Try matching CloudFlare
if (!$regionOk) {
	$regionOk = (@$_SERVER['HTTP_CF_IPCOUNTRY'] == 'ES');
}

// Finally, use remote IP matching
$ip = $_SERVER['REMOTE_ADDR'];
//$ip = $_SERVER['HTTP_X_FORWARDED_FOR'];

if (!$regionOk) {
	if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {
		$ipLocationDb = new IP2Location\Database('ip2location/IP2LOCATION-LITE-DB1.IPV6.BIN');
	} else {
		$ipLocationDb = new IP2Location\Database('ip2location/IP2LOCATION-LITE-DB1.BIN');
	}

	$ipLocation = $ipLocationDb->lookup($ip, IP2Location\Database::COUNTRY_CODE);
	$regionOk = ($ipLocation == 'ES');
}

if (!$regionOk) {
	$error = 'Estos códigos son únicamente válidos para McDonalds España.';
}

require('security.php');

if ($offer && !$error) {
	if (in_array($authKey, $offer['authKeys'])) {
		if ($offer['requiresAuth']) {
			$authInfoList = @json_decode(@file_get_contents("auth.json"), true);
			if ($authInfoList) {
				$codeUrl = "https://mcdonaldsws-app1.mo2o.com/es/v3/getUniqueCodeOfferByLoyalty";
				$authInfo = $authInfoList[mt_rand(0, count($authInfoList) - 1)];
				$user = $authInfo['email'];
				$devinfo = $authInfo['dev'];
				$devinfo['dateTime'] = date('c');
				$devinfo['isFirstRun'] = '0';
				$devinfo['runningSecs'] = mt_rand(5, 100);
				$cookies = $authInfo['cookies'];
			} else {
				$error = 'No se ha podido encontrar ninguna cuenta disponible';
			}
			$userLevel = 1;
		} else {
			$user = '';
			$userLevel = 0;
			$codeUrl = "https://mcdonaldsws-app1.mo2o.com/es/v3/getUniqueCodeOffer";
			$devinfo = devinfo_random();
			$cookies = array();
			$ch = mcd_request('https://api3.mo2o.com/mobilemetrics/app/v2/', $devinfo);
			$reply = curl_exec($ch);
			if (strpos($reply, "OK") === false) {
				$error = "Error registrando dispositivo nuevo";
			}
		}

		if (!$error) {
			$request = array(
				'idDevice'=> $devinfo['udid'],
				'idOffer'=> (int) $offerId,
				'userLevel'=> $userLevel
			);
			$ch = mcd_request("https://mcdonaldsws-app1.mo2o.com/es/v1/notificationsExchangeKiosko", $request);
			$reply = curl_exec($ch);
			if ($reply) {
				$reply = json_decode($reply, true);
				if ($reply['code'] != 100) {
					$error = 'Error solicitando canjeo: ' . $reply['msg'];
					echo '<!--'; var_dump($reply); echo '-->';
				}
			} else {
				$error = 'Error de comunicación durante el canjeo';
			}
		}

		if (!$error) {
			if (@$_GET['big'] == '1' && @$offer['bigCode']) {
				$offerCode = $offer['bigCode'];
			} else {
				$offerCode = $offer['code'];
			}

			$request = array(
				'deviceId' => $devinfo['udid'],
				'offerId' => $offerId,
				'offerType' => $offer['type'],
				'qrCode' => $offerCode,
				'user' => $user
			);

			$ch = mcd_request($codeUrl, $request, $cookies);
			$reply = curl_exec($ch);
			if ($reply) {
				//echo "<!-- ";
				//var_dump($request);
				//var_dump($reply);
				//echo "-->";
				$reply = json_decode($reply, true);
				if ($reply['code'] == 100) {
					$uniqueCode = $reply['response']['uniqueCode'];
				} else {
					$error = "Respuesta inválida: " . $reply['msg'] . ' (' . $reply['code'] . ')';
				}
			} else {
				$error = "Error de comunicación: " . curl_error($ch);
			}
			curl_close($ch);
		}
	} else {
		$error = "Esta web es de uso exclusivo para miembros del grupo <a href=\"https://t.me/McDonaldsOro\">@McDonaldsOro</a>";
	}
}

?>
<!doctype html>
<html lang="es">
	<head>
		<meta charset="utf-8">
		<title><?= $offer ? $offer['name'] : "Error" ?></title>
		<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">
		<link rel="stylesheet" href="style2.css">
		<link rel="shortcut icon" href="favicon.ico">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
	</head>
	<body>
		<h1>McDonald's Oro</h1>
		<div class="fullimage">
			<?php if ($offer) { ?>
				<img src="<?= $offer['image'] ?>" alt="<?= $offer['name'] ?>" id="offerimage">
			<?php } ?>
		</div>
		<main>
			<?php if ($offer) { ?>
				<h2><?= $offer['name'] ?></h2>

				<?php if (!$error) { ?>
					<p>Código: <?= $uniqueCode ?></p>
				<?php } else { ?>
					<p>Se ha producido un error al intentar generar un código nuevo</p>
					<p>Error: <?= $error ?></p>
					<p>Contacto: <a href="https://t.me/Zebstrika">@Zebstrika</a></p>
				<?php } ?>
			<?php } else { ?>
				<h2>Oferta no encontrada</h2>
			<?php } ?>
		</main>
		<div class="fullimage">
			<?php if (@$uniqueCode) { ?>
				<img id="offerqr" src="qrgen.php?code=<?= $uniqueCode ?>" alt="<?= $uniqueCode ?>">
			<?php } ?>
		</div>

		<?php if (false && @$_SERVER['HTTP_DNT'] != '1') { ?>
			<!-- Global site tag (gtag.js) - Google Analytics -->
			<script async src="https://www.googletagmanager.com/gtag/js?id=UA-132900854-1"></script>
			<script>
				window.dataLayer = window.dataLayer || [];
				function gtag(){dataLayer.push(arguments);}
				gtag('js', new Date());
				gtag('config', 'UA-132900854-1');
			</script>
		<?php } ?>
	</body>
</html>
