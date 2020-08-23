#!/usr/bin/python3

import os, sys, time, keyboard, datetime
import json, glob, struct, array
from bitstring import Bits
from fcntl import ioctl
from subprocess import *

SPATH = "/opt/retropie/configs/all/retroarch/screenshots/"
romname = "None"

def run_cmd(cmd):
# runs whatever in the cmd variable
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output

def get_devname(jid):
    fn = '/dev/input/'+jid
    jsdev = open(fn, 'rb')
    buf = array.array('B', [0] * 64)
    ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
    js_name = Bits(buf).bytes.rstrip(b'\x00').decode('utf-8')
    return js_name

def send_hotkey(key, repeat):
    # Press and release "2" once before actual input (bug?)
    keyboard.press("2")
    time.sleep(0.1)
    keyboard.release("2")
    time.sleep(0.1)

    keyboard.press("2")
    time.sleep(0.1)
    
    for i in range(repeat):
        keyboard.press(key)
        time.sleep(0.1)
        keyboard.release(key)
        time.sleep(0.1)
    
    keyboard.release("2")
    time.sleep(0.1)

def crop_img(filename):
    os.system("rm "+SPATH+romname+"*")
    send_hotkey("f8", 1)
    time.sleep(1)
    flist = glob.glob(SPATH+romname+"*")
    print(flist)
    if len(flist) > 0:
        os.system("convert " + flist[0] + " -crop " + position + " ./" + filename + ".png")

def get_romname():
    while True:
        ps_grep = run_cmd("ps -aux | grep emulators | grep -v 'grep'")
        if len(ps_grep) > 1:
            words = ps_grep.split()
            pid = words[1]
            if os.path.isfile("/proc/"+pid+"/cmdline") == False:
                continue
            path = run_cmd("strings -n 1 /proc/"+pid+"/cmdline | grep roms")
            romname = path.replace('"','').split("/")[-1].split(".")[0]
            return romname

def get_map(romname):
    db = {}
    if(os.path.isdir('./'+romname)):
        file_list = os.listdir('./'+romname)
        for f in file_list:
            if f.endswith('png'):
                size = os.path.getsize('./'+romname+'/'+f) 
                output = f.replace('.png','')  
                db[str(size)] = output  
    print db   

devname = get_devname('js0')
print("Device: "+devname)
romname = get_romname()
print("Rom: "+romname)
get_map(romname)
print("Map: "+romname)

f = open(romname+"/config.json", "r")
db = json.load(f)
f.close()
position = db["position"]

while True:
    crop_img("now")
    filesize = os.path.getsize("./now.png")
    character = db["size"].get(str(filesize))
    if character != None:
        print(character)
    time.sleep(3)
#time.sleep(3)
