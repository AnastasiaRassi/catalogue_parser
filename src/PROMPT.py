# Your extraction prompt
PROMPT = """Extract all product information from this catalogue image. Follow these rules:

- If a product shows multiple color swatches, list each color separately as individual options. Pick most probable color name.
- If it shows only one color swatch, list ONLY that color.
- If an item has color swatches for both cushion and fabric, set color options for BOTH separately.
- Escape asterisks so they don't become italic markdown (\*)
- Price is the large number visible WITHIN the images, usually on corners.

**JSON FORMAT:**
Output a JSON array. Each product should be an object with this structure:
```json
[
  {
    "page": 1,
    "model": "MOD#:7436/PP923A-8",
    "price": "78105",
    "description": "Set table + 8 chairs",
    "dimensions": "231/346\*104\*75 cm",
    "materials": {
      "chair": "PP Chairs",
      "table_frame": "Aluminum"
    },
    "colors": {
      "table": ["White", "Dark gray"],
      "chair": ["Beige"],
      "cushion": ["Green"]
    },
    "other_characteristics": {
      "seater": "1 table + 8 chairs"
    }
  }
]
```

**CHARACTERISTICS TO EXTRACT (only if present):**
- Seater (e.g., "1 table + 4 chairs")
- Top material (e.g., "Polywood")
- Frame material (e.g., "Steel frame", "Aluminum")
- Any colors and sizes
- Tent/canopy dimensions
- Anything unidentified (Crucial)

**RULES:**
- Omit any field that's not present in the image (don't include null or empty values)
- If you see a small product image beside a main product without its own description/price/model number, IGNORE it - it's just a combo suggestion
- Extract items even if they're missing some characteristics

**PAGE TRACKING:**
I will provide the page number - include it in each product's JSON object.

Page number for this image: """

