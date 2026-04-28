<?php
declare(strict_types=1);

require __DIR__ . '/lib.php';

header('Content-Type: text/plain; charset=UTF-8');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $secret = (string)($_POST['secret'] ?? '');

    if (!hash_equals(bot_secret(), $secret)) {
        http_response_code(403);
        echo 'forbidden';
        exit;
    }

    set_bot_cookie();
    echo 'ok';
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo 'method not allowed';
    exit;
}

if (!has_bot_cookie()) {
    http_response_code(403);
    echo 'forbidden';
    exit;
}

echo (string)(getenv('FLAG'));
