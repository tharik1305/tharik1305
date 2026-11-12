#!/usr/bin/env python3
"""Regenerate the retro TV using live GitHub statistics."""
import json, os, re, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

USER = os.environ.get("GITHUB_PROFILE", "tharik1305")
TOKEN = os.environ["GH_STATS_TOKEN"]
ROOT = Path(__file__).resolve().parents[1]

def request(url, payload=None):
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
               "User-Agent": "profile-tv-generator", "X-GitHub-Api-Version": "2022-11-28"}
    data = json.dumps(payload).encode() if payload else None
    if data: headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

user = request(f"https://api.github.com/users/{USER}")
now = datetime.now(timezone.utc)
start = now - timedelta(days=365)
# Match GitHub's rolling "last year" contribution window.
graphql = request("https://api.github.com/graphql", {"query": """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
      totalCommitContributions
      totalPullRequestContributions
    }
  }
}
""", "variables": {
    "login": USER,
    "from": start.isoformat().replace("+00:00", "Z"),
    "to": now.isoformat().replace("+00:00", "Z"),
}})
if graphql.get("errors"): raise RuntimeError(graphql["errors"])
collection = graphql["data"]["user"]["contributionsCollection"]
contrib = collection["contributionCalendar"]["totalContributions"]
commits = collection["totalCommitContributions"]
prs = collection["totalPullRequestContributions"]
followers = user["followers"]
repos = user["public_repos"]

svg = (ROOT / "tv-template.svg").read_text(encoding="utf-8")
# Replace only channel 1: preserve original TV frame and other three animated channels.
start = svg.index('<g class="ch0"')
end = svg.index('<g class="ch1"', start)
lines = [
    ("CONTRIB", contrib),
    ("COMMITS", commits),
    ("PULL REQ", prs),
    ("FOLLOWERS", followers),
    ("PUBLIC REPOS", repos),
]
body = ['<g class="ch0" shape-rendering="crispEdges">',
        '<text x="130" y="122" font-family="monospace" font-size="26" font-weight="bold" fill="#7ee787">STATS</text>',
        '<text x="610" y="122" text-anchor="end" font-family="monospace" font-size="20" fill="#7ee787">CH 01</text>']
for i, (label, value) in enumerate(lines):
    y = 182 + i * 48
    body += [f'<text x="130" y="{y}" font-family="monospace" font-size="19" fill="#4b8f55">{label}</text>',
             f'<text x="460" y="{y}" font-family="monospace" font-size="26" font-weight="bold" fill="#7ee787">{value:,}</text>']
body.append('</g>')
svg = svg[:start] + ''.join(body) + svg[end:]
# Keep Channel 04's contribution summary in sync with the same rolling 365-day total.
svg = re.sub(r'last 26 weeks · \d+ contributions',
             f'last 365 days · {contrib} contributions', svg)
# Show when data was last fetched, not a misleading live counter.
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
svg = svg.replace('</svg>', f'<text x="440" y="501" text-anchor="middle" font-family="monospace" font-size="10" fill="#7ee787">UPDATED {stamp}</text></svg>')
(ROOT / "tv-set.svg").write_text(svg, encoding="utf-8")
print(f"Updated TV: contributions={contrib}, commits={commits}, PRs={prs}, followers={followers}, repos={repos}")
