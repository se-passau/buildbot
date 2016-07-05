from buildbot.plugins import *
import os

infosun = {
    "polyjit-ci": {
        "host": "polyjit-ci",
        "password": None
    },
    "debussy-1": {
        "host": "debussy-1",
        "password": None
    }
}


def get_hostlist(slave_dict):
    hosts = []
    for k in infosun:
        hosts.append(infosun[k]["host"])
    return hosts


def configure(c):
    for k in infosun:
        slave = infosun[k]
        c['slaves'].append(buildslave.BuildSlave(slave["host"], slave[
            "password"]))
