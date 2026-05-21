# Sparsa Homeoclinic — Backup & Restore

These scripts use `mongodump` / `mongorestore` (already installed wherever MongoDB tools are present).
They work on Linux, macOS, and Windows (Git Bash / WSL).

## Daily backup

```bash
chmod +x /app/scripts/backup.sh
/app/scripts/backup.sh
```

### Environment variables (optional)
| Var                       | Default                       | Purpose                                 |
|--------------------------|--------------------------------|-----------------------------------------|
| `SPARSA_BACKUP_DIR`      | `/var/backups/sparsa`          | Where to write the `.tar.gz`            |
| `SPARSA_BACKUP_KEEP_DAYS`| `14`                           | Keep backups newer than this many days  |
| `MONGO_URL`              | `mongodb://localhost:27017`    | Mongo connection                        |
| `DB_NAME`                | `sparsa_homeoclinic`           | Database name                           |

### Schedule it
**Linux/macOS (cron — backup every night at 23:00):**
```
0 23 * * * /app/scripts/backup.sh >> /var/log/sparsa-backup.log 2>&1
```

**Windows (Task Scheduler):**
1. Open Task Scheduler → Create Task
2. Trigger: Daily 23:00
3. Action: Start a program
   - Program: `C:\Program Files\Git\bin\bash.exe`
   - Arguments: `-c "/c/app/scripts/backup.sh"`
4. Save & test.

## Restore

```bash
/app/scripts/restore.sh /var/backups/sparsa/sparsa_homeoclinic-20260221-230000.tar.gz
```

> ⚠️ `restore.sh` runs with `--drop`, replacing existing collections. Make a snapshot backup first if you're uncertain.

## What's inside a backup?
- All clinical data: patients, cases, clinical notes, prescriptions, pharmacy dispense, payments, reminders, audit logs, users, counters.
- **Attachments are stored in Emergent Object Storage**, not in MongoDB. They are durable independently of this backup. Only file *references* are in MongoDB.
