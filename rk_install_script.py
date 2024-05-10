import subprocess
import sys
# import argparse
import signal
from pick import pick
import os
import curses

debug = 0
# 执行终端命令
def sh_(cmd):
    try:
        p = subprocess.run(cmd, universal_newlines=True, check=False, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.stdout
    except RuntimeError as e:
        print(f'Error: {e}')


def run_command(command):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        shell=True
    )

    # 实时读取输出并打印
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    
    # 等待命令执行完成
    process.wait()

# ctrl c 退出程序
def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

def get_device_hardware_information():
    device_model = sh_('cat /proc/device-tree/model')
    if device_model == None:
        device_model = None    
    elif "5A" in device_model:
        device_model = "5A"
    elif "5B" in device_model:
        device_model = "5B"
    elif "3A" in device_model:
        device_model = "3A"
    elif "4B" in device_model:
        device_model = "4B"
    else:
        return None
    return device_model

def get_resolution(camera):
    if camera == 'imx519':
        return ["4656x3496", "3840x2160", "1920x1080", 'Exit']
    elif camera == 'arducam-pivariety':
        return ["4056x3040", "3840x2160", "1920x1080", 'Exit']
    else:
        return None

def file_list(file_type, file_dir):
    return [f for f in os.listdir(file_dir) if f.endswith('.{}'.format(file_type))]

# TODO 需要增加下载包（会有多版本内核），解压后安装
def deploy_camera_driver(platform):
    run_command("rm Arducam_RK_driver_5.10.160.tar.gz")
    run_command("wget https://github.com/ArduCAM/Arducam_RK_Driver/releases/download/arducam_rk_driver_v0.0.1/Arducam_RK_driver_5.10.160.tar.gz")
    run_command("tar avxf Arducam_RK_driver_5.10.160.tar.gz")
    run_command("rm -rf Arducam_RK_driver && cp -r Arducam_RK_driver_5.10.160 Arducam_RK_driver")
    if platform == "5A":
        folder_path = 'Arducam_RK_driver/rock-5a/'
        deb_files = file_list("deb", folder_path)
    elif platform == "5B":
        folder_path = 'Arducam_RK_driver/rock-5b/'
        deb_files = file_list("deb", folder_path)
    else:
        print("Sorry, your hardward cannot be supported.")
        sys.exit(0)

    for filename in deb_files:
        if "headers" in filename:
            run_command("sudo dpkg -i {}".format(folder_path + filename))

    for filename in deb_files:
        if "image" in filename:
            run_command("sudo dpkg -i {}".format(folder_path + filename))
    run_command("sudo dpkg -i Arducam_RK_driver/arducam-iqfiles.deb")

# rsetup
def install_dtbo(platform, camera):
    if platform == "5A":
        platform_name = "rock-5a"
    elif platform == "5B":
        platform_name = "rock-5b"
    else:
        print("Sorry, your hardward cannot be supported.")
        sys.exit(0)

    folder_path = 'Arducam_RK_driver/{}/'.format(platform_name) 
    dtbo_files = file_list("dtbo", folder_path)
    for filename in dtbo_files:
        # print(filename)
        if camera in filename:
            dtbo_file_name = filename
    
    if dtbo_file_name:
        dtbo_file_install_dir = "/boot/dtbo/{}".format(dtbo_file_name)
        # return dtbo_file_name
    else:
        print("Sorry, your hardward cannot be supported.")
        sys.exit(0)
    
    if debug:
        print("Arducam_RK_driver dtbo file:")
        print(folder_path+dtbo_file_name)
        print(dtbo_file_install_dir)
        print('\n')
    
    sh_("sudo cp {} {}".format(folder_path+dtbo_file_name, dtbo_file_install_dir))

    folder_path = '/boot/dtbo/' 
    dtbo_files = file_list("dtbo", folder_path)

    for filename in dtbo_files:
        if debug:
            print("/boot/dtbo dtbo file:")
            print(filename)
            print('\n')
        if camera not in filename:
            boot_dtbo_dir = folder_path + filename
            sh_("sudo mv {} {}".format(boot_dtbo_dir, boot_dtbo_dir + ".disabled"))
    
    sh_("sudo /usr/sbin/u-boot-update")

# Change resolution
def change_resolution(resolution):
    run_command("sudo /opt/arducam/camera_init.sh {} > logfile.log 2>&1 &".format(resolution))
    return 0

def show_gui(stdscr, title, title_len, options):
    # 清空屏幕
    stdscr.clear()
    
    # 当前选中的选项索引
    current_option = 0

    # 设置颜色属性
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, -1)  # 选中选项的颜色

    while True:
        stdscr.clear()
        # 显示菜单选项
        for i, option in enumerate(options):
            if i == current_option:
                # 选中的选项前面加星号
                stdscr.addstr(i + title_len, 1, "* " + option, curses.color_pair(1))
            else:
                stdscr.addstr(i + title_len, 1, "  " + option)

        stdscr.addstr(0, 0, title, curses.A_BOLD)

        # 刷新屏幕
        stdscr.refresh()
        curses.curs_set(0)

        # 获取用户输入
        key = stdscr.getch()

        if key == curses.KEY_UP and current_option > 0:
            # 上箭头键，向上移动选项
            current_option -= 1
        elif key == curses.KEY_DOWN and current_option < len(options) - 1:
            # 下箭头键，向下移动选项
            current_option += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            # 回车键，选择当前选项
            selected_option = options[current_option]
            if selected_option == 'Exit':
                sys.exit(0)
            return selected_option

if __name__ == '__main__':

    signal.signal(signal.SIGINT,signal_handler)

    device_model = get_device_hardware_information()

    if device_model == None:
        print("The device cannot be recognized.")
        sys.exit(0)

    title = 'Machine model: Radxa ROCK {}\nPlease choose camera: '.format(device_model)
    options = ['imx519', 'arducam-pivariety', 'Exit']
    camera_name = curses.wrapper(show_gui, title, 2, options)
    options = get_resolution(camera_name)
    title_resolution = 'Please choose camera resolution: '
    resolution = curses.wrapper(show_gui, title_resolution, 1, options)

    print('Machine model: Radxa ROCK {}\nChoose camera is: {}'.format(device_model, camera_name))
    print("Choose camera resolution is: {}".format(resolution))
    print("Start install camera driver..................................")
    
    uname_version = sh_("uname -r | grep -oP '\d+\.\d+\.\d+' | head -n1").strip()

    if uname_version != "5.10.160":
        deploy_camera_driver(device_model)
    install_dtbo(device_model, camera_name)
    change_resolution(resolution)
    print("The installation is complete.")

