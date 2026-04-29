---
name: marketplace-watch
description: Monitor marketplace/e-commerce listings for purchase candidates, verify live availability, filter stale/sold listings, and report buy/hold recommendations. Use for recurring product watches on Mercari, Yahoo Auctions/Flea Market, used shops, refurb stores, or price-threshold shopping alerts.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [marketplace, ecommerce, monitoring, shopping, cron, availability]
    related_skills: [personal-task-routing, hermes-agent]
---

# Marketplace Watch

Use this skill when the user asks to monitor marketplaces or e-commerce sites for products under constraints, especially recurring watches such as:

- “毎日21時に中古を探して”
- “メルカリで50万円以下が出たら教えて”
- “この型番の在庫をウォッチして”
- “買い候補だけ出して。売り切れはいらない”
- “価格・保証・状態を見て買い/待ち判定して”

## Class of task

Recurring or one-shot marketplace monitoring where listings can be stale, sold, dynamic, duplicated, or miscategorized, and the assistant must verify availability before recommending purchase.

## Core principle

Do not treat “URL exists + title + price” as purchasable. A marketplace listing is a candidate only after availability is verified from a reliable signal.

## Workflow

1. Capture product constraints:
   - required model/category
   - minimum specs
   - maximum price
   - must-have/bonus conditions
   - excluded variants
   - risk tolerance and resale/exit criteria
2. Search broadly:
   - marketplace search pages
   - item pages
   - used/refurb shop pages
   - general web search snippets only as discovery, not final proof
3. Normalize candidates:
   - product name
   - price
   - specs
   - condition
   - seller/shop
   - warranty/AppleCare/shop warranty
   - URL
   - last checked time
4. Verify availability:
   - item page says selling/on sale/in stock
   - buy/purchase button is present
   - no sold-out sticker or status
   - shop stock is not zero
   - page is not deleted, hidden, or publicly stopped
5. Filter exclusions before reporting.
6. Report only verified candidates as “有力候補”. Put uncertain items in “参考/未確認” or omit them.
7. Include the availability evidence in the report.

## Availability verification rules

### Strong positive signals

- “販売中”, “購入手続きへ”, “カートに入れる”, “在庫あり”
- visible purchase button
- shop page shows quantity or stock available
- auction/flea market page accepts bids or purchase

### Strong negative signals

- “売り切れ”, “売り切れました”, “SOLD”, “販売終了”, “在庫なし”, “公開停止中”
- missing purchase button where it should exist
- stock count 0
- page deleted/404/unavailable
- listing only appears in cached search snippets

### Weak signals — do not rely on these alone

- OpenGraph title/description
- `<meta name="product:price:amount">`
- search engine snippets
- item images still loading
- canonical URL existing
- price visible in stale HTML without current status

## Mercari-specific pitfalls

Mercari item pages often keep title, price, image, and OG/meta tags even after sale. For example, a sold item can still expose:

```html
<meta name="product:price:amount" content="500400">
<meta property="og:title" content="Mac Studio ... by メルカリ">
```

This does **not** prove the item is available.

For Mercari:

1. Do not use `product:price:amount` or OG metadata as availability proof.
2. Check page body/search-card state for:
   - `売り切れ`
   - `売り切れました`
   - `SOLD`
   - sold sticker
   - absence of `購入手続きへ`
3. If the dynamic page cannot be reliably inspected, mark the listing as “状態未確認” and do not recommend it as a buy candidate.
4. For recurring cron prompts, include an explicit exclusion rule for known sold item URLs that caused false positives.

## Cron prompt pattern

When creating or updating a recurring marketplace watch, make the prompt self-contained and include:

```text
Required product constraints:
- ...

Price policy:
- ...

Exclude:
- sold out / out of stock / discontinued / wrong variant

Availability check:
- Do not trust OG/meta price alone.
- Verify purchase button or on-sale/in-stock status.
- For Mercari, sold listings can retain title/price metadata; check sold labels/body/card state.
- If availability cannot be verified, do not list as an active candidate.

Report format:
1. Overall verdict: buy / strong / wait / none
2. Verified candidates with URL, price, specs, condition, warranty, availability evidence
3. Reference-only uncertain candidates, if useful
4. Excluded sold/out-of-stock examples, if relevant
5. Risk note / do-not-overpay reminder
```

## Reporting standards

For each candidate, include:

- price
- exact product/specs
- seller/shop
- URL
- condition
- warranty/return policy
- availability evidence, e.g. “購入ボタンあり”, “販売中表示あり”, “ショップ在庫あり”
- recommendation: buy / strong / wait / no

Avoid buy pressure. If the user has a strict budget or resale-risk concern, bias toward “wait” unless the listing clearly beats the threshold.

## Pitfalls

- Do not recommend sold Mercari listings just because metadata still has title and price.
- Do not mix variants with similar names; explicitly check model/spec requirements.
- Do not let “rare item” override the user’s price ceiling unless asked.
- Do not hide uncertainty. Label it.
- Do not create noisy recurring jobs without a stop condition or clear criteria.
- For high-price items, include exit/resale risk, warranty, seller trust, and payment constraints.
