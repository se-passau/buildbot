from buildbot.plugins import *

infosun = {
    "polyjit-ci": {
        "host": "polyjit-ci",
        "password": None,
        "properties": {
            "uchroot_image_path": "/data/polyjit/xenial-image/",
            "uchroot_binary": "/data/polyjit/erlent/build/uchroot",
            "can_build_llvm_debug": False
        },
    },
    "local": {
        "host": "local",
        "password": None,
        "properties": {
            "uchroot_image_path": "/dock/buildbot/xenial-image/",
            "uchroot_binary": "/dock/buildbot/erlent/build/uchroot",
            "can_build_llvm_debug": True
        },
    },
    "ivy-vm": {
        "host": "ivy-vm",
        "password": None,
        "properties": {
            "uchroot_image_path": "/buildbot/xenial-image/",
            "uchroot_binary": "/buildbot/erlent/build/uchroot",
            "can_build_llvm_debug": True
        },
    },
    "debussy": {
        "host": "debussy",
        "password": None,
        "properties": {
            "uchroot_image_path": "/scratch/pjtest/xenial-image/",
            "uchroot_binary": "/scratch/pjtest/erlent/build/uchroot",
            "has_munged": True,
            "testinputs": "/home/simbuerg/src/polyjit/pprof-test-data"
        },
        "can_build_llvm_debug": True
    }
}

def get_hostlist(slave_dict, predicate = None):
    if not predicate:
        predicate = lambda x : True
    hosts = []
    for k in slave_dict:
        if predicate(slave_dict[k]):
            hosts.append(slave_dict[k]["host"])
    return hosts


def configure(c):
    for k in infosun:
        slave = infosun[k]
        props = {}
        if "properties" in slave:
            props = slave["properties"]
        c['slaves'].append(buildslave.BuildSlave(slave["host"], slave[
            "password"], properties = props))
