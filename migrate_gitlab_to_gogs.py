#!/usr/bin/env python3

import requests
from http.client import responses
import json
import subprocess
import os
import sys

import argparse

def askToContinue(args, force = False):
    if force or (not args.no_confirm):
        try:
            input('Press Enter to continue or hit the interrupt key (normally Control-C or Delete) to cancel.')
        except KeyboardInterrupt:
            print()
            sys.exit("Canceling as requested by the user.")

def getToken(tokenName, tokenEnvName, tokenURL):
    if tokenEnvName in os.environ:
        token = os.environ[tokenEnvName]
        if len(token) < 1:
            sys.exit("Error: Environment variable '{}' must not be empty.".format(tokenEnvName))
    else:
        print()
        print("Please enter your personal {} access token. Alternatively, you can define environment variable '{}'.".format(tokenName, tokenEnvName))
        print("Hint: That token is not your password but a hash value which consists of random letters and numbers.")
        print("      You can generate an access token at {}.".format(tokenURL))
        token = input("{}=".format(tokenEnvName))
        if len(token) < 1:
            sys.exit("Error: The given token must not be empty.")

    return token

parser = argparse.ArgumentParser()

parser.add_argument('--gitlab_url',
                    help='URL to your GitLab instance. Must be in the format: http://my.gitlab.net',
                    required=True)
parser.add_argument('--gitlab_namespace',
                    help='The namespace in GitLab as it appears in URLs. For example, given the repository address http://my.gitlab.net/harry/my-awesome-repo.git, it shows that this repository lies within my personal namespace "harry". In that case, I would pass harry as parameter.',
                    required=True)

parser.add_argument('--gogs_url',
                    help='URL to your Gogs / Gitea instance. Must be in the format: http://my.gogs.net',
                    required=True)

parser.add_argument('--add_to_private',
                    default=None,
                    metavar='USER_NAME',
                    help='If you want to add the repositories under your own name, i.e. not in any organisation, use this parameter to specify your username.')
parser.add_argument('--add_to_organization',
                    default=None,
                    metavar='ORGANIZATION_NAME',
                    help='If you want to add all the repositories to an exisiting organisation, please pass the name to this parameter. Organizations correspond to groups in GitLab. The name can be taken from the organisation\'s dashboard URL. For example, if that dashboard is available at http://my.gogs.net/org/my-awesome-organisation/dashboard, then pass my-awesome-organisation as parameter.')

parser.add_argument('--no_confirm',
                    help='Skip user confirmation of each single step.',
                    action='store_true')
parser.add_argument('--skip_existing',
                    help='Skip any repository that already exists on the Gogs / Gitea instance without asking for confirmation.',
                    action='store_true')
parser.add_argument('--use_ssh',
                    help='Use SSH instead of HTTP(S) to clone and push repositories.',
                    action='store_true')

args = parser.parse_args()

if not (args.add_to_private or args.add_to_organization):
    parser.error("Please provide a user name via '--add_to_private' or an oranization name via '--add_to_organization'.")

if args.add_to_private and args.add_to_organization:
    parser.error("Please provide either a user name via '--add_to_private' or an oranization name via '--add_to_organization' (not both).")

print("Going to clone all repositories in namespace '{}' at the GitLab instance at {} to the current working directory ".format(args.gitlab_namespace, args.gitlab_url), end="")
print("and push them as repositories to ", end="")
if args.add_to_private:
    print("your personal account '{}' ".format(args.add_to_private), end="")
else:
    print("organisation '{}' ".format(args.add_to_organization), end="")
print("at the Gogs / Gitea instance at {}.".format(args.gogs_url))

askToContinue(args)

gitlab_api_url = args.gitlab_url + '/api/v4'
gogs_api_url = args.gogs_url + "/api/v1"

gitlab_token = getToken('GitLab', 'gitlab_token', "{}/profile/personal_access_tokens".format(args.gitlab_url))
gogs_token = getToken('Gogs / Gitea', 'gogs_token', "{}/user/settings/applications".format(args.gogs_url))

gitlabProjectsUrl = "{}/projects".format(gitlab_api_url)

print()
print("Getting projects from GitLab via API at {}...".format(gitlabProjectsUrl))

sessionGitlab = requests.Session()
# https://docs.gitlab.com/ee/api/#personal-access-tokens
sessionGitlab.headers.update({'Private-Token': gitlab_token})

project_list = []
gitlabProjectsNextPageUrl = gitlabProjectsUrl
currentPage = 1
totalPages = "tba"

while gitlabProjectsNextPageUrl is not None:
    print("Getting projects at page {} / {}...".format(currentPage, totalPages))
    res = sessionGitlab.get(gitlabProjectsNextPageUrl)

    if res.status_code != 200:
        sys.exit("Error: Could not get projects via API. HTTP status code '{} {}' and body: '{}'".format(res.status_code, responses[res.status_code], res.text))

    project_list += res.json()

    if "next" in res.links:
        gitlabProjectsNextPageUrl = res.links["next"]["url"]
        currentPage = currentPage + 1
        totalPages = res.headers["x-total-pages"]
    else:
        gitlabProjectsNextPageUrl = None

if len(project_list) == 0:
    print("Warning: Could not get any project via API.")

filtered_projects = list(filter(lambda x: x['path_with_namespace'].split('/')[0]==args.gitlab_namespace, project_list))

print("Going to migrate the following GitLab projects and repositories, respectively:")

for p in ([p['path_with_namespace'] for p in filtered_projects]):
    print("- {}".format(p))

askToContinue(args)

sessionGogs = requests.Session()
# https://docs.gitea.io/en-us/api-usage/#more-on-the-authorization-header
sessionGogs.headers.update({'Authorization': 'token {}'.format(gogs_token)})

