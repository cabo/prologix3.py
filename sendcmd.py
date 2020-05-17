#!/usr/bin/python3
#
# Written by John C Sager 2019-2020. Placed in the public domain
#

import sys, time, datetime, argparse
import prologix3

def getargs():
  parser = argparse.ArgumentParser(description='Send a command over IEEE-488 & print the response')
  parser.add_argument('-n', '--no-read', dest='rd', action='store_false', help="Don't read")
  parser.add_argument('-r', '--raw', dest='rw', action='store_true', help='Do a raw read')
  parser.add_argument('command', help='Required command string')
  a = parser.parse_args()
  return (a.rd,a.rw,a.command)

def wait_srq(ins,maxcount):
  count = 0
  srq=ins.get_srq()
  while srq == '0' and count < maxcount:
    count += 1
    srq = ins.get_srq()
  return count,srq,ins.spoll()

# ttyUSBgpib is set by a udev rule
# use /dev/ttyUSBn if you are sure what n is for the Prologix adapter
USB_DEVICE = '/dev/ttyUSBgpib'

GPIB_ADDRESS = 7 # set your own appropriately

readok,raw,cmd = getargs()

plx = prologix3.Prologix_USB(USB_DEVICE,delay=0.1)

scope = plx.instrument(GPIB_ADDRESS)

rubbish=scope.read() # read & discard any rubbish in the instrument's buffer

scope.write('*cls')
scope.write('*sre 16')



scope.write(cmd)
if readok:
  cm,srq,spoll = wait_srq(scope,200)
  if raw:
    response = scope.raw_read()
  else:
    response = scope.read().rstrip()
  print(response)

scope.close()
plx.close()

    

