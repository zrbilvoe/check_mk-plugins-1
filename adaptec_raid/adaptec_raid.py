#!/usr/bin/env python
# check-aacraid.py modified version of check from http://exchange.nagios.org/
#
# Additions:
#  - switch between check_mk and nrpe modes
#  - customize the command (so it works on Linux or Windows)

# Original by: Oliver Hookins, Paul De Audney and Barney Desmond.
# This version by Hereward Cooper <coops@fawk.eu>

# Change mode between 'check_mk' and 'nrpe' to reflect monitoring setup
mode = "check_mk"
#mode = "nrpe"

#command = "/usr/bin/sudo /usr/StorMan/arcconf"
command = '\"E:\Adaptec\Adaptec Storage Manager\\arcconf\"'

import sys, os, re, string

c_status_re = re.compile('^\s*Controller Status\s*:\s*(.*)$')
l_status_re = re.compile('^\s*Status of logical device\s*:\s*(.*)$')
l_device_re = re.compile('^Logical device number ([0-9]+).*$')
c_defunct_re = re.compile('^\s*Defunct disk drive count\s:\s*([0-9]+).*$')
c_degraded_re = re.compile('^\s*Logical devices/Failed/Degraded\s*:\s*([0-9]+)/([0-9]+)/([0-9]+).*$')
b_status_re = re.compile('^\s*Status\s*:\s*(.*)$')
b_temp_re = re.compile('^\s*Over temperature\s*:\s*(.*)$')
b_capacity_re = re.compile('\s*Capacity remaining\s*:\s*([0-9]+)\s*percent.*$')
b_time_re = re.compile('\s*Time remaining \(at current draw\)\s*:\s*([0-9]+) days, ([0-9]+) hours, ([0-9]+) minutes.*$')

cstatus = lstatus = ldevice = cdefunct = cdegraded = bstatus = btemp = bcapacity = btime = ""
lnum = ""
check_status = 0
result = ""

# Get logical drive status
for line in os.popen4(command + " GETCONFIG 1 LD")[1].readlines():
        # Match the regexs
        ldevice = l_device_re.match(line)
        if ldevice:
                lnum = ldevice.group(1)
                continue

        lstatus = l_status_re.match(line)
        if lstatus:
                if lstatus.group(1) != "Optimal":
                        check_status = 2
                result += "Logical Device " + lnum + " " + lstatus.group(1) + ","

# Get general card status
for line in os.popen4(command + " GETCONFIG 1 AD")[1].readlines():
        # Match the regexs
        cstatus = c_status_re.match(line)
        if cstatus:
                if cstatus.group(1) != "Optimal":
                        check_status = 2
                result += "Controller " + cstatus.group(1) + ","
                continue

        cdefunct = c_defunct_re.match(line)
        if cdefunct:
                if int(cdefunct.group(1)) > 0:
                        check_status = 2
                        result += "Defunct drives " + cdefunct_group(1) + ","
                continue

        cdegraded = c_degraded_re.match(line)
        if cdegraded:
                if int(cdegraded.group(2)) > 0:
                        check_status = 2
                        result += "Failed drives " + cdegraded.group(2) + ","
                if int(cdegraded.group(3)) > 0:
                        check_status = 2
                        result += "Degraded drives " + cdegraded.group(3) + ","
                continue

        bstatus = b_status_re.match(line)
        if bstatus:
                if bstatus.group(1) == "Not Installed":
                        continue

                if bstatus.group(1) == "Charging":
                        if check_status < 2:
                                check_status = 1
                elif bstatus.group(1) != "Optimal":
                        check_status = 2
                result += "Battery Status " + bstatus.group(1) + ","
                continue

        btemp = b_temp_re.match(line)
        if btemp:
                if btemp.group(1) != "No":
                        check_status = 2
                        result += "Battery Overtemp " + btemp.group(1) + ","
                continue

        bcapacity = b_capacity_re.match(line)
        if bcapacity:
                result += "Battery Capacity " + bcapacity.group(1) + "%,"
                if bcapacity.group(1) < 50:
                        if check_status < 2:
                                check_status = 1
                if bcapacity.group(1) < 25:
                        check_status = 2
                continue

        btime = b_time_re.match(line)
        if btime:
                timemins = int(btime.group(1)) * 1440 + int(btime.group(2)) * 60 + int(btime.group(3))
                if timemins < 1440:
                        if check_status < 2:
                                check_status = 1
                if timemins < 720:
                        check_status = 2
                result += "Battery Time "
                if timemins < 60:
                        result += str(timemins) + "mins,"
                else:
                        result += str(timemins/60) + "hours,"

if result == "":
        result = "No output from arcconf!"
        check_status = 3

# strip the trailing "," from the result string.
result = result.rstrip(",")

if mode == "check_mk":
        print check_status, "Adaptec_RAID -", result
elif mode == "nrpe":
        print result

# Delete log once we've finished
try:
        cwd = os.getcwd()
        fullpath = os.path.join(cwd,'UcliEvt.log')
        os.unlink(fullpath)
except:
        pass

if mode == "nrpe":
        sys.exit(check_status)
