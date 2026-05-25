# Chat Extract Skill

[English](#english) | [中文](#中文)

---

## 中文

### 简介

一个通过 ADB 连接安卓手机，自动滚动截取长截图并进行 OCR 文字识别，最终将聊天中的订单信息整理成 Excel 表格的工具。

本工具适用于：群聊订单汇总、客服聊天记录整理、农业供销订单提取等任何需要将手机聊天截图转换为结构化表格的场景。

### 功能

- **自动滚动长截图**：通过 ADB 连接安卓手机，模拟滑动并连续截图
- **智能拼接**：使用 OpenCV 相位相关法检测截图重叠区域，Alpha 融合拼接成长图
- **OCR 文字识别**：基于 RapidOCR 识别截图中的文字内容
- **Excel 导出**：将结构化数据导出为多 Sheet Excel（全部订单、按客户汇总、按商品汇总、按操作汇总）

### 环境要求

- Windows / macOS / Linux
- Android 手机（开启 USB 调试）
- ADB 工具已安装
- Python 3.8+

### 安装依赖

```bash
pip install Pillow numpy opencv-python rapidocr-onnxruntime pandas openpyxl
```

### 使用流程

#### 第一步：ADB 滚动截图

```bash
python scripts/adb_long_screenshot.py [输出目录]
```

#### 第二步：OCR 识别文字

```bash
# 识别长截图
python scripts/batch_ocr.py ./adb_screenshots/long_screenshot.png ./extracted/ocr_result.json

# 或识别多张截图
python scripts/batch_ocr.py ./adb_screenshots ./extracted/ocr_result.json
```

#### 第三步：整理结构化数据

根据 OCR 结果手动整理成 JSON 格式，参见 `SKILL.md` 中的数据格式说明。

#### 第四步：生成 Excel

```bash
python scripts/parse_to_excel.py ./extracted/structured_data.json ./extracted/orders.xlsx
```

### 免责声明

本工具仅通过 Android 官方 ADB 调试接口（`screencap`、`input swipe`）捕获用户手机屏幕上可见的内容，并使用 OCR 技术识别图片中的文字。

- **不涉及**破解、逆向工程任何即时通讯软件的通信协议
- **不涉及**访问任何软件的私有 API 或数据库
- **不绕过**任何软件的安全机制或限制
- 用户需确保使用本工具处理的内容已获得合法授权

---

## English

### Introduction

A tool that connects to an Android phone via ADB, automatically scrolls and captures long screenshots, performs OCR text recognition, and finally organizes order information from chat messages into an Excel spreadsheet.

This tool is suitable for: group chat order aggregation, customer service chat record organization, agricultural supply order extraction, or any scenario where mobile chat screenshots need to be converted into structured spreadsheets.

### Features

- **Auto-scrolling long screenshots**: Connect to an Android phone via ADB, simulate swiping and capture continuous screenshots
- **Smart stitching**: Uses OpenCV phase correlation to detect overlapping regions between screenshots, then stitches them into a long image with alpha blending
- **OCR text recognition**: Based on RapidOCR to recognize text content in screenshots
- **Excel export**: Exports structured data into a multi-sheet Excel file (All Orders, Summary by Customer, Summary by Product, Summary by Action)

### Requirements

- Windows / macOS / Linux
- Android phone (USB debugging enabled)
- ADB tools installed
- Python 3.8+

### Install Dependencies

```bash
pip install Pillow numpy opencv-python rapidocr-onnxruntime pandas openpyxl
```

### Workflow

#### Step 1: ADB Scrolling Screenshots

```bash
python scripts/adb_long_screenshot.py [output_dir]
```

#### Step 2: OCR Text Extraction

```bash
# Single long screenshot
python scripts/batch_ocr.py ./adb_screenshots/long_screenshot.png ./extracted/ocr_result.json

# Or multiple screenshots
python scripts/batch_ocr.py ./adb_screenshots ./extracted/ocr_result.json
```

#### Step 3: Organize Structured Data

Manually organize the OCR results into JSON format. See `SKILL.md` for data format specifications.

#### Step 4: Generate Excel

```bash
python scripts/parse_to_excel.py ./extracted/structured_data.json ./extracted/orders.xlsx
```

### Disclaimer

This tool only captures content visible on the user's phone screen through the official Android ADB debugging interface (`screencap`, `input swipe`), and uses OCR technology to recognize text in images.

- **Does NOT involve** cracking or reverse engineering the communication protocol of any instant messaging software
- **Does NOT involve** accessing any software's private API or database
- **Does NOT bypass** any software's security mechanisms or restrictions
- Users must ensure they have legal authorization to process the content using this tool
