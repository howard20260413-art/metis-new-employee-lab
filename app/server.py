#!/usr/bin/env python3
"""Metis 新進員工實作關卡輕量網頁伺服器與模擬環境狀態判定引擎"""

import json
import os
import re
import shlex
import shutil
import stat
import tarfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path("/opt/metis-lab")
STATIC_DIR = BASE_DIR / "app" / "static"
SEED_DIR = BASE_DIR / "seed_workspace"
WORK_ROOT = Path("/home/employee/workspace")

# 階段驗證碼與最終 Flag 定義
STAGE_TOKENS = {
    "stage1": "METIS-STAGE1-ONBOARD-OK",
    "stage2": "METIS-STAGE2-OPS-SECURE",
    "stage3": "METIS-STAGE3-INCIDENT-FIXED",
    "flag": "METIS{new_emp_audit_passed_2026}",
}


class LabState:
    """維護單機測試環境檔案系統與任務狀態"""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        if WORK_ROOT.exists():
            shutil.rmtree(WORK_ROOT)
        shutil.copytree(SEED_DIR, WORK_ROOT)
        # 設定初始權限（salary.csv 故意設為過寬的 644）
        salary_file = WORK_ROOT / "salary.csv"
        if salary_file.exists():
            os.chmod(salary_file, 0o644)
        # 確保隱藏目錄與機密檔案存在
        secret_dir = WORK_ROOT / "secret"
        secret_dir.mkdir(exist_ok=True)
        # 模擬進程清單（PID -> 進程資訊）
        self.processes = [
            {"pid": 101, "user": "root", "cpu": "0.1", "mem": "0.4", "cmd": "/sbin/init"},
            {"pid": 214, "user": "employee", "cpu": "0.3", "mem": "1.2", "cmd": "python3 /opt/metis-lab/app/server.py"},
            {"pid": 389, "user": "employee", "cpu": "0.0", "mem": "0.5", "cmd": "/usr/sbin/cron -f"},
            {"pid": 8742, "user": "employee", "cpu": "94.8", "mem": "18.5", "cmd": "/tmp/.cache_miner --daemon --stealth"},
            {"pid": 9104, "user": "employee", "cpu": "41.2", "mem": "6.1", "cmd": "bash -c /home/employee/workspace/secret/.exfil_sync.sh"},
        ]
        self.cwd = WORK_ROOT
        self.checked_in = False
        self.viewed_syslog_head = False
        self.viewed_syslog_tail = False
        self.stage3_unlocked = False
        self.incident_injected = False

    def inject_incident(self) -> None:
        """進入階段三（定期員工考核）時注入模擬入侵異常狀態"""
        if self.incident_injected:
            return
        self.incident_injected = True
        # 1. 被竄改權限的機密檔案
        audit_secret = WORK_ROOT / "secret" / ".intruder_manifest.txt"
        audit_secret.write_text(
            "=== 系統異常留存紀錄 ===\n"
            "入侵來源 IP: 10.99.14.22\n"
            "異常備份位置: /home/employee/workspace/secret/.intruder_manifest.txt\n"
            "聲明標記: METIS{new_emp_audit_passed_2026}\n"
            "備註: 管理員設定檔連接埠已被改回 80，且異常同步進程 PID 9104 仍在背景執行。\n",
            encoding="utf-8",
        )
        os.chmod(audit_secret, 0o666)
        # 2. 竄改 config.conf Port 為 9999
        cfg = WORK_ROOT / "config.conf"
        if cfg.exists():
            text = cfg.read_text(encoding="utf-8")
            text = re.sub(r"PORT=\d+", "PORT=9999", text)
            cfg.write_text(text, encoding="utf-8")
        # 3. 寫入入侵線索至 syslog
        syslog = WORK_ROOT / "var" / "log" / "syslog"
        with syslog.open("a", encoding="utf-8") as f:
            f.write(
                "Nov 19 10:42:11 office-host systemd[1]: ALERT unauthorized modification detected.\n"
                "Nov 19 10:42:15 office-host auditd[512]: Suspicious PID 9104 spawned; hidden artifact at secret/.intruder_manifest.txt\n"
            )

    def resolve_path(self, raw_path: str) -> Path:
        if raw_path in ("~", "~/"):
            return WORK_ROOT
        if raw_path.startswith("~/"):
            target = (WORK_ROOT / raw_path[2:]).resolve()
        elif raw_path.startswith("/home/employee/workspace"):
            target = Path(raw_path).resolve()
        elif raw_path.startswith("/var/log/"):
            target = (WORK_ROOT / raw_path.lstrip("/")).resolve()
        elif raw_path.startswith("/"):
            target = (WORK_ROOT / raw_path.lstrip("/")).resolve()
        else:
            target = (self.cwd / raw_path).resolve()
        # 限制所有操作皆在 WORK_ROOT 沙箱內，防止影響系統真實檔案
        if WORK_ROOT not in target.parents and target != WORK_ROOT:
            return WORK_ROOT
        return target

    def rel_display(self, path: Path) -> str:
        if path == WORK_ROOT:
            return "~"
        try:
            rel = path.relative_to(WORK_ROOT)
            return f"~/{rel.as_posix()}"
        except ValueError:
            return "/home/employee/workspace"

    def evaluate_tasks(self) -> dict:
        """即時評估 10 個日常任務與綜合情境題狀態"""
        # 任務 1：連線打卡上班（執行 whoami / pwd 確認）
        t1 = self.checked_in

        # 任務 2：探索工作環境（welcome.txt 仍可讀取且已進入/列出過目錄）
        welcome_src = WORK_ROOT / "welcome.txt"
        t2 = welcome_src.exists() and self.checked_in

        # 任務 3 & 4：建立 working/、寫入日報並改名為 daily_report.txt、備份 welcome.txt
        working_dir = WORK_ROOT / "working"
        daily_report = working_dir / "daily_report.txt"
        welcome_bak = working_dir / "welcome.txt"
        today_log = working_dir / "today_log.txt"

        t3 = working_dir.is_dir() and (
            (today_log.exists() and len(today_log.read_text(encoding="utf-8").strip()) > 0)
            or (daily_report.exists() and len(daily_report.read_text(encoding="utf-8").strip()) > 0)
        )
        t4 = (
            working_dir.is_dir()
            and welcome_bak.exists()
            and daily_report.exists()
            and not today_log.exists()
            and len(daily_report.read_text(encoding="utf-8").strip()) > 0
        )

        # 任務 5：清理 temp.log 與空目錄 old_backup/
        t5 = not (WORK_ROOT / "temp.log").exists() and not (WORK_ROOT / "old_backup").exists()

        stage1_done = all([t1, t2, t3, t4, t5])

        # 任務 6：日誌檢視（syslog 前後段）
        t6 = self.viewed_syslog_head and self.viewed_syslog_tail

        # 任務 7：修改 config.conf Port 為 8080
        cfg = WORK_ROOT / "config.conf"
        cfg_text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
        t7 = "PORT=8080" in cfg_text

        # 任務 8：打包 working/ 為 backup_day1.tar.gz 並解壓至 test/
        tar_path = WORK_ROOT / "backup_day1.tar.gz"
        test_dir = WORK_ROOT / "test"
        t8 = False
        if tar_path.exists() and test_dir.is_dir():
            extracted_files = list(test_dir.rglob("daily_report.txt"))
            t8 = len(extracted_files) > 0

        # 任務 9：salary.csv 權限收斂為 600
        salary_file = WORK_ROOT / "salary.csv"
        t9 = False
        if salary_file.exists():
            mode = stat.S_IMODE(salary_file.stat().st_mode)
            t9 = mode == 0o600

        # 任務 10：終止異常挖礦進程 PID 8742
        pids = {p["pid"] for p in self.processes}
        t10 = 8742 not in pids

        stage2_done = stage1_done and all([t6, t7, t8, t9, t10])

        if stage2_done and not self.stage3_unlocked:
            self.stage3_unlocked = True
            self.inject_incident()

        # 階段三：綜合情境異常排查（需終止 PID 9104、將 config.conf 改回 PORT=8080、且機密檔案權限收斂為 600）
        audit_secret = WORK_ROOT / "secret" / ".intruder_manifest.txt"
        secret_mode_ok = False
        if audit_secret.exists():
            secret_mode_ok = stat.S_IMODE(audit_secret.stat().st_mode) == 0o600

        stage3_done = (
            self.stage3_unlocked
            and (9104 not in pids)
            and ("PORT=8080" in cfg_text)
            and secret_mode_ok
        )

        return {
            "tasks": {
                "t1": t1,
                "t2": t2,
                "t3": t3,
                "t4": t4,
                "t5": t5,
                "t6": t6,
                "t7": t7,
                "t8": t8,
                "t9": t9,
                "t10": t10,
            },
            "stage1_done": stage1_done,
            "stage2_done": stage2_done,
            "stage3_unlocked": self.stage3_unlocked,
            "stage3_done": stage3_done,
            "tokens": {
                "stage1": STAGE_TOKENS["stage1"] if stage1_done else None,
                "stage2": STAGE_TOKENS["stage2"] if stage2_done else None,
                "stage3": STAGE_TOKENS["stage3"] if stage3_done else None,
            },
            "cwd": self.rel_display(self.cwd),
        }

    def run_command(self, raw_cmd: str) -> str:
        """執行受控 Linux 基礎指令模擬，支援管線與重導向"""
        cmd_line = raw_cmd.strip()
        if not cmd_line:
            return ""

        # 處理簡單輸出重導向 > 或 >>
        redirect_mode = None
        redirect_target = None
        if ">>" in cmd_line:
            parts = cmd_line.split(">>", 1)
            cmd_line, redirect_target = parts[0].strip(), parts[1].strip()
            redirect_mode = "a"
        elif ">" in cmd_line:
            parts = cmd_line.split(">", 1)
            cmd_line, redirect_target = parts[0].strip(), parts[1].strip()
            redirect_mode = "w"

        # 處理管線（例如 ps aux | grep ...）
        if "|" in cmd_line:
            segments = [s.strip() for s in cmd_line.split("|")]
            output = ""
            for seg in segments:
                output = self._exec_single(seg, stdin_text=output)
        else:
            output = self._exec_single(cmd_line)

        if redirect_mode and redirect_target:
            target_path = self.resolve_path(redirect_target)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with target_path.open(redirect_mode, encoding="utf-8") as f:
                f.write(output + ("\n" if output and not output.endswith("\n") else ""))
            return ""

        return output

    def _exec_single(self, seg: str, stdin_text: str = "") -> str:
        try:
            tokens = shlex.split(seg)
        except ValueError as e:
            return f"語法錯誤: {e}"
        if not tokens:
            return ""

        cmd, args = tokens[0], tokens[1:]

        if cmd == "help":
            return (
                "可用指令：whoami, pwd, ls [-la], cd <目錄>, mkdir <目錄>, touch <檔案>,\n"
                "echo <文字>, cat <檔案>, head [-n N] <檔案>, tail [-n N] <檔案>,\n"
                "cp <來源> <目的>, mv <來源> <目的>, rm <檔案>, rmdir <空目錄>,\n"
                "tar -czvf <壓縮檔> <目錄>, tar -xzvf <壓縮檔> [-C <目錄>],\n"
                "chmod <權限> <檔案>, ps [aux], grep <關鍵字>, kill <PID>, setport <埠號>"
            )

        if cmd == "whoami":
            self.checked_in = True
            return "employee"

        if cmd == "pwd":
            self.checked_in = True
            return "/home/employee/workspace" if self.cwd == WORK_ROOT else f"/home/employee/workspace/{self.cwd.relative_to(WORK_ROOT).as_posix()}"

        if cmd == "ls":
            show_all = any(a.startswith("-") and ("a" in a) for a in args)
            long_fmt = any(a.startswith("-") and ("l" in a) for a in args)
            path_args = [a for a in args if not a.startswith("-")]
            target = self.resolve_path(path_args[0]) if path_args else self.cwd
            if not target.exists():
                return f"ls: 無法存取 '{path_args[0]}': 沒有此一檔案或目錄"
            if target.is_file():
                return target.name
            entries = sorted(target.iterdir(), key=lambda p: p.name)
            lines = []
            for entry in entries:
                if not show_all and entry.name.startswith("."):
                    continue
                if long_fmt:
                    st = entry.stat()
                    perm = stat.filemode(st.st_mode)
                    oct_perm = oct(stat.S_IMODE(st.st_mode))[2:]
                    lines.append(f"{perm} ({oct_perm}) employee employee {st.st_size:>6} {entry.name}{'/' if entry.is_dir() else ''}")
                else:
                    lines.append(f"{entry.name}{'/' if entry.is_dir() else ''}")
            return "\n".join(lines)

        if cmd == "cd":
            target = self.resolve_path(args[0]) if args else WORK_ROOT
            if not target.exists() or not target.is_dir():
                return f"cd: {args[0] if args else '~'}: 沒有此一目錄"
            self.cwd = target
            return ""

        if cmd == "mkdir":
            if not args:
                return "mkdir: 缺少運算元"
            for a in args:
                if a.startswith("-"):
                    continue
                self.resolve_path(a).mkdir(parents=True, exist_ok=True)
            return ""

        if cmd == "touch":
            if not args:
                return "touch: 缺少檔案運算元"
            for a in args:
                p = self.resolve_path(a)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.touch(exist_ok=True)
            return ""

        if cmd == "echo":
            return " ".join(args)

        if cmd == "cat":
            if not args:
                return stdin_text
            out = []
            for a in args:
                p = self.resolve_path(a)
                if not p.exists() or p.is_dir():
                    out.append(f"cat: {a}: 沒有此一檔案")
                else:
                    out.append(p.read_text(encoding="utf-8", errors="replace").rstrip("\n"))
            return "\n".join(out)

        if cmd in ("head", "tail"):
            n = 10
            file_arg = None
            i = 0
            while i < len(args):
                if args[i] == "-n" and i + 1 < len(args):
                    n = int(args[i + 1])
                    i += 2
                elif args[i].startswith("-") and args[i][1:].isdigit():
                    n = int(args[i][1:])
                    i += 1
                else:
                    file_arg = args[i]
                    i += 1
            if file_arg:
                p = self.resolve_path(file_arg)
                if not p.exists() or p.is_dir():
                    return f"{cmd}: 無法開啟 '{file_arg}'"
                if p.name == "syslog":
                    if cmd == "head":
                        self.viewed_syslog_head = True
                    else:
                        self.viewed_syslog_tail = True
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            else:
                lines = stdin_text.splitlines()
            sliced = lines[:n] if cmd == "head" else lines[-n:]
            return "\n".join(sliced)

        if cmd == "cp":
            clean = [a for a in args if not a.startswith("-")]
            if len(clean) < 2:
                return "cp: 缺少檔案運算元"
            src, dst = self.resolve_path(clean[0]), self.resolve_path(clean[1])
            if not src.exists():
                return f"cp: 無法取得 '{clean[0]}' 的狀態"
            if dst.is_dir():
                dst = dst / src.name
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            return ""

        if cmd == "mv":
            if len(args) < 2:
                return "mv: 缺少檔案運算元"
            src, dst = self.resolve_path(args[0]), self.resolve_path(args[1])
            if not src.exists():
                return f"mv: 無法取得 '{args[0]}' 的狀態"
            if dst.is_dir():
                dst = dst / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return ""

        if cmd == "rm":
            clean = [a for a in args if not a.startswith("-")]
            if not clean:
                return "rm: 缺少運算元"
            for a in clean:
                p = self.resolve_path(a)
                if not p.exists():
                    return f"rm: 無法移除 '{a}': 沒有此一檔案或目錄"
                if p.is_dir():
                    return f"rm: 無法移除 '{a}': 是一個目錄（請用 rmdir）"
                p.unlink()
            return ""

        if cmd == "rmdir":
            if not args:
                return "rmdir: 缺少運算元"
            for a in args:
                p = self.resolve_path(a)
                if not p.exists() or not p.is_dir():
                    return f"rmdir: 移除 '{a}' 失敗: 不是目錄"
                if any(p.iterdir()):
                    return f"rmdir: 移除 '{a}' 失敗: 目錄非空"
                p.rmdir()
            return ""

        if cmd == "tar":
            if len(args) < 2:
                return "tar: 參數不足"
            flags = args[0]
            if "c" in flags:
                archive = self.resolve_path(args[1])
                target = self.resolve_path(args[2]) if len(args) > 2 else self.cwd
                if not target.exists():
                    return f"tar: {args[2]}: 無法開啟"
                with tarfile.open(archive, "w:gz") as tf:
                    tf.add(target, arcname=target.name)
                return f"已打包 {target.name} -> {archive.name}"
            if "x" in flags:
                archive = self.resolve_path(args[1])
                dest = self.cwd
                if "-C" in args:
                    idx = args.index("-C")
                    if idx + 1 < len(args):
                        dest = self.resolve_path(args[idx + 1])
                if not archive.exists():
                    return f"tar: {args[1]}: 無法開啟"
                dest.mkdir(parents=True, exist_ok=True)
                with tarfile.open(archive, "r:gz") as tf:
                    tf.extractall(dest, filter="data")
                return f"已解壓縮 {archive.name} 至 {self.rel_display(dest)}"
            return "tar: 請指定 -czvf 或 -xzvf"

        if cmd == "chmod":
            if len(args) < 2:
                return "chmod: 缺少運算元"
            mode_str, target_str = args[0], args[1]
            p = self.resolve_path(target_str)
            if not p.exists():
                return f"chmod: 無法存取 '{target_str}'"
            if not re.fullmatch(r"[0-7]{3}", mode_str):
                return "chmod: 請使用三位八進位權限碼（例如 600）"
            os.chmod(p, int(mode_str, 8))
            return ""

        if cmd in ("nano", "vim", "setport"):
            # 提供網頁內快速修改 config.conf 連接埠的相容指令
            if cmd == "setport" and args:
                cfg = WORK_ROOT / "config.conf"
                text = cfg.read_text(encoding="utf-8")
                text = re.sub(r"PORT=\d+", f"PORT={args[0]}", text)
                cfg.write_text(text, encoding="utf-8")
                return f"已將 config.conf 的 PORT 更新為 {args[0]}"
            return "提示：網頁終端機無全螢幕 TTY，請使用網頁右側「設定檔編輯器」或輸入 `setport 8080` 更新連接埠。"

        if cmd == "ps":
            header = "USER       PID %CPU %MEM COMMAND"
            rows = [
                f"{p['user']:<10} {p['pid']:<5} {p['cpu']:>4} {p['mem']:>4} {p['cmd']}"
                for p in self.processes
            ]
            return "\n".join([header] + rows)

        if cmd == "grep":
            if not args:
                return "grep: 缺少搜尋樣式"
            pattern = args[0]
            source_lines = []
            if len(args) > 1:
                p = self.resolve_path(args[1])
                if not p.exists() or p.is_dir():
                    return f"grep: {args[1]}: 沒有此一檔案"
                source_lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            else:
                source_lines = stdin_text.splitlines()
            matched = [line for line in source_lines if pattern in line]
            return "\n".join(matched)

        if cmd == "kill":
            clean = [a for a in args if not a.startswith("-")]
            if not clean or not clean[0].isdigit():
                return "kill: 請指定有效的數字 PID"
            pid = int(clean[0])
            before = len(self.processes)
            self.processes = [p for p in self.processes if p["pid"] != pid]
            if len(self.processes) == before:
                return f"kill: ({pid}) - 沒有此進程"
            return f"已終止進程 PID {pid}"

        return f"{cmd}: 找不到指令（輸入 help 查看支援指令）"


