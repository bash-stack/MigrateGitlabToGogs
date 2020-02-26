# Migration utility for moving from Gitlab to Gogs / Gitea

This tool provides an automated way to copy all repositories from a given Gitlab
namespace (e.g., Gitlab group) to Gogs / Gitea.  There, repositories can be
migrated to a user's personal space, or to a given organization. The latter
corresponds to GitLab groups. When migrating repositories, all the branches and
tags, all Git notes, and other attributes that are available in the GitLab
repository will be replicated into the new Gogs / Gitea repository.

Please note that in GitLab repositories are contained within projects, next to
the corresponding issues and the corresponding wiki. In Gogs / Gitea, all those
things are contained within a repository.

The following GitLab settings are replicated:

- the GitLab project name will become the repository name at Gogs / Gitea;
- the same applies to the description;
- if the GitLab project is public, the repository at Gogs / Gitea will become
  public as well; both private and internal GitLab projects will become private
  Gogs / Gitea repositories;
- archived GitLab projects will become archived Gogs / Gitea repositories
- the default branch
- if the issue tracker in the GitLab project is enabled, it will be enabled in
  the corresponding Gogs / Gitea repository too, if the tracker is disabled, the
  one at Gogs / Gitea will be disabled too;
- the same applies to the wiki.

Please note that issues and wiki content will _not_ be migrated.

Unless otherwise instructed, the tool is interactive: It asks for confirmation
for most of the steps in the migration process; if an issue occurs, the user
will be presented with different options on how to proceed. The tool can be run
in an non-interactive mode as well. Then, it migrates all repositories
automatically; if an issue occurs, the migration process will be stopped
immediately.

By default, the tools expects that the Gogs / Gitea organization already exists.
If not, the tool cancels the migration. However, you can instruct the tool to
create any non-existent organization. To give you the opportunity to safely
review all migrated repositories in that organization, the automatically created
organization will be private.

You can enforce some attributes on the Gogs / Gitea repository, like making it
private although the GitLab projects is public. Please see the command line
options for details.

The tool can use both HTTP(S) and SSH to clone and push repositories.

## Important Security Note

In order to simplify the process of running this script with servers that use self-signed certificates I have **disabled certificate verification**. If you do not know and trust the servers that you are migrating to and from **do not use this fork** as it will not check for faked certificates.


## Requirements

This tools is written in Python 3 and uses the following modules:

- `argparse`
- `datetime`
- `inquirer`
- `os`
- `requests`
- `responses`
- `subprocess`
- `sys`

**Note:** Most of the modules required are from Pythons standard library, but for those that arn't we recommend that they be installed in a virtual environement.

## Installation

After cloning down this project, the first thing you'll need to do is setup a virtual environment. There are several ways to do this but we recommend just using python3's built in `venv` command:

```
python3 -m venv .venv
```

Once the virtual environment has been setup you will need to activate it in order to install packages inside of it.

```
source .venv/bin/activate
```

You should now see the name of the virtual environment appended to the current user and path in your terminal. (e.g. `$ (.venv) user@dev-server:/current/path/`)

Now you can install the package dependencies using pip.

```
pip install -r requirements.txt
```

## Usage

**Virtual Environment Note:** If you installed the package dependencies in a virtual environment you will need to activate it before you can run the migration script (e.g.`source .venv/bin/activate`)

Run `python3 migrate_gitlab_to_gogs.py --help` for usage information:

```
usage: migrate_gitlab_to_gogs.py [-h] --gitlab_url GITLAB_URL
                                 --gitlab_namespace GITLAB_NAMESPACE
                                 --gogs_url GOGS_URL [--add_to_user USER_NAME]
                                 [--add_to_organization ORGANIZATION_NAME]
                                 [--create_organization] [--force_private]
                                 [--force_archive] [--force_disable_issues]
                                 [--force_disable_wiki] [--non_interactive]
                                 [--skip_existing_target] [--use_ssh]

optional arguments:
  -h, --help            show this help message and exit
  --gitlab_url GITLAB_URL
                        URL to your GitLab instance. Must be in the format:
                        http://my.gitlab.net
  --gitlab_namespace GITLAB_NAMESPACE
                        The namespace in GitLab as it appears in URLs. For
                        example, given the repository address
                        http://my.gitlab.net/harry/my-awesome-repo.git, it
                        shows that this repository lies within my personal
                        namespace "harry". In that case, I would pass harry as
                        parameter.
  --gogs_url GOGS_URL   URL to your Gogs / Gitea instance. Must be in the
                        format: http://my.gogs.net
  --add_to_user USER_NAME
                        If you want to add the repositories under your own
                        name, i.e. not in any organization, use this parameter
                        to specify your username.
  --add_to_organization ORGANIZATION_NAME
                        If you want to add all the repositories to an
                        organization, please pass the name to this parameter.
                        Organizations correspond to groups in GitLab. The name
                        can be taken from the organization's dashboard URL.
                        For example, if that dashboard is available at
                        http://my.gogs.net/org/my-awesome-
                        organization/dashboard, then pass my-awesome-
                        organization as parameter.
  --create_organization
                        If the target Gogs / Gitea organization does not exist
                        yet, create it and make it private. By default,
                        organizations are expected to exist already.
  --force_private       Make all migrated repositories private in Gogs / Gitea
                        even if public in corresponding Gitlab project.
  --force_archive       Archive all migrated repositories in Gogs / Gitea even
                        if not archived in corresponding Gitlab project.
  --force_disable_issues
                        Disable issue tracker in Gogs / Gitea for all migrated
                        repositories even if enabled in corresponding Gitlab
                        project.
  --force_disable_wiki  Disable wiki in Gogs / Gitea for all migrated
                        repositories even if enabled in corresponding Gitlab
                        project.
  --non_interactive     Migrate all repositories in the given GitLab namespace
                        automatically; if an issue occurs, the migration
                        process will be stopped immediately. By default, the
                        script asks for confirmation for most of the steps in
                        the migration process; if an issue occurs, the user
                        will be presented with different options on how to
                        proceed.
  --skip_existing_target
                        Skip any repository that already exists on the target
                        Gogs / Gitea instance without asking for confirmation.
  --use_ssh             Use SSH instead of HTTP(S) to clone and push
                        repositories.
```


### Example command

#### Group to Organization

The below command is used to migrate all of the repositories stored in Gitlab's `old` group to the `new` organization in Gitea:

```
python migrate_gitlab_to_gogs.py --gitlab_namespace old --add_to_organization new --gitlab_url http://gitlab.devserver.localdomain:30080 --gogs_url https://gitea.devserver.localdomain:3000 --skip_existing_target --use_ssh
```

**NOTE:** This command uses the `--use_ssh` flag so you won't have to type in the username and password for each repository. This requires both Gitlab and Gitea to have SSH setup and configured.

##### User to Different User

This command is used to migrate all of the repositories stored in Gitlab's `old` user to the `new` user account in Gitea:

```
python migrate_gitlab_to_gogs.py --gitlab_namespace old --add_to_user new --gitlab_url http://gitlab.devserver.localdomain:30080 --gogs_url https://gitea.devserver.localdomain:3000 --skip_existing_target --use_ssh
```

**NOTE:** This command uses the `--use_ssh` flag so you won't have to type in the username and password for each repository. This requires both Gitlab and Gitea to have SSH setup and configured.

### Compatibility

Please note: The tool has been tested on Linux and macOS only. As it depends on
`inquirer` [which does not support Windows yet](https://github.com/magmax/python-inquirer/issues/63),
this tool is not compatible with Windows either.
