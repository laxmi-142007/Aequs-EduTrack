from pathlib import Path

p = Path(r"backend\templates\internships\portal.html")
s = p.read_text(encoding="utf-8-sig")

# Replace corrupted emoji with ASCII HTML entities.
# HTML will render these correctly without storing emoji bytes in the file.
fixes = {
    "ðŸ¢": "&#127970;",       # 🏢
    "ðŸ†": "&#127359;",       # 🆕
    "ðŸ”": "&#128257;",       # 🔁
    "ðŸ…": "&#127942;",       # 🏆
    "ðŸ—‘ï¸": "&#128465;&#65039;",  # 🗑️
    "ðŸ«": "&#127979;",       # 🏫
}

for bad, good in fixes.items():
    s = s.replace(bad, good)

p.write_text(s, encoding="utf-8-sig")
print("Final icon cleanup completed.")
