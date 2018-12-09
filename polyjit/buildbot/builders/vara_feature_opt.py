import sys
import re
from collections import OrderedDict

from twisted.internet import defer

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, ucmd, ucompile, cmd,
                                    upload_file, ip, s_sbranch, s_abranch,
                                    s_nightly, s_force, s_trigger)
from polyjit.buildbot.repos import make_git_cb, make_force_cb, codebases
from buildbot.plugins import util, steps
from buildbot.changes import filter
from buildbot.process import buildstep, logobserver
from buildbot.interfaces import IRenderable

################################################################################
# Notes:
#
# Get the values for 'upstream_merge_base' with the following command:
#   - git merge-base origin/vara-60-dev upstream/release_60
################################################################################

UCHROOT_SRC_ROOT = '/mnt/vara-llvm'
CHECKOUT_BASE_DIR = '%(prop:builddir)s/vara-llvm'

# Adapt these values according to build type:
PROJECT_NAME = 'vara-feature-opt'
TRIGGER_BRANCH_REGEX = r"^(refs\/pull\/\d+\/merge)$"
BUILD_SUBDIR = '/build/opt'
BUILD_SCRIPT = 'build-opt.sh'
BUILD_DIR = '%(prop:builddir)s/vara-llvm/build/opt'

UCHROOT_BUILD_DIR = UCHROOT_SRC_ROOT + BUILD_SUBDIR

# Also adapt these values:
REPOS = OrderedDict()
REPOS['vara-llvm'] = {
    'default_branch': 'vara-60-dev',
    'checkout_dir': CHECKOUT_BASE_DIR,
    'checkout_subdir': '',
    'upstream_remote_url': 'https://git.llvm.org/git/llvm.git/',
    'upstream_merge_base': '089d4c0c490687db6c75f1d074e99c4d42936a50',
}
REPOS['vara-clang'] = {
    'default_branch': 'vara-60-dev',
    'checkout_dir': CHECKOUT_BASE_DIR + '/tools/clang',
    'checkout_subdir': '/tools/clang',
    'upstream_remote_url': 'https://git.llvm.org/git/clang.git/',
    'upstream_merge_base': 'ff0c0d8ab3e316bb6e2741fedb3b545e198eab7a',
}
REPOS['vara'] = {
    'default_branch': 'vara-dev',
    'checkout_dir': CHECKOUT_BASE_DIR + '/tools/VaRA',
    'checkout_subdir': '/tools/VaRA',
}
REPOS['compiler-rt'] = {
    'default_branch': 'release_60',
    'checkout_dir': CHECKOUT_BASE_DIR + '/projects/compiler-rt',
}
REPOS['clang-tools-extra'] = {
    'default_branch': 'release_60',
    'checkout_dir': CHECKOUT_BASE_DIR + '/tools/clang/tools/extra',
}

################################################################################

CODEBASE = make_git_cb(REPOS)
FORCE_CODEBASE = make_force_cb(REPOS)

P = util.Property

ACCEPTED_BUILDERS = slaves.get_hostlist(slaves.infosun, predicate=lambda host: host["host"] in {'ligeti', 'debussy'})

def trigger_branch_match(branch):
    pattern = re.compile(TRIGGER_BRANCH_REGEX)
    return pattern.match(branch)

@util.renderer
@defer.inlineCallbacks
def get_vara_feature_opt_results(props):
    all_logs = []
    master = props.master
    buildsteps = yield props.master.data.get(('builders', props.getProperty('buildername'),
                                              'builds', props.getProperty('buildnumber'), 'steps'))
    pr_comment_steps = {
        # 'step_name': True, if detailled cmd output is required (in case of failure)
        'cmake': True,
        'build VaRA': True,
        'run VaRA regression tests': True,
        'run Clang-Tidy': True,
        'run ClangFormat': True,
    }
    all_logs.append('### opt build result')
    for step in buildsteps:
        if step['name'] in pr_comment_steps:
            logs = yield master.data.get(("steps", step['stepid'], 'logs'))
            if logs is not None:
                log = logs[-1]
                if util.Results[step['results']] == 'success':
                    all_logs.append('* :heavy_check_mark: Step : {0} Result : {1}'.format(
                        step['name'], util.Results[step['results']]))
                else:
                    all_logs.append('### :boom: Step : {0} Result : {1}'.format(
                        step['name'], util.Results[step['results']]))
                    # full cmd output
                    if pr_comment_steps[step['name']]:
                        all_logs.append('<details><summary>Click to show details</summary>\n')
                        all_logs.append('```')
                        log['stepname'] = step['name']
                        log['content'] = yield master.data.get(("logs", log['logid'], 'contents'))
                        step_logs = log['content']['content'].split('\n')
                        for i, sl in enumerate(step_logs):
                            all_logs.append(sl[1:])
                        all_logs.append('```\n')
                        all_logs.append('</details>\n')

    defer.returnValue('\n'.join(all_logs))

class GenerateMakeCleanCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        command = yield self.makeRemoteShellCommand()
        yield self.runCommand(command)

        force_build_clean = None
        if self.hasProperty('options'):
            options = self.getProperty('options')
            force_build_clean = options['force_build_clean']

        if force_build_clean:
            self.build.addStepsAfterCurrentStep(get_uchroot_workaround_steps())
            self.build.addStepsAfterCurrentStep([
                define('FORCE_BUILD_CLEAN', 'true'),
                ucompile('ninja', 'clean', name='clean build dir',
                         workdir=UCHROOT_BUILD_DIR, haltOnFailure=True, warnOnWarnings=True)
            ])
        else:
            self.build.addStepsAfterCurrentStep([define('FORCE_BUILD_CLEAN', 'false')])

        defer.returnValue(command.results())

class GenerateGitCloneCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        command = yield self.makeRemoteShellCommand()
        yield self.runCommand(command)

        force_complete_rebuild = None
        if self.hasProperty('options'):
            options = self.getProperty('options')
            force_complete_rebuild = options['force_complete_rebuild']

        buildsteps = []

        for repo in REPOS:
            buildsteps.append(define(str(repo).upper() +'_ROOT', ip(REPOS[repo]['checkout_dir'])))

        if force_complete_rebuild:
            buildsteps.append(define('FORCE_COMPLETE_REBUILD', 'true'))
            buildsteps.append(steps.ShellCommand(name='Delete old build directory',
                                                 command=['rm', '-rf', 'build'],
                                                 workdir=ip(CHECKOUT_BASE_DIR)))

            for repo in REPOS:
                if 'repository_clone_url' in codebases[repo].keys():
                    url = codebases[repo]['repository_clone_url']
                else:
                    url = codebases[repo]['repository']
                branch = REPOS[repo]['default_branch']

                buildsteps.append(steps.Git(repourl=url, branch=branch, codebase=repo,
                                            name="checkout: {0}".format(url),
                                            description="checkout: {0}@{1}".format(url, branch),
                                            timeout=1200, progress=True, submodules=True,
                                            workdir=P(str(repo).upper()+'_ROOT'),
                                            mode='full', method='clobber'))
        else:
            self.build.addStepsAfterCurrentStep([define('FORCE_COMPLETE_REBUILD', 'false')])
            for repo in REPOS:
                if 'repository_clone_url' in codebases[repo].keys():
                    url = codebases[repo]['repository_clone_url']
                else:
                    url = codebases[repo]['repository']
                branch = REPOS[repo]['default_branch']

                buildsteps.append(steps.Git(repourl=url, branch=branch, codebase=repo,
                                            name="checkout: {0}".format(url),
                                            description="checkout: {0}@{1}".format(url, branch),
                                            timeout=1200, progress=True, submodules=True,
                                            workdir=P(str(repo).upper()+'_ROOT')))

        buildsteps.append(steps.ShellCommand(name='Create build directory',
                                             command=['mkdir', '-p', 'build'],
                                             workdir=ip(CHECKOUT_BASE_DIR), hideStepIf=True))

        self.build.addStepsAfterCurrentStep(buildsteps)

        defer.returnValue(command.results())


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
        command = yield self.makeRemoteShellCommand()
        yield self.runCommand(command)

        result = command.results()
        if result == util.SUCCESS:
            checkout_feature_br = self.get_feature_branch(self.observer.getStdout())

            if checkout_feature_br:
                self.build.addStepsAfterCurrentStep([
                    define('FEATURE', checkout_feature_br),
                    define('branch', checkout_feature_br),
                    steps.ShellCommand(
                        name='Checking out feature branch \"' + str(checkout_feature_br) + '\"',
                        command=['./tools/VaRA/utils/buildbot/bb-checkout-branches.sh',
                                 checkout_feature_br],
                        workdir=ip(CHECKOUT_BASE_DIR)),
                ])
            else:
                force_feature = None
                if self.hasProperty('options'):
                    options = self.getProperty('options')
                    force_feature = options['force_feature']

                self.build.addStepsAfterCurrentStep([
                    define('FEATURE', force_feature),
                    define('branch', ''),
                    steps.ShellCommand(
                        name=ip('Checking out feature branch \"%(prop:FEATURE)s\"'),
                        command=['./tools/VaRA/utils/buildbot/bb-checkout-branches.sh',
                                 force_feature],
                        workdir=ip(CHECKOUT_BASE_DIR)),
                ])

        defer.returnValue(result)


class GenerateBuildStepCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        command = yield self.makeRemoteShellCommand()
        yield self.runCommand(command)

        result = command.results()
        if result == util.SUCCESS:
            vara_files = self.observer.getStdout().strip().splitlines()
            match_lines = []
            for line in vara_files:
                match_lines.append('.*' + re.escape(line) + '.*warning[: ].*')
            # join all alternatives together and create pattern object
            pattern = re.compile('|'.join(match_lines))

            buildsteps = []
            for step in get_uchroot_workaround_steps():
                buildsteps.append(step)
            buildsteps.append(ucompile('ninja', haltOnFailure=True, warnOnWarnings=True,
                                       name='build VaRA',
                                       warningPattern=pattern,
                                       workdir=UCHROOT_BUILD_DIR))

            self.build.addStepsAfterCurrentStep(buildsteps)

            defer.returnValue(command.results())


class GenerateMergecheckCommand(buildstep.ShellMixin, steps.BuildStep):

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        steps.BuildStep.__init__(self, **kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)

    @defer.inlineCallbacks
    def run(self):
        command = yield self.makeRemoteShellCommand()
        yield self.runCommand(command)

        result = command.results()
        if result == util.SUCCESS:
            mergecheck_repo = self.getProperty('mergecheck_repo')
            current_branch = self.observer.getStdout().strip()
            default_branch = REPOS[mergecheck_repo]['default_branch']
            repo_subdir = REPOS[mergecheck_repo]['checkout_subdir']

            if default_branch == current_branch.replace('refs/heads/', ''):
                # This repository has no feature branch, so nothing has to be merged.
                defer.returnValue(result)

            self.build.addStepsAfterCurrentStep([
                steps.Compile(
                    command=['/scratch/pjtest/mergecheck/build/bin/mergecheck', 'rebase',
                             '--repo', '.' + repo_subdir,
                             '--upstream', 'refs/remotes/origin/' + default_branch,
                             '--branch', current_branch,
                             '-v', '--print-conflicts',
                            ],
                    workdir=ip(CHECKOUT_BASE_DIR),
                    name='Mergecheck \"' + mergecheck_repo + '\"',
                    warnOnWarnings=False, warningPattern=r'^CONFLICT \((content|add\/add)\).*'),
            ])

            defer.returnValue(result)


def get_uchroot_workaround_steps():
    workaround_steps = []
    workaround_steps.append(ucompile('true', name='uchroot /proc bug workaround', hideStepIf=True,
                                     haltOnFailure=False, flunkOnWarnings=False,
                                     flunkOnFailure=False, warnOnWarnings=False,
                                     warnOnFailure=False))
    workaround_steps.append(cmd("sleep 1", hideStepIf=True))
    return workaround_steps

