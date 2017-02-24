#!/usr/bin/env python

# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import string
import sys


symbols_dir=''
addr2line_cmd=''
cppfilt_cmd=''
###############################################################################
# match "#00  pc 0003f52e  /system/lib/libdvm.so" for example
###############################################################################
trace_line = re.compile("(.*)(\#[0-9]+)  (..) ([0-9a-f]{8})  ([^\r\n \t]*)")


# returns a list containing the function name and the file/lineno
def CallAddr2Line(lib, addr):
  global symbols_dir
  global addr2line_cmd
  global cppfilt_cmd

  if lib != "":
    cmd = addr2line_cmd + \
        " -f -e " + symbols_dir + lib + " 0x" + addr
    stream = os.popen(cmd)
    lines = stream.readlines()
    list = map(string.strip, lines)
  else:
    list = []
  if list != []:
    # Name like "move_forward_type<JavaVMOption>" causes troubles
    mangled_name = re.sub('<', '\<', list[0]);
    mangled_name = re.sub('>', '\>', mangled_name);
    cmd = cppfilt_cmd + " " + mangled_name
    stream = os.popen(cmd)
    list[0] = stream.readline()
    stream.close()
    list = map(string.strip, list)
  else:
    list = [ "(unknown)", "(unknown)" ]
  return list


###############################################################################
# similar to CallAddr2Line, but using objdump to find out the name of the
# containing function of the specified address
###############################################################################
def CallObjdump(lib, addr):
  global objdump_cmd
  global symbols_dir
  print symbols_dir
  unknown = "(unknown)"
  uname = os.uname()[0]
  if uname == "Darwin":
    proc = os.uname()[-1]
    if proc == "i386":
      uname = "darwin-x86"
    else:
      uname = "darwin-ppc"
  elif uname == "Linux":
    uname = "linux-x86"
  if lib != "":
    next_addr = string.atoi(addr, 16) + 1
    cmd = objdump_cmd \
        + " -C -d --start-address=0x" + addr + " --stop-address=" \
        + str(next_addr) \
        + " " + symbols_dir + lib
    stream = os.popen(cmd)
    lines = stream.readlines()
    map(string.strip, lines)
    stream.close()
  else:
    return unknown

  # output looks like
  #
  # file format elf32-littlearm
  #
  # Disassembly of section .text:
  #
  # 0000833c <func+0x4>:
  #        833c:       701a            strb    r2, [r3, #0]
  #
  # we want to extract the "func" part
  num_lines = len(lines)
  if num_lines < 2:
    return unknown
  func_name = lines[num_lines-2]
  func_regexp = re.compile("(^.*\<)(.*)(\+.*\>:$)")
  components = func_regexp.match(func_name)
  if components is None:
    return unknown
  return components.group(2)

###############################################################################
# determine the symbols directory in the local build
###############################################################################
def FindSymbolsDir():
  global symbols_dir

  

  symbols_dir = os.getcwd() + '/out/target/product/gs702a/symbols'
  print symbols_dir

###############################################################################
# determine the path of binutils
###############################################################################
def SetupToolsPath():
  global addr2line_cmd
  global objdump_cmd
  global cppfilt_cmd
  global symbols_dir

  uname = os.uname()[0]
  if uname == "Darwin":
    uname = "darwin-x86"
  elif uname == "Linux":
    uname = "linux-x86"
  prefix = "./prebuilts/gcc/" + uname + "/arm/arm-linux-androideabi-4.6/bin/"
  addr2line_cmd = prefix + "arm-linux-androideabi-addr2line"

  if (not os.path.exists(addr2line_cmd)):
    try:
      prefix = os.environ['ANDROID_BUILD_TOP'] + "/prebuilts/gcc/" + \
               uname + "/arm/arm-linux-androideabi-4.6/bin/"
    except:
      prefix = "";

    addr2line_cmd = prefix + "arm-linux-androideabi-addr2line"
    if (not os.path.exists(addr2line_cmd)):
      print addr2line_cmd + " not found!"
      sys.exit(1)

  objdump_cmd = prefix + "arm-linux-androideabi-objdump"
  cppfilt_cmd = prefix + "arm-linux-androideabi-c++filt"

###############################################################################
# look up the function and file/line number for a raw stack trace line
# groups[0]: log tag
# groups[1]: stack level
# groups[2]: "pc"
# groups[3]: code address
# groups[4]: library name
###############################################################################
def SymbolTranslation(groups):
  lib_name = groups[4]
  code_addr = groups[3]
  print lib_name
  print code_addr
  caller = CallObjdump(lib_name, code_addr)
  func_line_pair = CallAddr2Line(lib_name, code_addr)

  # If a callee is inlined to the caller, objdump will see the caller's
  # address but addr2line will report the callee's address. So the printed
  # format is desgined to be "caller<-callee  file:line"
  if (func_line_pair[0] != caller):
    s =  groups[0] + groups[1] + " " + caller + "<-" + \
          '  '.join(func_line_pair[:]) + " "
  else:
    s =  groups[0] + groups[1] + " " + '  '.join(func_line_pair[:]) + " "
  return s
###############################################################################

if __name__ == '__main__':
  # pass the options to adb
  
  adb_cmd  = "adb " + ' '.join(sys.argv[1:])
  
  f = open(sys.argv[1])
  lines = f.readlines()
  f.close()
  of = open(os.path.dirname(sys.argv[1]) + os.path.sep + 'result.txt', 'w')

  # setup addr2line_cmd and objdump_cmd
  SetupToolsPath()

  # setup the symbols directory
  FindSymbolsDir()

  # invoke the adb command and filter its output
  #stream = os.popen(adb_cmd)
  for line in lines:
      
    # EOF reached
    if (line == ''):
      break

    # remove the trailing \n
    line = line.strip()

    # see if this is a stack trace line
    match = trace_line.match(line)
    if (match):
      groups = match.groups()
      # translate raw address into symbols
      s = SymbolTranslation(groups)
      of.writelines(s + '\n')
      if not s:
          of.writelines(line + '\n')
    else:
      of.writelines(line + '\n')
      #sys.stdout.flush()
  of.close()
  # adb itself aborts

