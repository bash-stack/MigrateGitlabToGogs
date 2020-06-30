#!/usr/bin/env python3

import argparse
import datetime
import inquirer
import os
import requests
from http.client import responses
import subprocess
import sys

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

parser.add_argument('--add_to_user',
                    default=None,
                    metavar='USER_NAME',
                    help='If you want to add the repositories under your own name, i.e. not in any organization, use this parameter to specify your username.')
parser.add_argument('--add_to_organization',
                    default=None,
                    metavar='ORGANIZATION_NAME',
                    help='If you want to add all the repositories to an organization, please pass the name to this parameter. Organizations correspond to groups in GitLab. The name can be taken from the organization\'s dashboard URL. For example, if that dashboard is available at http://my.gogs.net/org/my-awesome-organization/dashboard, then pass my-awesome-organization as parameter.')

parser.add_argument('--create_organization',
                    help='If the target Gogs / Gitea organization does not exist yet, create it and make it private. By default, organizations are expected to exist already.',
                    action='store_true')

parser.add_argument('--force_private',
                    help='Make all migrated repositories private in Gogs / Gitea even if public in corresponding Gitlab project.',
                    action='store_true')
parser.add_argument('--force_archive',
                    help='Archive all migrated repositories in Gogs / Gitea even if not archived in corresponding Gitlab project.',
                    action='store_true')
parser.add_argument('--force_disable_issues',
                    help='Disable issue tracker in Gogs / Gitea for all migrated repositories even if enabled in corresponding Gitlab project.',
                    action='store_true')
parser.add_argument('--force_disable_wiki',
                    help='Disable wiki in Gogs / Gitea for all migrated repositories even if enabled in corresponding Gitlab project.',
                    action='store_true')

parser.add_argument('--non_interactive',
                    help='Migrate all repositories in the given GitLab namespace automatically; if an issue occurs, the migration process will be stopped immediately. By default, the script asks for confirmation for most of the steps in the migration process; if an issue occurs, the user will be presented with different options on how to proceed.',
                    action='store_true')
parser.add_argument('--skip_existing_target',
                    help='Skip any repository that already exists on the target Gogs / Gitea instance without asking for confirmation.',
                    action='store_true')
parser.add_argument('--use_ssh',
                    help='Use SSH instead of HTTP(S) to clone and push repositories.',
                    action='store_true')

args = parser.parse_args()

if not (args.add_to_user or args.add_to_organization):
    parser.error("Please provide a user name via '--add_to_user' or an oranization name via '--add_to_organization'.")

if args.add_to_user and args.add_to_organization:
    parser.error("Please provide either a user name via '--add_to_user' or an oranization name via '--add_to_organization' (not both).")

def askForConfirmationIfInteractive():
    if not args.non_interactive:
        if not inquirer.confirm("Do you want to continue?"):
            sys.exit("Canceling as requested by the user.")

print("Going to clone all repositories in namespace '{}' at the source GitLab instance at {} to the current working directory ".format(args.gitlab_namespace, args.gitlab_url), end="")
print("and push them as repositories to ", end="")
if args.add_to_user:
    print("your user account '{}' ".format(args.add_to_user), end="")
else:
    print("organization '{}' ".format(args.add_to_organization), end="")
print("at the target Gogs / Gitea instance at {}.".format(args.gogs_url))

askForConfirmationIfInteractive()

gitlab_api_url = args.gitlab_url + '/api/v4'
gogs_api_url = args.gogs_url + "/api/v1"

gitlab_token = getToken('GitLab', 'gitlab_token', "{}/profile/personal_access_tokens".format(args.gitlab_url))
gogs_token = getToken('Gogs / Gitea', 'gogs_token', "{}/user/settings/applications".format(args.gogs_url))

gitlabProjectsUrl = "{}/projects".format(gitlab_api_url)

print()
print("Getting source projects from GitLab via API at {}...".format(gitlabProjectsUrl))

sessionGitlab = requests.Session()
# https://docs.gitlab.com/ee/api/#personal-access-tokens
sessionGitlab.headers.update({'Private-Token': gitlab_token})

project_list = []
gitlabProjectsNextPageUrl = gitlabProjectsUrl
currentPage = 1
totalPages = ""

while gitlabProjectsNextPageUrl is not None:
    print("Getting projects at page {}{}...".format(currentPage, totalPages))
    res = sessionGitlab.get(gitlabProjectsNextPageUrl,verify=False)

    if res.status_code != 200:
        sys.exit("Error: Could not get source projects via API. HTTP status code '{} {}' and body: '{}'".format(res.status_code, responses[res.status_code], res.text))

    totalPages = " / {}".format(res.headers["x-total-pages"])
    project_list += res.json()

    if "next" in res.links:
        gitlabProjectsNextPageUrl = res.links["next"]["url"]
        currentPage = currentPage + 1
    else:
        gitlabProjectsNextPageUrl = None

if len(project_list) == 0:
    sys.exit("Warning: Could not get any source project via API.")

