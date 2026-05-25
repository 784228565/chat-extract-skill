---
name: chat-extract-skill
description: Extract and structure chat order records from mobile phone long screenshots into Excel. Use when the user needs to (1) capture long scrolling chat screenshots from an Android phone via ADB, (2) OCR extract text from chat screenshots, (3) manually organize chat records into structured data, or (4) convert structured chat records to Excel. Triggers on requests like "手机长截图提取订单", "聊天记录转Excel", "截屏整理表格", "群聊订单汇总", "OCR聊天记录生成表格", etc. Works for group chat apps, agricultural supply orders, customer service chat records, and any scenario where mobile chat screenshots need to be converted to structured spreadsheets.
---

# Chat Extract Skill

Extract structured order records from mobile chat screenshots and export to Excel.

## Prerequisites

- Android phone connected via ADB (USB debugging enabled)
- Python 3.8+
- Packages: `Pillow`, `numpy`, `opencv-python`, `rapidocr-onnxruntime`, `pandas`, `openpyxl`

Install:
```bash
pip install Pillow numpy opencv-python rapidocr-onnxruntime pandas openpyxl
```

## Workflow

### Step 1: Capture Long Screenshot via ADB

Connect phone, ensure chat window is open, then run:

```bash
python scripts/adb_long_screenshot.py [output_dir]
```

Defaults:
- Output: `./adb_screenshots/`
- Generates: `screenshot_*.png` (individual frames) + `long_screenshot.png` (stitched)

**Key parameters in script** (edit if needed):
- `SWIPE_DURATION = 900` — swipe speed in ms (slower = more stable)
- `SWIPE_START_RATIO = 0.50` — start swipe at 50% of screen height
- `SWIPE_END_RATIO = 0.25` — end swipe at 25% of screen height
- Tune these for your phone's screen size and scroll inertia.

### Step 2: OCR Extract Text

**Option A — Long screenshot (recommended if single long image is clean):**
```bash
python scripts/batch_ocr.py ./adb_screenshots/long_screenshot.png ./extracted/ocr_result.json
```

**Option B — Individual frames (if long screenshot has stitching issues):**
```bash
python scripts/batch_ocr.py ./adb_screenshots ./extracted/ocr_result.json
```

Output: `ocr_result.json` with `image`, `texts`, `full_text` per image.

### Step 3: AI Analyzes OCR and Structures Data

Read the OCR JSON output. Manually organize chat records into structured format.

**Typical group chat order format:**
```
[Sender Name]
[Date Time]
[Customer Name]
[Product1] [Quantity] [Unit]
[Product2] [Quantity] [Unit]
...
```

**Action keywords:**
- `退...` = return/refund
- `装...` = loading/pickup
- `送...` = delivery
- `拿...` = pickup
- (none) = purchase

Create a JSON file with this structure:

```json
[
  {
    "date": "4月16日",
    "time": "13:16:33",
    "sender": "AgentA",
    "customer": "CustomerA",
    "note": "",
    "items": [
      {"product": "ProductA", "quantity": "100", "unit": "袋", "action": "购买"}
    ]
  },
  {
    "date": "4月16日",
    "time": "13:17:05",
    "sender": "AgentA",
    "customer": "CustomerB",
    "note": "",
    "items": [
      {"product": "ProductA", "quantity": "70", "unit": "袋", "action": "退货"}
    ]
  }
]
```

> **Note:** The above JSON is a fictional example showing the data format only.

**Tips for data organization:**
- Each message = one object with `date`, `time`, `sender`, `customer`, `items[]`
- Split multiple items in one message into separate `items` entries
- Use `note` for special annotations (e.g., delivery address, source reference)
- Save as `./extracted/structured_data.json`

### Step 4: Generate Excel

```bash
python scripts/parse_to_excel.py ./extracted/structured_data.json ./extracted/orders.xlsx
```

Output Excel contains 4 sheets:
| Sheet | Content |
|-------|---------|
| `全部订单` | All item records with date, time, sender, customer, action, product, quantity, unit |
| `按客户汇总` | Order count per customer |
| `按商品汇总` | Frequency per product |
| `按操作汇总` | Count by action type (purchase/return/etc.) |

## Important Notes

- **Phone must stay awake** during ADB screenshot capture
- **Do not interact** with the phone while screenshot script runs
- **Sender names** must be identified manually from OCR output — provide them to the parser script
- **OCR accuracy** varies with image quality; manually verify critical entries
- For very long chats (>50 screens), consider capturing in segments to avoid memory issues
- If `batch_ocr.py` fails on large images, it auto-splits into chunks; results are merged and deduplicated
