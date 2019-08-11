#!/usr/bin/env python3

import requests
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
        print("Please provide your personal {} access token.".format(tokenName))
        print("Hint: That token is not your password but a hash value which consists of random letters and numbers.")
        print("      You can generate an access token at {}.".format(tokenURL))
        token = input("{}=".format(tokenEnvName))
        if len(token) < 1:
            sys.exit("Error: The given token must not be empty.")

    return token

parser = argparse.ArgumentParser()
parser.add_argument('--source_namespace',
                    help='The namespace in gitlab as it appears in URLs. For example, given the repository address http://mygitlab.com/harry/my-awesome-repo.git, it shows that this repository lies within my personal namespace "harry". Hence I would pass harry as parameter.',
                    required=True)
parser.add_argument('--add_to_private',default=None, action='store_true',help='If you want to add the repositories under your own name, ie. not in any organisation, use this flag.')
parser.add_argument('--add_to_organization',default=None, metavar='ORGANIZATION_NAME', help='If you want to add all the repositories to an exisiting organisation, please pass the name to this parameter. Organizations correspond to groups in Gitlab. The name can be taken from the URL, for example, if your organization is http://mygogs-repo.com/org/my-awesome-organisation/dashboard then pass my-awesome-organisation here')
parser.add_argument('--source_repo',
                    help='URL to your gitlab repo in the format http://mygitlab.com',
                    required=True)
parser.add_argument('--target_repo',
                    help='URL to your gogs / gitea repo in the format http://mygogs.com',
                    required=True)
parser.add_argument('--no_confirm',
                    help='Skip user confirmation of each single step',
                    action='store_true')
parser.add_argument('--skip_existing',
                    help='Skip repositories that already exist on remote without asking the user',
                    action='store_true')
parser.add_argument('--use_ssh',
                    help='Use ssh to pull/push files to repos',
                    action='store_true')

args = parser.parse_args()

if not (args.add_to_private or args.add_to_organization is not None):
    parser.error("Please either use flag '--add_to_private' or provide an oranization via '--add_to_organization'.")

print("Going to clone all repositories in namespace '{}' at '{}' to the current working directory ".format(args.source_namespace, args.source_repo), end="")
print("and push them as private repositories to ", end="")
if args.add_to_private:
    print("your personal account ", end="")
else:
    print("organisation '{}' ".format(args.add_to_organization), end="")
print("at '{}'.".format(args.target_repo))

askToContinue(args)

gitlab_url = args.source_repo + '/api/v4'
gogs_url = args.target_repo + "/api/v1"

gitlab_token = getToken('GitLab', 'gitlab_token', "{}/profile/personal_access_tokens".format(args.source_repo))
gogs_token = getToken('Gogs / Gitea', 'gogs_token', "{}/user/settings/applications".format(args.target_repo))

print()
print("Getting projects from Gitlab...")

s = requests.Session()
page_id = 1
finished = False
project_list = []
while not finished:
    print("Getting page {}".format(page_id))
    res = s.get(gitlab_url + '/projects?private_token=%s&page=%s'%(gitlab_token,page_id))
    assert res.status_code == 200, 'Error when retrieving the projects. The returned html is %s'%res.text
    project_list += json.loads(res.text)
    if len(json.loads(res.text)) < 1:
        finished = True
    else:
        page_id += 1

filtered_projects = list(filter(lambda x: x['path_with_namespace'].split('/')[0]==args.source_namespace, project_list))


print("Going to migrate the following GitLab projects and repositories, respectively:")

for p in ([p['path_with_namespace'] for p in filtered_projects]):
    print("- {}".format(p))

askToContinue(args)

for i in range(len(filtered_projects)):
    src_name = filtered_projects[i]['name']
    if args.use_ssh:
        src_url = filtered_projects[i]['ssh_url_to_repo']
    else:
        src_url = filtered_projects[i]['http_url_to_repo']
    src_description = filtered_projects[i]['description']
    dst_name = src_name.replace(' ','-')

    print('\n\nMigrating project %s to project %s now.'%(src_url,dst_name))

    askToContinue(args)

    # Create repo
    if args.add_to_private:
        print('Posting to:' + gogs_url + '/user/repos')
        create_repo = s.post(gogs_url+'/user/repos', data=dict(token=gogs_token, name=dst_name, private=True))

    elif args.add_to_organization:
        print('Posting to:' + gogs_url + '/org/%s/repos')
        create_repo = s.post(gogs_url+'/org/%s/repos'%args.add_to_organization,
                            data=dict(token=gogs_token, name=dst_name, private=True, description=src_description))
    if create_repo.status_code != 201:
        print('Could not create repo %s because of %s'%(src_name,json.loads(create_repo.text)['message']))
        if args.skip_existing:
            print('\nSkipped')
        else:
            askToContinue(args)
        continue

    dst_info = json.loads(create_repo.text)

    if args.use_ssh:
        dst_url = dst_info['ssh_url']
    else:
        dst_url = dst_info['html_url']

    # Mirror the git repository (http://blog.plataformatec.com.br/2013/05/how-to-properly-mirror-a-git-repository/)
    subprocess.check_call(['git','clone','--mirror',src_url])
    os.chdir(src_url.split('/')[-1])
    branches=subprocess.check_output(['git','branch','-a'])
    if len(branches) == 0:
        print('\n\nThis repository is empty - skipping push')
    else:
        subprocess.check_call(['git','push','--mirror',dst_url])
    os.chdir('..')
    subprocess.check_call(['rm','-rf',src_url.split('/')[-1]])

    print('\n\nFinished migration. New project URL is %s'%dst_info['html_url'])
    print('Please open the URL and check if everything is fine.')
    askToContinue(args)

print('\n\nEverything finished!\n')
