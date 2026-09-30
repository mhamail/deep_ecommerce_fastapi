n8n port: http://localhost:5678/

# User Message

```sh
Extract the product information from the following content.

Return only valid JSON.

Product webpage content:

{{$json.cleaned_content}}

Product image URLs:

{{$json.images}}

Main product image:

{{$json.thumbnail}}

Additional user instructions:

{{$node["Webhook"].json.body.prompt}}

```

##################################################################

# System Prompt

##################################################################

````sh
You are a product data extraction assistant.

Extract product information from the webpage content below.

Return ONLY valid JSON.
Do not return markdown.
Do not return ```json.
Do not add explanations.
Use exactly the following structure:

{
"name": "",
"short_description": "",
"description": "",
"thumbnail": "",
"images": [],
"tags": [],
"meta_title": "",
"meta_description": "",
"total_stock": 0,
"video_url": null,
"whats_in_box": "",
"variants": [
{
"sku": "",
"price": 0,
"discount_price": 0,
"stock": 0,
"weight": 0,
"position": 1,
"image": null
}
]
}

Rules:

1. "name" must be the actual product name.
2. "short_description" should be a concise product summary.
3. "description" should contain the useful product description from the webpage.
4. "thumbnail" must be exactly the "Main product image" URL given above. Do not pick a different image.
5. "images" must include every distinct additional product image URL from "Product image URLs" — at least 3-4 if that many are available. Never include the thumbnail URL in "images".
6. "tags" must contain relevant product tags.
7. "meta_title" must be suitable for SEO.
8. "meta_description" must be suitable for SEO.
9. "total_stock" must be a number.
10. "video_url" must always be null. Never fill it in, even if a video is found.
11. "whats_in_box" should describe what is included with the product if available.
12. "variants" MUST contain at least one object.
13. If the product has no variants, create exactly one default variant using the product's available information.
14. "sku" should use the actual SKU if available. Do not invent a SKU.
15. "price" is the regular/original price — always the HIGHER of the two prices shown.
16. "discount_price" is the sale price — always the LOWER of the two prices shown, and must be less than "price". Use null if there is only one price.
17. "stock" use 50 as the static stock.
18. "weight" must be a number representing kilograms, use null if not found .
19. "position" must start at 1.
20. "variants[].image" must always be null when there is only one variant.
21. Do not invent information that is not present on the webpage. Never invent placeholder or example URLs (e.g. example.com) for "thumbnail" or "images" — if none were provided above, use "" / [] instead.
22. If information is unavailable, use an empty string, empty array, null, or dont send these fields.
23. Do not include created_at or updated_at.
24. those fields are found then skip dont send these fields.

SHORT DESCRIPTION:

- Generate a concise ecommerce short description.
- It should normally be 1–3 sentences.
- Return it as valid HTML rich text.
- Use only safe tags such as <p>, <strong>, and <em>.
- Do not use Markdown.
- Do not use <html>, <head>, <body>, <style>, <script>, or iframe.

DESCRIPTION:

- Generate a useful, detailed ecommerce product description — several paragraphs, not one or two lines.
- Organize information clearly for customers, using headings/bullet lists for features and specs.
- Use valid HTML rich text.
- You may use <h2>, <h3>, <p>, <strong>, <em>, <ul>, <ol>, and <li>.
- Do not use Markdown.
- Do not use <html>, <head>, <body>, <style>, <script>, or iframe.
- Do not add claims that are not supported by the webpage.

SEO:

- Generate an appropriate meta_title.
- Generate an appropriate meta_description.
- Keep both relevant to the actual product.
````

##########################################################################

# Code In Javascript

##########################################################################

```js
const html = $json.data || "";
const MAX_IMAGES = 8;

/* -----------------------------
   Product gallery region — cut the page off before any "related /
   recommended products" widget, so their thumbnails never get scraped
   as if they belonged to this product.
----------------------------- */

const STOP_MARKERS = [
  "you might also like",
  "you may also like",
  "related products",
  "recommended for you",
  "customers also viewed",
  "frequently bought together",
  "similar products",
];

function galleryRegion(fullHtml) {
  const lower = fullHtml.toLowerCase();
  let cutoff = fullHtml.length;
  for (const marker of STOP_MARKERS) {
    const idx = lower.indexOf(marker);
    if (idx !== -1 && idx < cutoff) cutoff = idx;
  }
  return fullHtml.slice(0, cutoff);
}

const galleryHtml = galleryRegion(html);

/* -----------------------------
   Extract and normalize image URLs
----------------------------- */