LAB_STATE = LabState()


class LabRequestHandler(BaseHTTPRequestHandler):
    """處理靜態網頁資源與關卡 API 請求"""

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._send_json(LAB_STATE.evaluate_tasks())
            return
        if parsed.path == "/api/config":
            cfg = WORK_ROOT / "config.conf"
            content = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
            self._send_json({"content": content})
            return

        rel_path = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
        file_path = (STATIC_DIR / rel_path).resolve()
        if STATIC_DIR not in file_path.parents and file_path != STATIC_DIR / "index.html":
            self.send_error(403)
            return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        mime = "text/plain; charset=utf-8"
        if file_path.suffix == ".html":
            mime = "text/html; charset=utf-8"
        elif file_path.suffix == ".css":
            mime = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            mime = "application/javascript; charset=utf-8"

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        data = json.loads(raw)

        if parsed.path == "/api/exec":
            output = LAB_STATE.run_command(data.get("cmd", ""))
            state = LAB_STATE.evaluate_tasks()
            self._send_json({"output": output, "state": state})
            return

        if parsed.path == "/api/config":
            cfg = WORK_ROOT / "config.conf"
            cfg.write_text(data.get("content", ""), encoding="utf-8")
            state = LAB_STATE.evaluate_tasks()
            self._send_json({"ok": True, "state": state})
            return

        if parsed.path == "/api/reset":
            LAB_STATE.reset()
            self._send_json({"ok": True, "state": LAB_STATE.evaluate_tasks()})
            return

        self.send_error(404)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 80), LabRequestHandler)
    print("Metis New Employee Lab running on port 80...")
    server.serve_forever()


if __name__ == "__main__":
    main()
