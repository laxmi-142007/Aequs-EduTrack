from pathlib import Path

p = Path(r"backend\templates\internships\portal.html")
s = p.read_text(encoding="utf-8-sig")

fixes = {
    "ðŸ¢": "\U0001F3E2",
    "ðŸ†": "\U0001F195",
    "ðŸ”": "\U0001F504",
    "ðŸ…": "\U0001F3C6",
    "ðŸ—‘ï¸": "\U0001F5D1\U0000FE0F",
    "ðŸ«": "\U0001F3EB",
}

for bad, good in fixes.items():
    s = s.replace(bad, good)

p.write_text(s, encoding="utf-8-sig")
print("Emoji cleanup completed.")
