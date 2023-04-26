# -*- coding: utf-8 -*-
import re
import datetime
import argparse
import copy
from typing import Tuple, Pattern, Dict, Literal
from enum import Enum


class ChangeTypes(Enum):
    feat = 'feat'
    fix = 'fix'
    breaking = 'breaking'


Version = Tuple[int, int, int]
VersionToChangeTypeMap = Dict[ChangeTypes, Version]


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


def get_change_type_from(commits_in_pull_requests: list[str]) -> ChangeTypes:
    commits_starting_with_breaking = r'/breaking/.*$'
    commits_starting_with_feat = r'/feat/.*$'

    commits_containing_breaking_changes = [
        commit for commit in commits_in_pull_requests if re.search(commits_starting_with_breaking, commit)
    ]
    if commits_containing_breaking_changes:
        return ChangeTypes.breaking

    commits_containing_feat_changes = [
        commit for commit in commits_in_pull_requests if re.search(commits_starting_with_feat, commit)
    ]
    if commits_containing_feat_changes:
        return ChangeTypes.feat

    return ChangeTypes.fix


def calcualte_new_version_based_on(previous_version: str, commits_in_pull_request: list[str]):
    previous_version_as_list: list[int] = [
        int(number) for number in previous_version.split('.')
    ]
    version_to_change_based_on_change_type: VersionToChangeTypeMap = {
        ChangeTypes.breaking: (1, 0, 0),
        ChangeTypes.feat: (0, 1, 0),
        ChangeTypes.fix: (0, 0, 1)
    }
    change_type = get_change_type_from(commits_in_pull_request)
    default_change_type = version_to_change_based_on_change_type[ChangeTypes.fix]
    major, minor, patch = version_to_change_based_on_change_type.get(
        change_type, default_change_type)
    return calculate_new_version(previous_version_as_list, major, minor, patch)


# Eg: ## [X.Y.Z] - YYYY-MM-DD
def append_version_header_to(changelog_content: str, header_version_regex_common: Literal, new_version: str) -> str:
    today = datetime.date.today().isoformat()
    template = f'\n## [{new_version}] - {today}\n\n'
    regex = re.compile(r'##\s' + header_version_regex_common + r'\s-')
    index = re.search(regex, changelog_content).start()
    changelog_content = \
        changelog_content[:index - 1] + \
        template + \
        changelog_content[index:]
    return changelog_content


# Eg: [X.Y.Z]: github.com/owner/repository/compare/vX.Y.Z..vX.Y.Z
def append_version_footer_to(changelog_content: str, header_version_regex_common: Literal, new_version: str, previous_version: str):
    regex = re.compile(header_version_regex_common + r':\s*')
    index = re.search(regex, changelog_content).start()
    template = f'[{new_version}]: {file_arguments.repository_url}/compare/v{new_version}..v{previous_version}\n'
    changelog_content = \
        changelog_content[:index] + \
        template + \
        changelog_content[index:]
    return changelog_content


def get_headers_from_two_latest_versions(changelog_content: str, header_version_regex_common: Literal) -> tuple[str, str, str, str]:
    regex = re.compile(r'##\s' + header_version_regex_common + r'\s-\s(\d{4}-\d{2}-\d{2})')
    changelog_versions_headers = regex.findall(changelog_content)
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
        for commit in commits_from_pull_request:
            if commit.upper().startswith(message_prefix):
                message_text = commit.split(':', maxsplit=1)[1]
                if message_text.strip().capitalize() not in last_version_content_dict[key]:
                    last_version_content_dict[key].append(message_text.strip().capitalize())
    return last_version_content_dict


def convert_dictionary_to_string(dictionary: dict[str, list[str]]):
    content = ''
    for key, values in sorted(last_version_content_dict.items()):
        if values:
            content += f'### {key}\n\n'
            for value in values:
                content += f'- {value}.\n'
            content += '\n'
    return content


def get_release_content_index(changelog_content: str) -> tuple[int, int]:
    new_version, new_version_date, previous_version, previous_version_date = get_headers_from_two_latest_versions(
            changelog_content, header_version_regex_common)
    template_last_version = f'## [{new_version}] - {new_version_date}\n\n'
    template_previous_version = f'## [{previous_version}] - {previous_version_date}\n\n'
    starting_index = changelog_content.index(template_last_version) + len(template_last_version)
    ending_index = changelog_content.index(template_previous_version)
    return starting_index, ending_index


with open(changelog_path, 'r') as changelog_file:
    changelog_content_base = changelog_file.read()

file_arguments = define_arguments()
commits_from_pull_request = file_arguments.pull_request_commits.split('\n')
changelog_content = copy.deepcopy(changelog_content_base)
header_version_regex_common: Literal = r'\[(\d+\.\d+\.\d+)]'  # [X.Y.Z]
new_version_header_regex = re.compile(
    r'##\s' + header_version_regex_common + r'\s-', re.MULTILINE)
previous_version = re.findall(new_version_header_regex, changelog_content)[0]

new_version = calcualte_new_version_based_on(
    previous_version, commits_from_pull_request)
changelog_content = append_version_header_to(
    changelog_content, header_version_regex_common, new_version)
changelog_content = append_version_footer_to(
    changelog_content, header_version_regex_common, new_version, previous_version)
last_version_content_dict = add_sections_to_changelog()

there_are_valid_commits = any(last_version_content_dict.values())

if there_are_valid_commits:
    last_commits_version_content_string = convert_dictionary_to_string(last_version_content_dict)

    with open(changelog_path, 'w') as file:
        starting_index, ending_index = get_release_content_index(changelog_content)
        file.seek(starting_index)
        file.seek(ending_index)
        new_version_content_updated = \
            changelog_content[:starting_index] + \
            last_commits_version_content_string + \
            changelog_content[ending_index:]
        file.seek(0)
        file.write(new_version_content_updated)

    with open('VERSION', 'w') as version_file:
        version_file.write(f'v{new_version}')