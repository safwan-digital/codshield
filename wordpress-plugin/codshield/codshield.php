<?php
/**
 * Plugin Name:       COD Shield
 * Description:       Score your WooCommerce COD orders for fake-order risk before you dispatch. Upload an orders CSV export and get an explainable risk report — 17 checks, every score with its reasons. Companion to the COD Shield CLI (github.com/safwan-digital/codshield). Nothing is stored and nothing in your store is changed.
 * Version:           1.0.0
 * Author:            Safwan Digital
 * License:           GPLv2 or later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       codshield
 * Requires at least: 6.0
 * Requires PHP:      7.4
 */

if (!defined('ABSPATH')) {
    exit;
}

define('CODSHIELD_VERSION', '1.0.0');

add_action('admin_menu', function () {
    add_submenu_page(
        'woocommerce',
        'COD Shield',
        'COD Shield',
        'manage_woocommerce',
        'codshield',
        'codshield_render_page'
    );
});

/* ------------------------------------------------------------------ rules */
/* These mirror the COD Shield CLI (codshield.py) exactly — same checks,
   same points, same bands — so both versions score the same order the
   same way. */

function codshield_junk_tokens() {
    return array('test', 'asdf', 'qwerty', 'xxxx', 'xxx', 'fake', 'none',
                 'na', 'n/a', 'abc', 'xyz', 'demo', 'sample', 'nil', '-');
}

function codshield_disposable_domains() {
    return array('mailinator.com', 'guerrillamail.com', '10minutemail.com',
                 'tempmail.com', 'temp-mail.org', 'yopmail.com',
                 'throwawaymail.com', 'getnada.com', 'sharklasers.com');
}

function codshield_bad_statuses() {
    return array('cancelled', 'canceled', 'failed', 'refunded', 'on-hold');
}

function codshield_normalise_phone($raw) {
    $digits = preg_replace('/\D/', '', (string) $raw);
    if (strlen($digits) === 12 && substr($digits, 0, 2) === '91') {
        $digits = substr($digits, 2);
    } elseif (strlen($digits) === 11 && substr($digits, 0, 1) === '0') {
        $digits = substr($digits, 1);
    }
    return strlen($digits) === 10 ? $digits : null;
}

function codshield_longest_run($phone) {
    $best = 1;
    $run = 1;
    $direction = 0;
    $len = strlen($phone);
    for ($i = 1; $i < $len; $i++) {
        $step = intval($phone[$i]) - intval($phone[$i - 1]);
        if (($step === 1 || $step === -1) && ($direction === 0 || $step === $direction)) {
            $run++;
            $direction = $step;
        } elseif ($step === 1 || $step === -1) {
            $run = 2;
            $direction = $step;
        } else {
            $run = 1;
            $direction = 0;
        }
        if ($run > $best) {
            $best = $run;
        }
    }
    return $best;
}

function codshield_phone_flags($phone) {
    $flags = array();
    $counts = count_chars($phone, 1);
    foreach ($counts as $count) {
        if ($count >= 7) {
            $flags[] = 'repeated';
            break;
        }
    }
    if (codshield_longest_run($phone) >= 8) {
        $flags[] = 'sequential';
    }
    return $flags;
}

function codshield_looks_junk($text) {
    $tokens = preg_split('/[^a-z]+/', strtolower((string) $text));
    $junk = codshield_junk_tokens();
    foreach ($tokens as $t) {
        if ($t !== '' && in_array($t, $junk, true)) {
            return true;
        }
    }
    return false;
}

function codshield_band($score) {
    if ($score >= 50) {
        return array('HIGH', 'Hold - verify by call, or take a part-prepayment first');
    }
    if ($score >= 25) {
        return array('MEDIUM', 'Confirm on WhatsApp / call before dispatch');
    }
    return array('LOW', 'Safe to dispatch');
}

