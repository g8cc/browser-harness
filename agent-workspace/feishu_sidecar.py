"""Feishu Sidecar Daemon — 敏感数据直填浏览器，不经过 Agent 上下文。

Usage:
    python feishu_sidecar.py           # 前台运行（调试用）
    python feishu_sidecar.py --daemon  # 后台运行（生产用）

数据流: 飞书消息回复 → 本进程内存 → browser-harness daemon IPC → CDP → 浏览器
Agent 脚本永远接触不到用户输入的值。

Instead of WebSocket event subscription (unreliable for card callbacks),
this daemon polls the im/v1/messages API for user text replies.
"""

import json
import os
import platform
import subprocess
import sys
import time

SIDECAR_DIR = "/tmp/bh-feishu-sidecar"
REGISTRY_DIR = os.path.join(SIDECAR_DIR, "registry")
STATUS_DIR = os.path.join(SIDECAR_DIR, "status")
PID_FILE = os.path.join(SIDECAR_DIR, "sidecar.pid")

BH_NAME = os.environ.get("BU_NAME", "default")
BH_LARK_PROFILE = os.environ.get("BH_LARK_PROFILE", "qs")
_IS_MAC = platform.system() == "Darwin"


def _lc(*args):
    """Build a lark-cli argv with --profile injected when BH_LARK_PROFILE is set."""
    if BH_LARK_PROFILE:
        return ["lark-cli", "--profile", BH_LARK_PROFILE, *args]
    return ["lark-cli", *args]


def _ensure_dirs():
    for d in (SIDECAR_DIR, REGISTRY_DIR, STATUS_DIR):
        os.makedirs(d, mode=0o700, exist_ok=True)


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)
    os.chmod(path, 0o600)


