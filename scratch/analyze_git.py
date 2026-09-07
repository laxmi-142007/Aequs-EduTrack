import subprocess
from collections import defaultdict

cmd = ['git', 'log', '--reverse', '--pretty=format:%H%x09%an%x09%ae%x09%ad%x09%s', '--date=format:%Y-%m-%d %H:%M']
res = subprocess.check_output(cmd, encoding='utf-8')
commits = []
for line in res.strip().split('\n'):
    parts = line.split('\t')
    if len(parts) >= 5:
        commits.append({
            'hash': parts[0][:7],
            'author': parts[1],
            'email': parts[2],
            'datetime': parts[3],
            'subject': parts[4]
        })

print(f"Total commits: {len(commits)}")
by_date = defaultdict(list)
by_author = defaultdict(int)
for c in commits:
    d = c['datetime'].split(' ')[0]
    by_date[d].append(c)
    by_author[c['author']] += 1

print("\nCommits by author:")
for a, cnt in sorted(by_author.items(), key=lambda x: -x[1]):
    print(f"  {a}: {cnt}")

print("\nCommits by date:")
for d, clist in sorted(by_date.items()):
    print(f"\n=== {d} ({len(clist)} commits) ===")
    for c in clist:
        t = c['datetime'].split(' ')[1]
        print(f"  [{t}] ({c['author']}) [{c['hash']}] {c['subject']}")
