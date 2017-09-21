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

project_name     = 'vara-features'
trigger_branch_regex = "^(f-\S+)$"
uchroot_src_root = '/mnt/vara-llvm-features'
checkout_base_dir = '%(prop:builddir)s/vara-llvm-features'

repos = OrderedDict()

repos['vara-llvm'] = {
    'default_branch': 'vara-llvm-50-dev',
    'checkout_dir': checkout_base_dir,
    'checkout_subdir': '',
}
repos['vara-clang'] = {
    'default_branch': 'vara-clang-50-dev',
    'checkout_dir': checkout_base_dir + '/tools/clang',
    'checkout_subdir': '/tools/clang',
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

def trigger_branch_match(branch):
    pattern = re.compile(trigger_branch_regex)
    return pattern.match(branch)

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

class GenerateGitCheckoutCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    def get_feature_branch(self, stdout):
        for branch in stdout.split('\n'):
            if trigger_branch_match(branch):
                return branch
        return ''

    @defer.inlineCallbacks
    def run(self):
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)

        result = cmd.results()
        if result == util.SUCCESS:
            checkout_feature_br = self.get_feature_branch(self.observer.getStdout())

            if checkout_feature_br:
                self.build.addStepsAfterCurrentStep([
                    define('FEATURE', checkout_feature_br),
                    steps.ShellCommand(name='Checking out feature branch \"' + str(checkout_feature_br) + '\"',
                        command=['./tools/VaRA/utils/buildbot/bb-checkout-branches.sh', checkout_feature_br],
                        workdir=ip(checkout_base_dir)),
                ])
            else:
                force_feature = None
                if self.hasProperty('options'):
                    options = self.getProperty('options')
                    force_feature = options['force_feature']

                self.build.addStepsAfterCurrentStep([
                    define('FEATURE', force_feature),
                    steps.ShellCommand(name=ip('Checking out feature branch \"%(prop:FEATURE)s\"'),
                        command=['./tools/VaRA/utils/buildbot/bb-checkout-branches.sh', force_feature],
                        workdir=ip(checkout_base_dir)),
                ])

        defer.returnValue(result)

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
            # upstream_remote_url = repos[mergecheck_repo]['upstream_remote_url'] # needed in vara.py
            default_branch = repos[mergecheck_repo]['default_branch']
            repo_dir = uchroot_src_root + repos[mergecheck_repo]['checkout_subdir']

            if default_branch == current_branch.replace('refs/heads/', ''):
                # This repository has no feature branch, so nothing has to be merged.
                defer.returnValue(result)

            # TODO: use ucompile and add warningregex
            self.build.addStepsAfterCurrentStep([
                ucmd('/opt/mergecheck/bin/mergecheck', 'rebase',
                    '--repo', repo_dir,
                    '--upstream', 'refs/remotes/origin/' + default_branch,
                    '--branch', current_branch,
                    '-v', '--print-conflicts',
                    name='Mergecheck \"' + mergecheck_repo + '\"', haltOnFailure=False, warnOnWarnings=True),
            ])

            defer.returnValue(result)


# yapf: disable
def configure(c):
    f = util.BuildFactory()

    # TODO Check if this can be done without a dummy command
    #f.addStep(GenerateGitCloneCommand())
    f.addStep(GenerateGitCloneCommand(name="Dummy_1", command=['true'], haltOnFailure=True, hideStepIf=True))

    f.addStep(GenerateGitCheckoutCommand(
        name="Get branch names",
        command=['./tools/VaRA/utils/buildbot/bb-get-branches.sh'], workdir=ip(checkout_base_dir),
        haltOnFailure=True, hideStepIf=True))

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

    f.addStep(ucompile('python3', 'tidy-vara-gcc.py', '-p', '/mnt/build',
        workdir='vara-llvm-features/tools/VaRA/test/',
        name='run Clang-Tidy', haltOnFailure=False, warnOnWarnings=True, env={'PATH': ["/mnt/build/bin", "${PATH}"]}))

    # Mergecheck
    for repo in ['vara-llvm', 'vara-clang', 'vara']:
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
                util.StringParameter(name="force_feature",
                            label="feature-branch to build:",
                            default="", size=80),
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
                  change_filter=util.ChangeFilter(branch_fn=trigger_branch_match),
                  treeStableTimer=5 * 60),
        force_sched,
        s_trigger('trigger-build-' + project_name, codebase, ['build-' + project_name]),
    ])
# yapf: enable


register(sys.modules[__name__])