numberOfProjectsToMigrate = len(filtered_projects)

for projectCounter in range(numberOfProjectsToMigrate):
    currentGitlabProject = filtered_projects[projectCounter]

    src_name = currentGitlabProject['name']
    if args.use_ssh:
        src_url = currentGitlabProject['ssh_url_to_repo']
    else:
        src_url = currentGitlabProject['http_url_to_repo']
    dst_name = src_name.replace(' ','-')

    print()
    print("[{}/{}] Migrating repository at {} to destination '{}'...".format(projectCounter + 1, numberOfProjectsToMigrate, src_url, dst_name))
    askToContinue(args)

    post_url = None
    if args.add_to_private:
        post_url = gogs_api_url + '/user/repos'
    else:
        post_url = gogs_api_url + "/org/{}/repos".format(args.add_to_organization)

    createRepoOption = {
        "auto_init": False, # Do NOT initialize repository as this would add .gitignore, License, and README.
        "description": currentGitlabProject["description"],
        "name": dst_name,
        "private": False if currentGitlabProject["visibility"] == "public" else True, # private and internal GitLab projects become private repositories
    }

    print()
    print("[{}/{}] Creating repository '{}' by POSTing {} to: {}".format(projectCounter + 1, numberOfProjectsToMigrate, dst_name, createRepoOption, post_url))
    create_repo = sessionGogs.post(post_url, json=createRepoOption)

    # 201: Created - The request has been fulfilled, resulting in the creation of a new resource.
    if create_repo.status_code != 201:
        print("Warning: Could not create repository '{}'. HTTP status code '{} {}' and body: '{}'".format(dst_name, create_repo.status_code, responses[create_repo.status_code], create_repo.text))
        # 409: Conflict - Indicates that the request could not be processed because of conflict in the current state of the resource.
        if create_repo.status_code == 409:
            if args.skip_existing:
                print("Skipping existing repository.")
            else:
                print("Shall we skip that existing repository and continue?")
                askToContinue(args, True)
            continue
        else:
            sys.exit("Error: Cannot handle HTTP status code.")

    dst_info = create_repo.json()

    if args.use_ssh:
        dst_url = dst_info['ssh_url']
    else:
        dst_url = dst_info['html_url']

    # Mirror the git repository (http://blog.plataformatec.com.br/2013/05/how-to-properly-mirror-a-git-repository/)
    print()
    print("[{}/{}] Cloning repository from: {}".format(projectCounter + 1, numberOfProjectsToMigrate, src_url))
    subprocess.check_call(['git', 'clone', '--mirror', src_url])

    os.chdir(src_url.split('/')[-1])

    print()
    print("[{}/{}] Pushing repository to: {}".format(projectCounter + 1, numberOfProjectsToMigrate, dst_url))
    branches=subprocess.check_output(['git','branch','-a'])
    if len(branches) == 0:
        print("Warning: This repository is empty - skipping push.")
    else:
        subprocess.check_call(['git','push','--mirror',dst_url])

    os.chdir('..')
    subprocess.check_call(['rm','-rf',src_url.split('/')[-1]])

    # This has to be done after migrating the repository -- as it might be archived.
    # If we would set the repository as archived before we would have pushed it,
    # this would faile because one cannot push to archived repositories.
    patch_url = "{}/repos/{}/{}".format(gogs_api_url, args.add_to_organization if args.add_to_organization else args.add_to_private, dst_name)

    editRepoOption = {
        "allow_merge_commits":          dst_info["allow_merge_commits"],            # no equivalent GitLab setting found
        "allow_rebase":                 dst_info["allow_rebase"],                   # no equivalent GitLab setting found
        "allow_rebase_explicit":        dst_info["allow_rebase_explicit"],          # no equivalent GitLab setting found
        "allow_squash_merge":           dst_info["allow_squash_merge"],             # no equivalent GitLab setting found
        "archived":                     currentGitlabProject["archived"],           # use GitLab setting
        "default_branch":               currentGitlabProject["default_branch"],     # use GitLab setting
        "description":                  dst_info["description"],                    # do not change as it was given on create (cf. above)
        "has_issues":                   currentGitlabProject["issues_enabled"],     # use GitLab setting
        "has_pull_requests":            dst_info["has_pull_requests"],              # no equivalent GitLab setting found
        "has_wiki":                     currentGitlabProject["wiki_enabled"],       # use GitLab setting
        "ignore_whitespace_conflicts":  dst_info["ignore_whitespace_conflicts"],    # no equivalent GitLab setting found
        "name":                         dst_info["name"],                           # do not change as it was given on create (cf. above)
        "private":                      dst_info["private"],                        # do not change as it was given on create (cf. above)
        "website":                      dst_info["website"]                         # no equivalent GitLab setting found
    }

    print()
    print("[{}/{}] Editing repository '{}' by PATCHing with '{}' to: {}".format(projectCounter + 1, numberOfProjectsToMigrate, dst_name, editRepoOption, patch_url))
    patch_repo = sessionGogs.patch(patch_url, json=editRepoOption)

    # 200: OK - Standard response for successful HTTP requests.
    if patch_repo.status_code != 200:
        print("Warning: Could not edit repository '{}'. HTTP status code '{} {}' and body: '{}'".format(dst_name, patch_repo.status_code, responses[patch_repo.status_code], patch_repo.text))
        print("Shall we ignore that isse and continue?")
        askToContinue(args, True)

    print()
    print("[{}/{}] Completed migration of repository '{}'. Please open the new Gogs / Gitea repository at {}, check there if everything is as expected, and continue the migration afterwards.".format(projectCounter + 1, numberOfProjectsToMigrate, dst_name, dst_info['html_url']))
    askToContinue(args)

print()
print("Migration completed.")
