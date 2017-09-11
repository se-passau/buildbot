import sys
from collections import OrderedDict

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, ucmd, ucompile, cmd,
                                    upload_file, ip, s_sbranch, s_abranch,
                                    s_nightly, s_force, s_trigger,
                                    hash_upload_to_master)
from polyjit.buildbot.repos import make_cb, make_new_cb, make_git_cb, make_force_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

################################################################################

project_name     = 'vara-features'
trigger_branches = 'f-*'
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
    'default_branch': 'master',
    'checkout_dir': checkout_base_dir + '/tools/clang/tools/extra',
}

################################################################################

codebase = make_git_cb(repos)
force_codebase = make_force_cb(repos)

P = util.Property

def can_build_llvm_debug(host):
    if 'can_build_llvm_debug' in host['properties']:
        return host['properties']['can_build_llvm_debug']
    return False

accepted_builders = slaves.get_hostlist(slaves.infosun, predicate=can_build_llvm_debug)


# yapf: disable
def configure(c):
    steps = []

    for repo in repos:
        steps.append(define(str(repo).upper() +'_ROOT', ip(repos[repo]['checkout_dir'])))

    for repo in repos:
        steps.append(git(repo, repos[repo]['default_branch'], codebases, workdir=P(str(repo).upper()+'_ROOT')))

    steps += [
        define('UCHROOT_SRC_ROOT', uchroot_src_root),
        ucmd('cmake', P('UCHROOT_SRC_ROOT'),
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
             description='cmake O3, Assertions, PIC, Shared'),
        ucompile('ninja', haltOnFailure=True, name='build VaRA'),
        ucompile('ninja', 'check-vara', haltOnFailure=True, name='run VaRA regression tests'),
        ucmd('python3', 'tidy-vara.py', haltOnFailure=False, workdir='tools/VaRA/test', name='run Clang-Tidy'),
    ]

    c['builders'].append(builder('build-' + project_name, None, accepted_builders,
                         tags=['vara'], factory=util.BuildFactory(steps)))

def schedule(c):
    c['schedulers'].extend([
        s_abranch('build-' + project_name + '-sched', codebase, ['build-' + project_name],
                  change_filter=filter.ChangeFilter(branch_re=trigger_branches),
                  treeStableTimer=5 * 60),
        s_force('force-build-' + project_name, force_codebase, ['build-' + project_name]),
        s_trigger('trigger-build-' + project_name, codebase, ['build-' + project_name]),
        s_nightly('nightly-sched-build-' + project_name, codebase,
                  ['build-vara'],
                  hour=22, minute=0)
    ])
# yapf: enable


register(sys.modules[__name__])
