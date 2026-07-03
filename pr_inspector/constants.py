STATUS_GREEN = "GREEN_TECHNICALLY_READY"
STATUS_YELLOW = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
STATUS_RED = "RED_DO_NOT_MERGE"

OWNER_STATUS = {
    STATUS_GREEN: "🟢 سبز — از نظر فنی آماده است",
    STATUS_YELLOW: "🟡 زرد — فعلاً متوقف شود",
    STATUS_RED: "🔴 قرمز — ادغام نشود",
}
OWNER_INVALID = "⚪ گزارش نامعتبر — بررسی باید تکرار شود"

OWNER_ACTION = {
    STATUS_GREEN: "ادغام می‌تواند پس از تأیید لازم انجام شود.",
    STATUS_YELLOW: "فعلاً ادغام نشود؛ ابتدا اقدام مشخص‌شده انجام شود.",
    STATUS_RED: "ادغام نشود؛ ابتدا مشکل مسدودکننده برطرف شود.",
}
OWNER_INVALID_ACTION = "گزارش دیگر معتبر نیست و بررسی باید تکرار شود."

SPECIALIST_APPROVALS = {
    "HUMAN_TECHNICAL_REVIEW_REQUIRED",
    "SECURITY_OR_DOMAIN_SPECIALIST_REQUIRED",
}
DOMAIN_SPECIALIST_REQUIRED = {
    "AUTHENTICATION", "AUTHORIZATION", "PAYMENTS", "PERSONAL_DATA",
    "REGULATED_DATA", "CRYPTOGRAPHY", "DESTRUCTIVE_CHANGE",
    "DATABASE_MIGRATION", "PRODUCTION_INFRASTRUCTURE", "BACKUP_RECOVERY",
    "SECURITY_BOUNDARY", "SUPPLY_CHAIN", "SAFETY_CRITICAL",
    "PROTECTED_" + "CREDENTIALS",
}
