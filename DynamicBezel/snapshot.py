#!/usr/bin/python
#-*- coding: utf-8 -*-

import os, sys, time, keyboard, datetime
import json, glob

SPATH = "/opt/retropie/configs/all/retroarch/screenshots/"
game = sys.argv[1]
size = sys.argv[2]
character = sys.argv[3]

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
    os.system("rm "+SPATH+game+"*")
    send_hotkey("f8", 1)
    time.sleep(1)
    flist = glob.glob(SPATH+game+"*")
    print flist
    if len(flist) > 0:
        os.system("convert " + flist[0] + " -crop " + size + " ./" + filename + ".png")

crop_img(character)

#time.sleep(3)
