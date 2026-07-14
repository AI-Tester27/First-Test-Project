# Sparsa Homeoclinic — Backup & Restore Guide

These scripts use `mongodump` / `mongorestore` (already installed wherever MongoDB tools are present).
They work on Linux, macOS, and Windows (Git Bash / WSL).

## 1. What's in a backup?
- **MongoDB:** patients, cases, clinical notes, prescriptions (all versions), pharmacy dispense, payments, reminders, audit logs, users, counters.
- **Attachments:** stored in Emergent Object Storage — durable independently of these backups. Only file *references* are in MongoDB.

## 2. Manual one-off backup

```bash
chmod +x /app/scripts/backup.sh
/app/scripts/backup.sh
```

That's it. You'll get a tar.gz at `/var/backups/sparsa/sparsa_homeoclinic-YYYYMMDD-HHMMSS.tar.gz`.

### Environment variables (optional)
| Var                       | Default                       | Purpose                                 |
|--------------------------|--------------------------------|-----------------------------------------|
| `SPARSA_BACKUP_DIR`      | `/var/backups/sparsa`          | Where to write the `.tar.gz`            |
| `SPARSA_BACKUP_KEEP_DAYS`| `14`                           | Keep backups newer than this many days  |
| `MONGO_URL`              | `mongodb://localhost:27017`    | Mongo connection                        |
| `DB_NAME`                | `sparsa_homeoclinic`           | Database name                           |

## 3. Schedule it (DAILY at 23:00)

### A. Linux / macOS server PC (cron)

```bash
sudo mkdir -p /var/backups/sparsa
sudo chown $USER /var/backups/sparsa

# Edit your crontab
crontab -e
```

Add this line:
```
0 23 * * * /app/scripts/backup.sh >> /var/log/sparsa-backup.log 2>&1
```

Save and exit. Verify it's scheduled:
```bash
crontab -l
```

Test the script runs without errors before relying on it:
```bash
/app/scripts/backup.sh
ls -lh /var/backups/sparsa/
```

You should see something like:
```
-rw-r--r-- 1 user user 124K Feb 21 23:00 sparsa_homeoclinic-20260221-230000.tar.gz
```

Tail the log next morning to confirm:
```bash
tail -50 /var/log/sparsa-backup.log
```

### B. Windows server PC (Task Scheduler)

**Prerequisite:** install Git for Windows — it ships with `bash.exe` we need.

1. Open **Task Scheduler** (Windows search → "Task Scheduler") → click **Create Task** (right pane).
2. **General tab**
   - Name: `Sparsa Daily Backup`
   - Run whether user is logged on or not
   - Check "Run with highest privileges"
3. **Triggers tab** → New
   - Begin the task: **On a schedule**
   - Daily, Start: today at **23:00**
   - Repeat task every: leave blank (just daily)
4. **Actions tab** → New
   - Action: **Start a program**
   - Program/script: `C:\Program Files\Git\bin\bash.exe`
   - Add arguments: `-c "/c/app/scripts/backup.sh >> /c/Logs/sparsa-backup.log 2>&1"`
   - Start in: `C:\app\scripts`
5. **Conditions tab** → uncheck "Start the task only if the computer is on AC power"
6. Save (it will ask for the user password — enter the one that should own the backups).
7. **Test it:** right-click the task → **Run**. Then check `C:\Logs\sparsa-backup.log` and your `SPARSA_BACKUP_DIR`.

### C. Recommended: also backup off-site

The tar.gz files are tiny (few hundred KB to a few MB). Add a second step that syncs them off-machine:

**Linux** — rsync to NAS / external drive:
```
0 23 * * * /app/scripts/backup.sh && rsync -a /var/backups/sparsa/ user@nas.local:/sparsa-offsite/
```

**Windows** — Robocopy to OneDrive / Google Drive folder:
```
Program: robocopy
Arguments: C:\var\backups\sparsa C:\Users\YOU\OneDrive\sparsa-backups /MIR /R:2 /W:5
```

## 4. Restore from a backup

```bash
/app/scripts/restore.sh /var/backups/sparsa/sparsa_homeoclinic-20260221-230000.tar.gz
```

> ⚠️ `restore.sh` runs with `mongorestore --drop`, replacing existing collections. Make a fresh backup first if you're uncertain.

## 5. Verify integrity (recommended quarterly)

Pretend the clinic PC died and restore a backup onto a test mongo instance:

```bash
docker run --rm -d -p 27018:27017 --name sparsa-restore-test mongo:7
export MONGO_URL="mongodb://localhost:27018"
/app/scripts/restore.sh /var/backups/sparsa/your-latest.tar.gz
# Connect with mongosh and spot-check counts:
mongosh "mongodb://localhost:27018" --eval 'use sparsa_homeoclinic; db.patients.countDocuments(); db.cases.countDocuments();'
docker stop sparsa-restore-test
```

If counts match production, you're good.

## 6. Troubleshooting

| Symptom                                          | Fix                                                                 |
|--------------------------------------------------|---------------------------------------------------------------------|
| `mongodump: command not found`                   | Install MongoDB Database Tools (separate package on most distros)   |
| Task Scheduler "Last Run Result: 0x1"            | The script exited non-zero — open the log file to see the error     |
| Cron runs but no file appears                    | Cron uses minimal `$PATH`. Use absolute paths in the script (already done) |
| Backup folder fills the disk                     | Reduce `SPARSA_BACKUP_KEEP_DAYS`, or sync off-site and prune locally |
| Restore fails on indexes                         | `--drop` should handle it; if not, drop the DB manually first       |
