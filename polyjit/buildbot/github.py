from __future__ import absolute_import
from __future__ import print_function

from buildbot.www.hooks.github import GitHubEventHandler

import hmac
import json
import logging
import re
from hashlib import sha1

from dateutil.parser import parse as dateparse

from twisted.internet import defer
from twisted.python import log

from buildbot.changes.github import PullRequestMixin
from buildbot.util import bytes2unicode
from buildbot.util import httpclientservice
from buildbot.util import unicode2bytes
from buildbot.www.hooks.base import BaseHookHandler

_HEADER_EVENT = b'X-GitHub-Event'
_HEADER_SIGNATURE = b'X-Hub-Signature'

DEFAULT_SKIPS_PATTERN = (r'\[ *skip *ci *\]', r'\[ *ci *skip *\]')
DEFAULT_GITHUB_API_URL = 'https://api.github.com'

class CustomGitHubHandler(GitHubEventHandler):
    def handle_pull_request(self, payload, event):
        changes = None

        branch = "refs/pull/{}/merge".format(payload['number'])

        if payload['action'] not in ("opened", "synchronize"):
            logging.info("PR %r %r, ignoring",
                         payload['number'], payload['action'])
            return None
        else:
            changes = []

            number = payload['number']
            refname = 'refs/pull/{}/merge'.format(number)
            commits = payload['pull_request']['commits']
            title = payload['pull_request']['title']
            comments = payload['pull_request']['body']
            repo_full_name = payload['repository']['full_name']
            head_sha = payload['pull_request']['head']['sha']
            properties = self.extractProperties(payload['pull_request'])
            properties.update({'event': event})

            # FIXME: Buildbot only schedules a build, if there is at least one change.
            # Unfortunately, there seems to be no easy way to get a list of all
            # the changed files.
            # If possible, we should get this list and include it here.
            # Until this is implemented properly, we use a dummy change here so
            # that buildbot starts a build.
            # This means, of course, that _all_ pull requests are built, even if they contain
            # no meaningful change.

            # Create a synthetic change
            change = {
                'id': payload['pull_request']['head']['sha'],
                'message': payload['pull_request']['body'],
                'timestamp': payload['pull_request']['updated_at'],
                'url': payload['pull_request']['html_url'],
                'author': {
                    'username': payload['pull_request']['user']['login'],
                },
                'comments': u'GitHub Pull Request #{0} ({1} commit{2})\n{3}\n{4}'.format(
                    number, commits, 's' if commits != 1 else '', title, comments),
                'properties': properties,
                'added': [],
                'removed': [],
                'modified': ['dummy'],
            }

        repo = payload['repository']['name']
        repo_url = payload['repository']['html_url']

        changes.append(self.process_pull_request_change(
            change, branch, repo, repo_url))

        return changes, 'git'

    def process_pull_request_change(self, change, branch, repo, repo_url):
        files = change['added'] + change['removed'] + change['modified']
        who = ""
        if 'username' in change['author']:
            who = change['author']['username']
        else:
            who = change['author']['name']
        if 'email' in change['author']:
            who = "%s <%s>" % (who, change['author']['email'])

        comments = change['comments']
        if len(comments) > 1024:
            trim = " ... (trimmed, commit message exceeds 1024 characters)"
            comments = comments[:1024 - len(trim)] + trim

        info_change = {'revision': change['id'],
             'revlink': change['url'],
             'who': who,
             'comments': comments,
             'category': 'pull',
             'properties': change['properties'],
             'repository': repo_url,
             'files': files,
             'project': repo,
             'branch': branch}

        return info_change
