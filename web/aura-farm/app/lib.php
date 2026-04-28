<?php
declare(strict_types=1);

function bot_secret(): string
{
    return (string)(getenv('BOT_SECRET') ?: 'f9a585d5d3c90ac6a4ad6c23bea450718b3707c59aba45089189e6ca3edc2654');
}

function bot_cookie_name(): string
{
    return 'aura_bot';
}

function bot_cookie_value(): string
{
    return hash_hmac('sha256', 'aura-bot-cookie', bot_secret());
}

function set_bot_cookie(): void
{
    $name = bot_cookie_name();
    $value = bot_cookie_value();

    setcookie($name, $value, [
        'expires' => time() + 900,
        'path' => '/',
        'secure' => true,
        'httponly' => true,
        'samesite' => 'None',
    ]);

    $_COOKIE[$name] = $value;
}

function has_bot_cookie(): bool
{
    $cookie = (string)($_COOKIE[bot_cookie_name()] ?? '');

    return $cookie !== '' && hash_equals(bot_cookie_value(), $cookie);
}
