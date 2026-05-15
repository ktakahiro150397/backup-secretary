#!/usr/bin/env python3
"""Obsidian vault 自動整理スクリプト: ルートの .md をプロジェクトフォルダに自動分類 (標準ライブラリのみ)"""

import os
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime

VAULT = "/opt/data/obsidian/obsidian_git"

def run(cmd, cwd=VAULT, check=False):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result

def parse_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    current_key = None
    current_list = None
    for line in m.group(1).splitlines():
        stripped = line.rstrip()
        if not stripped:
            continue
        # リスト項
        if stripped.startswith('- '):
            if current_list is not None:
                current_list.append(stripped[2:].strip())
            continue
        # キー: バリュー
        kv = re.match(r'^([\w]+)\s*:\s*(.*)$', stripped)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val.startswith('[') and val.endswith(']'):
                # inline array → リストに
                inner = val[1:-1]
                fm[key] = [v.strip().strip('"\'') for v in inner.split(',') if v.strip()]
            elif val.startswith('"') and val.endswith('"'):
                fm[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                fm[key] = val[1:-1]
            else:
                fm[key] = val
            current_key = key
            current_list = None
            if val == '' or val.endswith(':'):
                # 空バリューで次の行からリストかも
                fm[key] = []
                current_list = fm[key]
        else:
            current_key = None
            current_list = None
    return fm

def dump_frontmatter(fm):
    lines = ["---"]
    for key, val in fm.items():
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        elif isinstance(val, str) and (':' in val or '"' in val or val.startswith('[')):
            lines.append(f'{key}: "{val}"')
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines)

def set_frontmatter(path, key, value):
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if not fm:
        fm = {"title": path.stem, "date": datetime.now().strftime("%Y-%m-%d"), "tags": []}
        body = text
    else:
        body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)
    fm[key] = value
    new_text = dump_frontmatter(fm) + "\n\n" + body.lstrip()
    path.write_text(new_text, encoding="utf-8")

def get_projects():
    proj_dir = Path(VAULT) / "10_Projects"
    if not proj_dir.exists():
        return []
    return [d.name for d in proj_dir.iterdir() if d.is_dir()]

def score_project(filepath, content, projects):
    scores = {}
    name_lower = filepath.stem.lower()
    content_lower = content.lower()[:3000]
    for proj in projects:
        proj_lower = proj.lower()
        score = 0
        if proj_lower in name_lower:
            score += 50
        for word in re.split(r'[\s\-_]', proj_lower):
            if len(word) >= 2 and word in name_lower:
                score += 10
        if proj_lower in content_lower:
            score += 30
        for word in re.split(r'[\s\-_]', proj_lower):
            if len(word) >= 2 and word in content_lower:
                score += 5
        scores[proj] = score
    return scores

def find_similar_files(project_path, threshold=0.7):
    md_files = [f for f in project_path.rglob("*.md") if not f.name.startswith("_MOC_")]
    similar = []
    for i, a in enumerate(md_files):
        for b in md_files[i+1:]:
            sa, sb = a.stem.lower(), b.stem.lower()
            wa, wb = set(sa.split()), set(sb.split())
            common = wa & wb
            all_words = wa | wb
            if all_words and len(common) / len(all_words) >= threshold:
                similar.append((str(a.relative_to(VAULT)), str(b.relative_to(VAULT))))
    return similar

def update_moc(project_name, project_path):
    moc_path = project_path / f"_MOC_{project_name}.md"
    md_files = sorted([f for f in project_path.rglob("*.md") if f.name != moc_path.name])
    lines = [
        "---",
        f'title: "{project_name} - Map of Content"',
        f'project: "{project_name}"',
        "type: moc",
        f'updated: {datetime.now().strftime("%Y-%m-%d")}',
        "---",
        "",
        f"# {project_name} - Map of Content",
        "",
        f"合計ファイル数: {len(md_files)}",
        "",
        "| # | ファイル | タイトル | タグス | プロジェクト |",
        "|---|------|-------|------|---------|",
    ]
    for idx, f in enumerate(md_files, 1):
        rel = str(f.relative_to(VAULT))
        content = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        title = fm.get("title", f.stem)
        tags = ", ".join(fm.get("tags", []) or [])
        proj = fm.get("project", project_name)
        wikilink = f"[[{rel}|{f.stem}]]"
        lines.append(f"| {idx} | {wikilink} | {title} | {tags} | {proj} |")
    similar = find_similar_files(project_path)
    if similar:
        lines.extend(["", "## 関連ファイル（類似したファイル）", ""])
        for a, b in similar:
            lines.append(f"- [[{a}]] ↔ [[{b}]]")
    lines.extend(["", f"_Generated on: {datetime.now().strftime('%Y-%m-%d')}_"])
    moc_path.write_text("\n".join(lines), encoding="utf-8")
    return moc_path

