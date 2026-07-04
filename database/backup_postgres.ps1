# PowerShell automated Postgres Backup script for Churn Prediction Database
# Saved at: database/backup_postgres.ps1

# Configurable parameters
$DbName = "subscription_churn_db"
$DbUser = "postgres"
$DbHost = "localhost"
$DbPort = "5432"
$BackupDir = "C:\Users\shrut\OneDrive\Desktop\team_3\bootcamp-ace-26-team-3\database\backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = "$BackupDir\db_backup_$Timestamp.dump"
$LogFile = "$BackupDir\backup_log.txt"

# Ensure backup directory exists
if (!(Test-Path -Path $BackupDir)) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
}

# Write starting log
"[$Timestamp] PostgreSQL backup started." | Out-File -FilePath $LogFile -Append

# Read password from environment or fallback to database config file
if ($env:PGPASSWORD -eq $null -or $env:PGPASSWORD -eq "") {
    # Check if a local config file exists
    $ConfigPath = Join-Path (Split-Path $MyInvocation.MyCommand.Path) ".env.db"
    if (Test-Path -Path $ConfigPath) {
        $Config = Get-Content $ConfigPath | ConvertFrom-StringData
        if ($Config.ContainsKey("PGPASSWORD")) {
            $env:PGPASSWORD = $Config["PGPASSWORD"]
        }
    }
}

# Find pg_dump.exe in common installation paths if it is not already in PATH
$PgDumpPath = "pg_dump.exe"
if (!(Get-Command $PgDumpPath -ErrorAction SilentlyContinue)) {
    $CommonPaths = @(
        "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\13\bin\pg_dump.exe"
    )
    foreach ($Path in $CommonPaths) {
        if (Test-Path -Path $Path) {
            $PgDumpPath = $Path
            break
        }
    }
}

"[$Timestamp] Using pg_dump from: $PgDumpPath" | Out-File -FilePath $LogFile -Append

# Execute backup
& $PgDumpPath -U $DbUser -h $DbHost -p $DbPort -F c -b -v -f $BackupFile $DbName 2>> $LogFile

if ($LASTEXITCODE -eq 0) {
    "[$Timestamp] PostgreSQL backup succeeded: $BackupFile" | Out-File -FilePath $LogFile -Append
    
    # Clean up backups older than 14 days
    $LimitDate = (Get-Date).AddDays(-14)
    $OldBackups = Get-ChildItem -Path $BackupDir -Filter "*.dump" | Where-Object { $_.CreationTime -lt $LimitDate }
    foreach ($File in $OldBackups) {
        Remove-Item -Force $File.FullName
        "[$Timestamp] Removed expired backup: $($File.Name)" | Out-File -FilePath $LogFile -Append
    }
    "[$Timestamp] PostgreSQL backup cleanup finished." | Out-File -FilePath $LogFile -Append
} else {
    "[$Timestamp] PostgreSQL backup failed with exit code $LASTEXITCODE. Verify log entries above." | Out-File -FilePath $LogFile -Append
}

# Clear password environment variable for security
$env:PGPASSWORD = $null
