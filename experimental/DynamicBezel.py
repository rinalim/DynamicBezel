#!/usr/bin/python

import os, sys, time, keyboard, datetime
import json, glob, struct, array, errno, filecmp
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

now_1p = "default"
now_2p = "default"
prev_1p = ""
prev_2p = ""
refresh_interval = 1
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
    ps_grep = run_cmd("ps -ef | grep '" + pname + "' | grep -v grep")
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

def send_hotkey(key, repeat):
    # Press and release "2" once before actual input (bug?)
    keyboard.press("2")
    time.sleep(0.1)
    keyboard.release("2")
    time.sleep(0.05)

    keyboard.press("2")
    time.sleep(0.1)
    
    for i in range(repeat):
        keyboard.press(key)
        time.sleep(0.1)
        keyboard.release(key)
        time.sleep(0.05)
    
    keyboard.release("2")
    #time.sleep(0.1)

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
        if player == "all":
            os.system("convert " + flist[-1] + " -crop " + config['1p']['position'] + " ./" + '1p' + ".png")
            os.system("convert " + flist[-1] + " -crop " + config['2p']['position'] + " ./" + '2p' + ".png")
        else:
            os.system("convert " + flist[-1] + " -crop " + config[player]['position'] + " ./" + player + ".png")
        os.system("rm -f "+PATH_SS+romname+"*")
        return True
    else:
        return False

def compare_img(file1, file2):
    os.system("compare -metric PSNR " + file1 + " " + file2 + " ./diff.png > ./compare.txt 2>&1")
    result = run_cmd("cat ./compare.txt")
    if result == 'inf':
        return True
    else:
        return False

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
    dup_size = []
    input_data = {}
    if(os.path.isdir(PATH_HOME+'bezel/'+romname+'/'+player)):
        file_list = os.listdir(PATH_HOME+'bezel/'+romname+'/'+player+'/input')
        for f in file_list:
            if f.endswith('png'):
                size = os.path.getsize(PATH_HOME+'bezel/'+romname+'/'+player+'/input/'+f)
                filename = f.replace('.png','')
                if input_data.get(str(size)) != None:
                    if input_data[str(size)] != filename.split('_')[0]:
                        dup_size.append(str(size))
                else:
                    input_data[str(size)] = filename.split('_')[0]
        for d in dup_size:
            filelist = []
            for f in file_list:
                if f.endswith('png'):
                    size = os.path.getsize(PATH_HOME+'bezel/'+romname+'/'+player+'/input/'+f)
                    if d == str(size):
                        filelist.append(f)
            input_data[d] = filelist

    return input_data


def show_image(img_name, player):
    global now_1p, now_2p, prev_1p, prev_2p, refresh_interval
    png_path = PATH_HOME + "bezel/" + romname + '/' + player + "/output/" + img_name + ".png"
    if os.path.isfile(png_path) == True:
        if player == '1p':
            if img_name != now_1p:
                if img_name != 'default' or prev_1p == 'default':
                    os.system("echo " + png_path + " > /tmp/bezel." + player)
                    now_1p = img_name
                prev_1p = img_name
        elif player == '2p':
            if img_name != now_2p:
                if img_name != 'default' or prev_2p == 'default':
                    os.system("echo " + png_path + " > /tmp/bezel." + player)
                    now_2p = img_name
                prev_2p = img_name
        if now_1p == 'default':
            refresh_interval = 1
        else:
            refresh_interval = 3
        if is_running("/tmp/bezel." + player) == False:
            if player == '1p':
                os.system(VIEWER_1P + " &")
            elif player == '2p':
                os.system(VIEWER_2P + " &")


def change_bezel(player):
    print "Change bezel"
    
    if player == 'all':
        players = ['1p', '2p']
    else:
        players = [player]
    
    for p in players:
        if config.get(p) == None:
           print "No config found for " + p
           return False

    send_hotkey("f8", 1)
    if crop_img(player) == False:
        print "No image to crop"
        return False

    for p in players:
        if os.path.isfile('./' + p + '.png') == True:
            filesize = os.path.getsize('./' + p + '.png')
            target = config[p]['input'].get(str(filesize))
            if target != None:
                if str(type(target)) == "<type 'str'>":
                    show_image(target, p)
                elif str(type(target)) == "<type 'list'>":
                    for t in target:
                        t_path = PATH_HOME+'bezel/'+romname+'/'+p+'/input/'+t
                        if compare_img('./' + p + '.png', t_path) == True:
                            show_image(t.split('_')[0], p)
            else:
                show_image("default", p)
    return True

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
    
    global romname, btn_hotkey, btn_left, btn_right, config, VIEWER_1P, VIEWER_2P

    time.sleep(3)
    if is_running("/PauseMenu.py /dev/input") == True:
        mode = "auto"
        print "Auto mode"
    else:
        mode = "manual"
        print "Manual mode"

    if mode == "manual":
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
    if os.path.isfile(PATH_HOME+'bezel/'+romname+"/config.json") == False:
        sys.exit(0)
    f = open(PATH_HOME+'bezel/'+romname+"/config.json", "r")
    config = json.load(f)
    f.close()
    print config

    if config.get('1p') != None:
        config['1p']['input'] = get_input(romname, '1p')
        if config['1p']['display'] == 'main': 
            VIEWER_1P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.1p -f -a fill -T blend --duration 100 -l " + config['1p']['layer']
        elif config['1p']['display'] == 'second':
            VIEWER_1P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.1p -f -a fill -T blend --duration 100 -l " + config['1p']['layer'] + " -d 7"
    if config.get('2p') != None:    
        config['2p']['input'] = get_input(romname, '2p')
        if config['2p']['display'] == 'main': 
            VIEWER_2P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.2p -f -a fill -T blend --duration 100 -l " + config['2p']['layer']
        elif config['2p']['display'] == 'second':
            VIEWER_2P = PATH_DYNAMICBEZEL + "omxiv-bezel /tmp/bezel.2p -f -a fill -T blend --duration 100 -l " + config['2p']['layer'] + " -d 7"     
    print config
    
    # Initialize
    os.system("pkill -ef omxiv-bezel")
    os.system("rm -f "+PATH_SS+romname+"*")
    os.system("rm -f ./*png")
    # Show default image
    show_image('default', '1p')
    show_image('default', '2p')

    if mode == "manual":
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

    elif mode == "auto":
        time.sleep(7)
        while True:
            if is_running('omxiv-pause') == True:
                if is_running('omxiv-bezel') == True:
                    os.system("pkill -ef omxiv-bezel")
            else:
                if is_running('omxiv-bezel') == False:
                    show_image(now_1p, '1p')
                    show_image(now_2p, '2p')
                else:
                    if config.get('2p') != None:
                        change_bezel('all')
                    else:
                        change_bezel('1p')
            time.sleep(refresh_interval)

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
