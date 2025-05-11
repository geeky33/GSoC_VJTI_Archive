import re
import os
import glob
import json
from github import Github

def get_org_list_from_directories():
    """Get organization list from directories in the repository"""
    org_dirs = []
    for dir_path in glob.glob("*"):
        if os.path.isdir(dir_path) and not dir_path.startswith('.') and dir_path not in ['.github', 'assets']:
            org_dirs.append(dir_path)
    return sorted(org_dirs)

def update_org_list(content):
    """Update the organization list based on directories in the repo"""
    org_dirs = get_org_list_from_directories()

    org_section = re.search(r'(## Org Submission Checklist\s*\n+)((?:- \[.\][^\n]*\n+)*)', content, re.MULTILINE)
    if not org_section:
        return content

    org_lines = [f"- [x] {org}" for org in org_dirs]
    new_section = org_section.group(1) + '\n'.join(org_lines) + '\n\n'
    return content[:org_section.start()] + new_section + content[org_section.end():]

def count_proposals():
    """Count total number of PDF proposals in the repository"""
    return len(glob.glob("**/*.pdf", recursive=True))

def update_proposal_count(content):
    """Update the proposal count in the README"""
    count = count_proposals()
    return re.sub(r'Total proposals submitted: \*\*\d+\*\*', f'Total proposals submitted: **{count}**', content)

def get_contributors():
    g = Github(os.getenv('GITHUB_TOKEN'))
    repo = g.get_repo(os.getenv('GITHUB_REPOSITORY'))
    contributors = {}

    try:
        for contributor in repo.get_contributors():
            username = contributor.login.lower()
            if not any(bot in username for bot in ['[bot]', 'actions-user', 'dependabot']):
                contributors[username] = (
                    contributor.name or contributor.login,
                    f'https://github.com/{contributor.login}'
                )
    except Exception as e:
        print(f"Error getting contributors: {e}")

    if os.getenv('GITHUB_EVENT_NAME') == 'pull_request_target':
        try:
            with open(os.environ.get('GITHUB_EVENT_PATH')) as f:
                event = json.load(f)
                pr_user = event.get('pull_request', {}).get('user')
                if pr_user:
                    username = pr_user['login'].lower()
                    if not any(bot in username for bot in ['[bot]', 'actions-user', 'dependabot']):
                        contributors[username] = (
                            pr_user.get('name') or pr_user['login'],
                            f"https://github.com/{pr_user['login']}"
                        )
        except Exception as e:
            print(f"Error processing PR author from event file: {e}")

    return contributors

def update_contributors_section(content, contributors):
    contrib_match = re.search(r'(## Contributors\s*\n+<!-- Add contributors below -->)(.*?)(\n+##|\Z)', content, re.DOTALL)
    if not contrib_match:
        return content

    contrib_lines = [f"- [{name}]({url})" for _, (name, url) in sorted(contributors.items(), key=lambda x: x[1][0].lower())]

    avatar_html = "<div align=\"center\">\n"
    for _, (_, url) in sorted(contributors.items()):
        github_username = url.split('/')[-1]
        avatar_html += f'  <a href="{url}"><img src="https://github.com/{github_username}.png" width="60px" alt="{github_username}" /></a>\n'
    avatar_html += "</div>\n\n"

    new_section = contrib_match.group(1) + '\n' + '\n'.join(contrib_lines) + '\n\n' + avatar_html
    return content[:contrib_match.start()] + new_section + content[contrib_match.end(0):]

if __name__ == "__main__":
    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()

    content = update_proposal_count(content)
    content = update_org_list(content)
    contributors = get_contributors()
    content = update_contributors_section(content, contributors)
    content = re.sub(r'\n{3,}##', r'\n\n##', content)

    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(content)
