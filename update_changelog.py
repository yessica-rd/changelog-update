# -*- coding: utf-8 -*-
import re
import datetime
import argparse
import copy
from enum import Enum


class ChangeTypes(Enum):
    feat = 'feat'
    fix = 'fix'
    breaking = 'breaking'


changelog_path = './CHANGELOG.md'


def calculate_new_version(version: list[int], major=0, minor=0, patch=0) -> str:
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


def get_type_of_change(commits_from_pull_request: list[str]) -> ChangeTypes:
    breaking_commits = [commit for commit in commits_from_pull_request if re.search(
        r'/breaking/.*$', commit)]
    if breaking_commits:
        return ChangeTypes.breaking
    feature_commits = [
        commit for commit in commits_from_pull_request if re.search(r'/feat/.*$', commit)]
    if feature_commits:
        return ChangeTypes.feat
    return ChangeTypes.fix


def calcualte_new_version_based_on(previous_version, commits_from_pull_request):
    previous_version_as_integer: list[int] = [
        int(number) for number in previous_version.split('.')]  # 100
    version_change_allowed_types = {
        ChangeTypes.breaking: (1, 0, 0),
        ChangeTypes.feat: (0, 1, 0),
        ChangeTypes.fix: (0, 0, 1)
    }
    change_type_from_branch = get_type_of_change(commits_from_pull_request)
    major, minor, patch = version_change_allowed_types.get(change_type_from_branch,
                                                           version_change_allowed_types[ChangeTypes.fix])
    return calculate_new_version(previous_version_as_integer, major, minor, patch)


def calculate_version_header(new_version: str, header_version_regex_common, changelog_content: str) -> str:
    today = datetime.date.today().isoformat()
    new_version_header_index = re.search(
        r'##\s' + header_version_regex_common + r'\s-', changelog_content).start()
    new_version_header_content = f'\n## [{new_version}] - {today}\n\n'
    changelog_content = \
        changelog_content[:new_version_header_index - 1] + \
        new_version_header_content + \
        changelog_content[new_version_header_index:]
    return changelog_content


def add_changelog_footer(header_version_regex_common, changelog_content: str, new_version: str, previous_version: str):
    new_version_footer_index = re.search(
        header_version_regex_common + r':\s*', changelog_content).start()
    new_version_footer_content = \
        f'[{new_version}]: {file_arguments.repository_url}/compare/v{new_version}..v{previous_version}\n'
    changelog_content = \
        changelog_content[:new_version_footer_index] + \
        new_version_footer_content + \
        changelog_content[new_version_footer_index:]
    return changelog_content


def get_last_version_content(changelog_content: str) -> tuple[str, str, str, str]:
    versions_headers_regex = re.compile(
        r'##\s' + header_version_regex_common + r'\s-\s(\d{4}-\d{2}-\d{2})')
    changelog_versions_headers = versions_headers_regex.findall(
        changelog_content)
    new_version, new_version_date = changelog_versions_headers[0]
    previous_version, previous_version_date = changelog_versions_headers[1]
    return new_version, new_version_date, previous_version, previous_version_date


def add_sections_to_changelog():
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
    for message_prefix, key in allowed_commits_messages.items():
        if key not in last_version_content_dict:
            last_version_content_dict[key] = []
        [last_version_content_dict[key].append(message_text.strip().capitalize())
         for commit in commits_from_pull_request
         if commit.upper().startswith(message_prefix)
         for keyword, message_text in [commit.split(':', maxsplit=1)]
         if message_text.strip().capitalize() not in last_version_content_dict[key]]
    return last_version_content_dict


with open(changelog_path, 'r') as changelog_file:
    changelog_content_base = changelog_file.read()

file_arguments = define_arguments()
commits_from_pull_request = file_arguments.pull_request_commits.split('\n')
changelog_content = copy.deepcopy(changelog_content_base)
header_version_regex_common = r'\[(\d+\.\d+\.\d+)]'
new_version_header_regex = re.compile(
    r'##\s' + header_version_regex_common + r'\s-', re.MULTILINE)
previous_version = re.findall(new_version_header_regex, changelog_content)[0]


new_version = calcualte_new_version_based_on(
    previous_version, commits_from_pull_request)
changelog_content = calculate_version_header(
    new_version, header_version_regex_common, changelog_content)
changelog_content = add_changelog_footer(header_version_regex_common,
                     changelog_content, new_version, previous_version)
last_version_content_dict = add_sections_to_changelog()

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

    with open(changelog_path, 'w') as file:
        new_version, new_version_date, previous_version, previous_version_date = get_last_version_content(
            changelog_content)
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