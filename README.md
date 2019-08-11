# Migration utility for moving from Gitlab to Gogs / Gitea

This tool provides an automated way to copy all repositories from a given Gitlab
namespace (e.g., Gitlab group) to Gogs / Gitea.  There, repositories can be
migrated to a user's personal space, or to a given organization. The latter
corresponds to GitLab groups. When migrating repositories, all the branches and
tags that are available in the GitLab repository will be replicated into the new
Gogs / Gitea repository. Git notes and other attributes are replicated as well.

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

## Usage

Run `python3 migrate_gitlab_to_gogs.py --help` for usage information:

```
usage: migrate_gitlab_to_gogs.py [-h] --gitlab_url GITLAB_URL
                                 --gitlab_namespace GITLAB_NAMESPACE
                                 --gogs_url GOGS_URL [--add_to_user USER_NAME]
                                 [--add_to_organization ORGANIZATION_NAME]
                                 [--force_private] [--force_archive]
                                 [--force_disable_issues]
                                 [--force_disable_wiki] [--no_confirm]
                                 [--skip_existing] [--use_ssh]

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
                        name, i.e. not in any organisation, use this parameter
                        to specify your username.
  --add_to_organization ORGANIZATION_NAME
                        If you want to add all the repositories to an
                        exisiting organisation, please pass the name to this
                        parameter. Organizations correspond to groups in
                        GitLab. The name can be taken from the organisation's
                        dashboard URL. For example, if that dashboard is
                        available at http://my.gogs.net/org/my-awesome-
                        organisation/dashboard, then pass my-awesome-
                        organisation as parameter.
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
  --no_confirm          Skip user confirmation of each single step.
  --skip_existing       Skip any repository that already exists on the Gogs /
                        Gitea instance without asking for confirmation.
  --use_ssh             Use SSH instead of HTTP(S) to clone and push
                        repositories.
```

## Requirements

This tools is written in Python 3 using the following modules:

- `argparse`
- `os`
- `requests`
- `responses`
- `subprocess`
- `sys`