function codshield_score_order($order, $context, $high, $very_high) {
    $score = 0;
    $reasons = array();
    $add = function ($points, $reason) use (&$score, &$reasons) {
        $score += $points;
        $reasons[] = $reason;
    };

    $raw_phone = $order['phone'];
    $phone = codshield_normalise_phone($raw_phone);
    $digits_only = preg_replace('/\D/', '', (string) $raw_phone);
    if ($raw_phone === '' || ($phone === null && $digits_only === '')) {
        $add(30, 'Phone missing or unreadable');
    } elseif ($phone === null) {
        $add(30, 'Phone is not a valid 10-digit Indian mobile');
    }
    if ($phone !== null) {
        if (strpos('6789', $phone[0]) === false) {
            $add(15, 'Phone series cannot be a mobile (does not start 6-9)');
        }
        foreach (codshield_phone_flags($phone) as $flag) {
            if ($flag === 'repeated') {
                $add(25, 'Phone looks typed, not real (repeated digits)');
            }
            if ($flag === 'sequential') {
                $add(25, 'Phone looks typed, not real (number sequence)');
            }
        }
        if (!empty($context['counts'][$phone]) && $context['counts'][$phone] >= 3) {
            $add(15, 'Same phone on 3+ orders in this file');
        }
        if (!empty($context['names'][$phone]) && count($context['names'][$phone]) >= 2) {
            $add(20, 'Same phone used with different names');
        }
        if (!empty($context['bad'][$phone])) {
            $add(25, 'This phone had a cancelled/failed order before');
        }
    }

    if (strlen(preg_replace('/[^A-Za-z]/', '', $order['name'])) < 3) {
        $add(10, 'Name looks incomplete');
    }
    if (codshield_looks_junk($order['name']) || codshield_looks_junk($order['address'])) {
        $add(20, 'Name or address contains junk text (test/asdf/fake...)');
    }

    $address = trim($order['address'] . ' ' . $order['city']);
    if (strlen($address) < 20) {
        $add(15, 'Address too short to deliver reliably');
    }

    $pin = preg_replace('/\D/', '', (string) $order['pincode']);
    if ($pin === '') {
        $add(15, 'PIN code missing');
    } elseif (strlen($pin) !== 6 || $pin[0] === '0') {
        $add(15, 'PIN code format invalid');
    }

    $email = strtolower($order['email']);
    if ($email === '') {
        $add(5, 'Email missing');
    } elseif (strpos($email, '@') !== false) {
        $domain = substr(strrchr($email, '@'), 1);
        if (in_array($domain, codshield_disposable_domains(), true)) {
            $add(15, 'Disposable / throwaway email domain');
        }
    }

    if ($order['total_value'] !== null) {
        if ($order['total_value'] >= $very_high) {
            $add(15, 'Very-high-value COD order (>= very-high threshold)');
        } elseif ($order['total_value'] >= $high) {
            $add(10, 'High-value COD order (>= high threshold)');
        }
    }

    return array(min($score, 100), $reasons);
}


/* ------------------------------------------------------------- CSV import */

function codshield_column_aliases() {
    return array(
        'order_id'  => array('order id', 'order number', 'order', 'id', 'number'),
        'name'      => array('billing name', 'customer name', 'name', 'full name', 'billing first name'),
        'last_name' => array('billing last name'),
        'phone'     => array('billing phone', 'phone', 'mobile', 'phone number', 'billing mobile', 'customer phone'),
        'email'     => array('billing email', 'email', 'customer email', 'email address'),
        'address'   => array('billing address 1', 'billing address', 'address', 'shipping address 1', 'shipping address', 'address 1'),
        'city'      => array('billing city', 'city', 'shipping city'),
        'pincode'   => array('billing postcode', 'postcode', 'pincode', 'pin code', 'zip', 'billing pin code', 'shipping postcode'),
        'total'     => array('order total', 'total', 'grand total', 'amount'),
        'payment'   => array('payment method', 'payment', 'payment gateway'),
        'status'    => array('order status', 'status'),
    );
}

function codshield_map_columns($headers) {
    $norm = array();
    foreach ($headers as $i => $h) {
        $key = trim(preg_replace('/[^a-z0-9]+/', ' ', strtolower((string) $h)));
        $norm[$key] = $i;
    }
    $map = array();
    foreach (codshield_column_aliases() as $canonical => $aliases) {
        foreach ($aliases as $alias) {
            if (isset($norm[$alias])) {
                $map[$canonical] = $norm[$alias];
                break;
            }
        }
    }
    return $map;
}

function codshield_cell($row, $map, $key) {
    if (!isset($map[$key]) || !isset($row[$map[$key]])) {
        return '';
    }
    return trim((string) $row[$map[$key]]);
}

function codshield_parse_total($raw) {
    $clean = preg_replace('/[^0-9.]/', '', str_replace(',', '', (string) $raw));
    return $clean === '' ? null : floatval($clean);
}

function codshield_is_cod($order) {
    $payment = strtolower($order['payment']);
    if ($payment === '') {
        return true;
    }
    return strpos($payment, 'cod') !== false
        || strpos($payment, 'cash on delivery') !== false;
}

