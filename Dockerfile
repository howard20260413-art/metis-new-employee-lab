# METIS Linux 基礎實作關卡：新進員工日常作業與定期異常排查考核
# 平台會讓容器保持運作（keep_alive），所以這裡不需要 CMD。
FROM debian:stable-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps tar gzip grep sed coreutils findutils \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash student

# 建立工作區目錄架構（含空目錄 old_backup 與模擬系統日誌目錄）
RUN mkdir -p /home/student/old_backup /home/student/docs /home/student/.audit_vault /var/log/office \
    && chown -R student:student /home/student /var/log/office

# 複製一般工作檔案與干擾檔案（權限 644）
COPY --chown=student:student --chmod=0644 home/welcome.txt home/temp.log home/config.conf home/salary.csv home/notes_draft.txt /home/student/
COPY --chown=student:student --chmod=0644 home/docs/ /home/student/docs/
COPY --chown=student:student --chmod=0644 home/syslog /var/log/office/syslog

# 複製隱藏設定與受竄改機密檔案（初始權限過寬 666，考核需排查並收斂為 600）
COPY --chown=student:student --chmod=0644 home/.hidden_notice /home/student/.hidden_notice
COPY --chown=student:student --chmod=0666 home/.audit_vault/.intruder_manifest.txt /home/student/.audit_vault/.intruder_manifest.txt
COPY --chown=student:student --chmod=0755 home/.audit_vault/.exfil_sync.sh /home/student/.audit_vault/.exfil_sync.sh

# 模擬背景異常進程啟動腳本（於使用者首次互動或手動排查時可透過 ps 觀察；同時在 /etc/bash.bashrc 確保學生登入時背景進程存在）
RUN echo 'pgrep -f ".exfil_sync.sh" >/dev/null || (nohup /home/student/.audit_vault/.exfil_sync.sh >/dev/null 2>&1 &)' >> /etc/bash.bashrc
