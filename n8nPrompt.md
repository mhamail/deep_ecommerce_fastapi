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

// The page's own URL — needed to resolve relative/protocol-relative image
// paths correctly no matter which site was scraped (Shopify, Amazon,
// Daraz, ...). Never hardcode a domain here.
//
// Prefer an explicit field from the workflow if one is wired up, but don't
// depend on it: fall back to the page's own <meta property="og:url"> or
// <link rel="canonical">, which almost every real product page has, so
// this works even if $json has no url/link field at this node.
const ogUrlMatch =
  html.match(
    /<meta[^>]+property=["']og:url["'][^>]+content=["']([^"']+)["']/i,
  ) ||
  html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:url["']/i);
const canonicalMatch = html.match(
  /<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i,
);

/* -----------------------------
   Extract and normalize image URLs
----------------------------- */

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

// Collapse CDN size/crop variants of the same photo (e.g. "?width=420"
// vs "?width=800") down to one canonical URL, so "images" reflects
// distinct product photos rather than the same photo repeated.
function canonicalKey(url) {
  return url.split("?")[0].replace(/_(?:\d+x\d*|\d+x)(?=\.[a-z]+$)/i, "");
}

const images = [];

// Get <img> tags
const imgTags = html.match(/<img\b[^>]*>/gi) || [];

for (const tag of imgTags) {
  const attributes = [
    "src",
    "data-src",
    "data-original",
    "data-image",
    "data-image-url",
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

/* -----------------------------
   Clean image list
----------------------------- */

const filteredImages = [...new Set(images)].filter((url) => {
  const lower = url.toLowerCase();

  // Ignore obvious non-product images
  if (lower.includes("placeholder")) return false;
  if (lower.includes("logo")) return false;
  if (lower.includes("icon")) return false;
  if (lower.includes("favicon")) return false;

  // Only images
  return /\.(jpg|jpeg|png|webp|gif|avif)(\?|$)/i.test(url);
});

// One entry per distinct photo — keep the first (usually largest/first
// listed) URL seen for each canonical key.
const seenKeys = new Set();
const uniqueImages = [];
for (const url of filteredImages) {
  const key = canonicalKey(url);
  if (!seenKeys.has(key)) {
    seenKeys.add(key);
    uniqueImages.push(url);
  }
}

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

const thumbnail = ogImage || uniqueImages[0] || "";

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
