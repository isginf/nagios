#!/usr/bin/python3
#
# Run a nagios / icinga check in parallel on x hosts and generate one result
#
#
# Copyright 2017 ETH Zurich, ISGINF, Bastian Ballmann
# E-Mail: bastian.ballmann@inf.ethz.ch
# Web: http://www.isg.inf.ethz.ch
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License.
# If not, see <http://www.gnu.org/licenses/>.


###[ Imporing modules ]###

import sys
import subprocess
import argparse
from signal import signal, SIGINT, SIGKILL
from multiprocessing import Process, Queue


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-H", "--hosts", help="Comma separated list of hosts", required=True)
parser.add_argument("-p", "--plugin", help="Full path to nagios plugin", default="/usr/lib64/nagios/plugins/check_ping")
parser.add_argument("-a", "--plugin-args", help="Optional arguments for use with plugin")
parser.add_argument("-n", "--number-processes", help="Optional number of parallel processes", type=int, default=4)
args = parser.parse_args()

hosts = args.hosts.split(",")
processes = []

OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3


#
# SIGNAL HANDLERS
#

def clean_shutdown(signal, frame):
    for process in processes:
        process.terminate()

    print("Got killed by SIGINT")
    sys.exit(UNKNOWN)

signal(SIGINT, clean_shutdown)


###[ Subroutines ]###

def check_plugin(work_queue, result_queue):
    """
    Grab a host, run the check and return the result
    """
    while not work_queue.empty():
        host = work_queue.get()
        cmd = args.plugin + " -H " + host

        if args.plugin_args and args.plugin_args != "''":
            cmd = cmd + " " + args.plugin_args

        result = subprocess.getoutput(cmd)
        result_queue.put([host, result])


def parallel_work(jobs, number_processes):
    """
    Setup queues, start the processes and wait until the job is done
    """
    work_queue = Queue()
    result_queue = Queue()
    result = {}

    for job in jobs:
        work_queue.put(job)

    if number_processes > len(jobs):
        number_processes = len(jobs)

    for i in range(number_processes):
        worker = Process(target=check_plugin, args=(work_queue,result_queue))
        processes.append(worker)
        worker.start()

    # wait until we got a result for all hosts
    while len(result.keys()) < len(hosts):
        data = result_queue.get()

        if " | " in data[1]:
            parsed = data[1].split(" | ")
        else:
            parsed = data[1].split(" - ")

        if len(parsed) > 1:
            result[data[0]] = {"status": parsed[0], "output": parsed[1]}
        else:
            result[data[0]] = {"status": parsed[0], "output": None}

    return result


###[ MAIN PART ]###

all_results = parallel_work(hosts, args.number_processes)
exit_code = UNKNOWN
output = ""
hosts_unknown = []
hosts_critical = []
hosts_warning = []

for (host, result) in all_results.items():
    if "CRITICAL" in result["status"]:
        hosts_critical.append(host)
    elif "WARNING" in result["status"]:
        hosts_warning.append(host)
    elif not "OK" in result["status"] and not "up and running" in result["status"]:
        hosts_unknown.append(host)

if len(hosts_critical) > 0:
    exit_code = CRITICAL
    output += str(len(hosts_critical)) + " Hosts status critical " + ", ".join(sorted(hosts_critical)) + "<br>"
elif len(hosts_warning) > 0:
    exit_code = WARNING
    output += str(len(hosts_warning)) + " Hosts status warning " + ", ".join(sorted(hosts_warning)) + "<br>"
elif len(hosts_unknown) > 0:
    exit_code = UNKNOWN
    output += str(len(hosts_unknown)) + " Hosts status unknown " + ", ".join(sorted(hosts_unknown)) + "<br>"
else:
    exit_code = OK
    output += ":)"

print(output)
sys.exit(exit_code)
