# datatran_test.py - 传感器数据上报 / 模拟器
# 原版：一次性 POST 一组固定值。
# 升级版（2026-09-04）：可定时循环上报，数值带随机游走小波动，让 IoT 曲线动起来，更接近真实养殖水体。
#
# 用法（先启动系统，再在项目根运行）：
#   python tests/datatran_test.py                         # 每 3 秒无限循环，Ctrl+C 停止
#   python tests/datatran_test.py -n 1 -c 5               # 每 1 秒一次，共发 5 次后自动退出
#   python tests/datatran_test.py --temp 28 --ph 7.0 --oxygen 4.5   # 指定基准值
import argparse
import random
import time

import requests

URL = "http://127.0.0.1:5000/update_sensor"
AUTH_TOKEN = "fishery2026"   # 与 config.AUTH_TOKEN 保持一致
HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}

# 基准值与随机游走参数（模拟养殖水体的缓慢波动）
PARAMS = {
    "temp":   {"base": 26.0, "lo": 20.0, "hi": 32.0, "step": 0.30},
    "ph":     {"base": 7.2,  "lo": 6.5,  "hi": 8.5,  "step": 0.06},
    "oxygen": {"base": 6.0,  "lo": 4.0,  "hi": 9.0,  "step": 0.25},
}


def walk(key, cur):
    """带均值回归的随机游走：围绕 base 缓慢波动，钳制在 [lo, hi]。"""
    p = PARAMS[key]
    nxt = cur + random.uniform(-p["step"], p["step"])
    nxt += (p["base"] - nxt) * 0.15   # 轻微拉回基准，避免一路漂走
    return round(max(p["lo"], min(p["hi"], nxt)), 2)


def send(values):
    """POST 一组传感器值，返回服务器响应（JSON）。"""
    resp = requests.post(URL, json=values, headers=HEADERS, timeout=5)
    return resp.json()


def main():
    ap = argparse.ArgumentParser(description="传感器数据模拟上报")
    ap.add_argument("-n", "--interval", type=float, default=3.0, help="上报间隔秒（默认 3）")
    ap.add_argument("-c", "--count", type=int, default=0, help="上报次数（0 = 无限直到 Ctrl+C）")
    for k in PARAMS:
        ap.add_argument(f"--{k}", type=float, default=PARAMS[k]["base"], help=f"{k} 基准值")
    args = ap.parse_args()

    for k in PARAMS:
        PARAMS[k]["base"] = getattr(args, k)

    cur = {k: PARAMS[k]["base"] for k in PARAMS}
    sent = 0
    print("传感器模拟上报已启动 (Ctrl+C 停止)...", flush=True)
    try:
        while args.count == 0 or sent < args.count:
            cur = {k: walk(k, cur[k]) for k in PARAMS}
            values = {k: str(cur[k]) for k in PARAMS}   # 服务端按字符串存
            try:
                result = send(values)
                sent += 1
                ts = time.strftime("%H:%M:%S")
                print(f"[{ts}] #{sent} temp={values['temp']} ph={values['ph']} "
                      f"oxygen={values['oxygen']} -> {result}", flush=True)
            except requests.RequestException as e:
                print(f"[{time.strftime('%H:%M:%S')}] 上报失败（服务未启动？）: {e}", flush=True)
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n已停止（共上报 {sent} 次）。")


if __name__ == "__main__":
    main()
  
   