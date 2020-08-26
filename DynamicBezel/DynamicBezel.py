#!/usr/bin/python

import os, sys, time, keyboard, datetime
import json, glob, struct, array, errno
from bitstring import Bits
from fcntl import ioctl
from subprocess import *
from pyudev import Context

OPT = '/opt/retropie'
ES_INPUT = OPT+'/configs/all/emulationstation/es_input.cfg'
RETROARCH_CFG = OPT+'/configs/all/retroarch-joypads/'
PATH_HOME = "/home/pi/DynamicBezel/"
PATH_DYNAMICBEZEL = OPT+'/configs/all/DynamicBezel/'
PATH_SS = "/opt/retropie/configs/all/retroarch/screenshots/"
VIEWER = ""

JS_MIN = -32768
JS_MAX = 32768
JS_REP = 0.20

JS_THRESH = 0.75

JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80

event_format = 'IhBB'
event_size = struct.calcsize(event_format)

btn_hotkey = -1
btn_down = -1
romname = "None"
config = {}
HOTKEY_BTN_ON = False

def run_cmd(cmd):
# runs whatever in the cmd variable
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output
        
def is_running(pname):
    ps_grep = run_cmd("ps -ef | grep " + pname + " | grep -v grep")
    if len(ps_grep) > 1 and "bash" not in ps_grep:
        return True
    else:
        return False

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

def get_devname(dev):
    jsdev = open(dev, 'rb')
    buf = array.array('B', [0] * 64)
    ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
    js_name = Bits(buf).bytes.rstrip(b'\x00').decode('utf-8')
    return js_name

def crop_img():
    #os.system("rm "+PATH_SS+romname+"*")
    #send_hotkey("f8", 1)
    time.sleep(0.5)
    flist = glob.glob(PATH_SS+romname+"*")
    if len(flist) > 0:
        os.system("convert " + flist[-1] + " -crop " + config['position'] + " ./" + config['device'] + ".png")
    os.system("rm -f "+PATH_SS+romname+"*")

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

def get_input(romname, device_id):
    input_data = {}
    if(os.path.isdir(PATH_HOME+'bezel/'+romname+'/'+device_id)):
        file_list = os.listdir(PATH_HOME+'bezel/'+romname+'/'+device_id+'/input')
        for f in file_list:
            if f.endswith('png'):
                size = os.path.getsize(PATH_HOME+'bezel/'+romname+'/'+device_id+'/input/'+f)
                filename = f.replace('.png','')
                input_data[str(size)] = filename.split('_')[0]
    return input_data   

def show_image(img_name):
    png_path = PATH_HOME + "bezel/" + romname + '/' + config['device'] + "/output/" + img_name + ".png"
    if os.path.isfile(png_path) == True:
        os.system("echo " + png_path + " > /tmp/bezel." + config['device'])
        if is_running("/tmp/bezel." + config['device']) == False:
            os.system(VIEWER + " &")

def change_bezel():
    print "Change bezel"
    crop_img()
    if os.path.isfile('./' + config['device'] + '.png') == True:
        filesize = os.path.getsize('./' + config['device'] + '.png')
        target = config['input'].get(str(filesize))
        if target != None:
            print target
            show_image(target)
        else:
            show_image("default")

def open_devices():
    devs = [sys.argv[1]]

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
    global HOTKEY_BTN_ON

    (js_time, js_value, js_type, js_number) = struct.unpack(event_format, event)

    # ignore init events
    if js_type & JS_EVENT_INIT:
        return False

    if js_type == JS_EVENT_AXIS and js_number <= 7 and js_number % 2 == 1:
        if js_value >= JS_MAX * JS_THRESH:
            if HOTKEY_BTN_ON == True:
                change_bezel()

    if js_type == JS_EVENT_BUTTON:
        if js_value == 1:
            if js_number == btn_hotkey:
                HOTKEY_BTN_ON = True
            if js_number == btn_down and HOTKEY_BTN_ON == True :
                change_bezel()
            #else:
            #    return False
        elif js_value == 0:
                HOTKEY_BTN_ON = False

    return True

def main():
    
    global romname, btn_hotkey, btn_down, config

    # check if the controller is connected
    if os.path.isfile(sys.argv[1]) == False:
        print "Cannot find controller " + sys.argv[1]
        sys.exit()

    devname = get_devname(sys.argv[1])
    print "Device: " + devname
    keymap = load_retroarch_cfg(devname)
    btn_hotkey = int(keymap.get('enable_hotkey'))
    btn_down = int(keymap.get('down'))
    print "Hotkey: " + str(btn_hotkey)
    print "Down: " + str(btn_down)
    romname = get_romname()
    print "Rom: " + romname
    
    f = open(PATH_HOME+'bezel/'+romname+"/config.json", "r")
    json_data = json.load(f)
    f.close()
    for j in json_data:
        if j['device'] == sys.argv[1].replace('/dev/input/',''):
            config = j
            config['input'] = get_input(romname, j['device'])
    print config
    os.system("pkill -ef /tmp/bezel." + config['device'])

    if config['screen'] == 'main': 
        VIEWER = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel." + config['device'] + " -f -a fill -l " + config['layer']
    elif config['screen'] == 'second':
        VIEWER = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel." + config['device'] + " -f -a fill -l " + config['layer'] + ' -d 7'
    else:
        print "Cannot find controller " + sys.argv[1]
        sys.exit()

    os.system("rm -f "+PATH_SS+romname+"*")
    # Show default image
    show_image('default')

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
            if cmp(js_devs, [sys.argv[1]]):
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
