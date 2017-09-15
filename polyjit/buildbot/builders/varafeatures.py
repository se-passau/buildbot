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
from buildbot.plugins import util, steps
from buildbot.changes import filter
from buildbot.process import buildstep, logobserver
from twisted.internet import defer

################################################################################

project_name     = 'vara-features'
trigger_branch_regex = "^(f-\S+)$"
uchroot_src_root = '/mnt/vara-llvm-features'
checkout_base_dir = '%(prop:builddir)s/vara-llvm-features'

repos = OrderedDict()

repos['vara-llvm'] = {
    'default_branch': 'vara-llvm-50-dev',
    'checkout_dir': checkout_base_dir,
}
repos['vara-clang'] = {
    'default_branch': 'vara-clang-50-dev',
    'checkout_dir': checkout_base_dir + '/tools/clang',
}
repos['vara'] = {
    'default_branch': 'vara-dev',
    'checkout_dir': checkout_base_dir + '/tools/VaRA',
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

@util.renderer
def builderNames(props):
    builders = set()
    builders.add('build-vara-features')
    return list(builders)

class GenerateStagesCommand(buildstep.ShellMixin, steps.BuildStep):

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
            feature_br = self.get_feature_branch(self.observer.getStdout())

            if feature_br:
                self.build.addStepsAfterCurrentStep([
                    define('FEATURE', feature_br),
                    steps.ShellCommand(name='Checking out feature branch \"' + str(feature_br) + '\"',
                        command=['./tools/VaRA/utils/buildbot/bb-checkout-branches.sh', feature_br],
                        workdir=ip(checkout_base_dir)),
                ])

        defer.returnValue(result)


# yapf: disable
def configure(c):
    f = util.BuildFactory()

    for repo in repos:
        f.addStep(define(str(repo).upper() +'_ROOT', ip(repos[repo]['checkout_dir'])))

    for repo in repos:
        f.addStep(git(repo, repos[repo]['default_branch'], codebases, workdir=P(str(repo).upper()+'_ROOT')))

    f.addStep(GenerateStagesCommand(
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

    f.addStep(ucompile('ninja', haltOnFailure=True, warnOnWarnings=True, name='build VaRA'))

    f.addStep(ucompile('ninja', 'check-vara', haltOnFailure=True, warnOnWarnings=True, name='run VaRA regression tests'))

    f.addStep(ucompile('python3', 'tidy-vara-gcc.py', '-p', '/mnt/build', haltOnFailure=False, warnOnWarnings=True, workdir='vara-llvm-features/tools/VaRA/test/', name='run Clang-Tidy', env={'PATH': ["/mnt/build/bin", "${PATH}"]}))

    c['builders'].append(builder('build-' + project_name, None, accepted_builders, tags=['vara'], factory=f))

def schedule(c):
    c['schedulers'].extend([
        s_abranch('build-' + project_name + '-sched', codebase, builderNames,
                  change_filter=util.ChangeFilter(branch_fn=trigger_branch_match),
                  treeStableTimer=5 * 60),
        # TODO: Fix force build: Add ability to choose arbitraty feature branches;
        # Currently, this is not possible, because the branch list cannot be changed dynamically
        #s_force('force-build-' + project_name, force_codebase, ['build-' + project_name]),
        s_trigger('trigger-build-' + project_name, codebase, ['build-' + project_name]),
        # TODO: Fix nightly scheduler (currently not working)
        #s_nightly('nightly-sched-build-' + project_name, codebase,
        #          ['build-' + project_name],
        #          hour=22, minute=0)
    ])
# yapf: enable


register(sys.modules[__name__])
