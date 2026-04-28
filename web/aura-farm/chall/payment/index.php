<?php
declare(strict_types=1);

$appOrigin = rtrim(getenv('APP_ORIGIN') ?: 'http://localhost:8080', '/');

function context_from(array $data, string $appOrigin): array
{
    $productId = trim((string)($data['product_id'] ?? ''));
    $productName = trim((string)($data['product_name'] ?? ''));
    $price = is_numeric($data['price'] ?? null) ? (float)$data['price'] : 0.0;
    $returnOrigin = trim((string)($data['return_origin'] ?? ''));
    if ($returnOrigin === '') {
        $returnOrigin = $appOrigin;
    }

    return [
        'product_id' => $productId,
        'product_name' => $productName,
        'price' => $price,
        'return_origin' => $returnOrigin,
    ];
}

function h(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES);
}

function hidden_context_fields(array $context): void
{
    ?>
    <input type="hidden" name="product_id" value="<?php echo h($context['product_id']); ?>" />
    <input type="hidden" name="product_name" value="<?php echo h($context['product_name']); ?>" />
    <input type="hidden" name="price" value="<?php echo h((string)$context['price']); ?>" />
    <input type="hidden" name="return_origin" value="<?php echo h($context['return_origin']); ?>" />
    <?php
}

function selected_product_label(array $context): string
{
    return $context['product_name'] !== '' ? $context['product_name'] : $context['product_id'];
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $context = context_from($_POST, $appOrigin);
    $redirectPath = '/failure/';
    $payload = [
        'type' => 'payment',
        'status' => 'failure',
        'reason' => 'insufficient_funds',
        'productId' => $context['product_id'],
        'productName' => $context['product_name'],
        'price' => $context['price'],
        'path' => $redirectPath,
    ];
    $targetOrigin = $context['return_origin'] !== '' ? $context['return_origin'] : $appOrigin;
    $payloadJson = json_encode($payload, JSON_UNESCAPED_SLASHES);
    $targetJson = json_encode($targetOrigin, JSON_UNESCAPED_SLASHES);
    ?>
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Aura Payment Failed</title>
    <link rel="stylesheet" href="/assets/ui.css" />
  </head>
  <body class="result-page">
    <div class="result-card">
      <h1>Payment failed</h1>
      <button class="button primary" type="button" id="go-now">Go now</button>
    </div>
    <script>
      (function () {
        const payload = <?php echo $payloadJson; ?>;
        const targetOrigin = <?php echo $targetJson; ?>;
        const hasOpener = window.opener && !window.opener.closed;
        const baseOrigin = targetOrigin.replace(/\/$/, '');
        const redirectPath = payload.path || '/failure/';
        const goNow = document.getElementById('go-now');
        if (goNow) {
          goNow.addEventListener('click', () => {
            window.location.assign(`${baseOrigin}${redirectPath}`);
          });
        }
        if (hasOpener) {
          window.opener.postMessage(payload, targetOrigin);
          setTimeout(() => window.close(), 600);
          return;
        }
        setTimeout(() => {
          window.location.assign(`${baseOrigin}${redirectPath}`);
        }, 400);
      })();
    </script>
  </body>
</html>
<?php
    exit;
}

$context = context_from($_GET, $appOrigin);
?>
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Aura Checkout</title>
    <link rel="stylesheet" href="/assets/ui.css" />
  </head>
  <body>
    <div class="page">
      <header class="topbar">
        <a class="brand" href="/">AuraPay</a>
      </header>

      <main class="stack">
        <h1>Checkout</h1>

        <?php if ($context['product_id'] !== ''): ?>
          <section class="panel summary" aria-label="Selected product">
            <h2><?php echo h(selected_product_label($context)); ?></h2>
            <span class="price">$<?php echo number_format($context['price'], 2); ?></span>
          </section>
        <?php else: ?>
          <section class="panel">
            <p class="muted">No product selected.</p>
          </section>
        <?php endif; ?>

        <?php if ($context['product_id'] !== ''): ?>
          <section class="panel">
            <h2>Payment</h2>
            <form method="post">
              <?php hidden_context_fields($context); ?>
              <div class="button-row">
                <button class="button primary" type="submit">Pay</button>
              </div>
            </form>
          </section>
        <?php endif; ?>
      </main>
    </div>
  </body>
</html>
