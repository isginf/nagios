#!/usr/bin/python
#
# Run a nagios check parallel on x hosts
#
#
# Copyright 2013 ETH Zurich, ISGINF, Bastian Ballmann
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
import commands
from multiprocessing import Process, Queue


###[ Configuration ]###

hosts = [
          "host1",
          "host2",
          "host3"
        ]

nr_of_threads = 20
plugin_cmd="/usr/lib64/nagios/plugins/check_ping"

OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3


###[ Subroutines ]###

def check_plugin(work_queue, result_queue):
    """
    Grab a host, run the check and return the result
    """
    while work_queue.qsize():
        host = work_queue.get()
        result = commands.getoutput(plugin_cmd + " -H " + host)
        result_queue.put([host, result])

def parallel_work(jobs, nr_of_threads):
    """
    Setup queues, start the processes and wait until the job is done
    """
    work_queue = Queue()
    result_queue = Queue()
    result = {}

    for job in jobs:
        work_queue.put(job)

    if nr_of_threads > len(jobs):
        nr_of_threads = len(jobs)

    for i in range(nr_of_threads):
        worker = Process(target=check_plugin, args=(work_queue,result_queue))
        worker.start()

    while len(result.keys()) < len(jobs):
        data = result_queue.get()

        if " | " in data[1]:
            (status, output) = data[1].split(" | ")
            status = status.replace("IPMI Status: ","")
        else:
            status = "UNKNOWN"
            output = data[1]

        result[data[0]] = {"status": status, "output": output}
        #print "Host " + data[0] + " " + status

    return result


###[ MAIN PART ]###

all_results = parallel_work(hosts, nr_of_threads)
exit_code = UNKNOWN
output = ""
hosts_unknown = []
hosts_critical = []

for (host, result) in all_results.items():
    if result["status"] == "UNKNOWN":
        hosts_unknown.append(host)
    elif result["status"] != "OK":
        hosts_critical.append(host)

if len(hosts_critical) > 0:
    exit_code = CRITICAL
    output += str(len(hosts_critical)) + " Hosts critical " + ", ".join(sorted(hosts_critical)) + "<br>"
elif len(hosts_unknown) > 0:
    exit_code = UNKNOWN
    output += str(len(hosts_unknown)) + " Hosts down " + ", ".join(sorted(hosts_unknown)) + "<br>"
else:
    exit_code = OK
    output = ":)"

print output
sys.exit(exit_code)
