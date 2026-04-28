<?php
declare(strict_types=1);

header('X-Frame-Options: DENY');
header("Content-Security-Policy: frame-ancestors 'none'");

$products = [
    'a1' => ['id' => 'a1', 'name' => '100 Aura', 'price' => 5.00],
    'a2' => ['id' => 'a2', 'name' => '250 Aura', 'price' => 11.00],
    'a3' => ['id' => 'a3', 'name' => '500 Aura', 'price' => 20.00],
    'a4' => ['id' => 'a4', 'name' => '1000 Aura', 'price' => 37.00],
    'a5' => ['id' => 'a5', 'name' => '2500 Aura', 'price' => 85.00],
    'a6' => ['id' => 'a6', 'name' => '5000 Aura', 'price' => 160.00],
];
$paymentOrigin = rtrim(getenv('PAYMENT_ORIGIN') ?: 'http://localhost:8081', '/');

$visualLabels = [
    'a1' => '100',
    'a2' => '250',
    'a3' => '500',
    'a4' => '1K',
    'a5' => '2.5K',
    'a6' => '5K',
];

function visual_label(string $id, array $visualLabels): string
{
    return $visualLabels[$id] ?? 'Aura';
}

function visual_class(string $id): string
{
    return preg_match('/\Aa[1-6]\z/', $id) === 1 ? 'visual-' . $id : 'visual-default';
}

function money(float $price): string
{
    return '$' . number_format($price, 2);
}
?>
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AuraBuy</title>
    <link rel="stylesheet" href="/assets/ui.css" />
  </head>
  <body>
    <div class="page">
      <header class="topbar">
        <a class="brand" href="/products.php">AuraBuy</a>
      </header>

      <main>
        <div class="section-head">
          <h1>Aura Bundles</h1>
          <div id="status" class="status">Ready for checkout.</div>
        </div>

        <section class="products" aria-label="Aura bundles">
          <?php foreach ($products as $product): ?>
            <?php $visualId = (string)$product['id']; ?>
            <article class="product-card">
              <div class="product-image <?php echo htmlspecialchars(visual_class($visualId), ENT_QUOTES); ?>">
                <div class="aura-art" aria-hidden="true">
                  <strong><?php echo htmlspecialchars(visual_label($visualId, $visualLabels), ENT_QUOTES); ?></strong>
                  <small>Aura</small>
                </div>
              </div>
              <div class="product-body">
                <h2 class="product-title"><?php echo htmlspecialchars($product['name'], ENT_QUOTES); ?></h2>
                <div class="product-foot">
                  <span class="price"><?php echo money((float)$product['price']); ?></span>
                  <button
                    class="button primary buy"
                    type="button"
                    data-product-id="<?php echo htmlspecialchars($product['id'], ENT_QUOTES); ?>"
                    data-name="<?php echo htmlspecialchars($product['name'], ENT_QUOTES); ?>"
                    data-price="<?php echo htmlspecialchars((string)$product['price'], ENT_QUOTES); ?>"
                  >
                    Buy now
                  </button>
                </div>
              </div>
            </article>
          <?php endforeach; ?>
        </section>
      </main>
    </div>

    <script>
      (function () {
        const paymentOrigin = <?php echo json_encode($paymentOrigin, JSON_UNESCAPED_SLASHES); ?>;
        const statusEl = document.getElementById('status');
        const redirectTo = (path) => {
          window.location.assign(path);
        };

        document.querySelectorAll('.buy').forEach((button) => {
          button.addEventListener('click', () => {
            statusEl.textContent = 'Opening checkout...';
            const url = new URL(paymentOrigin + '/');
            url.searchParams.set('product_id', button.dataset.productId);
            url.searchParams.set('product_name', button.dataset.name);
            url.searchParams.set('price', button.dataset.price);
            url.searchParams.set('return_origin', window.location.origin);
            window.open(url.toString(), '_blank');
          });
        });

        window.addEventListener('message', (event) => {
          // if (event.origin !== paymentOrigin) {
          //   return;
          // }

          const data = event.data;
          if (!data || data.type !== 'payment') {
            return;
          }

          const redirectPath =
            typeof data.path === 'string' && data.path !== ''
              ? data.path
              : data.status === 'success'
                ? '/success/'
                : '/failure/';

          if (data.status !== 'success') {
            statusEl.textContent = 'Payment failed. Redirecting...';
            redirectTo(redirectPath);
            return;
          }

          statusEl.textContent = 'Payment confirmed. Redirecting...';
          redirectTo(redirectPath);
        });
      })();
    </script>
  </body>
</html>
