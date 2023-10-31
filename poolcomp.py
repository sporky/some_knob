#!/usr/bin/env python3

from bigrest.bigip import BIGIP
from time import sleep
import argparse
import sys
import json
from collections import Counter


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("host_one", help="BIG-IP IP/FQDN cluster member 1")
    parser.add_argument("host_two", help="BIG-IP IP/FQDN cluster member 2")
    parser.add_argument("user", help="BIG-IP Username")

    return parser.parse_args()


def get_credentials_from_vault_maybe(user):
    # insert whatever you do to lookup passwords here
    # please don't do this:
    pwdb = {"admin": "boogers"}
    return pwdb.get(user, "somepassword")


def instantiate_bigip(host, user):
    pw = get_credentials_from_vault_maybe(user)
    try:
        obj = BIGIP(host, user, pw, session_verify=False)
    except Exception as e:
        print(f"Failed to connect to {args.host} due to {type(e).__name__}:\n")
        print(f"{e}")
        sys.exit()
    return obj


def deploy_script():
    # slurp the file - assumes it's in same directory
    with open("poolstatus.tcl") as f:
        tmsh_script = f.read()
    try:
        cli_script = {"name": "poolstatus.tcl", "apiAnonymous": tmsh_script}
        b.create("/mgmt/tm/cli/script", cli_script)
    except Exception as e:
        print(f"{e}")
        sys.exit()


def run_poolstatus(b):
    try:
        data = {"command": "run", "name": "/Common/poolstatus.tcl", "utilCmdArgs": ""}
        b.command("/mgmt/tm/cli/script", data)
    except Exception as e:
        print(f"{e}")


def poolstatus_response_fixup(raw):
    results = []
    for p in raw:
        p.update(device=b.device)
        results.append(p)
    return results


def download_poolstatus_data(b):
    filename = "poolstatus.json"
    try:
        b.download(
            "/mgmt/cm/autodeploy/software-image-downloads",
            filename,
        )
        fh = open(filename)
        raw = json.load(fh)
        fh.close()
        return raw

    except Exception as e:
        print(f"{e}")


def delete_tmp_files(b):
    filename = "poolstatus.json"
    try:
        data = {}
        data["command"] = "run"
        data["utilCmdArgs"] = f"/shared/images/{filename}"
        result = b.command("/mgmt/tm/util/unix-rm", data)
        if result != "":
            print(f"cleanup results: {result}")
    except Exception as e:
        print(f"{e}")


def counter_by_key(A, B, key):
    ac = Counter([d[key] for d in A])
    bc = Counter([d[key] for d in B])

    print(f"{key}\n  A {ac}\n  B {bc}\n")


def compare_results(results):
    pA = results.pop(0)
    pB = results.pop(0)
    # take out the trash
    pA.pop()
    pB.pop()

    # quick check; counts of each pool status and pool member monitor status should be sameish
    keys_to_compare = ["pool_avail", "monitor_status"]
    for k in keys_to_compare:
        counter_by_key(pA, pB, k)

    # naive member by member check..
    # create dicts for easier lookups
    pdA = {f"{p['pool']}/{p['member']}": p for p in pA}
    pdB = {f"{p['pool']}/{p['member']}": p for p in pB}

    print(f"monitor status differences")
    for k, v in pdA.items():
        a_mem = v
        b_mem = pdB[k]

        if a_mem["monitor_status"] != b_mem["monitor_status"]:
            print(f"{k} - A: {a_mem['monitor_status']}  B: {b_mem['monitor_status']}")


if __name__ == "__main__":
    args = build_parser()

    bipa = instantiate_bigip(args.host_one, args.user)
    bipb = instantiate_bigip(args.host_two, args.user)

    results = []

    for b in [bipa, bipb]:
        if not b.exist("/mgmt/tm/cli/script/poolstatus.tcl"):
            deploy_script()

        run_poolstatus(b)
        results.append(download_poolstatus_data(b))
        delete_tmp_files(b)

    compare_results(results)