function codshield_score_file($tmp_path, $high, $very_high) {
    $fh = fopen($tmp_path, 'r');
    if ($fh === false) {
        return array('error' => 'Could not open the uploaded file.');
    }
    $headers = fgetcsv($fh);
    if ($headers === false) {
        fclose($fh);
        return array('error' => 'That file looks empty.');
    }
    if (isset($headers[0])) {
        $headers[0] = preg_replace('/^\xEF\xBB\xBF/', '', $headers[0]);
    }
    $map = codshield_map_columns($headers);
    $orders = array();
    $row_count = 0;
    while (($row = fgetcsv($fh)) !== false && $row_count < 5000) {
        if (count($row) === 1 && trim((string) $row[0]) === '') {
            continue;
        }
        $row_count++;
        $name = codshield_cell($row, $map, 'name');
        $last = codshield_cell($row, $map, 'last_name');
        if ($last !== '' && stripos($name, $last) === false) {
            $name = trim($name . ' ' . $last);
        }
        $orders[] = array(
            'order_id'    => codshield_cell($row, $map, 'order_id'),
            'name'        => $name,
            'phone'       => codshield_cell($row, $map, 'phone'),
            'email'       => codshield_cell($row, $map, 'email'),
            'address'     => codshield_cell($row, $map, 'address'),
            'city'        => codshield_cell($row, $map, 'city'),
            'pincode'     => codshield_cell($row, $map, 'pincode'),
            'total'       => codshield_cell($row, $map, 'total'),
            'total_value' => codshield_parse_total(codshield_cell($row, $map, 'total')),
            'payment'     => codshield_cell($row, $map, 'payment'),
            'status'      => strtolower(codshield_cell($row, $map, 'status')),
        );
    }
    fclose($fh);
    if (!$orders) {
        return array('error' => 'No order rows found in that file.');
    }

    $context = array('counts' => array(), 'names' => array(), 'bad' => array());
    $bad_statuses = codshield_bad_statuses();
    foreach ($orders as $o) {
        $phone = codshield_normalise_phone($o['phone']);
        if ($phone === null) {
            continue;
        }
        $context['counts'][$phone] = isset($context['counts'][$phone])
            ? $context['counts'][$phone] + 1 : 1;
        if ($o['name'] !== '') {
            $context['names'][$phone][strtolower($o['name'])] = true;
        }
        if (in_array($o['status'], $bad_statuses, true)) {
            $context['bad'][$phone] = true;
        }
    }
    foreach ($context['names'] as $phone => $set) {
        $context['names'][$phone] = array_keys($set);
    }

    $results = array();
    foreach ($orders as $o) {
        if (in_array($o['status'], $bad_statuses, true)) {
            $results[] = $o + array('score' => '', 'band' => 'CLOSED',
                'action' => 'Not scored (order already cancelled/failed/refunded)',
                'reasons' => array());
            continue;
        }
        if (!codshield_is_cod($o)) {
            $results[] = $o + array('score' => '', 'band' => 'PREPAID',
                'action' => 'Not scored (prepaid order)', 'reasons' => array());
            continue;
        }
        list($score, $reasons) = codshield_score_order($o, $context, $high, $very_high);
        list($band, $action) = codshield_band($score);
        $results[] = $o + array('score' => $score, 'band' => $band,
            'action' => $action, 'reasons' => $reasons);
    }

    $rank = array('HIGH' => 0, 'MEDIUM' => 1, 'LOW' => 2, 'PREPAID' => 3, 'CLOSED' => 4);
    usort($results, function ($a, $b) use ($rank) {
        $ra = $rank[$a['band']];
        $rb = $rank[$b['band']];
        if ($ra !== $rb) {
            return $ra - $rb;
        }
        $sa = is_int($a['score']) ? $a['score'] : -1;
        $sb = is_int($b['score']) ? $b['score'] : -1;
        return $sb - $sa;
    });
    return array('results' => $results);
}

/* -------------------------------------------------------------------- page */

