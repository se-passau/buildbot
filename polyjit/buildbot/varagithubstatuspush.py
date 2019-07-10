from __future__ import absolute_import
from __future__ import print_function

from buildbot.reporters.github import GitHubStatusPush

import re

from twisted.internet import defer
from twisted.python import log

from buildbot.process.properties import Interpolate
from buildbot.process.properties import Properties
from buildbot.process.results import CANCELLED
from buildbot.process.results import EXCEPTION
from buildbot.process.results import FAILURE
from buildbot.process.results import RETRY
from buildbot.process.results import SKIPPED
from buildbot.process.results import SUCCESS
from buildbot.process.results import WARNINGS
from buildbot.reporters import http
from buildbot.util import httpclientservice
from buildbot.util.giturlparse import giturlparse

HOSTED_BASE_URL = 'https://api.github.com'

class VaraGitHubStatusPush(GitHubStatusPush):

    @defer.inlineCallbacks
    def send(self, build):
        props = Properties.fromDict(build['properties'])
        props.master = self.master

        if build['complete']:
            state = {
                SUCCESS: 'success',
                WARNINGS: 'success',
                FAILURE: 'failure',
                SKIPPED: 'success',
                EXCEPTION: 'error',
                RETRY: 'pending',
                CANCELLED: 'error'
            }.get(build['results'], 'error')
            description = yield props.render(self.endDescription)
        elif self.startDescription:
            state = 'pending'
            description = yield props.render(self.startDescription)
        else:
            return

        context = yield props.render(self.context)

        sourcestamps = build['buildset'].get('sourcestamps')

        if not sourcestamps or not sourcestamps[0]:
            return

        branch = props['branch']
        m = re.search(r"refs/pull/([0-9]*)/merge", branch)
        if m:
            issue = m.group(1)
        else:
            # We only want to comment pull requests, so we exit here
            return

        for sourcestamp in sourcestamps:
            if branch == sourcestamp['branch']:
                project = sourcestamp['project']
                repository = sourcestamp['repository']
                sha = sourcestamp['revision']
                break

        if project is None:
            log.err('Failed to determine the project of PR "{branch}"'.format(
                    branch=branch))
            return

        if "/" in project:
            repoOwner, repoName = project.split('/')
        else:
            giturl = giturlparse(repository)
            repoOwner = giturl.owner
            repoName = giturl.repo

        if self.verbose:
            log.msg("Updating github status: repoOwner={repoOwner}, repoName={repoName}".format(
                repoOwner=repoOwner, repoName=repoName))

        try:
            yield self.createStatus(
                repo_user=repoOwner,
                repo_name=repoName,
                sha=sha,
                state=state,
                target_url=build['url'],
                context=context,
                issue=issue,
                description=description
            )
            if self.verbose:
                log.msg(
                    'Updated status with "{state}" for {repoOwner}/{repoName} '
                    'at {sha}, context "{context}", issue {issue}.'.format(
                        state=state, repoOwner=repoOwner, repoName=repoName,
                        sha=sha, issue=issue, context=context))
        except Exception as e:
            log.err(
                e,
                'Failed to update "{state}" for {repoOwner}/{repoName} '
                'at {sha}, context "{context}", issue {issue}.'.format(
                    state=state, repoOwner=repoOwner, repoName=repoName,
                    sha=sha, issue=issue, context=context))


class VaraGitHubPullRequestCommentPush(VaraGitHubStatusPush):
    neededDetails = dict(wantProperties=True)

    def setDefaults(self, context, startDescription, endDescription):
        self.context = ''
        self.startDescription = startDescription
        self.endDescription = endDescription or 'Build done.'

    def createStatus(self,
                     repo_user, repo_name, sha, state, target_url=None,
                     context=None, issue=None, description=None):
        """
        :param repo_user: GitHub user or organization
        :param repo_name: Name of the repository
        :param issue: Pull request number
        :param state: one of the following 'pending', 'success', 'error'
                      or 'failure'.
        :param description: Short description of the status.
        :return: A deferred with the result from GitHub.

        This code comes from txgithub by @tomprince.
        txgithub is based on twisted's webclient agent, which is much less reliable and featureful
        as txrequest (support for proxy, connection pool, keep alive, retry, etc)
        """
        payload = {'body': description}

        return self._http.post(
            '/'.join(['/repos', repo_user, repo_name, 'issues', issue, 'comments']),
            json=payload)
