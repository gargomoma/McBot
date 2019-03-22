<?php

require_once('phpqrcode.php');

$code = @$_GET['code'];
if (!preg_match("/^[0-9]{12}$/", $code)) {
	die('Nope');
}

QRcode::png($code, false, QR_ECLEVEL_L, 1);

?>
