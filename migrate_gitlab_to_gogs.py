#!/usr/bin/env python3

import requests
from http.client import responses
import json
import subprocess
import os
import sys

import argparse

def askToContinue(args):
    if not args.no_confirm:
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
parser.add_argument('--source_namespace',
                    help='The namespace in GitLab as it appears in URLs. For example, given the repository address http://my.gitlab.net/harry/my-awesome-repo.git, it shows that this repository lies within my personal namespace "harry". In that case, I would pass harry as parameter.',
                    required=True)
parser.add_argument('--add_to_private',default=None, action='store_true',help='If you want to add the repositories under your own name, i.e. not in any organisation, use this flag.')
parser.add_argument('--add_to_organization',default=None, metavar='ORGANIZATION_NAME', help='If you want to add all the repositories to an exisiting organisation, please pass the name to this parameter. Organizations correspond to groups in GitLab. The name can be taken from the organisation\'s dashboard URL. For example, if that dashboard is available at http://my.gogs.net/org/my-awesome-organisation/dashboard, then pass my-awesome-organisation as parameter.')
parser.add_argument('--source_repo',
                    help='URL to your GitLab instance. Must be in the format: http://my.gitlab.net',
                    required=True)
parser.add_argument('--target_repo',
                    help='URL to your Gogs / Gitea instance. Must be in the format: http://my.gogs.net',
                    required=True)
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

if not (args.add_to_private or args.add_to_organization is not None):
    parser.error("Please either use flag '--add_to_private' or provide an oranization via '--add_to_organization'.")

print("Going to clone all repositories in namespace '{}' at the GitLab instance at {} to the current working directory ".format(args.source_namespace, args.source_repo), end="")
print("and push them as private repositories to ", end="")
if args.add_to_private:
    print("your personal account ", end="")
else:
    print("organisation '{}' ".format(args.add_to_organization), end="")
print("at the Gogs / Gitea instance at {}.".format(args.target_repo))

askToContinue(args)

gitlab_url = args.source_repo + '/api/v4'
gogs_url = args.target_repo + "/api/v1"

gitlab_token = getToken('GitLab', 'gitlab_token', "{}/profile/personal_access_tokens".format(args.source_repo))
gogs_token = getToken('Gogs / Gitea', 'gogs_token', "{}/user/settings/applications".format(args.target_repo))

gitlabProjectsUrl = "{}/projects".format(gitlab_url)

print()
print("Getting projects from GitLab via API at {}...".format(gitlabProjectsUrl))

sessionGitlab = requests.Session()
# https://docs.gitlab.com/ee/api/#personal-access-tokens
sessionGitlab.headers.update({'Private-Token': gitlab_token})

page_id = 1
finished = False
project_list = []
while not finished:
    print("Getting page {}".format(page_id))
    res = sessionGitlab.get("{}?page={}".format(gitlabProjectsUrl, page_id))

    if res.status_code != 200:
        sys.exit("Error: Could not get projects via API. HTTP status code '{} {}' and body: '{}'".format(res.status_code, responses[res.status_code], res.text))

    project_list += json.loads(res.text)
    if len(json.loads(res.text)) < 1:
        finished = True
    else:
        page_id += 1

if len(project_list) == 0:
    print("Warning: Could not get any project via API.")

filtered_projects = list(filter(lambda x: x['path_with_namespace'].split('/')[0]==args.source_namespace, project_list))

print("Going to migrate the following GitLab projects and repositories, respectively:")

for p in ([p['path_with_namespace'] for p in filtered_projects]):
    print("- {}".format(p))

askToContinue(args)

sessionGogs = requests.Session()
# https://docs.gitea.io/en-us/api-usage/#more-on-the-authorization-header
sessionGogs.headers.update({'Authorization': 'token {}'.format(gogs_token)})

for projectCounter in range(len(filtered_projects)):
    src_name = filtered_projects[projectCounter]['name']
    if args.use_ssh:
        src_url = filtered_projects[projectCounter]['ssh_url_to_repo']
    else:
        src_url = filtered_projects[projectCounter]['http_url_to_repo']
    src_description = filtered_projects[projectCounter]['description']
    dst_name = src_name.replace(' ','-')

    print()
    print("[{}/{}] Migrating repository at {} to destination '{}'...".format(projectCounter + 1, len(filtered_projects), src_url, dst_name))
    askToContinue(args)

    post_url = None
    if args.add_to_private:
        post_url = gogs_url + '/user/repos'
    else:
        post_url = gogs_url + "/org/{}/repos".format(args.add_to_organization)

    print()
    print("[{}/{}] Creating private repository '{}' via POSTing to: {}".format(projectCounter + 1, len(filtered_projects), dst_name, post_url))
    create_repo = sessionGogs.post(post_url, data=dict(name=dst_name, private=True, description=src_description))

    # 201: Created - The request has been fulfilled, resulting in the creation of a new resource.
    if create_repo.status_code != 201:
        print("Warning: Could not create repository '{}'. HTTP status code '{} {}' and body: '{}'".format(dst_name, create_repo.status_code, responses[create_repo.status_code], create_repo.text))
        if create_repo.status_code == 409:
            if args.skip_existing:
                print("Skipping existing repository.")
            else:
                print("Shall we skip that existing repository and continue?")
                askToContinue(args)
            continue
        else:
            sys.exit("Error: Cannot handle HTTP status code.")

    dst_info = json.loads(create_repo.text)

    if args.use_ssh:
        dst_url = dst_info['ssh_url']
    else:
        dst_url = dst_info['html_url']

    # Mirror the git repository (http://blog.plataformatec.com.br/2013/05/how-to-properly-mirror-a-git-repository/)
    print()
    print("[{}/{}] Cloning repository from: {}".format(projectCounter + 1, len(filtered_projects), src_url))
    subprocess.check_call(['git', 'clone', '--mirror', src_url])

    os.chdir(src_url.split('/')[-1])

    print()
    print("[{}/{}] Pushing repository to: {}".format(projectCounter + 1, len(filtered_projects), dst_url))
    branches=subprocess.check_output(['git','branch','-a'])
    if len(branches) == 0:
        print("Warning: This repository is empty - skipping push.")
    else:
        subprocess.check_call(['git','push','--mirror',dst_url])

    os.chdir('..')
    subprocess.check_call(['rm','-rf',src_url.split('/')[-1]])

    print()
    print("[{}/{}] Completed migration of repository '{}'. New project URL: {} Please open that URL, check if everything is as expected, and continue the migration afterwards.".format(projectCounter + 1, len(filtered_projects), dst_name, dst_info['html_url']))
    askToContinue(args)

print()
print("Migration completed.")
