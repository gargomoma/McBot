<?php

function language_header_parse($header=null) {
	if ($header == null) {
		if (isset($_SERVER['HTTP_ACCEPT_LANGUAGE'])) {
			$header = $_SERVER['HTTP_ACCEPT_LANGUAGE'];
		} else {
			return array();
		}
	}

	$langs = array();
	foreach (explode(',', $header) as $lang) {
		$lang = explode(';q=', $lang);
		$langs[strtolower($lang[0])] = (sizeof($lang) == 1 ? 1.0 : (float) $lang[1]);
	}
	arsort($langs);

	return array_keys($langs);
}
