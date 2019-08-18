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

## Usage

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

## Requirements

This tools is written in Python 3 using the following modules:

- `argparse`
- `datetime`
- `inquirer`
- `os`
- `requests`
- `responses`
- `subprocess`
- `sys`

Please note: The tool has been tested on Linux and macOS only. As it depends on
`inquirer` [which does not support Windows yet](https://github.com/magmax/python-inquirer/issues/63),
this tool is not compatible with Windows either.
