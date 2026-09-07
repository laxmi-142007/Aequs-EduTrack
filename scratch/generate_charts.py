import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

os.makedirs('docs/images', exist_ok=True)
os.makedirs('scratch/generated_charts', exist_ok=True)

# Set global styles
plt.rcParams['font.sans-serif'] = 'Segoe UI', 'DejaVu Sans', 'Arial'
plt.rcParams['font.family'] = 'sans-serif'

# -------------------------------------------------------------
# Chart 1: Comprehensive Gantt Chart (Aug 12 - Sep 07, 2026)
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(14, 7), dpi=300)

tasks = [
    ("Phase 1: Project Scaffolding & Core Architecture", "2026-08-12", "2026-08-13", "#2563eb"),
    ("Phase 2: REST APIs & Portal Foundation", "2026-08-13", "2026-08-18", "#3b82f6"),
    ("Phase 3: Major Feature Sprint & Global UI/UX", "2026-08-18", "2026-08-24", "#1d4ed8"),
    ("Phase 4: Auth, Bulk Operations & SQL Server", "2026-08-24", "2026-08-26", "#0284c7"),
    ("Phase 5: Internship & School Portal Completion", "2026-08-26", "2026-08-28", "#0d9488"),
    ("Phase 6: School APIs & Comprehensive Testing Suite", "2026-08-28", "2026-08-31", "#059669"),
    ("Phase 7: Eligibility Engine & Student Class Resolvers", "2026-08-31", "2026-09-02", "#10b981"),
    ("Phase 8: Inventory Supply Chain & Stock Tracking", "2026-09-01", "2026-09-04", "#8b5cf6"),
    ("Phase 9: Volunteer Portal, QR Generation & Public Forms", "2026-09-04", "2026-09-05", "#d97706"),
    ("Phase 10: Architectural Audit & Codebase Streamlining", "2026-09-05", "2026-09-07", "#dc2626"),
]

y_pos = range(len(tasks))
for i, (task_name, start_str, end_str, color) in enumerate(tasks):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    duration = (end - start).days + 1
    ax.barh(i, duration, left=mdates.date2num(start), height=0.55, align='center', color=color, alpha=0.88, edgecolor='#0f172a', linewidth=0.8)
    ax.text(mdates.date2num(start) + 0.15, i, f" {task_name}", va='center', ha='left', color='#ffffff', fontweight='bold', fontsize=9.5)

ax.set_yticks(y_pos)
ax.set_yticklabels([t[0].split(':')[0] for t in tasks], fontsize=10, fontweight='bold', color='#1e293b')
ax.invert_yaxis()

ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.grid(axis='x', linestyle='--', alpha=0.45, color='#94a3b8')

ax.set_title("Aequs EduTrack — Project Development Gantt Chart (Aug 12 – Sep 07, 2026)", fontsize=14, fontweight='bold', pad=18, color='#0f172a')
plt.xlabel("Development Timeline", fontsize=11, fontweight='bold', labelpad=10, color='#334155')
plt.tight_layout()

for out_p in ["docs/images/gantt_chart.png", "scratch/generated_charts/gantt_chart.png"]:
    plt.savefig(out_p, dpi=300)
plt.close()
print("Gantt chart saved.")

# -------------------------------------------------------------
# Chart 2: Module Evolution & Feature Maturity
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(13, 7.5), dpi=300)

modules = [
    ("Accounts & RBAC", [("Aug 12", "Init"), ("Aug 18", "Branding"), ("Aug 24", "Auth Flow")]),
    ("Academics", [("Aug 12", "Models"), ("Aug 13", "Portal UI"), ("Aug 18", "Sync"), ("Aug 25", "Class Master"), ("Aug 28", "API Suite")]),
    ("Schools", [("Aug 12", "Directory"), ("Aug 13", "Seed"), ("Aug 28", "Portal Views & CRUD API")]),
    ("Students", [("Aug 12", "Core"), ("Aug 18", "Filter Bar"), ("Aug 24", "Bulk Upload"), ("Aug 31", "Equivalents")]),
    ("Eligibility", [("Aug 12", "Rules"), ("Aug 18", "Sync"), ("Aug 24", "Matrix"), ("Aug 31", "Bugfix & Clean")]),
    ("Inventory & Laptops", [("Aug 12", "Laptops"), ("Aug 13", "Warehouse"), ("Aug 18", "Merge"), ("Sep 01", "Requests"), ("Sep 02", "Tracking")]),
    ("Internships", [("Aug 18", "Models"), ("Aug 26", "Portal Complete"), ("Sep 05", "Docs UI")]),
    ("Events", [("Aug 18", "Scaffolding"), ("Sep 01", "Inventory Link"), ("Sep 05", "Integration")]),
    ("Volunteers", [("Aug 18", "Models"), ("Sep 05", "Portal, QR & Public Form")]),
    ("Reports & Audit", [("Aug 18", "Logs"), ("Sep 04", "JSON API"), ("Sep 05", "Dashboards")]),
]

