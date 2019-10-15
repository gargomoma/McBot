<?php

function mcd_request($url, $body, $cookies=array()) {
	$headers = array(
		'Content-type: application/json',
		'Accept: application/json',
		'User-Agent: okhttp/3.9.0'
	);

	foreach ($cookies as $key => $value) {
		array_push($headers, "Cookie: $key=$value");
	}

	$body = json_encode($body);
	$ch = curl_init($url);
	curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
	curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
	curl_setopt($ch, CURLOPT_SSLCERT, "mcdonaldsws.mo2o.com_client-android.p12");
	curl_setopt($ch, CURLOPT_SSLCERTPASSWD, "android");
	curl_setopt($ch, CURLOPT_SSLCERTTYPE, "P12");
	curl_setopt($ch, CURLOPT_TIMEOUT, 5);
	//curl_setopt($ch, CURLOPT_PROXY, "socks5://127.0.0.1:9050");

	return $ch;
}

?>
