# metis-new-employee-lab

[METIS](https://github.com/codedriven101/metis) 的 Linux 基礎與資安排查關卡映像：學生以 `student` 登入一台 Linux 主機，透過 10 項新進員工日常維運任務與最終定期考核（系統異常排查），逐步取得各階段驗證碼與機密檔案中的最終 `FLAG`。

本專案結構對齊官方範本 `codedriven101/metis-linux-basics`，包含 `.github/workflows/build-image.yml`、`home/`、`Dockerfile` 與 `README.md`。

## 映像

```
ghcr.io/howard20260413-art/metis-new-employee-lab:v1.0.0
```

推送 `v*` tag 時由 GitHub Actions（`.github/workflows/build-image.yml`）自動建置並推送至 `ghcr.io`，job summary 會印出含 `@sha256:` 的完整名稱。

## 在關卡編輯器怎麼填

| 欄位 | 填什麼 |
| :-- | :-- |
| 目標 → 類型 | Linux 主機 |
| 映像 | `ghcr.io/howard20260413-art/metis-new-employee-lab:v1.0.0` |
| 登入使用者 | `student`（預設） |
| shell | `/bin/bash`（預設） |
| 難度／預估時間 | easy／30m |

### 題目設定（依序作答，共 3 題）

#### 第 1 題：階段一—新進員工報到與基礎檔案整理（任務 1～5）
* **題目說明**：
  > 歡迎加入研發維運部！請打開「目標主機」終端機，閱讀家目錄下的 `welcome.txt` 並列出隱藏檔案（`ls -la`），依序完成：建立 `working/` 目錄、撰寫 `today_log.txt` 並改名為 `daily_report.txt`、備份 `welcome.txt` 至 `working/`，以及清理 `temp.log` 與空目錄 `old_backup/`。完成後請檢視隱藏的內部稽核備忘取得階段一確認碼。
* **答案**：`FLAG{stage1_onboard_clean_ok}`（不要勾「忽略大小寫」）
* **提示**：
  1. 使用 `ls -la` 可以看到以 `.` 開頭的隱藏檔案 `.hidden_notice`。（扣分 0.1）
  2. 使用 `cat ~/.hidden_notice` 即可取得階段一確認碼。（扣分 0.3）

#### 第 2 題：階段二—系統日誌、組態、備份與權限維運（任務 6～10）
* **題目說明**：
  > 接著請檢視系統日誌 `/var/log/office/syslog`（分別使用 `head` 與 `tail` 查看前後段紀錄），依照日誌指示完成組態調整、打包備份還原測試、收斂機密薪資表權限，並取得階段二維運驗證碼。
* **答案**：`FLAG{stage2_ops_hardening_ok}`（不要勾「忽略大小寫」）
* **提示**：
  1. 系統日誌位於 `/var/log/office/syslog`，試試 `head -n 5 /var/log/office/syslog` 與 `tail -n 10 /var/log/office/syslog`。（扣分 0.1）
  2. 在 `syslog` 紀錄中尋找 `Stage2 Ops Verification Token` 那一行。（扣分 0.3）

#### 第 3 題（最終考核）：定期員工考核—入侵異常排查與機密 Flag 回報
* **題目說明**：
  > 部門主管突然通知：系統剛才偵測到異常入侵跡象！組態檔連接埠遭竄改、背景出現異常同步腳本進程，且入侵者在隱藏目錄留下了權限異常的機密聲明檔。請運用前兩階段所學（日誌排查、組態修復為 `PORT=8080`、終止異常進程、收斂機密檔權限為 `600`），找出機密檔案中的最終 `FLAG` 回報主管！
* **答案**：`FLAG{new_emp_audit_passed_2026}`（不要勾「忽略大小寫」）
* **提示**：
  1. 用 `tail -n 5 /var/log/office/syslog` 查看最新的 `ALERT` 警報，找出異常腳本與隱藏檔案路徑。（扣分 0.1）
  2. 檢查 `/home/student/.audit_vault/.intruder_manifest.txt`，修復異常狀態（`sed` 或編輯器改回 `PORT=8080`、`ps aux` 找出 `.exfil_sync.sh` 並 `kill`、`chmod 600` 收斂權限）後讀出 `FLAG=`。（扣分 0.3）

## 映像裡有什麼

| 路徑 | 擁有者／權限 | 用途 |
| :-- | :-- | :-- |
| `/home/student/welcome.txt` | student / 644 | 新人入職手冊與 10 項任務指引 |
| `/home/student/.hidden_notice` | student / 644 | 隱藏稽核備忘（含階段一確認碼） |
| `/home/student/temp.log`、`old_backup/` | student / 644 | 任務 5 需清理的暫存檔與空目錄 |
| `/home/student/notes_draft.txt`、`docs/*` | student / 644 | 干擾檔案與內部規範參考文件 |
| `/home/student/config.conf` | student / 644 | 服務組態檔（遭竄改為 `PORT=9999`，需修復為 `8080`） |
| `/home/student/salary.csv` | student / 644 | 機密薪資表（需用 `chmod 600` 收斂權限） |
| `/var/log/office/syslog` | student / 644 | 模擬系統與稽核日誌（含階段二驗證碼與入侵線索） |
| `/home/student/.audit_vault/.exfil_sync.sh` | student / 755 | 模擬背景異常進程腳本（需用 `ps` 與 `kill` 終止） |
| `/home/student/.audit_vault/.intruder_manifest.txt` | student / 666 | 被竄改權限的隱藏機密檔案（需設為 `600`，內含最終 `FLAG`） |

## 本機建置與驗證

```sh
# 建置測試映像
docker build -t metis-new-employee-lab:dev .

# 以 student 身分進入容器驗證（模擬 METIS Linux 主機環境）
docker run --rm -it -u student -w /home/student metis-new-employee-lab:dev bash
```

確認無誤後，推送 `v1.0.0` tag 至 GitHub，Actions 即會自動建置並推送 `ghcr.io/howard20260413-art/metis-new-employee-lab:v1.0.0`。
