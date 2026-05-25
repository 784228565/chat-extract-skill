#!/usr/bin/env python3
"""Convert structured chat records to Excel."""
import json
import sys
from pathlib import Path

import pandas as pd


def normalize_records(data):
    """Support both nested and flat JSON formats."""
    if not data:
        return []

    # Detect format: nested (messages with items) vs flat (each item is a record)
    first = data[0]
    if "items" in first:
        # Nested format
        flat = []
        for msg in data:
            for item in msg.get("items", []):
                flat.append({
                    "日期": msg.get("date", ""),
                    "时间": msg.get("time", ""),
                    "发送者": msg.get("sender", ""),
                    "客户名": msg.get("customer", ""),
                    "操作类型": item.get("action", "购买"),
                    "商品名称": item.get("product", ""),
                    "数量": str(item.get("quantity", "")),
                    "单位": item.get("unit", ""),
                    "备注": msg.get("note", "") + (item.get("note", "")),
                })
        return flat
    else:
        # Flat format
        return [{
            "日期": r.get("date", ""),
            "时间": r.get("time", ""),
            "发送者": r.get("sender", ""),
            "客户名": r.get("customer", ""),
            "操作类型": r.get("action", "购买"),
            "商品名称": r.get("product", ""),
            "数量": str(r.get("quantity", "")),
            "单位": r.get("unit", ""),
            "备注": r.get("note", ""),
        } for r in data]


def export_excel(flat_records, output_path):
    df = pd.DataFrame(flat_records)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="全部订单", index=False)
        ws = writer.sheets["全部订单"]
        for column in ws.columns:
            max_len = max(len(str(cell.value) or "") for cell in column)
            ws.column_dimensions[column[0].column_letter].width = min(max_len + 2, 50)

        if len(df) > 0:
            cust = df.groupby("客户名").size().reset_index(name="订单项数").sort_values("订单项数", ascending=False)
            cust.to_excel(writer, sheet_name="按客户汇总", index=False)

            prod = df.groupby("商品名称").size().reset_index(name="出现次数").sort_values("出现次数", ascending=False)
            prod.to_excel(writer, sheet_name="按商品汇总", index=False)

            act = df.groupby("操作类型").size().reset_index(name="数量")
            act.to_excel(writer, sheet_name="按操作汇总", index=False)

    print(f"Excel saved: {output_path}")
    print(f"Total records: {len(df)}")
    return df


def main(structured_json_path, output_excel_path):
    with open(structured_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} records")

    flat = normalize_records(data)
    print(f"Normalized to {len(flat)} item records")

    df = export_excel(flat, output_excel_path)
    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_to_excel.py <structured_json> [output.xlsx]")
        print("")
        print("  structured_json: JSON with chat records (nested or flat format)")
        print("  output.xlsx    : Output Excel path (default: input_dir/orders.xlsx)")
        print("")
        print("Nested format:")
        print('  [{"date":"...","time":"...","sender":"...","customer":"...",')
        print('    "items":[{"product":"...","quantity":"100","unit":"袋","action":"购买"}]}]')
        print("")
        print("Flat format:")
        print('  [{"date":"...","time":"...","sender":"...","customer":"...",')
        print('    "product":"...","quantity":"100","unit":"袋","action":"购买"}]')
        sys.exit(1)

    json_path = sys.argv[1]
    default_output = str(Path(json_path).parent / "orders.xlsx")
    output = sys.argv[2] if len(sys.argv) > 2 else default_output
    main(json_path, output)
