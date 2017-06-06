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
    "debussy": {
        "host": "debussy",
        "password": None,
        "properties": {
            "uchroot_image_path": "/local/hdd/pjtest/xenial-image/",
            "uchroot_binary": "/scratch/pjtest/erlent/build/uchroot",
            "testinputs": "/scratch/pjtest/pprof-test-data",
            "has_munged": True,
            "can_build_llvm_debug": True
        }
    },
    "ligeti": {
        "host": "ligeti",
        "password": None,
        "properties": {
            "uchroot_image_path": "/local/hdd/pjtest/xenial-image/",
            "uchroot_binary": "/scratch/pjtest/erlent/build/uchroot",
            "testinputs": "/scratch/pjtest/pprof-test-data",
            "has_munged": True,
            "can_build_llvm_debug": True
        }
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