def main():
    os.chdir(VAULT)
    print("[1/5] git pull...")
    run("git pull --rebase --autostash origin main || true", check=False)
    
    projects = get_projects()
    print(f"[2/5] 検出したプロジェクト: {projects}")
    
    vault_path = Path(VAULT)
    root_md_files = [f for f in vault_path.glob("*.md") if f.is_file()]
    moved = []
    updated_fm = []
    
    print(f"[3/5] ルートの未分類ファイル数: {len(root_md_files)}")
    
    for md_file in root_md_files:
        content = md_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        existing_project = fm.get("project")
        if existing_project:
            expected_dir = vault_path / "10_Projects" / existing_project
            if md_file.parent == expected_dir or any(p == expected_dir for p in md_file.parents):
                continue
        
        scores = score_project(md_file, content, projects)
        best_proj = max(scores, key=scores.get) if scores else None
        best_score = scores.get(best_proj, 0) if best_proj else 0
        
        if best_proj and best_score >= 20:
            target_dir = vault_path / "10_Projects" / best_proj
            target_path = target_dir / md_file.name
            if target_path.exists():
                print(f"  [SKIP] 同名ファイルが存在: {target_path}")
                continue
            rel_src = str(md_file.relative_to(VAULT))
            rel_dst = str(target_path.relative_to(VAULT))
            run(f'git mv "{rel_src}" "{rel_dst}"', check=False)
            set_frontmatter(target_path, "project", best_proj)
            moved.append((md_file.name, best_proj, best_score))
            updated_fm.append(str(target_path.relative_to(VAULT)))
            print(f"  [MOVE] {md_file.name} -> 10_Projects/{best_proj}/ (スコア: {best_score})")
        else:
            uncategorized_dir = vault_path / "20_Areas" / "未分類"
            uncategorized_dir.mkdir(parents=True, exist_ok=True)
            target_path = uncategorized_dir / md_file.name
            if target_path.exists():
                print(f"  [SKIP] 同名ファイルが存在: {target_path}")
                continue
            rel_src = str(md_file.relative_to(VAULT))
            rel_dst = str(target_path.relative_to(VAULT))
            run(f'git mv "{rel_src}" "{rel_dst}"', check=False)
            set_frontmatter(target_path, "project", "未分類")
            moved.append((md_file.name, "未分類", best_score))
            updated_fm.append(str(target_path.relative_to(VAULT)))
            print(f"  [MOVE] {md_file.name} -> 20_Areas/未分類/ (スコア: {best_score})")
    
    print("[4/5] MOC 更新...")
    updated_mocs = []
    for proj in projects:
        proj_path = vault_path / "10_Projects" / proj
        if proj_path.exists():
            moc_path = update_moc(proj, proj_path)
            updated_mocs.append(str(moc_path.relative_to(VAULT)))
    
    print("[5/5] git commit/push...")
    status = run('git status --porcelain')
    if status.stdout.strip():
        run('git add -A')
        run(f'git commit -m "auto: vault organize {datetime.now().strftime("%Y-%m-%d")}"')
        run('git push origin main')
    else:
        print("  変更がないためコミットはスキップします")
    
    print("\n" + "="*50)
    print("整理レポート")
    print("="*50)
    print(f"移動したファイル: {len(moved)}")
    for name, proj, score in moved:
        print(f"  - {name} -> {proj} (スコア: {score})")
    print(f"\nfrontmatter 更新: {len(updated_fm)}")
    for path in updated_fm:
        print(f"  - {path}")
    print(f"\nMOC 更新: {len(updated_mocs)}")
    for path in updated_mocs:
        print(f"  - {path}")
    print("="*50)

if __name__ == "__main__":
    main()
