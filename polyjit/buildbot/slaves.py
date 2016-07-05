from buildbot.plugins import *

infosun = {
    "polyjit-ci": {
        "host": "polyjit-ci",
        "password": None
    },
    "debussy-1": {
        "host": "debussy-1",
        "password": None
    },
    "local": {
        "host": "local",
        "password": None
    }
}


def get_hostlist(slave_dict):
    hosts = []
    for k in slave_dict:
        hosts.append(infosun[k]["host"])
    return hosts


def configure(c):
    for k in infosun:
        slave = infosun[k]
        c['slaves'].append(buildslave.BuildSlave(slave["host"], slave[
            "password"]))
