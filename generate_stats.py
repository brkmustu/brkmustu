import os
import json
import urllib.request
from datetime import datetime

USERNAME = os.environ.get("GITHUB_ACTOR")
TOKEN = os.environ.get("GH_TOKEN")

def fetch_github_stats():
    query = """
    query($login: String!) {
      user(login: $login) {
        name
        login
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes {
            stargazers { totalCount }
            forks { totalCount }
            languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
          totalPullRequestContributions
          totalIssueContributions
        }
      }
    }
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USERNAME}}).encode("utf-8"),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))["data"]["user"]

def update_history(stats):
    history_file = "stats-history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    history = json.loads(content)
        except Exception:
            history = []
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    # Aynı gün içinde birden fazla çalışırsa üzerine yaz
    history = [entry for entry in history if entry["date"] != today]
    history.append({
        "date": today,
        "stars": stats["stars"],
        "commits": stats["commits"],
        "prs": stats["prs"],
        "issues": stats["issues"],
        "followers": stats["followers"]
    })
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    return history

def generate_svg(stats, history):
    # İlk kayıttan bugüne farkı hesapla (Büyüme göstergesi)
    first_record = history[0] if history else stats
    star_diff = stats["stars"] - first_record["stars"]
    star_badge = f"+{star_diff} (Takip Başlangıcından Beri)" if star_diff > 0 else "Aktif Takip Ediliyor"

    langs_svg = ""
    y_offset = 175
    for lang, data in stats["top_langs"]:
        percent = data["percent"]
        color = data["color"] or "#58a6ff"
        bar_width = int((percent / 100) * 180)
        langs_svg += f"""
        <g transform="translate(260, {y_offset})">
          <circle cx="6" cy="-4" r="5" fill="{color}" />
          <text x="18" y="0" fill="#c9d1d9" font-size="12" font-family="Segoe UI, Ubuntu, sans-serif">{lang} ({percent:.1f}%)</text>
          <rect x="0" y="6" width="180" height="6" rx="3" fill="#21262d" />
          <rect x="0" y="6" width="{max(bar_width, 4)}" height="6" rx="3" fill="{color}" />
        </g>
        """
        y_offset += 32

    svg_content = f"""<svg width="480" height="285" viewBox="0 0 480 285" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="478" height="283" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="2"/>
      
      <!-- Başlık -->
      <text x="25" y="38" fill="#58a6ff" font-size="18" font-weight="bold" font-family="Segoe UI, Ubuntu, sans-serif">
        {stats['name']} — GitHub İstatistikleri
      </text>
      <text x="25" y="56" fill="#8b949e" font-size="11" font-family="Segoe UI, Ubuntu, sans-serif">
        Son Güncelleme: {datetime.utcnow().strftime("%d.%m.%Y")} • Kayıtlı Gün: {len(history)} • {star_badge}
      </text>
      <line x1="25" y1="68" x2="455" y2="68" stroke="#21262d" stroke-width="1"/>

      <!-- Sol Sütun: Genel Metrikler -->
      <g transform="translate(25, 98)" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">
        <text x="0" y="0" fill="#8b949e">⭐ Toplam Star:</text>
        <text x="155" y="0" fill="#f0f6fc" font-weight="bold">{stats['stars']}</text>

        <text x="0" y="30" fill="#8b949e">🔥 Toplam Commit (1 Yıl):</text>
        <text x="155" y="30" fill="#f0f6fc" font-weight="bold">{stats['commits']}</text>

        <text x="0" y="60" fill="#8b949e">🚀 Pull Requests:</text>
        <text x="155" y="60" fill="#f0f6fc" font-weight="bold">{stats['prs']}</text>

        <text x="0" y="90" fill="#8b949e">🐛 Açılan Issue:</text>
        <text x="155" y="90" fill="#f0f6fc" font-weight="bold">{stats['issues']}</text>

        <text x="0" y="120" fill="#8b949e">📦 Public Repo Sayısı:</text>
        <text x="155" y="120" fill="#f0f6fc" font-weight="bold">{stats['repos']}</text>

        <text x="0" y="150" fill="#8b949e">👥 Takipçiler:</text>
        <text x="155" y="150" fill="#f0f6fc" font-weight="bold">{stats['followers']}</text>
      </g>

      <!-- Sağ Sütun: En Çok Kullanılan Diller -->
      <text x="260" y="98" fill="#58a6ff" font-size="13" font-weight="bold" font-family="Segoe UI, Ubuntu, sans-serif">
        En Çok Kullanılan Diller
      </text>
      {langs_svg}
    </svg>"""

    with open("stats-card.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)

if __name__ == "__main__":
    raw = fetch_github_stats()
    
    total_stars = sum(repo["stargazers"]["totalCount"] for repo in raw["repositories"]["nodes"])
    commits = raw["contributionsCollection"]["totalCommitContributions"] + raw["contributionsCollection"]["restrictedContributionsCount"]
    
    lang_totals = {}
    lang_colors = {}
    for repo in raw["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            size = edge["size"]
            lang_totals[name] = lang_totals.get(name, 0) + size
            lang_colors[name] = edge["node"]["color"]
            
    total_size = sum(lang_totals.values()) or 1
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:4]
    top_langs = [(name, {"percent": (size / total_size) * 100, "color": lang_colors[name]}) for name, size in sorted_langs]

    parsed_stats = {
        "name": raw["name"] or raw["login"],
        "stars": total_stars,
        "commits": commits,
        "prs": raw["contributionsCollection"]["totalPullRequestContributions"],
        "issues": raw["contributionsCollection"]["totalIssueContributions"],
        "repos": raw["repositories"]["totalCount"],
        "followers": raw["followers"]["totalCount"],
        "top_langs": top_langs
    }

    history_data = update_history(parsed_stats)
    generate_svg(parsed_stats, history_data)