def _read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _safe_remove(path):
    try:
        os.unlink(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Browser-harness IPC (replicates _ipc.connect + _ipc.request + helpers.cdp)
# ---------------------------------------------------------------------------

def _bh_send(req):
    """Send a CDP command via browser-harness daemon IPC."""
    import socket

    sock_path = "/tmp/bu-%s.sock" % BH_NAME
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect(sock_path)
    s.sendall((json.dumps(req) + "\n").encode())
    data = b""
    while not data.endswith(b"\n"):
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
    s.close()
    return json.loads(data or b"{}")


def _bh_cdp(method, **params):
    result = _bh_send({"method": method, "params": params})
    if "error" in result:
        raise RuntimeError(result["error"])
    return result.get("result", {})


# ---------------------------------------------------------------------------
# CDP fill_input sequence (mirrors browser_harness.helpers.fill_input)
# ---------------------------------------------------------------------------

def _fill_input(selector, text):
    """Fill a browser input field via CDP. Value stays in this process only."""

    focus_js = (
        "(()=>{const e=document.querySelector(%s);if(!e)return false;"
        "e.focus();return true;})()"
    ) % json.dumps(selector)

    result = _bh_cdp("Runtime.evaluate", expression=focus_js, returnByValue=True)
    if result.get("result", {}).get("value") is not True:
        raise RuntimeError("Element not found: " + selector)

    select_mod = 4 if _IS_MAC else 2
    _bh_cdp("Input.dispatchKeyEvent", type="rawKeyDown", key="a", code="KeyA",
            modifiers=select_mod, windowsVirtualKeyCode=65, nativeVirtualKeyCode=65)
    _bh_cdp("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA",
            modifiers=select_mod, windowsVirtualKeyCode=65, nativeVirtualKeyCode=65)

    _bh_cdp("Input.dispatchKeyEvent", type="keyDown", key="Backspace", code="Backspace",
            windowsVirtualKeyCode=8, nativeVirtualKeyCode=8)
    _bh_cdp("Input.dispatchKeyEvent", type="keyUp", key="Backspace", code="Backspace",
            windowsVirtualKeyCode=8, nativeVirtualKeyCode=8)

    for ch in text:
        _bh_cdp("Input.dispatchKeyEvent", type="keyDown", key=ch, text=ch)
        if len(ch) == 1:
            _bh_cdp("Input.dispatchKeyEvent", type="char", text=ch)
        _bh_cdp("Input.dispatchKeyEvent", type="keyUp", key=ch)

    event_js = (
        "(()=>{const e=document.querySelector(%s);"
        "if(e){e.dispatchEvent(new Event('input',{bubbles:true}));"
        "e.dispatchEvent(new Event('change',{bubbles:true}));}})()"
    ) % json.dumps(selector)
    _bh_cdp("Runtime.evaluate", expression=event_js)


# ---------------------------------------------------------------------------
# Message polling (replaces WebSocket event subscription)
# ---------------------------------------------------------------------------

def _poll_messages(chat_id, since_time_ms, page_size=5):
    """Fetch recent messages from a chat via lark-cli API.

    Returns list of (sender_type, text, create_time_ms) tuples.
    """
    params = json.dumps({
        "container_id_type": "chat",
        "container_id": chat_id,
        "page_size": str(page_size),
        "sort_type": "ByCreateTimeDesc",
    })
    result = subprocess.run(
        _lc("api", "GET", "/open-apis/im/v1/messages",
            "--as", "bot", "--params", params),
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        resp = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if resp.get("code", -1) != 0:
        return []
    items = resp.get("data", {}).get("items", [])
    messages = []
    for item in items:
        create_ms = int(item.get("create_time", "0"))
        if create_ms <= since_time_ms:
            continue
        sender = item.get("sender", {})
        sender_type = sender.get("sender_type", "")
        msg_type = item.get("msg_type", "")
        if msg_type != "text":
            continue
        try:
            content = json.loads(item.get("body", {}).get("content", "{}"))
        except (json.JSONDecodeError, TypeError):
            continue
        text = content.get("text", "")
        if text:
            messages.append((sender_type, text, create_ms))
    return messages


# ---------------------------------------------------------------------------
# Sidecar main loop
# ---------------------------------------------------------------------------

def run_sidecar():
    """Main sidecar loop: poll registry files and check for user replies."""
    _ensure_dirs()

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    print("Sidecar daemon started (PID: %d)" % os.getpid(), flush=True)
    print("Polling for Feishu message replies...", flush=True)

    try:
        while True:
            try:
                entries = list(os.scandir(REGISTRY_DIR))
            except OSError:
                time.sleep(0.5)
                continue

            for entry in entries:
                if not entry.is_file() or not entry.name.endswith(".json"):
                    continue

                registry = _read_json(entry.path)
                if registry is None:
                    continue

                request_id = entry.name.replace(".json", "")
                chat_id = registry.get("chat_id")
                sent_time_ms = int(registry.get("sent_time_ms", "0"))
                selector = registry.get("selector")

                if not chat_id or not selector or not sent_time_ms:
                    continue

                messages = _poll_messages(chat_id, sent_time_ms)
                user_reply = None
                for sender_type, text, create_ms in messages:
                    if sender_type == "user":
                        user_reply = text
                        break

                if user_reply is not None:
                    _safe_remove(entry.path)
                    try:
                        _fill_input(selector, user_reply)
                        _write_json(
                            os.path.join(STATUS_DIR, request_id + ".json"),
                            {"status": "filled", "selector": selector},
                        )
                        print("Filled %s for request %s" % (selector, request_id),
                              flush=True)
                    except Exception as e:
                        _write_json(
                            os.path.join(STATUS_DIR, request_id + ".json"),
                            {"status": "error", "message": str(e)},
                        )
                        print("Fill error for %s: %s" % (request_id, e), flush=True)

            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        _safe_remove(PID_FILE)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        _ensure_dirs()
        if os.path.exists(PID_FILE):
            try:
                old_pid = int(open(PID_FILE).read().strip())
                os.kill(old_pid, 0)
                print("Sidecar already running (PID: %d)" % old_pid)
                sys.exit(0)
            except (OSError, ValueError):
                pass

        pid = os.fork()
        if pid > 0:
            print("Sidecar daemon started (PID: %d)" % pid)
            sys.exit(0)

        os.setsid()
        sys.stdin = open(os.devnull)
        sys.stdout = open(os.path.join(SIDECAR_DIR, "sidecar.log"), "a")
        sys.stderr = sys.stdout
        run_sidecar()
    else:
        run_sidecar()
