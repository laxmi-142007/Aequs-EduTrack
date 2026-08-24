from pathlib import Path

p = Path(r"backend\templates\internships\portal.html")

s = p.read_text(encoding="utf-8-sig")

# IMPORTANT:
# These are Unicode escape sequences, so the terminal cannot corrupt them.
fixes = {
    "\u00f0\u0178\u0092\u00bc": "\U0001f4bc",  # 💼
    "\u00f0\u0178\u0093\u00a5": "\U0001f4e5",  # 📥
    "\u00f0\u0178\u008f\u00a2": "\U0001f3e2",  # 🏢
    "\u00f0\u0178\u017d\u0093": "\U0001f393",  # 🎓
    "\u00e2\u0161\u00a1": "\u26a1",            # ⚡
    "\u00f0\u0178\u2020\u0091": "\U0001f191",  # 🆑
    "\u00e2\u201a\u00b9": "\u20b9",             # ₹
    "\u00f0\u0178\u017d\u00af": "\U0001f3af",  # 🎯
    "\u00f0\u0178\u2011\u00a5": "\U0001f465",  # 👥
    "\u00f0\u0178\u201c": "\U0001f4c4",         # 📄
    "\u00f0\u0178\u201d\u00e4": "\U0001f504",  # 🔄
    "\u00f0\u0178\u201c\u2020": "\U0001f4c6",  # 📆
    "\u00f0\u0178\u2013\u00a8\u00ef\u00b8\u008f": "\U0001f5a8\ufe0f",
    "\u00e2\u0153\u2026": "\u2705",
    "\u00e2\u0161\u00a0\u00ef\u00b8\u008f": "\u26a0\ufe0f",
    "\u00f0\u0178\u201c\u00ef\u00b8\u008f": "\U0001f4dd",
    "\u00f0\u0178\u2017\u2011\u00ef\u00b8\u008f": "\U0001f5d1\ufe0f",
    "\u00f0\u0178\u00ab": "\U0001f52e",
    "\u00e2\u0153\u201c": "\u2713",
    "\u00e2\u0153\u00ef\u00b8\u008f": "\u2714\ufe0f",
    "\u00e2\u20ac\u00a2": "\u2022",
}

count = 0

for bad, good in fixes.items():
    n = s.count(bad)
    if n:
        s = s.replace(bad, good)
        count += n
        print("Fixed:", repr(bad), "->", repr(good), "count:", n)

# Entries that were already turned into ??
# We know exactly where these occur.
s = s.replace(
    "<span>??</span> + New Program Track",
    "<span>\U0001f3e2</span> + New Program Track"
)

s = s.replace(
    '<div class="kpi-icon">??</div>',
    '<div class="kpi-icon">\U0001f3e2</div>'
)

s = s.replace(
    "<span>??</span> Programs & Tracks",
    "<span>\U0001f3e2</span> Programs & Tracks"
)

s = s.replace(
    "<span>??</span> Eligible Candidates Pool",
    "<span>\U0001f3af</span> Eligible Candidates Pool"
)

s = s.replace(
    "<span>??</span> {{ prog.company_name }}",
    "<span>\U0001f3e2</span> {{ prog.company_name }}"
)

s = s.replace(
    '<h3 id="modal-program-title"><span>??</span> Create Internship Track</h3>',
    '<h3 id="modal-program-title"><span>\U0001f3e2</span> Create Internship Track</h3>'
)

s = s.replace(
    "<h3><span>??</span> Assign Candidate to Internship Track</h3>",
    '<h3><span>\U0001f3af</span> Assign Candidate to Internship Track</h3>'
)

p.write_text(s, encoding="utf-8", newline="")

# Verification
s = p.read_text(encoding="utf-8")

patterns = [
    "ðŸ",
    "â‚¹",
    "â€¢",
    "ï¸",
    "âœ",
    "âš",
]

print()
print("=" * 50)
print("REPAIR COMPLETE")
print("=" * 50)
print("Replacements:", count)

for x in patterns:
    print(repr(x), "remaining:", s.count(x))

print("Literal ?? remaining:", s.count("??"))

if any(x in s for x in patterns):
    print("WARNING: mojibake still exists")
elif "??" in s:
    print("WARNING: literal ?? still exists")
else:
    print("SUCCESS: FILE IS CLEAN")