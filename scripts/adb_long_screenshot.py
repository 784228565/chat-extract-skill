#!/usr/bin/env python3
"""
ADB 滚动长截屏工具 v3.0 —— 基于用户提供的思路改进
核心滑动策略：从屏幕 50% 滑到 25%，duration=900ms（慢速减少惯性）
拼接：本地相位相关法 + Alpha 融合（不依赖外部 HTTP 服务）

用法:
    python adb_long_screenshot_v3.py [输出目录] [选项]
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def run_adb(cmd, timeout=30):
    full_cmd = f"adb {cmd}"
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        err = result.stderr.strip()
        if err:
            print(f"[ADB 错误] {err}")
    return result.stdout.strip(), result.returncode


def get_screen_size():
    out, rc = run_adb("shell wm size")
    if rc != 0 or "x" not in out:
        return 1080, 2400
    for part in out.split():
        if "x" in part:
            try:
                w, h = map(int, part.split("x"))
                return w, h
            except ValueError:
                continue
    return 1080, 2400


def capture_screenshot(index, output_dir):
    remote_path = f"/sdcard/adb_ss_v3_{index:03d}.png"
    local_path = output_dir / f"screenshot_{index:03d}.png"

    _, rc1 = run_adb(f"shell screencap -p {remote_path}")
    if rc1 != 0:
        return None

    _, rc2 = run_adb(f"pull {remote_path} \"{local_path}\"")
    if rc2 != 0:
        return None

    run_adb(f"shell rm {remote_path}")
    return local_path


def swipe_up_v3(w, h, duration=900):
    """
    用户提供的滑动策略：从屏幕 50% 滑到 25%
    滑动距离 = 25% 屏高，duration=900ms（慢速减少惯性）
    """
    x1 = int(w * 0.5)
    x2 = int(w * 0.5)
    y1 = int(h * 0.5)
    y2 = int(h * 0.25)
    swipe_dist = y1 - y2

    print(f"    滑动: {swipe_dist}px ({x1},{y1})→({x2},{y2}), duration={duration}ms")
    run_adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    return swipe_dist


def phase_correlation_overlap(img1_path, img2_path):
    """相位相关法计算精确重叠偏移"""
    img1 = cv2.imread(str(img1_path))
    img2 = cv2.imread(str(img2_path))
    if img1 is None or img2 is None:
        return None, 0.0

    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    # 提取 img1 底部 50% 和 img2 顶部 50%+余量
    template_h = int(h1 * 0.50)
    search_h = int(h2 * 0.70)

    # 裁剪左右边距，避免曲面屏边缘干扰
    margin_x = int(w1 * 0.08)
    region1 = img1[h1 - template_h : h1, margin_x:-margin_x if margin_x > 0 else w1]
    region2 = img2[:search_h, margin_x:-margin_x if margin_x > 0 else w2]

    if region1.shape[0] < 50 or region2.shape[0] < 50:
        return None, 0.0

    # 预处理：高斯模糊 + 降采样加速
    gray1 = cv2.cvtColor(region1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(region2, cv2.COLOR_BGR2GRAY)
    gray1 = cv2.GaussianBlur(gray1, (5, 5), 1.0)
    gray2 = cv2.GaussianBlur(gray2, (5, 5), 1.0)

    # 降采样到 1/2 加速计算
    scale = 0.5
    g1s = cv2.resize(gray1, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    g2s = cv2.resize(gray2, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    try:
        (dx, dy_small), resp = cv2.phaseCorrelate(np.float32(g1s), np.float32(g2s))
    except cv2.error:
        return None, 0.0

    if resp < 0.15:
        return None, resp

    # 映射回原图分辨率
    dy = dy_small / scale
    overlap_y = template_h - dy

    # 合理性检查
    max_overlap = int(min(h1, h2) * 0.95)
    if overlap_y < 10 or overlap_y > max_overlap:
        return None, resp

    print(f"    相位相关: 重叠={overlap_y:.1f}px, 置信度={resp:.4f}")
    return max(0, overlap_y), resp


def template_match_fallback(img1_path, img2_path):
    """模板匹配 fallback"""
    img1 = cv2.imread(str(img1_path))
    img2 = cv2.imread(str(img2_path))
    if img1 is None or img2 is None:
        return None

    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    template_h = int(h1 * 0.45)
    template = img1[h1 - template_h :, :]
    search_h = int(h2 * 0.65)
    search_region = img2[:search_h, :]

    if search_region.shape[0] < template.shape[0]:
        return None

    result = cv2.matchTemplate(search_region, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < 0.55:
        return None

    if max_loc[1] > template_h:
        return None

    overlap_y = template_h - max_loc[1]
    max_reasonable = int(min(h1, h2) * 0.90)
    if overlap_y > max_reasonable:
        return None

    print(f"    模板匹配(fallback): 重叠={overlap_y}px, 置信度={max_val:.3f}")
    return max(0, overlap_y)


def find_overlap(img1_path, img2_path):
    """综合重叠检测"""
    overlap, confidence = phase_correlation_overlap(img1_path, img2_path)
    if overlap is not None and confidence >= 0.15:
        return overlap
    return template_match_fallback(img1_path, img2_path)


def images_are_similar(img1_path, img2_path, threshold=0.005):
    img1 = cv2.imread(str(img1_path))
    img2 = cv2.imread(str(img2_path))
    if img1 is None or img2 is None:
        return False
    if img1.shape != img2.shape:
        return False
    diff = cv2.absdiff(img1, img2)
    non_zero = np.count_nonzero(diff > 10)
    ratio = non_zero / diff.size
    print(f"    差异比例: {ratio:.4f}")
    return ratio < threshold


def alpha_blend_stitch(image_paths, overlap_heights, output_path):
    """Alpha 渐入渐出融合拼接"""
    if not image_paths:
        return

    images = [Image.open(str(p)).convert("RGB") for p in image_paths]
    widths = [img.width for img in images]
    min_width = min(widths)

    resized = []
    for img in images:
        if img.width != min_width:
            ratio = min_width / img.width
            new_h = int(img.height * ratio)
            resized.append(img.resize((min_width, new_h), Image.Resampling.LANCZOS))
        else:
            resized.append(img)

    while len(overlap_heights) < len(resized) - 1:
        overlap_heights.append(None)

    total_height = resized[0].height
    for i in range(1, len(resized)):
        overlap = overlap_heights[i - 1]
        if overlap is None or overlap <= 0 or overlap > resized[i - 1].height * 0.9:
            overlap = int(min(resized[i - 1].height, resized[i].height) * 0.40)
            print(f"  图片 {i} 使用默认重叠: {overlap}px")
        total_height += resized[i].height - overlap

    print(f"\n拼接后图片尺寸: {min_width} x {total_height}")
    result = np.zeros((total_height, min_width, 3), dtype=np.uint8)

    y_offset = 0
    img0_np = np.array(resized[0])
    h0 = img0_np.shape[0]
    result[y_offset:y_offset + h0, :] = img0_np
    y_offset += h0

    for i in range(1, len(resized)):
        overlap = overlap_heights[i - 1]
        if overlap is None or overlap <= 0 or overlap > resized[i - 1].height * 0.9:
            overlap = int(min(resized[i - 1].height, resized[i].height) * 0.40)

        curr_img = np.array(resized[i])
        curr_h = curr_img.shape[0]

        blend_h = min(overlap, curr_h)
        non_blend_h = curr_h - blend_h

        if non_blend_h > 0:
            paste_y = y_offset - overlap
            result[paste_y:paste_y + non_blend_h, :] = curr_img[:non_blend_h, :]

        if blend_h > 0:
            blend_y_start = y_offset - overlap + non_blend_h
            blend_y_end = blend_y_start + blend_h

            prev_blend = result[blend_y_start:blend_y_end, :].astype(np.float32)
            curr_blend = curr_img[non_blend_h:non_blend_h + blend_h, :].astype(np.float32)

            alpha = np.linspace(0, 1, blend_h).reshape(-1, 1, 1)
            blended = (1 - alpha) * prev_blend + alpha * curr_blend
            result[blend_y_start:blend_y_end, :] = blended.astype(np.uint8)

        y_offset = blend_y_start + blend_h

    # 裁剪底部空白
    non_zero_rows = np.where(np.any(result > 0, axis=(1, 2)))[0]
    if len(non_zero_rows) > 0:
        result = result[:non_zero_rows[-1] + 1, :]

    Image.fromarray(result).save(str(output_path), quality=95)
    print(f"长截图已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="ADB 滚动长截屏工具 v3.0")
    parser.add_argument("output_dir", nargs="?", default="./adb_screenshots_v3", help="输出目录")
    parser.add_argument("--max", type=int, default=50, help="最大截图次数")
    parser.add_argument("--delay", type=float, default=1.0, help="截图后等待秒数")
    parser.add_argument("--swipe-delay", type=float, default=1.0, help="滑动后等待秒数")
    parser.add_argument("--no-stitch", action="store_true", help="仅截图不拼接")
    parser.add_argument("--stop-similar", type=int, default=3, help="连续相似停止阈值")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    out, rc = run_adb("devices")
    if rc != 0 or "device" not in out:
        print("错误: ADB 未连接设备")
        sys.exit(1)

    devices = [line for line in out.splitlines() if "\tdevice" in line]
    if not devices:
        print("错误: 没有检测到已授权的设备")
        sys.exit(1)
    print(f"检测到设备: {devices[0].split()[0]}")

    w, h = get_screen_size()
    print(f"屏幕分辨率: {w}x{h}")
    print(f"输出目录: {output_dir.resolve()}")
    print(f"滑动策略: 50%→25% (距离={int(h*0.25)}px, duration=900ms)")
    print(f"最大截图: {args.max}张\n")

    print("=== 5秒后开始截图，请切换到目标页面 ===")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    screenshot_paths = []
    overlap_heights = []
    consecutive_similar = 0

    for i in range(args.max):
        print(f"\n[{i + 1}/{args.max}] 截图中...")
        path = capture_screenshot(i, output_dir)
        if path is None:
            print("截图失败，跳过")
            continue
        print(f"  已保存: {path.name}")
        screenshot_paths.append(path)

        if len(screenshot_paths) >= 2:
            if images_are_similar(screenshot_paths[-2], screenshot_paths[-1]):
                consecutive_similar += 1
                print(f"  检测到相似图片 ({consecutive_similar}/{args.stop_similar})")
                if consecutive_similar >= args.stop_similar:
                    print("\n已滑到底部，停止截图")
                    for _ in range(consecutive_similar):
                        p = screenshot_paths.pop()
                        if p.exists():
                            p.unlink()
                            print(f"  删除重复截图: {p.name}")
                    for _ in range(consecutive_similar - 1):
                        if overlap_heights:
                            overlap_heights.pop()
                    break
            else:
                consecutive_similar = 0

            print("  相位相关检测重叠...")
            overlap = find_overlap(screenshot_paths[-2], screenshot_paths[-1])
            overlap_heights.append(overlap)

        if i < args.max - 1:
            print(f"  向上滑动...")
            swipe_up_v3(w, h)
            time.sleep(args.swipe_delay)
            time.sleep(args.delay)

    print(f"\n共截取 {len(screenshot_paths)} 张图片")

    if not args.no_stitch and len(screenshot_paths) >= 2:
        stitched_path = output_dir / "long_screenshot.png"
        print("\n开始拼接长图（Alpha 融合）...")
        alpha_blend_stitch(screenshot_paths, overlap_heights, stitched_path)
    elif args.no_stitch:
        print("已跳过拼接")
    else:
        print("截图数量不足，无法拼接")

    print("\n完成！")


if __name__ == "__main__":
    main()