filtered_projects = list(filter(lambda x: x['path_with_namespace'].split('/')[0]==args.gitlab_namespace, project_list))

if len(filtered_projects) == 0:
    sys.exit("Warning: Could not get any source project in namespace '{}' via API.".format(args.gitlab_namespace))

if not args.non_interactive:
    print()
    print("Which GitLab projects do you want to migrate?")
    selected = inquirer.checkbox(message = "Use up / down arrow keys to navigate, space to select / deselect, enter to confirm and continue", choices = [p['path_with_namespace'] for p in filtered_projects])
    filtered_projects = list(filter(lambda x: x['path_with_namespace'] in selected, filtered_projects))
    if len(filtered_projects) == 0:
        sys.exit("No project selected.")

print()
print("Going to migrate the following GitLab projects and repositories, respectively:")

for p in ([p['path_with_namespace'] for p in filtered_projects]):
    print("- {}".format(p))

askForConfirmationIfInteractive()

sessionGogs = requests.Session()
# https://docs.gitea.io/en-us/api-usage/#more-on-the-authorization-header
sessionGogs.headers.update({'Authorization': 'token {}'.format(gogs_token)})

if args.add_to_organization:

    get_org_url = "{}/orgs/{}".format(gogs_api_url, args.add_to_organization)

    print()
    print("Testing if organization '{}' already exists by GETting: {}".format(args.add_to_organization, get_org_url))
    get_org = sessionGogs.get(get_org_url,verify=False)

    # 200: OK -> org exists
    if get_org.status_code == 200:
        print("Okay, organization '{}' exists already.".format(args.add_to_organization))
    # 404: Not Found -> org does not exist
    elif get_org.status_code == 404:
        if not args.create_organization:
            sys.exit("Error: Organization '{}' does not exist.".format(args.add_to_organization))
        else:
            print("Creating private organization as it does not exist yet: {}".format(args.add_to_organization))

            post_org_url = "{}/orgs".format(gogs_api_url)

            createOrgOption = {
                "username": args.add_to_organization,
                "description": "Created automatically during migration from GitLab to Gogs / Gitea ({})".format(datetime.datetime.now().replace(microsecond=0).isoformat()),
                "visibility": "private"
            }

            print("Creating private organization '{}' by POSTing {} to: {}".format(args.add_to_organization, createOrgOption, post_org_url))
            create_org = sessionGogs.post(post_org_url, json=createOrgOption)

            # 201: Created - The request has been fulfilled, resulting in the creation of a new resource.
            if create_org.status_code == 201:
                print("Created private organization: {}".format(args.add_to_organization))
                create_org.json()
            else:
                sys.exit("Error: Could not create organization of target '{}'. HTTP status code '{} {}' and body: '{}'".format(dst_path, create_org.status_code, responses[create_org.status_code], create_org.text))
    else:
        sys.exit("Error: Cannot handle HTTP status code '{} {}' and body: '{}'".format(get_org.status_code, responses[get_org.status_code], get_org.text))



numberOfProjectsToMigrate = len(filtered_projects)

