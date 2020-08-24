#!/usr/bin/python3

import os, sys, time, keyboard, datetime
import json, glob, struct, array
from bitstring import Bits
from fcntl import ioctl
from subprocess import *
from pyudev import Context

OPT = '/opt/retropie'
ES_INPUT = OPT+'/configs/all/emulationstation/es_input.cfg'
RETROARCH_CFG = OPT+'/configs/all/retroarch-joypads/'
PATH_HOME = "/home/pi/DynamicBezel/"
PATH_SS = "/opt/retropie/configs/all/retroarch/screenshots/"

romname = "None"
btn_select = '-1'
SELECT_BTN_ON = False

def run_cmd(cmd):
# runs whatever in the cmd variable
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output

def load_retroarch_cfg(dev_name):
    retroarch_key = {}
    f = open(RETROARCH_CFG + dev_name + '.cfg', 'r')
    while True:
        line = f.readline()
        if not line: 
            break
        if '_btn' in line or '_axis' in line:
            line = line.replace('\n','')
            line = line.replace('input_','')
            line = line.replace('_btn','')
            line = line.replace('_axis','')
            words = line.split()
            retroarch_key[words[0]] = words[2].replace('"','')
    return retroarch_key

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
    os.system("rm "+PATH_SS+romname+"*")
    send_hotkey("f8", 1)
    time.sleep(1)
    flist = glob.glob(PATH_SS+romname+"*")
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
    if(os.path.isdir(PATH_HOME+romname)):
        file_list = os.listdir(PATH_HOME+romname)
        for f in file_list:
            if f.endswith('png'):
                size = os.path.getsize(PATH_HOME+romname+'/'+f)
                output = f.replace('.png','')
                db[str(size)] = output.split('_')[0]
    return db   

def open_devices():
    devs = ['/dev/input/js0']

    fds = []
    for dev in devs:
        try:
            fds.append(os.open(dev, os.O_RDONLY | os.O_NONBLOCK ))
        except:
            pass

    return devs, fds

def close_fds(fds):
    for fd in fds:
        os.close(fd)

def read_event(fd):
    while True:
        try:
            event = os.read(fd, event_size)
        except OSError, e:
            if e.errno == errno.EWOULDBLOCK:
                return None
            return False

        else:
            return event

def process_event(event):
    global SELECT_BTN_ON

    (js_time, js_value, js_type, js_number) = struct.unpack(event_format, event)

    # ignore init events
    if js_type & JS_EVENT_INIT:
        return False

    if js_type == JS_EVENT_AXIS and js_number <= 7 and js_number % 2 == 1:
        if js_value <= JS_MIN * JS_THRESH:
            if SELECT_BTN_ON == True:
                print "Change bezel"
                crop_img("now")
                filesize = os.path.getsize("./now.png")
                character = db["size"].get(str(filesize))
                if character != None:
                    print(character)
                    '''
                    os.system("echo " + PATH_VOLUMEJOY + "png/volume" + str(vol/6) + ".png > /tmp/volume.txt")
                        if is_running("omxiv-volume") == False:
                            os.system(PATH_VOLUMEJOY + "omxiv-volume " + PATH_VOLUMEJOY + "png/background.png -l 30001 -a center &")
                            os.system(PATH_VOLUMEJOY + "omxiv-volume /tmp/volume.txt -f -t 5 -T blend --duration 20 -l 30002 -a center &")
                    '''

    if js_type == JS_EVENT_BUTTON:
        if js_value == 1:
            if js_number == btn_select:
                SELECT_BTN_ON = True
            else:
                return False
        elif js_value == 0:
                SELECT_BTN_ON = False

    return True

def main():
    
    global romname, btn_select

    devname = get_devname('js0')
    print("Device: "+devname)
    keymap = load_retroarch_cfg(devname)
    btn_select = keymap.get('select')
    print("Select: "+btn_select)
    romname = get_romname()
    print("Rom: "+romname)
    db = get_map(romname)
    print(db)

    f = open(PATH_HOME+romname+"/config.json", "r")
    db = json.load(f)
    f.close()
    position = db[0]["position"]
    
    js_fds=[]
    rescan_time = time.time()
    while True:
        do_sleep = True
        if not js_fds:
            js_devs, js_fds = open_devices()
            if js_fds:
                i = 0
                current = time.time()
                js_last = [None] * len(js_fds)
                for js in js_fds:
                    js_last[i] = current
                    i += 1
            else:
                time.sleep(1)
        else:
            i = 0
            for fd in js_fds:
                event = read_event(fd)
                if event:
                    do_sleep = False
                    if time.time() - js_last[i] > JS_REP:
                        if process_event(event):
                            js_last[i] = time.time()
                elif event == False:
                    close_fds(js_fds)
                    js_fds = []
                    break
                i += 1

        if time.time() - rescan_time > 2:
            rescan_time = time.time()
            if cmp(js_devs, get_devices()):
                close_fds(js_fds)
                js_fds = []

        if do_sleep:
            time.sleep(0.01)

if __name__ == "__main__":
    import sys

    try:
        main()

    # Catch all other non-exit errors
    except Exception as e:
        sys.stderr.write("Unexpected exception: %s" % e)
        sys.exit(1)

    # Catch the remaining exit errors
    except:
        sys.exit(0)
