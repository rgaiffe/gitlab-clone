#!/usr/bin/env python3

import argparse
import os
import requests
import sys
import json
import git

from pathlib import Path
from loguru import logger
from git import Repo

GITLAB_API_URI = "https://gitlab.com/api/graphql"
# Choose namespace here
NAMESPACE = ""


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workdir",
        type=str,
        help="Workdir when all projects is located or is cloned default $HOME",
    )
    parser.add_argument(
        "--gitlab-token",
        type=str,
        required=True,
        help="Gitlab token with read_api and read_repository permissions (https://gitlab.com/-/profile/personal_access_tokens)",
    )
    return parser.parse_args()


def get_gitlab_repos(gitlab_token: str) -> list:
    headers = {"Authorization": "Bearer {}".format(gitlab_token)}
    query = """
    {
        namespace(fullPath: "%s") {
            projects(includeSubgroups: true) {
                nodes {
                    sshUrlToRepo
                    fullPath
                }
            }
        }
    }
    """ % (
        NAMESPACE
    )
    ret = requests.post(GITLAB_API_URI, headers=headers, json={"query": query})
    if (
        ret.status_code != 200
        or "errors" in json.loads(ret.content.decode("utf-8")).keys()
    ):
        logger.error(
            "Gitlab Graphql API return an error: Status code {} Message: {}".format(
                ret.status_code, ret.content.decode("utf-8")
            )
        )
        sys.exit(1)
    return json.loads(ret.content.decode("utf-8"))["data"]["namespace"]["projects"][
        "nodes"
    ]


def clone_repo(workdir: str, repo: dict) -> None:
    try:
        Repo.clone_from(repo["sshUrlToRepo"], "{}/{}".format(workdir, repo["fullPath"]))
    except git.exc.GitCommandError as err:
        logger.error(err)


def pull_repo(workdir: str, repoPath: str) -> None:
    try:
        git.cmd.Git("{}/{}".format(workdir, repoPath)).pull()
    except git.exc.GitCommandError as err:
        logger.error(err)


def get_repos(workdir: str, repos: list) -> None:
    for repo in repos:
        repoName = repo["fullPath"].split("/")[-1:][0]
        if not os.path.exists("{}/{}".format(workdir, repo["fullPath"])):
            logger.info(
                "Cloning {} to {}/{}".format(repoName, workdir, repo["fullPath"])
            )
            clone_repo(workdir, repo)
        else:
            logger.info(
                "Pulling {} localised in {}/{}".format(
                    repoName, workdir, repo["fullPath"]
                )
            )
            pull_repo(workdir, repo["fullPath"])


def get_workdir(args: argparse.Namespace) -> str:
    if not args.workdir:
        workdir = os.environ.get("HOME")
    else:
        workdir = args.workdir
    return workdir


def main() -> None:
    logger.remove()
    logger.add(sys.stdout, format="[{time:HH:mm:ss}] :: <lvl>{message}</lvl>")
    args = get_args()
    workdir = get_workdir(args)
    repos = get_gitlab_repos(args.gitlab_token)
    get_repos(workdir, repos)


if __name__ == "__main__":
    main()
