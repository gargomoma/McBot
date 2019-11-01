<?php

function ip_match($ip, $block) {
	// Parse IP
	$ip = inet_pton($ip);

	// Parse block IP and length
	list($blockip, $blocklen) = explode('/', $block);
	$blockip = inet_pton($blockip);
	$blocklen = intval($blocklen);

	// If families do not match, abort
	if (strlen($ip) != strlen($blockip)) {
		return false;
	}

	// Check if first bytes match
	$exactbytes = intdiv($blocklen, 8);
	if (substr($ip, 0, $exactbytes) != substr($blockip, 0, $exactbytes)) {
		return false;
	}

	$tailbits = $blocklen % 8;
	if ($tailbits > 0) {
		$iptail = ord($ip[$exactbytes]);
		$blocktail = ord($blockip[$exactbytes]);
		$mask = 0xFF ^ (0xFF >> $tailbits);
		if (($iptail & $mask) != ($blocktail & $mask)) {
			return false;
		}
	}

	return true;
}

?>
