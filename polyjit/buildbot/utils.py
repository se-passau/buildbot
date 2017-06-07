from buildbot.plugins import *
from buildbot.steps.trigger import Trigger
from buildbot.steps import master

import os

P = util.Property


def builder(name, builddir, slaves, **kwargs):
    if builddir:
        return util.BuilderConfig(name=name, workerbuilddir=builddir,
                                  workernames=slaves, **kwargs)
    else:
        return util.BuilderConfig(name=name, workernames=slaves, **kwargs)


def define(prop, value, **kwargs):
    """Hide SetProperty steps from waterfall by default."""
    return master.SetProperty(property=prop, value=value, hideStepIf=True,
                              **kwargs)


def cmddef(**kwargs):
    env = {
        "LC_ALL": "C",
    }
    env.update(kwargs.pop('env', {}))
    return steps.SetPropertyFromCommand(warnOnFailure=True,
                                        warnOnWarnings=True,
                                        env=env,
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
    return steps.FileUpload(workersrc=src, masterdest=tgt, **kwargs)


def download_file(src, tgt, **kwargs):
    return steps.FileDownload(mastersrc=src, workerdest=tgt, **kwargs)


def rmdir(target, **kwargs):
    return steps.RemoveDirectory(dir=target, **kwargs)


def mkdir(target, **kwargs):
    return steps.MakeDirectory(dir=target, **kwargs)


def cmd(*args, **kwargs):
    command = args
    if (len(args) == 1) and isinstance(args[0], str):
        command = str(args[0])

    if "haltOnFailure" not in kwargs:
        kwargs["haltOnFailure"] = True
    if "logEnviron" not in kwargs:
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
               '-M', ip("%(prop:builddir)s:/mnt"),
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

    return compile(P("uchroot_binary"), "-C", "-E", "-A", "-u", uid, "-g", gid,
        '-r', P("uchroot_image_path"), '-w', os.path.join("/mnt", workdir),
        '-M', ip("%(prop:builddir)s:/mnt"),
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
    if "haltOnFailure" not in kwargs:
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
    waitForFinish = kwargs.pop("waitForFinish", True)
    return Trigger(waitForFinish=waitForFinish, **kwargs)


def extract_rc(propertyname):
    name = propertyname

    def extract_rc_wrapper(rc, stdout, stderr):
        return {name: rc == 0}
    return extract_rc_wrapper


def property_is_true(propname):
    prop = propname

    def property_is_true_wrapper(step):
        return bool(step.getProperty(prop))
    return property_is_true_wrapper


def property_is_false(propname):
    prop = propname

    def property_is_false_wrapper(step):
        return not bool(step.getProperty(prop))
    return property_is_false_wrapper


def hash_download_from_master(mastersrc, slavedst, tag):
    steps = [
        cmddef(command="stat {0}".format(slavedst),
               extract_fn=extract_rc('have_{0}'.format(tag))),
        download_file(src="{0}.md5".format(mastersrc),
                      tgt="{0}.md5".format(slavedst),
                      doStepIf=property_is_true("have_{0}".format(tag))),
        cmddef(command="md5sum -c {0}.md5".format(slavedst),
               extract_fn=extract_rc('have_newest_{0}'.format(tag)),
               doStepIf=property_is_true("have_{0}".format(tag))),
        download_file(src=mastersrc, tgt=slavedst,
                      doStepIf=property_is_false(
                          "have_newest_{0}".format(tag))),
    ]
    return steps


def hash_upload_to_master(filename, slavesrc, masterdst, url):
    steps = [
        cmd("md5sum {0} > {0}.md5".format(filename), workdir=P("builddir")),
        upload_file(src=slavesrc,
                    tgt=masterdst,
                    url="{0}/{1}".format(url, filename),
                    description="Uploading {0}".format(filename),
                    descriptionDone="Uploaded {0}".format(filename)),
        upload_file(src="{0}.md5".format(slavesrc),
                    tgt="{0}.md5".format(masterdst),
                    url="{0}/{1}.md5".format(url, filename),
                    description="Uploading {0}.md5".format(filename),
                    descriptionDone="Uploaded {0}.md5".format(filename))
    ]
    return steps


def clean_unpack(filename, tag):
    return [
        rmdir("build/{0}".format(tag),
              doStepIf=property_is_false("have_newest_{0}".format(tag))),
        mkdir("build/{0}".format(tag)),
        cmd("tar", "xzf", filename, "-C", tag,
            doStepIf=property_is_false("have_newest_{0}".format(tag)),
            description="Unpacking {0}".format(tag))
    ]


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