// Note: root-relative paths (e.g. "/cdn/img.jpg", no leading "//" or
// "http") are intentionally dropped rather than resolved against a
// guessed domain — resolving them wrong (as happened before) is worse
// than skipping them, and real product pages almost always serve their
// actual photos as absolute or protocol-relative URLs anyway.
function normalizeUrl(url) {
  if (!url) return "";

  url = url.trim();

  // Remove HTML entities
  url = url.replace(/&amp;/gi, "&").replace(/&quot;/gi, '"');

  // Ignore data/base64 images
  if (url.startsWith("data:")) return "";

  // Protocol-relative URL
  if (url.startsWith("//")) {
    return "https:" + url;
  }

  // Already complete URL
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }

  return "";
}

// Collapse CDN size/crop variants of the same photo down to one
// canonical key, so "images" reflects distinct product photos rather
// than the same photo repeated at different resolutions.
function canonicalKey(url) {
  let key = url.split("?")[0];

  // Shopify-style: "...product_800x.jpg" vs "...product_1024x.jpg"
  key = key.replace(/_(?:\d+x\d*|\d+x)(?=\.[a-z]+$)/i, "");

  // Amazon-style: "...I/51NXLo3Bc7L._AC_SY355_....jpg" vs
  // "...I/51NXLo3Bc7L._AC_SY450_....jpg" — same image id, different
  // size/style descriptor between the id and the extension. Amazon ids
  // can contain "+" and "-" (e.g. "71Ow+CjPL8L"), not just alnum.
  key = key.replace(/\/([A-Za-z0-9+-]{6,15})\.[^/.]+\.([a-z]+)$/i, "/$1.$2");

  return key;
}

/* -----------------------------
   Known non-product images — detected structurally (favicon links, and
   <img> tags whose class/id/alt semantically say "logo"), never by
   filename. A site's own AI-generated product photos can be named
   anything, including something that looks like a "logo" filename on
   some other store, so filename guessing is unsafe here; markup
   semantics ("this <img> IS the header logo") are what's actually
   universal across sites.
----------------------------- */

