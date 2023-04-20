# -*- coding: utf-8 -*-
import re
import datetime
import argparse
import copy

def calculate_new_version(version, major=0, minor=0, patch=0):
    version[0] += major
    version[1] = 0 if major > 0 else version[1] + minor
    version[2] = 0 if major > 0 or minor > 0 else version[2] + patch
    return '.'.join(map(str, version))


def define_arguments():
    arguments_dictionary = {
        'repository_url': {'help': 'remote repository url'},
        'pull_request_commits': {'help': 'pull request commits'}
    }
    parser = argparse.ArgumentParser()
    for key, value in arguments_dictionary.items():
        parser.add_argument('--{}'.format(key), **value)
    return parser.parse_args()


def type_of_change():
    breaking_commits = [commit for commit in commits_from_pull_request if re.search(r'/breaking/.*$', commit)]
    if breaking_commits:
        return 'breaking'
    feature_commits = [
        commit for commit in commits_from_pull_request if re.search(r'/feat/.*$', commit)]
    if feature_commits:
        return 'feat'
    return 'fix'


with open('CHANGELOG.md', 'r') as changelog_file:
    changelog_content_base = changelog_file.read()

file_arguments = define_arguments()
commits_from_pull_request = file_arguments.pull_request_commits.split('\n')
changelog_content = copy.deepcopy(changelog_content_base)
header_version_regex_common = r'\[(\d+\.\d+\.\d+)]'
new_version_header_regex = re.compile(
    r'##\s' + header_version_regex_common + r'\s-', re.MULTILINE)
previous_version = re.findall(new_version_header_regex, changelog_content)[0]

# Update version
previous_version_parsed_numbers = [
    int(number) for number in previous_version.split('.')]
version_change_allowed_types = {
    'breaking': ('breaking', 1, 0, 0),
    'feat': ('feat', 0, 1, 0),
    'fix': ('fix', 0, 0, 1)
}
change_type_from_branch = type_of_change()
update_version_type, major, minor, patch = version_change_allowed_types.get(change_type_from_branch,
                                                                            version_change_allowed_types['fix'])
new_version = calculate_new_version(
    previous_version_parsed_numbers, major, minor, patch)

# Create version header
today = datetime.date.today().isoformat()
new_version_header_index = re.search(
    r'##\s' + header_version_regex_common + r'\s-', changelog_content).start()
new_version_header_content = f'\n## [{new_version}] - {today}\n\n'
changelog_content = \
    changelog_content[:new_version_header_index - 1] + \
    new_version_header_content + \
    changelog_content[new_version_header_index:]

# Footer
new_version_footer_index = re.search(
    header_version_regex_common + r':\s*', changelog_content).start()
new_version_footer_content = \
    f'[{new_version}]: {file_arguments.repository_url}/compare/v{new_version}..v{previous_version}\n'
changelog_content = \
    changelog_content[:new_version_footer_index] + \
    new_version_footer_content + \
    changelog_content[new_version_footer_index:]
# Get last version content if changelog version has been previously updated
versions_headers_regex = re.compile(
    r'##\s' + header_version_regex_common + r'\s-\s(\d{4}-\d{2}-\d{2})')
changelog_versions_headers = versions_headers_regex.findall(changelog_content)
new_version, new_version_date = changelog_versions_headers[0]
previous_version, previous_version_date = changelog_versions_headers[1]

latest_versions_content_regex = \
    f'## [{new_version}] - {new_version_date}\n\n(.+)\n\n## [{previous_version}] - {previous_version_date}\n\n'

last_version_from_changelog_content = \
    re.search(latest_versions_content_regex, changelog_content, re.DOTALL)

changelog_keys = {'Added', 'Changed', 'Fixed', 'Removed'}
last_version_content_dict = {key: [] for key in changelog_keys}

allowed_commits_messages = {
    'ADD:': 'Added',
    'FEAT:': 'Added',
    'FEATURE:': 'Added',
    'CHANGE:': 'Changed',
    'REFACTOR:': 'Changed',
    'FIX:': 'Fixed',
    'REMOVE:': 'Removed'
}
# Add commits to dictionary if they are allowed
for message_prefix, key in allowed_commits_messages.items():
    if key not in last_version_content_dict:
        last_version_content_dict[key] = []
    [last_version_content_dict[key].append(message_text.strip().capitalize())
     for commit in commits_from_pull_request
     if commit.upper().startswith(message_prefix)
     for keyword, message_text in [commit.split(':', maxsplit=1)]
     if message_text.strip().capitalize() not in last_version_content_dict[key]]

there_are_valid_commits = any(last_version_content_dict.values())

if there_are_valid_commits:
    # Convert dictionary to string alphabetically sorted by keys
    last_commits_version_content_string = ''
    for key, values in sorted(last_version_content_dict.items()):
        if values:
            last_commits_version_content_string += f'### {key}\n\n'
            for value in values:
                last_commits_version_content_string += f'- {value}.\n'
            last_commits_version_content_string += '\n'

    with open('CHANGELOG.md', 'w') as file:
        pattern_new = f'## [{new_version}] - {new_version_date}\n\n'
        pattern_old = f'## [{previous_version}] - {previous_version_date}\n\n'
        position_start = changelog_content.index(
            pattern_new) + len(pattern_new)
        position_end = changelog_content.index(pattern_old)
        file.seek(position_start)
        file.seek(position_end)
        new_version_content_updated = \
            changelog_content[:position_start] + \
            last_commits_version_content_string + \
            changelog_content[position_end:]
        file.seek(0)
        file.write(new_version_content_updated)

    with open('VERSION', 'w') as version_file:
        version_file.write(f'v{new_version}')