y_pos = range(len(modules))
for i, (mod_name, events) in enumerate(modules):
    ax.hlines(y=i, xmin=0, xmax=len(events)-1, color='#cbd5e1', linestyle='-', linewidth=2.5, zorder=1)
    for j, (dt, label) in enumerate(events):
        ax.scatter(j, i, color='#2563eb', s=160, edgecolors='#1e3a8a', linewidths=2, zorder=2)
        ax.text(j, i + 0.22, f"{dt}\n{label}", ha='center', va='bottom', fontsize=8, fontweight='bold', color='#1e293b')

ax.set_yticks(y_pos)
ax.set_yticklabels([m[0] for m in modules], fontsize=10.5, fontweight='bold', color='#0f172a')
ax.invert_yaxis()
ax.set_xticks([])
ax.set_xlim(-0.6, 4.6)
ax.set_ylim(len(modules) - 0.3, -0.6)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['left'].set_visible(False)

ax.set_title("Aequs EduTrack — Module Evolution & Release Timeline", fontsize=14, fontweight='bold', pad=20, color='#0f172a')
plt.tight_layout()

for out_p in ["docs/images/module_evolution.png", "scratch/generated_charts/module_evolution.png"]:
    plt.savefig(out_p, dpi=300)
plt.close()
print("Module evolution saved.")

# -------------------------------------------------------------
# Chart 3: Development Phases Summary (Commits & 2-Contributor Share)
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

phases = [
    "P1: Foundation\n(Aug 12)",
    "P2: REST APIs\n(Aug 13)",
    "P3: UI & Deploy\n(Aug 18)",
    "P4: Auth & Bulk\n(Aug 24)",
    "P5: Academics & DB\n(Aug 25-27)",
    "P6: Schools & Test\n(Aug 28)",
    "P7: Fixes & Docs\n(Aug 31)",
    "P8: Inventory\n(Sep 1-2)",
    "P9: Volunteers\n(Sep 4-5)",
    "P10: Audit\n(Sep 7)",
]
commits_per_phase = [2, 1, 19, 3, 6, 6, 5, 5, 14, 1]

bars = ax1.bar(range(len(phases)), commits_per_phase, color='#3b82f6', edgecolor='#1e3a8a', linewidth=1, alpha=0.9)
bars[2].set_color('#1d4ed8')  # Peak 1 (Aug 18)
bars[8].set_color('#2563eb')  # Peak 2 (Sep 05)

for bar in bars:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.3, f"{int(yval)}", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#1e293b')

ax1.set_xticks(range(len(phases)))
ax1.set_xticklabels(phases, rotation=45, ha='right', fontsize=8.5, fontweight='bold', color='#334155')
ax1.set_ylabel("Number of Commits", fontsize=10, fontweight='bold', color='#1e293b')
ax1.set_title("Commit Distribution Across Phases", fontsize=12, fontweight='bold', pad=12, color='#0f172a')
ax1.grid(axis='y', linestyle='--', alpha=0.5)

# Authors: Rishab (Code-Cool-2006) and salonidalvi-008
authors = [
    'Rishab / Code-Cool-2006\n(42 commits / 69%)',
    'Saloni Dalvi / salonidalvi-008\n(19 commits / 31%)'
]
counts = [42, 19]
colors = ['#2563eb', '#0d9488']

wedges, texts, autotexts = ax2.pie(
    counts, labels=authors, autopct='%1.0f%%', startangle=140,
    colors=colors, explode=(0.04, 0.04), textprops={'fontsize': 10, 'weight': 'bold'}
)
for at in autotexts:
    at.set_color('white')
    at.set_fontsize(12)

ax2.set_title("Team Commit Share (61 Total Commits - 2 Contributors)", fontsize=12, fontweight='bold', pad=12, color='#0f172a')

plt.tight_layout()
for out_p in ["docs/images/phases_summary.png", "scratch/generated_charts/phases_summary.png"]:
    plt.savefig(out_p, dpi=300)
plt.close()
print("Phases summary saved.")
