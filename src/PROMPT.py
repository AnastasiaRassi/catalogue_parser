PROMPT = """
Extract product data from this catalogue page.

Return ONLY a valid JSON array. No markdown, no explanation.

For each product, include only fields that are visible or inferable from the image:
{
  "page": number,
  "model": string or null,
  "price": string or null,
  "dimensions": string or null,
  "materials": object or null,
  "colors": object or null,
  "seater": string or null,
  "other": object or null
}

Rules:
- Use null for missing values.
- The code on the corner of images is price.
- Keep asterisks (*) and slashes (/) as normal characters.
- Do not use backslashes in text values.
- Split multiple color swatches into separate color lists.
- If only one swatch is shown, use that color only.
- Ignore tiny thumbnail-only suggestion images with no own price/model/description.
- If the same product ID appears in different variants, create separate objects when color or other visible details differ.
- Include the page number in every product object.
- Do NOT infer or guess materials, dimensions, or specifications.
- If a characteristic is explicitly written but does not match existing fields, include it under a consistent, descriptive key.
- Only extract or infer colors when the same product model appears multiple times with different visible variations.
- In that case, use color to distinguish the variants (based on visible differences or swatches).
- If a product appears only once, do not infer color unless it is explicitly written.
- If color is unclear, use null.
Page number:
"""


# # Your extraction prompt
# PROMPT = """Extract all product information from this catalogue image. Follow these rules:
# If a product shows multiple color swatches, list each color separately as options, Pick most probable color name if only one is present.
# Keep asterisks (*) as normal characters. Do not use backslashes.
# Price is the large number visible WITHIN the images, usually on corners.

# **JSON FORMAT:**
# Output a JSON array. Example:
# ```json
# [
#   {
#     "page": 1,
#     "model": "MOD#:7436/PP923A-8",
#     "price": "78105",
#     "dimensions": "231/346\*104\*75 cm",
#     "materials": {
#       "chair": "PP Chairs",
#       "table_frame": "Aluminum"
#     },
#     "colors": {
#       "table": ["White", "Dark gray"],
#       "chair": ["Beige"],
#       "cushion": ["Green"]
#     } etc..
# ]
# ```
# Only extract this data IF PRESENT otherwise put null. Additional characteristics may be present in the images - 
# extract them under proper json keys but be consistent across products.
# exmaples:
# - Seater (e.g., "1 table + 4 chairs")
# - Top material (e.g., "Polywood")
# - Frame material (e.g., "Steel frame", "Aluminum")
# - Any colors and sizes
# - Tent/canopy dimensions
# - Anything unidentified (Crucial)

# **RULES:**
# - If you see a small product image beside a main product without its own description/price/model number, IGNORE it - it's just a combo suggestion
# - Extract items even if they're missing some or all characteristics just use null
# - if a product id appears for different  items, keep track of what differentiates them like one chair is red one is white so we extarct them seperately and if color isnt written down you extract it. 

# **PAGE TRACKING:**
# I will provide the page number - include it in each product's JSON object.

# Page number for this image: """