# yapf: disable
def configure(c):
    f = util.BuildFactory()

    # TODO Check if this can be done without a dummy command
    #f.addStep(GenerateGitCloneCommand())
    f.addStep(GenerateGitCloneCommand(name="Dummy_1", command=['true'],
                                      haltOnFailure=True, hideStepIf=True))

    f.addStep(define('UCHROOT_SRC_ROOT', UCHROOT_SRC_ROOT))
    f.addStep(define('UCHROOT_BUILD_DIR', UCHROOT_BUILD_DIR))

    f.addStep(GenerateGitCheckoutCommand(
        name="Get branch names",
        command=['./tools/VaRA/utils/buildbot/bb-get-branches.sh'], workdir=ip(CHECKOUT_BASE_DIR),
        haltOnFailure=True, hideStepIf=True))

    # CMake
    for step in get_uchroot_workaround_steps():
        f.addStep(step)
    f.addStep(ucompile('../tools/VaRA/utils/vara/builds/' + BUILD_SCRIPT,
                       env={'PATH': '/opt/cmake/bin:/usr/local/bin:/usr/bin:/bin'},
                       name='cmake',
                       description=BUILD_SCRIPT,
                       workdir=UCHROOT_SRC_ROOT + '/build'))

    f.addStep(GenerateMakeCleanCommand(name="Dummy_2", command=['true'],
                                       haltOnFailure=True, hideStepIf=True))

    # use mergecheck tool to make sure the 'upstream' remote is present
    for repo in ['vara-llvm', 'vara-clang']:
        f.addStep(steps.Compile(
            command=['/scratch/pjtest/mergecheck/build/bin/mergecheck', 'rebase',
                     '--repo', '.' + REPOS[repo]['checkout_subdir'],
                     '--remote-url', REPOS[repo]['upstream_remote_url'],
                     '--remote-name', 'upstream',
                     '--upstream', 'refs/remotes/upstream/master',
                     '--branch', 'refs/remotes/upstream/master',
                     '-v'],
            workdir=ip(CHECKOUT_BASE_DIR),
            name='Add upstream remote to repository.', hideStepIf=True))

    # Prepare project file list to filter out compiler warnings
    f.addStep(cmd("../../tools/VaRA/utils/vara/getVaraSourceFiles.sh",
                  "--all", "--include-existing",
                  "--relative-to", ip(BUILD_DIR),
                  "--output", "buildbot-source-file-list.txt",
                  workdir=ip(BUILD_DIR), hideStepIf=True))

    # Compile Step
    f.addStep(GenerateBuildStepCommand(name="Dummy_3",
                                       command=['cat', 'buildbot-source-file-list.txt'],
                                       workdir=ip(BUILD_DIR),
                                       haltOnFailure=True, hideStepIf=True))

    # Regression Test step
    for step in get_uchroot_workaround_steps():
        f.addStep(step)
    f.addStep(ucompile('ninja', 'check-vara', name='run VaRA regression tests',
                       workdir=UCHROOT_BUILD_DIR,
                       haltOnFailure=False, warnOnWarnings=True))

    # Clang-Tidy
    for step in get_uchroot_workaround_steps():
        f.addStep(step)
    f.addStep(ucompile('python3', 'tidy-vara.py', '-p', UCHROOT_BUILD_DIR, '-j', '8', '--gcc',
                       workdir='vara-llvm/tools/VaRA/test/', name='run Clang-Tidy',
                       haltOnFailure=False, warnOnWarnings=True,
                       env={'PATH': [UCHROOT_BUILD_DIR + "/bin", "${PATH}"]}, timeout=3600))

    # ClangFormat
    for step in get_uchroot_workaround_steps():
        f.addStep(step)
    f.addStep(ucompile('bash', 'bb-clang-format.sh', '--all', '--line-numbers',
                       workdir='vara-llvm/tools/VaRA/utils/buildbot',
                       name='run ClangFormat', haltOnFailure=False, warnOnWarnings=True,
                       env={'PATH': [UCHROOT_BUILD_DIR + "/bin", "${PATH}"]}))

    # Mergecheck
    for repo in ['vara-llvm', 'vara-clang', 'vara']:
        f.addStep(define('mergecheck_repo', repo))
        f.addStep(GenerateMergecheckCommand(name="Dummy_4", command=['git', 'symbolic-ref', 'HEAD'],
                                            workdir=ip(REPOS[repo]['checkout_dir']),
                                            haltOnFailure=True, hideStepIf=True))

    c['builders'].append(builder(PROJECT_NAME, None, ACCEPTED_BUILDERS, tags=['vara'],
                                 factory=f))

def schedule(c):
    force_sched = s_force(
        name="force-build-" + PROJECT_NAME,
        cb=FORCE_CODEBASE,
        builders=[PROJECT_NAME],
        properties=[
            util.NestedParameter(name="options", label="Build Options", layout="vertical", fields=[
                util.StringParameter(name="force_feature", label="feature-branch to build:",
                                     default="", size=80),
                util.BooleanParameter(name="force_build_clean", label="force a make clean",
                                      default=False),
                util.BooleanParameter(name="force_complete_rebuild",
                                      label="force complete rebuild and fresh git clone",
                                      default=False),
            ])
        ]
    )

    c['schedulers'].extend([
        s_abranch(PROJECT_NAME + '-sched', CODEBASE, [PROJECT_NAME],
                  change_filter=util.ChangeFilter(branch_fn=trigger_branch_match),
                  treeStableTimer=5 * 60),
        force_sched,
        s_trigger('trigger-' + PROJECT_NAME, CODEBASE, [PROJECT_NAME]),
    ])
# yapf: enable


register(sys.modules[__name__])
