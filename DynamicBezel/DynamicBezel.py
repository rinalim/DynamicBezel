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
VIEWER_1P = ""
VIEWER_2P = ""

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
btn_left = -1
btn_right= -1
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
            #line = line.replace('_btn','')
            #line = line.replace('_axis','')
            words = line.split()
            retroarch_key[words[0]] = words[2].replace('"','')
    return retroarch_key

def get_devname(dev):
    jsdev = open(dev, 'rb')
    buf = array.array('B', [0] * 64)
    ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
    js_name = Bits(buf).bytes.rstrip(b'\x00').decode('utf-8')
    return js_name

def crop_img(player):
    time.sleep(0.5)
    flist = glob.glob(PATH_SS+romname+"*")
    if len(flist) > 0:
        os.system("convert " + flist[-1] + " -crop " + config[player]['position'] + " ./" + player + ".png")
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

def get_input(romname, player):
    input_data = {}
    if(os.path.isdir(PATH_HOME+'bezel/'+romname+'/'+player)):
        file_list = os.listdir(PATH_HOME+'bezel/'+romname+'/'+player+'/input')
        for f in file_list:
            if f.endswith('png'):
                size = os.path.getsize(PATH_HOME+'bezel/'+romname+'/'+player+'/input/'+f)
                filename = f.replace('.png','')
                input_data[str(size)] = filename.split('_')[0]
    return input_data   

def show_image(img_name, player):
    png_path = PATH_HOME + "bezel/" + romname + '/' + player + "/output/" + img_name + ".png"
    if os.path.isfile(png_path) == True:
        os.system("echo " + png_path + " > /tmp/bezel." + player)
        if is_running("/tmp/bezel." + player) == False:
            if player == '1p':
                print (VIEWER_1P + " &")
                os.system(VIEWER_1P + " &")
            elif player == '2p':
                os.system(VIEWER_2P + " &")

def change_bezel(player):
    if config.get(player) == None:
        print "No config found for " + player
        return false
    print "Change bezel"
    keyboard.press_and_release("f8")
    #time.sleep(0.1)
    #keyboard.release(key)
    crop_img(player)
    if os.path.isfile('./' + player + '.png') == True:
        filesize = os.path.getsize('./' + player + '.png')
        target = config[player]['input'].get(str(filesize))
        if target != None:
            print target
            show_image(target, player)
        else:
            show_image("default", player)
    return true

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

    if js_type == JS_EVENT_AXIS and js_number <= 7 and js_number % 2 == 0:
        if js_value <= JS_MIN * JS_THRESH:
            if HOTKEY_BTN_ON == True:
                change_bezel('1p')
        elif js_value >= JS_MAX * JS_THRESH:
            if HOTKEY_BTN_ON == True:
                change_bezel('2p')

    if js_type == JS_EVENT_BUTTON:
        if js_value == 1:
            if js_number == btn_hotkey:
                HOTKEY_BTN_ON = True
            elif js_number == btn_left and HOTKEY_BTN_ON == True :
                change_bezel('1p')
            elif js_number == btn_right and HOTKEY_BTN_ON == True :
                change_bezel('2p')
        elif js_value == 0:
                HOTKEY_BTN_ON = False

    return True

def main():
    
    global romname, btn_hotkey, btn_left, btn_right, config

    devname = get_devname(sys.argv[1])
    print "Device: " + devname
    keymap = load_retroarch_cfg(devname)
    btn_hotkey = int(keymap.get('enable_hotkey_btn'))
    if keymap.get('left_btn') != None:
        btn_left = int(keymap.get('left_btn'))
    if keymap.get('right_btn') != None:
        btn_right = int(keymap.get('right_btn'))
    print "Hotkey: " + str(btn_hotkey)
    print "Left: " + str(btn_left)
    print "Right: " + str(btn_right)
    romname = get_romname()
    print "Rom: " + romname
    
    f = open(PATH_HOME+'bezel/'+romname+"/config.json", "r")
    config = json.load(f)
    f.close()
    print config

    if config.get('1p') != None:
        config['1p']['input'] = get_input(romname, '1p')
        if config['1p']['display'] == 'main': 
            VIEWER_1P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.1p -f -a fill -l " + config['1p']['layer']
        elif config['1p']['display'] == 'second':
            VIEWER_1P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.1p -f -a fill -l " + config['1p']['layer'] + " -d 7"
    if config.get('2p') != None:    
        config['2p']['input'] = get_input(romname, '2p')
        if config['2p']['display'] == 'main': 
            VIEWER_2P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.2p -f -a fill -l " + config['2p']['layer']
        elif config['2p']['display'] == 'second':
            VIEWER_2P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.2p -f -a fill -l " + config['2p']['layer'] + " -d 7"     
    print config
    
    # Initialize
    os.system("pkill -ef /tmp/bezel.")
    os.system("rm -f "+PATH_SS+romname+"*")
    # Show default image
    show_image('default', '1p')
    show_image('default', '2p')

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