for projectCounter in range(numberOfProjectsToMigrate):
    currentGitlabProject = filtered_projects[projectCounter]

    src_name = currentGitlabProject['name']
    if args.use_ssh:
        src_url = currentGitlabProject['ssh_url_to_repo']
    else:
        src_url = currentGitlabProject['http_url_to_repo']
    dst_name = src_name.replace(' ','-')

    dst_path = "{}/{}".format(args.add_to_organization if args.add_to_organization else args.add_to_user, dst_name)

    def printProgress(msg, *values):
        print(msg.format(projectCounter + 1, numberOfProjectsToMigrate, dst_path, *values))

    dst_info = None

    print()
    printProgress("[{}/{}] Migrating to target Gogs / Gitea repository '{}' from source GitLab project at: {}", src_url)
    askForConfirmationIfInteractive()

    get_repo_url = "{}/repos/{}".format(gogs_api_url, dst_path)

    printProgress("[{}/{}] Testing if target repository '{}' already exists by GETting: {}", get_repo_url)
    get_repo = sessionGogs.get(get_repo_url,verify=False)
    # 200: OK - Standard response for successful HTTP requests.
    if get_repo.status_code == 200:
        if args.skip_existing_target:
            printProgress("[{}/{}] Skipping existing target repository '{}'.")
            continue
        elif args.non_interactive:
            sys.exit("Error: Canceling because target repository exists already.")
        else:
            dst_info = get_repo.json()
            if dst_info['empty']:
                print("Target repository '{}' exists already and is empty.".format(dst_path))
                print("Do you want to skip this repository, to use this empty repository as migration target, or to completely cancel the migration?")
                choice = inquirer.list_input("Use up / down arrow keys to navigate, enter to confirm and continue",
                                    choices=['skip', 'migrate', 'cancel'])
                if choice == "skip":
                    printProgress("[{}/{}] Skipping target repository '{}' as requested by the user.")
                    continue
                elif choice == "migrate":
                    pass
                else:
                    sys.exit("Canceling as requested by the user.")

            else:
                print("Warning: Target repository '{}' alread exists and contains some data. If you do not want to skip it, the migration will be canceled.".format(dst_path))
                if inquirer.confirm("Do you want to skip this repository and continue? "):
                    printProgress("[{}/{}] Skipping target repository '{}' as requested by the user.")
                    continue
                else:
                    sys.exit("Canceling as target repository '{}' exists already and is not empty.".format(dst_path))
    else:
        printProgress("[{}/{}] Okay, target repository '{}' does not exist yet.")

    if not dst_info:
        # creating repository as it does not exist already
        post_repo_url = None
        if args.add_to_user:
            post_repo_url = gogs_api_url + '/user/repos'
        else:
            post_repo_url = gogs_api_url + "/org/{}/repos".format(args.add_to_organization)

        createRepoOption = {
            "auto_init": False, # Do NOT initialize repository as this would add .gitignore, License, and README.
            "description": currentGitlabProject["description"],
            "name": dst_name,
            "private": False if currentGitlabProject["visibility"] == "public" else True, # private and internal GitLab projects become private repositories
        }

        printProgress("[{}/{}] Creating target repository '{}' by POSTing {} to: {}", createRepoOption, post_repo_url)
        create_repo = sessionGogs.post(post_repo_url, json=createRepoOption)

        # 201: Created - The request has been fulfilled, resulting in the creation of a new resource.
        if create_repo.status_code == 201:
            printProgress("[{}/{}] Created target repository '{}'.")
            dst_info = create_repo.json()
        else:
            sys.exit("Error: Could not create target repository '{}'. HTTP status code '{} {}' and body: '{}'".format(dst_path, create_repo.status_code, responses[create_repo.status_code], create_repo.text))

    if args.use_ssh:
        dst_url = dst_info['ssh_url']
    else:
        dst_url = dst_info['html_url']

    # Mirror the git repository (http://blog.plataformatec.com.br/2013/05/how-to-properly-mirror-a-git-repository/)
    printProgress("[{}/{}] Cloning source repository for target '{}' from: {}", src_url)
    subprocess.check_call(['git', '-c http.sslVerify=false', 'clone', '--mirror', src_url])
    printProgress("[{}/{}] Cloned source repository for target '{}'.")

    os.chdir(src_url.split('/')[-1])

    printProgress("[{}/{}] Pushing to target repository '{}': {}", dst_url)
    branches=subprocess.check_output(['git','-c http.sslVerify=false','branch','-a'])
    if len(branches) == 0:
        printProgress("[{}/{}] Skipping push to target repository '{}' because it is empty (no branches).")
    else:
        subprocess.check_call(['git','-c http.sslVerify=false','push','--mirror',dst_url])
        printProgress("[{}/{}] Pushed to target repository '{}'.")


    os.chdir('..')
    subprocess.check_call(['rm','-rf',src_url.split('/')[-1]])

    # This has to be done after migrating the repository -- as it might be archived.
    # If we would set the repository as archived before we would have pushed it,
    # this would faile because one cannot push to archived repositories.
    patch_url = "{}/repos/{}".format(gogs_api_url, dst_path)

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

    if args.force_private:
        editRepoOption["private"] = True

    if args.force_archive:
        editRepoOption["archived"] = True

    if args.force_disable_issues:
        editRepoOption["has_issues"] = False

    if args.force_disable_wiki:
        editRepoOption["has_wiki"] = False

    printProgress("[{}/{}] Updating settings of target repository '{}' by PATCHing with '{}' to: {}", editRepoOption, patch_url)
    patch_repo = sessionGogs.patch(patch_url, json=editRepoOption)

    # 200: OK - Standard response for successful HTTP requests.
    if patch_repo.status_code == 200:
        printProgress("[{}/{}] Updated target repository '{}'.")
    else:
        print("Warning: Could not edit target repository '{}'. HTTP status code '{} {}' and body: '{}'".format(dst_path, patch_repo.status_code, responses[patch_repo.status_code], patch_repo.text))
        if args.non_interactive:
            sys.exit("Error: Canceling.")
        else:
            if inquirer.confirm("Do you want to ignore that issue and continue?"):
                continue
            else:
                sys.exit("Canceling as requested by the user.")

    if args.non_interactive:
        printProgress("[{}/{}] Completed migration to target repository '{}'.")
    else:
        printProgress("[{}/{}] Completed migration to target repository '{}'. Please go to {}, check if the new Gogs / Gitea repository has been migrated successfully, and continue the migration afterwards.", dst_info['html_url'])

    askForConfirmationIfInteractive()

print()
print("Migration completed -- processed the following GitLab projects and repositories, respectively:")
for p in ([p['path_with_namespace'] for p in filtered_projects]):
    print("- {}".format(p))

if args.non_interactive:
    print()
    print("Please go to {} and check if the new Gogs / Gitea repositories have been migrated successfully.".format(args.gogs_url))
