import sys, re
from collections import OrderedDict

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, ucmd, ucompile, cmd,
                                    upload_file, ip, s_sbranch, s_abranch,
                                    s_nightly, s_force, s_trigger,
                                    hash_upload_to_master)
from polyjit.buildbot.repos import make_cb, make_new_cb, make_git_cb, make_force_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util, steps, schedulers
from buildbot.changes import filter
from buildbot.process import buildstep, logobserver
from twisted.internet import defer

from buildbot.interfaces import IRenderable
from zope.interface import implementer

################################################################################
# Notes:
#
# Get the values for 'upstream_merge_base' with the following commands:
#   - git merge-base origin/vara-llvm-50-dev upstream/release_50
#   - git merge-base origin/vara-clang-50-dev upstream/release_50
################################################################################

project_name     = 'vara'
trigger_branches = 'vara-dev|vara-llvm-50-dev|vara-clang-50-dev'
uchroot_src_root = '/mnt/vara-llvm'
checkout_base_dir = '%(prop:builddir)s/vara-llvm'

repos = OrderedDict()

repos['vara-llvm'] = {
    'default_branch': 'vara-llvm-50-dev',
    'checkout_dir': checkout_base_dir,
    'checkout_subdir': '',
    'upstream_remote_url': 'https://git.llvm.org/git/llvm.git/',
    'upstream_merge_base': '3359933e710d5dae2815cf2fd3d776dfb3ffe1fa',
}
repos['vara-clang'] = {
    'default_branch': 'vara-clang-50-dev',
    'checkout_dir': checkout_base_dir + '/tools/clang',
    'checkout_subdir': '/tools/clang',
    'upstream_remote_url': 'https://git.llvm.org/git/clang.git/',
    'upstream_merge_base': '0bc78694a319f80a28ca30e4d9d69c292ee12dee',
}
repos['vara'] = {
    'default_branch': 'vara-dev',
    'checkout_dir': checkout_base_dir + '/tools/VaRA',
    'checkout_subdir': '/tools/VaRA',
}
repos['compiler-rt'] = {
    'default_branch': 'release_50',
    'checkout_dir': checkout_base_dir + '/projects/compiler-rt',
}
repos['clang-tools-extra'] = {
    'default_branch': 'release_50',
    'checkout_dir': checkout_base_dir + '/tools/clang/tools/extra',
}

################################################################################

codebase = make_git_cb(repos)
force_codebase = make_force_cb(repos)

P = util.Property

accepted_builders = slaves.get_hostlist(slaves.infosun, predicate=lambda host: host["host"] in {'debussy', 'ligeti'})

# TODO check
class GenerateMakeCleanCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        force_build_clean = None
        if self.hasProperty('options'):
            options = self.getProperty('options')
            force_build_clean = options['force_build_clean']

        if force_build_clean:
            self.build.addStepsAfterCurrentStep([
                define('FORCE_BUILD_CLEAN', 'true'),
                ucompile('ninja', 'clean', haltOnFailure=True, warnOnWarnings=True, name='clean build dir')
            ])
        else:
            self.build.addStepsAfterCurrentStep([define('FORCE_BUILD_CLEAN', 'false')])

        defer.returnValue(cmd.results())

class GenerateGitCloneCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        force_complete_rebuild = None
        if self.hasProperty('options'):
            options = self.getProperty('options')
            force_complete_rebuild = options['force_complete_rebuild']

        buildsteps = []

        for repo in repos:
            buildsteps.append(define(str(repo).upper() +'_ROOT', ip(repos[repo]['checkout_dir'])))

        if force_complete_rebuild:
            buildsteps.append(define('FORCE_COMPLETE_REBUILD', 'true'))
            buildsteps.append(steps.ShellCommand(name='Delete old build directory',
                              command=['rm', '-rf', 'build'], workdir=ip(checkout_base_dir + '/../')))

            for repo in repos:
                url = codebases[repo]['repository']
                branch = repos[repo]['default_branch']
                buildsteps.append(steps.Git(repourl=url, branch=branch, codebase=repo,
                                  name="checkout: {0}".format(url), description="checkout: {0}@{1}".format(url, branch),
                                  timeout=1200, progress=True, workdir=P(str(repo).upper()+'_ROOT'),
                                  mode='full', method='clobber'))
        else:
            self.build.addStepsAfterCurrentStep([define('FORCE_COMPLETE_REBUILD', 'false')])
            for repo in repos:
                buildsteps.append(git(repo, repos[repo]['default_branch'], codebases, workdir=P(str(repo).upper()+'_ROOT')))

        self.build.addStepsAfterCurrentStep(buildsteps)

        defer.returnValue(cmd.results())


class GenerateMergecheckCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        result = cmd.results()
        if result == util.SUCCESS:
            mergecheck_repo = self.getProperty('mergecheck_repo')
            current_branch = self.observer.getStdout().strip()
            upstream_remote_url = repos[mergecheck_repo]['upstream_remote_url']
            default_branch = repos[mergecheck_repo]['default_branch']
            repo_dir = uchroot_src_root + repos[mergecheck_repo]['checkout_subdir']
            upstream_merge_base = repos[mergecheck_repo]['upstream_merge_base']

            if 'upstream_merge_base' not in repos[mergecheck_repo]:
                # This repository has no remote to compare against , so no mergecheck has to be done.
                defer.returnValue(result)

            self.build.addStepsAfterCurrentStep([
                ucompile('/opt/mergecheck/bin/mergecheck', 'rebase',
                    '--repo', repo_dir,
                    '--remote-url', upstream_remote_url,
                    '--remote-name', 'upstream',
                    '--onto', 'refs/remotes/upstream/master'
                    '--upstream', upstream_merge_base,
                    '--branch', current_branch,
                    '-v', '--print-conflicts',
                    name='Mergecheck \"' + mergecheck_repo + '\"',
                    haltOnFailure=False, warnOnWarnings=True, warningPattern='^CONFLICT.*'),
            ])

            defer.returnValue(result)


# yapf: disable
def configure(c):
    f = util.BuildFactory()

    # TODO Check if this can be done without a dummy command
    #f.addStep(GenerateGitCloneCommand())
    f.addStep(GenerateGitCloneCommand(name="Dummy_1", command=['true'], haltOnFailure=True, hideStepIf=True))

    f.addStep(define('UCHROOT_SRC_ROOT', uchroot_src_root))
    f.addStep(ucmd('cmake', P('UCHROOT_SRC_ROOT'),
                   '-DCMAKE_BUILD_TYPE=Debug',
                   '-DCMAKE_C_FLAGS=-g -fno-omit-frame-pointer',
                   '-DCMAKE_CXX_FLAGS=-g -fno-omit-frame-pointer',
                   '-DBUILD_SHARED_LIBS=On',
                   '-DLLVM_TARGETS_TO_BUILD=X86',
                   '-DLLVM_BINUTILS_INCDIR=/usr/include',
                   '-DLLVM_ENABLE_PIC=On',
                   '-DLLVM_ENABLE_ASSERTIONS=On',
                   '-DLLVM_ENABLE_TERMINFO=Off',
                   '-G', 'Ninja',
                   env={
                       'PATH': '/opt/cmake/bin:/usr/local/bin:/usr/bin:/bin'
                   },
                   name='cmake',
                   description='cmake O3, Assertions, PIC, Shared'))

    f.addStep(GenerateMakeCleanCommand(name="Dummy_2", command=['true'], haltOnFailure=True, hideStepIf=True))

    f.addStep(ucompile('ninja', haltOnFailure=True, warnOnWarnings=True, name='build VaRA'))

    f.addStep(ucompile('ninja', 'check-vara', haltOnFailure=True, warnOnWarnings=True, name='run VaRA regression tests'))

    # TODO fix hardcoded path
    f.addStep(ucompile('python3', 'tidy-vara-gcc.py', '-p', '/mnt/build',
        workdir='vara-llvm/tools/VaRA/test/',
        name='run Clang-Tidy', haltOnFailure=False, warnOnWarnings=True, env={'PATH': ["/mnt/build/bin", "${PATH}"]}))

    # Mergecheck
    for repo in repos:
        f.addStep(define('mergecheck_repo', repo))
        f.addStep(GenerateMergecheckCommand(name="Dummy_3", command=['git', 'symbolic-ref', 'HEAD'],
            workdir=ip(repos[repo]['checkout_dir']), haltOnFailure=True, hideStepIf=True))

    c['builders'].append(builder('build-' + project_name, None, accepted_builders, tags=['vara'], factory=f))

def schedule(c):
    force_sched = s_force(
        name="force-build-" + project_name,
        cb=force_codebase,
        builders=["build-" + project_name],
        properties=[
            util.NestedParameter(name="options", label="Build Options", layout="vertical", fields=[
                util.BooleanParameter(name="force_build_clean",
                            label="force a make clean",
                                    default=False),
                util.BooleanParameter(name="force_complete_rebuild",
                            label="force complete rebuild and fresh git clone",
                                    default=False),
            ])
        ]
    )

    c['schedulers'].extend([
        s_abranch('build-' + project_name + '-sched', codebase, ['build-' + project_name],
                  change_filter=filter.ChangeFilter(branch_re=trigger_branches),
                  treeStableTimer=5 * 60),
        force_sched,
        s_trigger('trigger-build-' + project_name, codebase, ['build-' + project_name]),
        # TODO: Fix nightly scheduler (currently not working)
        #s_nightly('nightly-sched-build-' + project_name, codebase,
        #          ['build-' + project_name],
        #          hour=22, minute=0)
    ])
# yapf: enable


register(sys.modules[__name__])
