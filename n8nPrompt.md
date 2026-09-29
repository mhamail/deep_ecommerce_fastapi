n8n port: http://localhost:5678/

# User Message

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

# System Prompt

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
"whats_in_box": "",
"variants": [
{
"sku": "",
"price": 0,
"discount_price": 0,
"stock": 0,
"weight": 0,
"position": 1,
"image": ""
}
]
}

Rules:

1. "name" must be the actual product name.
2. "short_description" should be a concise product summary.
3. "description" should contain the useful product description from the webpage.
4. "thumbnail" must be exactly the "Main product image" URL given above. Do not pick a different image.
5. "images" must contain URLs of additional product images, not including the thumbnail — never repeat the thumbnail URL inside "images".
6. "tags" must contain relevant product tags.
7. "meta_title" must be suitable for SEO.
8. "meta_description" must be suitable for SEO.
9. "total_stock" must be a number.
10. If a product video is found, skip it — do not add "video_url" or send a "video" field at all.
11. "whats_in_box" should describe what is included with the product if available.
12. "variants" MUST contain at least one object.
13. If the product has no variants, create exactly one default variant using the product's available information.
14. "sku" should use the actual SKU if available. Do not invent a SKU.
15. "price" must be a number.
16. "discount_price" must be a number. If discount_price is unavailable, use null.
17. "stock" use 50 as the static stock.
18. "weight" must be a number representing kilograms, use null if not found .
19. "position" must start at 1.
20. "variants[].image" must be null if there is only one variant.
21. Do not invent information that is not present on the webpage.
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

##########################################################################

# Code In Javascript

##########################################################################

```js
const html = $json.data || '';

/* -----------------------------
   Extract and normalize image URLs
----------------------------- */

function normalizeUrl(url) {
  if (!url) return '';

  url = url.trim();

  // Remove HTML entities
  url = url
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"');

  // Ignore data/base64 images
  if (url.startsWith('data:')) return '';

  // Protocol-relative URL
  if (url.startsWith('//')) {
    return 'https:' + url;
  }

  // Relative URL
  if (url.startsWith('/')) {
    return 'https://smaronics.com' + url;
  }

  // Already complete URL
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  return '';
}

const images = [];

// Get <img> tags
const imgTags = html.match(/<img\b[^>]*>/gi) || [];

for (const tag of imgTags) {

  const attributes = [
    'src',
    'data-src',
    'data-original',
    'data-image',
    'data-image-url'
  ];

  for (const attr of attributes) {
    const regex = new RegExp(
      `${attr}\\s*=\\s*["']([^"']+)["']`,
      'i'
    );

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
    /(?:srcset|data-srcset)\s*=\s*["']([^"']+)["']/i
  );

  if (srcsetMatch) {
    const srcsetUrls = srcsetMatch[1]
      .split(',')
      .map(item => item.trim().split(/\s+/)[0]);

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

const uniqueImages = [
  ...new Set(images)
].filter(url => {

  const lower = url.toLowerCase();

  // Ignore obvious non-product images
  if (lower.includes('placeholder')) return false;
  if (lower.includes('logo')) return false;
  if (lower.includes('icon')) return false;
  if (lower.includes('favicon')) return false;

  // Only images
  return /\.(jpg|jpeg|png|webp|gif|avif)(\?|$)/i.test(url);
});

/* -----------------------------
   Thumbnail — prefer og:image (Shopify sets this to the real product
   image, not the logo). Falls back to the first scraped <img> only if
   og:image is missing.
----------------------------- */

const ogImageMatch = html.match(
  /<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i
) || html.match(
  /<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']/i
);

const ogImage = ogImageMatch ? normalizeUrl(ogImageMatch[1]) : '';

const thumbnail = ogImage || uniqueImages[0] || '';

/* -----------------------------
   Clean webpage text
----------------------------- */

let text = html;

text = text
  .replace(/<script[\s\S]*?<\/script>/gi, '')
  .replace(/<style[\s\S]*?<\/style>/gi, '')
  .replace(/<noscript[\s\S]*?<\/noscript>/gi, '')
  .replace(/<svg[\s\S]*?<\/svg>/gi, '')
  .replace(/<!--[\s\S]*?-->/g, '');

text = text
  .replace(/<\/(p|div|section|article|h1|h2|h3|h4|h5|h6|li|tr)>/gi, '\n')
  .replace(/<br\s*\/?>/gi, '\n')
  .replace(/<li[^>]*>/gi, '\n- ');

text = text.replace(/<[^>]+>/g, ' ');

text = text
  .replace(/&nbsp;/gi, ' ')
  .replace(/&amp;/gi, '&')
  .replace(/&quot;/gi, '"')
  .replace(/&#39;/gi, "'")
  .replace(/&lt;/gi, '<')
  .replace(/&gt;/gi, '>');

text = text
  .replace(/[ \t]+/g, ' ')
  .replace(/\n\s*\n\s*\n+/g, '\n\n')
  .trim();

return {
  json: {
    cleaned_content: text,
    thumbnail,
    images: uniqueImages.filter(url => url !== thumbnail)
  }
};
```
