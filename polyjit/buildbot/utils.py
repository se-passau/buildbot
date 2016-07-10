from buildbot.plugins import *
from buildbot.steps.trigger import Trigger
from buildbot.steps import master, shell

import os

P = util.Property

def builder(name, workdir, slaves, **kwargs):
    if workdir:
        return util.BuilderConfig(name=name,
                                  slavebuilddir=workdir,
                                  slavenames=slaves,
                                  **kwargs)
    else:
        return util.BuilderConfig(name=name, slavenames=slaves, **kwargs)


def define(prop, value, **kwargs):
    """Hide SetProperty steps from waterfall by default."""
    return master.SetProperty(property=prop, value=value, hideStepIf=True,
                              **kwargs)


def cmddef(**kwargs):
    return steps.SetPropertyFromCommand(warnOnFailure=True,
                                        warnOnWarnings=True,
                                        **kwargs)


def ip(text):
    return util.Interpolate(text)


def git(name, branch, cb, **kwargs):
    repo = cb[name]['repository']

    return steps.Git(repourl=repo,
                     branch=branch,
                     name="checkout: {0}".format(repo),
                     description="checkout: {0}@{1}".format(repo, branch),
                     mode="incremental",
                     timeout=1200,
                     codebase=name,
                     progress=True,
                     **kwargs)

def compile(*args, **kwargs):
    return steps.Compile(command=args, logEnviron=False, **kwargs)


def upload_file(src, tgt, **kwargs):
    return steps.FileUpload(slavesrc=src, masterdest=tgt, **kwargs)


def download_file(src, tgt, **kwargs):
    return steps.FileDownload(mastersrc=src, slavedest=tgt, **kwargs)


def rmdir(target, **kwargs):
    return steps.RemoveDirectory(dir=target, **kwargs)

def mkdir(target, **kwargs):
    return steps.MakeDirectory(dir=target, **kwargs)

def cmd(*args, **kwargs):
    command = args
    if isinstance(args[0], str):
        command = str(args[0])

    if not "haltOnFailure" in kwargs:
        kwargs["haltOnFailure"] = True
    if not "logEnviron" in kwargs:
        kwargs["logEnviron"] = False
    return steps.ShellCommand(command=command, **kwargs)


def ucmd(*args, **kwargs):
    uid = kwargs.pop('uid', 0)
    gid = kwargs.pop('gid', 0)
    workdir = kwargs.pop('workdir', "build")
    env = {
        "LC_ALL": "C",
    }
    env.update(kwargs.pop('env', {}))

    return cmd(P("uchroot_binary"), "-C", "-E", "-A",
               "-u", uid, "-g", gid,
               '-r', P("uchroot_image_path"),
               '-w', os.path.join("/mnt", workdir),
               '-M', ip("%(prop:workdir)s:/mnt"),
               workdir=workdir,
               usePTY=True,
               env=env,
               *args, **kwargs)

def ucompile(*args, **kwargs):
    uid = kwargs.pop('uid', 0)
    gid = kwargs.pop('gid', 0)
    workdir = kwargs.pop('workdir', "build")
    env = {
        "LC_ALL": "C",
    }
    env.update(kwargs.pop('env', {}))

    return compile(P("uchroot_binary"), "-C", "-E", "-A",
               "-u", uid, "-g", gid,
               '-r', P("uchroot_image_path"),
               '-w', os.path.join("/mnt", workdir),
               '-M', ip("%(prop:workdir)s:/mnt"),
               workdir=workdir,
               usePTY=True,
               env=env,
               *args, **kwargs)


def test(*args, **kwargs):
    return steps.Test(command=args,
                      logEnviron=False,
                      flunkOnFailure=False,
                      warnOnFailure=True,
                      **kwargs)


def pylint(*args, **kwargs):
    return steps.PyLint(command=args, **kwargs)


def upload_dir(srcdir, tgtdir, **kwargs):
    return steps.DirectoryUpload(slavesrc=srcdir,
                                 masterdest=tgtdir,
                                 compress="bz2",
                                 **kwargs)


def master_cmd(command, **kwargs):
    if not "haltOnFailure" in kwargs:
        kwargs["haltOnFailure"] = True
    return steps.MasterShellCommand(command=command, **kwargs)


def s_force(name, cb, builders, **kwargs):
    return schedulers.ForceScheduler(name=name,
                                     codebases=cb,
                                     builderNames=builders,
                                     **kwargs)


def s_sbranch(name, cb, builders, **kwargs):
    return schedulers.SingleBranchScheduler(name=name,
                                            codebases=cb,
                                            builderNames=builders,
                                            **kwargs)


def s_trigger(name, cb, builders, **kwargs):
    return schedulers.Triggerable(name=name,
                                  codebases=cb,
                                  builderNames=builders,
                                  **kwargs)


def trigger(**kwargs):
    if not "waitForFinish" in kwargs:
        kwargs["waitForFinish"] = True

    return Trigger(**kwargs)


@util.renderer
def benchbuild_slurm(props):
    experiment = "empty"
    if props.hasProperty("experiment"):
        experiment = props.getProperty("experiment")

    cmd = ["benchbuild", "-v", "slurm", "-E", experiment]

    if props.hasProperty("group"):
        group = props.getProperty("group")
        if group:
            for g in group:
                cmd = cmd + ["-G", g]
    return cmd
