#!/usr/bin/env python3
"""
Agent 集成示例
展示如何在 Agent 工具中集成 cookies 管理
"""

import subprocess
import sys
import json


class CookiesManager:
    """Cookies 管理器"""
    
    def __init__(self, project_dir=None):
        if project_dir is None:
            project_dir = "/Users/wardonguo/Documents/work/code/AI/AIworkspace/browser-harness"
        self.project_dir = project_dir
        self.cli_path = f"{project_dir}/cookies-cli.sh"
    
    def check_status(self):
        """检查 cookies 状态"""
        try:
            result = subprocess.run(
                [self.cli_path, "status"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout.strip()
            
            if "STATUS=expired" in output:
                site = ""
                for line in output.split("\n"):
                    if line.startswith("SITE="):
                        site = line.split("=", 1)[1]
                return {
                    "status": "expired",
                    "site": site,
                    "need_login": True
                }
            elif "STATUS=valid" in output:
                return {
                    "status": "valid",
                    "need_login": False
                }
            else:
                return {
                    "status": "unknown",
                    "error": output
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def sync_cookies(self):
        """同步 cookies"""
        try:
            result = subprocess.run(
                [self.cli_path, "sync"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout.strip()
            
            if "SYNC=success" in output:
                return {
                    "success": True,
                    "message": "同步成功"
                }
            else:
                return {
                    "success": False,
                    "error": output
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_and_sync(self):
        """检查并同步"""
        status = self.check_status()
        
        if status.get("need_login"):
            return {
                "action": "need_login",
                "site": status.get("site", ""),
                "message": f"请在主浏览器登录 {status.get('site', '网站')}"
            }
        
        # 尝试同步
        sync_result = self.sync_cookies()
        
        if sync_result.get("success"):
            return {
                "action": "synced",
                "message": "cookies 已同步，可以无人值守操作"
            }
        else:
            return {
                "action": "sync_failed",
                "error": sync_result.get("error", "未知错误")
            }


def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print("用法: python agent-integration.py [check|sync|auto]")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = CookiesManager()
    
    if command == "check":
        result = manager.check_status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "sync":
        result = manager.sync_cookies()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "auto":
        result = manager.check_and_sync()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()