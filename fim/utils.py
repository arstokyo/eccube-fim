from datetime import timezone, timedelta
from pathlib import Path

# Japan Standard Time — used for timestamps throughout fim/
JST = timezone(timedelta(hours=9))

# Log directory created by install.sh; may not exist in test environments
LOG_DIR = Path("/var/log/eccube-fim")