function codshield_render_page() {
    if (!current_user_can('manage_woocommerce')) {
        wp_die('Not allowed.');
    }
    $high = 5000.0;
    $very_high = 10000.0;
    $results = null;
    $error = '';

    if (!empty($_POST['codshield_run']) && !empty($_FILES['codshield_csv'])) {
        check_admin_referer('codshield_upload');
        $high = isset($_POST['high_value']) ? floatval($_POST['high_value']) : $high;
        $very_high = isset($_POST['very_high_value']) ? floatval($_POST['very_high_value']) : $very_high;
        $file = $_FILES['codshield_csv'];
        if ($file['error'] !== UPLOAD_ERR_OK) {
            $error = 'The upload failed. Please try again.';
        } elseif ($file['size'] > 5 * 1024 * 1024) {
            $error = 'That file is over 5 MB — export a smaller date range.';
        } elseif (strtolower(pathinfo($file['name'], PATHINFO_EXTENSION)) !== 'csv') {
            $error = 'Please upload a .csv file (WooCommerce > Orders > Export).';
        } else {
            $out = codshield_score_file($file['tmp_name'], $high, $very_high);
            if (isset($out['error'])) {
                $error = $out['error'];
            } else {
                $results = $out['results'];
            }
        }
    }

    $band_colors = array('HIGH' => '#b91c1c', 'MEDIUM' => '#b45309',
                         'LOW' => '#15803d', 'PREPAID' => '#6b7280',
                         'CLOSED' => '#6b7280');
    ?>
    <div class="wrap">
        <h1>COD Shield</h1>
        <p>Score cash-on-delivery orders for <strong>fake-order risk before you
        dispatch</strong>. Export from WooCommerce &gt; Orders &gt; Export, upload the
        CSV here, and get every COD order scored 0–100 with the exact reasons —
        17 explainable checks (typed phone numbers, junk addresses, bad PINs,
        throwaway emails, repeat offenders, high-value orders). The file is read
        once and discarded; <strong>nothing is stored and nothing in your store
        is changed</strong>.</p>

        <?php if ($error !== '') : ?>
            <div class="notice notice-error"><p><?php echo esc_html($error); ?></p></div>
        <?php endif; ?>

        <form method="post" enctype="multipart/form-data" style="margin:18px 0;">
            <?php wp_nonce_field('codshield_upload'); ?>
            <input type="hidden" name="codshield_run" value="1">
            <p>
                <label><strong>Orders CSV:</strong>
                    <input type="file" name="codshield_csv" accept=".csv" required>
                </label>
            </p>
            <p>
                <label>High-value threshold (&#8377;)
                    <input type="number" name="high_value" step="1" min="0"
                           value="<?php echo esc_attr($high); ?>" style="width:110px;">
                </label>
                <label style="margin-left:16px;">Very-high-value (&#8377;)
                    <input type="number" name="very_high_value" step="1" min="0"
                           value="<?php echo esc_attr($very_high); ?>" style="width:110px;">
                </label>
                <button class="button button-primary" style="margin-left:16px;">Score orders</button>
            </p>
        </form>

        <?php if ($results !== null) :
            $counts = array('HIGH' => 0, 'MEDIUM' => 0, 'LOW' => 0, 'PREPAID' => 0, 'CLOSED' => 0);
            foreach ($results as $r) {
                $counts[$r['band']]++;
            }
            ?>
            <h2>Report — <?php echo count($results); ?> orders:
                HIGH <?php echo $counts['HIGH']; ?> · MEDIUM <?php echo $counts['MEDIUM']; ?> ·
                LOW <?php echo $counts['LOW']; ?> · PREPAID <?php echo $counts['PREPAID']; ?> ·
                CLOSED <?php echo $counts['CLOSED']; ?></h2>
            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th style="width:7%;">Order</th>
                        <th style="width:15%;">Customer</th>
                        <th style="width:11%;">Phone</th>
                        <th style="width:8%;">Total</th>
                        <th style="width:6%;">Score</th>
                        <th style="width:8%;">Band</th>
                        <th style="width:17%;">Suggested action</th>
                        <th>Reasons</th>
                    </tr>
                </thead>
                <tbody>
                <?php foreach ($results as $r) : ?>
                    <tr>
                        <td><?php echo esc_html($r['order_id']); ?></td>
                        <td><?php echo esc_html($r['name']); ?></td>
                        <td><?php echo esc_html($r['phone']); ?></td>
                        <td><?php echo esc_html($r['total']); ?></td>
                        <td><strong><?php echo esc_html($r['score']); ?></strong></td>
                        <td><strong style="color:<?php echo esc_attr($band_colors[$r['band']]); ?>;">
                            <?php echo esc_html($r['band']); ?></strong></td>
                        <td><?php echo esc_html($r['action']); ?></td>
                        <td><?php echo esc_html(implode('; ', $r['reasons'])); ?></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
            <p class="description" style="margin-top:12px;">A score is a triage
            signal, not a verdict — confirm HIGH orders before dispatch; do not
            auto-cancel on a score. Phone and PIN rules are India-specific in
            this version.</p>
        <?php endif; ?>
    </div>
    <?php
}