function knownNonProductKeys(fullHtml) {
  const keys = new Set();

  const iconMatches =
    fullHtml.match(
      /<link[^>]+rel=["'](?:shortcut )?icon["'][^>]+href=["']([^"']+)["']/gi,
    ) || [];
  for (const tag of iconMatches) {
    const hrefMatch = tag.match(/href=["']([^"']+)["']/i);
    const url = hrefMatch && normalizeUrl(hrefMatch[1]);
    if (url) keys.add(canonicalKey(url));
  }

  const imgTags = fullHtml.match(/<img\b[^>]*>/gi) || [];
  for (const tag of imgTags) {
    const isLogo = /(?:class|id|alt)\s*=\s*["'][^"']*logo[^"']*["']/i.test(tag);
    if (!isLogo) continue;

    const srcMatch = tag.match(/(?:src|data-src)\s*=\s*["']([^"']+)["']/i);
    const url = srcMatch && normalizeUrl(srcMatch[1]);
    if (url) keys.add(canonicalKey(url));
  }

  return keys;
}

/* -----------------------------
   Structured data — schema.org Product JSON-LD is the most reliable,
   platform-agnostic source of the product's OWN images (Shopify,
   WooCommerce, and most other storefronts emit this). Used first when
   present; falls back to scraping <img> tags otherwise.
----------------------------- */

function jsonLdProductImages(fullHtml) {
  const blocks =
    fullHtml.match(
      /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi,
    ) || [];

  for (const block of blocks) {
    const bodyMatch = block.match(/>([\s\S]*?)<\/script>/i);
    if (!bodyMatch) continue;

    let data;
    try {
      data = JSON.parse(bodyMatch[1]);
    } catch (e) {
      continue;
    }

    const candidates = Array.isArray(data)
      ? data
      : [data, ...(Array.isArray(data["@graph"]) ? data["@graph"] : [])];

    for (const item of candidates) {
      const type = item && item["@type"];
      const isProduct =
        type === "Product" || (Array.isArray(type) && type.includes("Product"));
      if (!isProduct || !item.image) continue;

      if (typeof item.image === "string") return [item.image];
      if (Array.isArray(item.image)) {
        return item.image
          .map((img) => (typeof img === "string" ? img : img && img.url))
          .filter(Boolean);
      }
      if (item.image.url) return [item.image.url];
    }
  }

  return [];
}

/* -----------------------------
   Amazon's own gallery markup — the real full-size photos live in a
   data-a-dynamic-image="{...}" JSON attribute (url -> [w,h]) on each
   gallery <img>, not in a plain src/data-src attribute. Purely additive:
   only ever finds something on pages that actually have this attribute.
----------------------------- */

function amazonDynamicImages(regionHtml) {
  const attrMatches =
    regionHtml.match(/data-a-dynamic-image=(["'])(\{.*?\})\1/gi) || [];

  const urls = [];
  for (const attrMatch of attrMatches) {
    const valueMatch = attrMatch.match(/data-a-dynamic-image=(["'])(\{.*?\})\1/i);
    if (!valueMatch) continue;

    const jsonText = valueMatch[2].replace(/&quot;/gi, '"').replace(/&amp;/gi, "&");

    try {
      const parsed = JSON.parse(jsonText);
      urls.push(...Object.keys(parsed));
    } catch (e) {
      // not valid JSON for this attribute — skip it
    }
  }
  return urls;
}

// Amazon's best source: the page embeds one JS object PER DISTINCT PHOTO
// under `'colorImages': { 'initial': A.$.parseJSON('[ {...}, {...} ]') }`,
// each with a single canonical "hiRes" URL. Unlike scraping every
// data-a-dynamic-image size-variant map, this is already deduplicated by
// Amazon itself — one entry per photo, not per resolution.
function amazonColorImages(fullHtml) {
  const wrapperMatch = fullHtml.match(
    /'colorImages'\s*:\s*\{\s*'initial'\s*:\s*A\.\$\.parseJSON\('(.+?)'\)/,
  );
  if (!wrapperMatch) return [];

  const jsonText = wrapperMatch[1].replace(/\\"/g, '"').replace(/\\\\/g, "\\");

  let parsed;
  try {
    parsed = JSON.parse(jsonText);
  } catch (e) {
    return [];
  }
  if (!Array.isArray(parsed)) return [];

  return parsed
    .map(
      (item) =>
        item &&
        (item.hiRes || item.large || (item.main && Object.keys(item.main)[0])),
    )
    .filter(Boolean);
}

const amazonImages = amazonColorImages(html);

/* -----------------------------
   AliExpress embeds a clean per-product "imagePathList" array (full-
   resolution URLs) in an inline script. A neighboring "summImagePathList"
   holds 80x80 thumbnail-rail crops of the SAME photos — deliberately
   never read here, so those small crops can't end up in the results.
   The negative lookbehind stops "imagePathList" from also matching as
   a substring of "summImagePathList".
----------------------------- */

function aliExpressImages(fullHtml) {
  const match = fullHtml.match(/(?<!summ)"imagePathList"\s*:\s*(\[[^\]]*\])/i);
  if (!match) return [];

  try {
    const parsed = JSON.parse(match[1]);
    if (Array.isArray(parsed)) return parsed.filter((u) => typeof u === "string");
  } catch (e) {
    // not valid JSON — skip it
  }
  return [];
}

const aliExpressImgs = aliExpressImages(html);

const images = amazonImages.length
  ? amazonImages
  : aliExpressImgs.length
    ? aliExpressImgs
    : amazonDynamicImages(galleryHtml);

// Only fall back to generic <img>-tag scraping when neither Amazon
// source found anything — otherwise thumbnail-rail/alt-size <img>s (with
// their own distinct ids) would sneak in as noise alongside the already-
// clean, already-deduplicated Amazon result above.
if (!images.length) {
  // Get <img> tags (only within the product gallery region — see above)
  const imgTags = galleryHtml.match(/<img\b[^>]*>/gi) || [];

  for (const tag of imgTags) {
    const attributes = [
      "src",
      "data-src",
      "data-original",
      "data-image",
      "data-image-url",
      "data-old-hires",
    ];

    for (const attr of attributes) {
      const regex = new RegExp(`${attr}\\s*=\\s*["']([^"']+)["']`, "i");

      const match = tag.match(regex);

      if (match && match[1]) {
        const url = normalizeUrl(match[1]);

        if (url) {
          images.push(url);
        }
      }
    }

    // Handle srcset
    const srcsetMatch = tag.match(
      /(?:srcset|data-srcset)\s*=\s*["']([^"']+)["']/i,
    );

    if (srcsetMatch) {
      const srcsetUrls = srcsetMatch[1]
        .split(",")
        .map((item) => item.trim().split(/\s+/)[0]);

      for (const src of srcsetUrls) {
        const url = normalizeUrl(src);

        if (url) {
          images.push(url);
        }
      }
    }
  }
}

/* -----------------------------
   Clean image list
----------------------------- */

const nonProductKeys = knownNonProductKeys(html);

const filteredImages = [...new Set(images)].filter((url) => {
  const lower = url.toLowerCase();

  // Ignore obvious non-product images (filename-based — a coarse,
  // best-effort net; knownNonProductKeys above is the reliable,
  // structural check for logos that don't say so in the filename).
  // "icon" is deliberately not checked here — too many legitimate
  // product names contain it (e.g. "icon-shaped lamp").
  if (lower.includes("placeholder")) return false;
  if (lower.includes("logo")) return false;
  if (lower.includes("favicon")) return false;

  if (nonProductKeys.has(canonicalKey(url))) return false;

  // Only images
  return /\.(jpg|jpeg|png|webp|gif|avif)(\?|$)/i.test(url);
});

// One entry per distinct photo — keep the first (usually largest/first
// listed) URL seen for each canonical key.
const seenKeys = new Set();
const scrapedImages = [];
for (const url of filteredImages) {
  const key = canonicalKey(url);
  if (!seenKeys.has(key)) {
    seenKeys.add(key);
    scrapedImages.push(url);
  }
}

// Prefer structured data when the page provides it; it's already scoped
// to this product, so no gallery-region/blacklist filtering is needed.
const jsonLdImages = jsonLdProductImages(html)
  .map(normalizeUrl)
  .filter(Boolean);

const uniqueImages = (jsonLdImages.length ? jsonLdImages : scrapedImages).slice(
  0,
  MAX_IMAGES,
);

/* -----------------------------
   Thumbnail — prefer og:image (Shopify sets this to the real product
   image, not the logo). Falls back to the first scraped <img> only if
   og:image is missing.
----------------------------- */

const ogImageMatch =
  html.match(
    /<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i,
  ) ||
  html.match(
    /<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']/i,
  );

const ogImage = ogImageMatch ? normalizeUrl(ogImageMatch[1]) : "";

// Shopify's Web Pixels Manager init payload embeds the CURRENT page's own
// product/variant under "productVariants" — unlike the neighboring
// "products" array (other catalog items, for cross-sell tracking, never
// safe to use here), this is scoped to just this page. Used only when
// og:image is missing, as a safety net, not a replacement for it.
function shopifyPixelThumbnail(fullHtml) {
  const match = fullHtml.match(
    /"productVariants"\s*:\s*\[\s*\{[\s\S]{0,400}?"image"\s*:\s*\{\s*"src"\s*:\s*"([^"]+)"/,
  );
  if (!match) return "";
  return match[1].replace(/\\\//g, "/");
}

const thumbnail =
  ogImage || normalizeUrl(shopifyPixelThumbnail(html)) || uniqueImages[0] || "";

/* -----------------------------
   Clean webpage text
----------------------------- */

let text = html;

text = text
  .replace(/<script[\s\S]*?<\/script>/gi, "")
  .replace(/<style[\s\S]*?<\/style>/gi, "")
  .replace(/<noscript[\s\S]*?<\/noscript>/gi, "")
  .replace(/<svg[\s\S]*?<\/svg>/gi, "")
  .replace(/<!--[\s\S]*?-->/g, "");

text = text
  .replace(/<\/(p|div|section|article|h1|h2|h3|h4|h5|h6|li|tr)>/gi, "\n")
  .replace(/<br\s*\/?>/gi, "\n")
  .replace(/<li[^>]*>/gi, "\n- ");

text = text.replace(/<[^>]+>/g, " ");

text = text
  .replace(/&nbsp;/gi, " ")
  .replace(/&amp;/gi, "&")
  .replace(/&quot;/gi, '"')
  .replace(/&#39;/gi, "'")
  .replace(/&lt;/gi, "<")
  .replace(/&gt;/gi, ">");

text = text
  .replace(/[ \t]+/g, " ")
  .replace(/\n\s*\n\s*\n+/g, "\n\n")
  .trim();

return {
  json: {
    cleaned_content: text,
    thumbnail,
    images: uniqueImages.filter((url) => url !== thumbnail),
  },
};
```

#######################################################

# Structured Output Parser

#######################################################

```js
{
  "name": "string",
  "short_description": "string",
  "description": "string",
  "thumbnail": "string",
  "images": ["string"],
  "tags": ["string"],
  "meta_title": "string",
  "meta_description": "string",
  "total_stock": 0,
  "video_url": null,
  "whats_in_box": "string",
  "variants": [
    {
      "sku": "string",
      "price": 0,
      "discount_price": 0,
      "stock": 0,
      "weight": 0,
      "position": 1,
      "image": null
    }
  ]
}
```
