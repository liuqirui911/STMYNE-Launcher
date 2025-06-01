# -*- coding: utf-8 -*-
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import (StringProperty, ListProperty, NumericProperty,
                             BooleanProperty, DictProperty, ObjectProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex as hex
from kivy.config import Config
from kivy.core.text import LabelBase
import sys
import os
import json
import requests
from threading import Thread
import time
from datetime import datetime
import re
import random
import socket
import struct

# 设置初始窗口大小并确保最小尺寸
Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '720')
Config.set('graphics', 'minimum_width', '1000')
Config.set('graphics', 'minimum_height', '600')
Window.clearcolor = (0.75, 0.88, 1, 1)  # 更柔和的蓝色背景

# 在Windows上隐藏边框
if sys.platform == 'win32':
    Window.borderless = True


# 生成资源文件目录访问路径
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):  # 是否Bundle Resource
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# 解决Windows中文乱码问题
if sys.platform == 'win32':
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('MC.Launcher')

    # 设置控制台编码为UTF-8
    try:
        os.system('chcp 65001 > nul')
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        # 尝试设置标准输出编码
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception as e:
        print(f"编码设置警告: {e}")

# 注册中文字体
try:
    font_paths = [
        resource_path(os.path.join("res", "hk4e_zh-cn.ttf")),
        'hk4e_zh-cn.ttf'
    ]

    registered = False
    for font_path in font_paths:
        try:
            LabelBase.register(name='ChineseFont', fn_regular=font_path)
            print(f"已注册中文字体: {font_path}")
            registered = True
            break
        except:
            continue

    if not registered:
        print("无法加载任何中文字体，使用默认字体")
except Exception as e:
    print(f"无法加载中文字体: {e}, 使用默认字体")


# 全局翻译函数
def tr(key):
    app = App.get_running_app()
    return app.get_text(key) if app else key


# 创建KV字符串
kv_string = '''
#:import hex kivy.utils.get_color_from_hex
#:import tr __main__.tr
#:import LabelBase kivy.core.text.LabelBase
#:set chinese_font 'ChineseFont' if 'ChineseFont' in LabelBase._fonts else 'Roboto'
#:import StringProperty kivy.properties.StringProperty
#:import ListProperty kivy.properties.ListProperty

<MCDropDownButton>:
    size_hint: None, None
    size: dp(180), dp(40)
    padding: dp(10)
    canvas.before:
        Color:
            rgba: (0.4, 0.6, 0.9, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(5),]
        Color:
            rgba: (0.2, 0.4, 0.7, 1)
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(5)]
            width: dp(1)
    Label:
        text: root.text
        font_size: sp(18)
        font_name: chinese_font
        color: (1, 1, 1, 1)
        halign: 'center'
        valign: 'middle'

<MCLoaderDropdown>:
    Button:
        size_hint_y: None
        height: dp(40)
        background_normal: ''
        background_color: (0.5, 0.7, 0.9, 1)
        text: root.selected_loader
        font_size: sp(16)
        font_name: chinese_font
        color: (1, 1, 1, 1)
        on_release: root.open(self)

<MCButton>:
    text: ""
    bg_color: [0.4, 0.6, 0.9, 1]
    text_color:  [1, 1, 1, 1]
    size_hint: None, None
    size: dp(200), dp(50)
    padding: dp(10)
    canvas.before:
        Color:
            rgba: root.bg_color if root.bg_color else ((0.4, 0.6, 0.9, 1) if root.state == 'normal' else (0.3, 0.5, 0.8, 1))
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8),]
        Color:
            rgba: (0.2, 0.4, 0.7, 1)
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(8)]
            width: dp(1)
        # 添加阴影效果
        Color:
            rgba: (0, 0, 0, 0.1)
        RoundedRectangle:
            pos: (self.x+dp(2), self.y-dp(2))
            size: self.size
            radius: [dp(8),]
    Label:
        text: root.text
        font_size: sp(20)
        font_name: chinese_font
        color: root.text_color if root.text_color else (1, 1, 1, 1)
        halign: 'center'
        valign: 'middle'
        text_size: self.size

<MCVersionCard>:
    orientation: 'vertical'
    size_hint: None, None
    size: dp(300), dp(170)  # 增加高度以容纳加载器选择
    padding: dp(10)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: (0.5, 0.7, 0.9, 1) if root.selected else (0.85, 0.92, 1, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8),]
        Color:
            rgba: (0.3, 0.5, 0.8, 1)
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(8)]
            width: dp(1)
        # 添加阴影效果
        Color:
            rgba: (0, 0, 0, 0.05) if root.selected else (0, 0, 0, 0.03)
        RoundedRectangle:
            pos: (self.x+dp(2), self.y-dp(2))
            size: self.size
            radius: [dp(8),]

    Label:
        text: root.version_name
        font_size: sp(20)
        font_name: chinese_font
        bold: True
        color: (0.1, 0.2, 0.4, 1)
        size_hint_y: None
        height: dp(30)
        halign: 'center'
        text_size: self.width, None

    BoxLayout:
        size_hint_y: None
        height: dp(25)
        spacing: dp(5)

        Label:
            text: tr('type') + ': ' + root.release_type.capitalize()
            font_size: sp(16)
            font_name: chinese_font
            color: (0.3, 0.3, 0.5, 1)
            size_hint_x: 0.6
            halign: 'left'
            text_size: self.width, None

        Label:
            text: tr('release_date') + ': ' + root.release_date
            font_size: sp(16)
            font_name: chinese_font
            color: (0.3, 0.3, 0.5, 1)
            size_hint_x: 0.4
            halign: 'right'
            text_size: self.width, None

    BoxLayout:
        size_hint_y: None
        height: dp(25)
        spacing: dp(5)

        Label:
            text: tr('size') + ': ' + root.file_size
            font_size: sp(16)
            font_name: chinese_font
            color: (0.3, 0.3, 0.5, 1)
            size_hint_x: 1.0  # 占据整行宽度
            halign: 'left'
            text_size: self.width, None

    Label:
        text: root.description if root.description else tr('no_description')
        font_size: sp(14)
        font_name: chinese_font
        color: (0.4, 0.4, 0.6, 1)
        size_hint_y: None
        height: dp(30)
        halign: 'center'
        valign: 'middle'
        text_size: self.width, None
        shorten: True
        shorten_from: 'right'

    # 加载器选择区域 - 修改为下拉菜单
    BoxLayout:
        size_hint_y: None
        height: dp(30)
        padding: [dp(2), 0]
        spacing: dp(5)

        Label:
            text: tr('loader') + ':'
            font_size: sp(16)
            font_name: chinese_font
            color: (0.3, 0.3, 0.5, 1)
            size_hint_x: 0.4
            halign: 'left'
            text_size: self.width, None

        MCDropDownButton:
            id: loader_dropdown
            size_hint_x: 0.6
            text: tr(root.selected_loader)
            on_press: root.show_loader_dropdown(self)

<MCServerCard>:
    orientation: 'vertical'
    size_hint: None, None
    size: dp(280), dp(120)  # 增加高度以容纳MOTD
    padding: dp(10)
    canvas.before:
        Color:
            rgba: (0.65, 0.82, 1, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8),]
        Color:
            rgba: (0.3, 0.5, 0.8, 1)
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(8)]
            width: dp(1)
        # 添加阴影效果
        Color:
            rgba: (0, 0, 0, 0.03)
        RoundedRectangle:
            pos: (self.x+dp(2), self.y-dp(2))
            size: self.size
            radius: [dp(8),]

    Label:
        text: root.server_name
        font_size: sp(18)
        font_name: chinese_font
        bold: True
        color: (0.1, 0.2, 0.4, 1)
        size_hint_y: None
        height: dp(30)
        halign: 'center'
        text_size: self.width, None

    Label:
        id: motd_label
        text: root.motd if root.motd else tr('fetching_motd')
        font_size: sp(14)
        font_name: chinese_font
        color: (0.3, 0.3, 0.5, 1)
        size_hint_y: None
        height: dp(30)
        halign: 'center'
        valign: 'middle'
        text_size: self.width, None
        shorten: True
        shorten_from: 'right'

    BoxLayout:
        size_hint_y: None
        height: dp(25)
        spacing: dp(5)

        Label:
            text: tr('players') + f': {root.player_count}/{root.max_players}'
            font_size: sp(16)
            font_name: chinese_font
            color: (0.3, 0.3, 0.5, 1)
            size_hint_x: 0.5
            halign: 'center'
            text_size: self.width, None

        Label:
            text: root.ping
            font_size: sp(16)
            font_name: chinese_font
            color: (0.3, 0.3, 0.5, 1)
            size_hint_x: 0.5
            halign: 'center'
            text_size: self.width, None

<MainScreen>:
    selected_version: ''
    selected_loader: 'vanilla'
    status: 'Ready'
    progress: 0
    version_data: []

    BoxLayout:
        orientation: 'vertical'
        padding: dp(15)
        spacing: dp(10)

        # 顶部标题栏
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: dp(10)
            canvas.before:
                Color:
                    rgba: (0.8, 0.92, 1, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                id: title_label
                text: tr('STMYNE Launcher')
                font_size: sp(30)
                font_name: chinese_font
                bold: True
                color: (0.1, 0.2, 0.4, 1)
                size_hint_x: 0.6
                halign: 'left'
                text_size: self.width, None

            Label:
                text: 'v1.6.0'
                font_size: sp(18)
                font_name: chinese_font
                color: (0.3, 0.3, 0.5, 1)
                size_hint_x: 0.2
                halign: 'right'
                text_size: self.width, None

            MCButton:
                id: lang_btn
                text: tr('language') + ': ' + tr('english')
                size: dp(180), dp(40)
                bg_color: (0.5, 0.7, 0.9, 1)
                text_color: (0.1, 0.2, 0.4, 1)
                on_press: app.show_language_dropdown(self)

        # 主内容区域
        BoxLayout:
            spacing: dp(15)

            # 左侧 - 版本选择
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.6
                spacing: dp(10)

                Label:
                    id: versions_label
                    text: tr('available_versions')
                    font_size: sp(20)
                    font_name: chinese_font
                    bold: True
                    color: (0.1, 0.2, 0.4, 1)
                    size_hint_y: None
                    height: dp(35)
                    halign: 'left'
                    text_size: self.width, None

                ScrollView:
                    bar_width: dp(8)
                    bar_color: hex('#4A7BC3')
                    bar_inactive_color: hex('#4A7BC3')
                    scroll_type: ['bars', 'content']

                    GridLayout:
                        id: version_grid
                        cols: 1
                        spacing: dp(20)  # 增加行间距
                        padding: dp(8)
                        size_hint_y: None
                        height: self.minimum_height

            # 右侧 - 服务器和启动控制
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.4
                spacing: dp(10)

                Label:
                    id: servers_label
                    text: tr('multiplayer_servers')
                    font_size: sp(20)
                    font_name: chinese_font
                    bold: True
                    color: (0.1, 0.2, 0.4, 1)
                    size_hint_y: None
                    height: dp(35)
                    halign: 'left'
                    text_size: self.width, None

                ScrollView:
                    bar_width: dp(8)
                    bar_color: hex('#4A7BC3')
                    bar_inactive_color: hex('#4A7BC3')
                    scroll_type: ['bars', 'content']

                    GridLayout:
                        id: server_grid
                        cols: 1
                        spacing: dp(10)
                        padding: dp(8)
                        size_hint_y: None
                        height: self.minimum_height

                BoxLayout:
                    size_hint_y: None
                    height: dp(90)
                    padding: dp(10)
                    canvas.before:
                        Color:
                            rgba: (0.85, 0.93, 1, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(8),]
                        # 添加阴影效果
                        Color:
                            rgba: (0, 0, 0, 0.05)
                        RoundedRectangle:
                            pos: (self.x+dp(2), self.y-dp(2))
                            size: self.size
                            radius: [dp(8),]

                    Label:
                        id: selected_label
                        text: tr('selected') + ': ' + (root.selected_version if root.selected_version else tr('none'))
                        font_size: sp(18)
                        font_name: chinese_font
                        color: (0.1, 0.2, 0.4, 1)
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.width, None

                    Label:
                        id: loader_label
                        text: tr('loader') + ': ' + tr(root.selected_loader)
                        font_size: sp(16)
                        font_name: chinese_font
                        color: (0.3, 0.3, 0.5, 1)
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.width, None

                BoxLayout:
                    size_hint_y: None
                    height: dp(50)
                    spacing: dp(12)

                    MCButton:
                        id: settings_btn
                        text: tr('settings')
                        on_press: root.manager.current = 'settings'
                        bg_color: (0.6, 0.8, 1, 1)
                        text_color: (0.1, 0.2, 0.4, 1)
                        size_hint_x: 0.5

                    MCButton:
                        id: launch_btn
                        text: tr('launch_game')
                        on_press: root.launch_game()
                        bg_color: (0.3, 0.7, 0.3, 1)
                        text_color: (1, 1, 1, 1)
                        size_hint_x: 0.5

        # 底部状态栏
        BoxLayout:
            size_hint_y: None
            height: dp(35)
            padding: dp(5)
            canvas.before:
                Color:
                    rgba: (0.8, 0.92, 1, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                id: status_label
                text: tr('status') + ': ' + root.status
                font_size: sp(16)
                font_name: chinese_font
                color: (0.3, 0.3, 0.5, 1)
                halign: 'left'
                text_size: self.width, None

            ProgressBar:
                value: root.progress
                max: 100
                size_hint_x: 0.4
                background_color: (0.9, 0.95, 1, 1)
                color: (0.3, 0.6, 0.9, 1)

<SettingsScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(15)
        spacing: dp(10)

        # 顶部标题栏
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: dp(10)
            canvas.before:
                Color:
                    rgba: (0.8, 0.92, 1, 1)
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                id: settings_title
                text: tr('settings')
                font_size: sp(30)
                font_name: chinese_font
                bold: True
                color: (0.1, 0.2, 0.4, 1)
                size_hint_x: 0.8
                halign: 'left'
                text_size: self.width, None

            MCButton:
                id: back_btn
                text: tr('back')
                size: dp(100), dp(40)
                on_press: root.manager.current = 'main'
                bg_color: (0.6, 0.8, 1, 1)
                text_color: (0.1, 0.2, 0.4, 1)

        # 设置选项
        ScrollView:
            bar_width: dp(8)
            bar_color: hex('#4A7BC3')
            bar_inactive_color: hex('#4A7BC3')
            scroll_type: ['bars', 'content']

            GridLayout:
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)
                padding: dp(10)

                # 游戏设置
                BoxLayout:
                    size_hint_y: None
                    height: dp(40)

                    Label:
                        id: game_settings_title
                        text: tr('game_settings')
                        font_size: sp(24)
                        font_name: chinese_font
                        bold: True
                        color: (0.1, 0.2, 0.4, 1)
                        halign: 'left'
                        text_size: self.width, None

                MCLSettingItem:
                    id: java_path_item
                    title: tr('java_path')
                    value: '/usr/bin/java'

                MCLSettingItem:
                    id: memory_item
                    title: tr('memory_allocation')
                    value: '4GB'

                MCLSettingItem:
                    id: resolution_item
                    title: tr('resolution')
                    value: '1280x720'

                MCLSettingItem:
                    id: fullscreen_item
                    title: tr('fullscreen')
                    value: tr('off')

                # 账户设置
                BoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    padding: [0, dp(15), 0, 0]

                    Label:
                        id: account_settings_title
                        text: tr('account_settings')
                        font_size: sp(24)
                        font_name: chinese_font
                        bold: True
                        color: (0.1, 0.2, 0.4, 1)
                        halign: 'left'
                        text_size: self.width, None

                MCLSettingItem:
                    id: username_item
                    title: tr('username')
                    value: 'Player123'

                MCLSettingItem:
                    id: skin_item
                    title: tr('skin')
                    value: tr('default')

                # 启动器设置
                BoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    padding: [0, dp(15), 0, 0]

                    Label:
                        id: launcher_settings_title
                        text: tr('launcher_settings')
                        font_size: sp(24)
                        font_name: chinese_font
                        bold: True
                        color: (0.1, 0.2, 0.4, 1)
                        halign: 'left'
                        text_size: self.width, None

                MCLSettingItem:
                    id: theme_item
                    title: tr('theme')
                    value: tr('sky_blue')

                MCLSettingItem:
                    id: auto_update_item
                    title: tr('auto_update')
                    value: tr('enabled')

<MCLSettingItem>:
    size_hint_y: None
    height: dp(45)
    padding: dp(8)
    canvas.before:
        Color:
            rgba: (0.9, 0.95, 1, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6),]
        # 添加阴影效果
        Color:
            rgba: (0, 0, 0, 0.03)
        RoundedRectangle:
            pos: (self.x+dp(1), self.y-dp(1))
            size: self.size
            radius: [dp(6),]

    BoxLayout:
        spacing: dp(8)

        Label:
            id: title_label
            text: root.title
            font_size: sp(20)
            font_name: chinese_font
            color: (0.1, 0.2, 0.4, 1)
            size_hint_x: 0.4
            halign: 'left'
            bold: True
            text_size: self.width, None

        Label:
            id: value_label
            text: root.value
            font_size: sp(18)
            font_name: chinese_font
            color: (0.3, 0.3, 0.5, 1)
            size_hint_x: 0.6
            halign: 'right'
            text_size: self.width, None
'''

Builder.load_string(kv_string)


# 格式化日期
def format_date(date_str):
    try:
        # 尝试解析带有时区信息的日期
        if '+' in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except:
        return date_str.split('T')[0]  # 只取日期部分


# 格式化文件大小
def format_size(size):
    if size > 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    elif size > 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


# 去除Minecraft格式代码
def clean_motd(motd):
    # 移除§格式代码
    cleaned = re.sub(r'§[0-9a-fk-or]', '', motd)
    # 移除特殊字符
    cleaned = re.sub(r'[^\x20-\x7E]', '', cleaned)
    return cleaned.strip()[:50]  # 限制长度


# Minecraft服务器查询协议实现
class MinecraftServerQuery:
    @staticmethod
    def query_server(host, port=25565, timeout=3.0):
        """
        查询Minecraft服务器状态
        返回包含服务器信息的字典，如果查询失败返回None
        """
        try:
            # 创建TCP套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            # 连接到服务器
            sock.connect((host, port))

            # 发送握手包
            handshake = struct.pack('>b', 0xFE)  # 握手包标识
            sock.send(handshake)

            # 接收响应
            response = sock.recv(4096)

            # 解析响应
            if response.startswith(b'\xFF'):
                # 移除开头的\xFF和两个字节的长度字段
                data = response[3:].decode('utf-16be', errors='replace')

                # 分割响应字段
                fields = data.split('\x00')

                if len(fields) >= 6:
                    return {
                        'motd': fields[3],
                        'players': int(fields[4]),
                        'max_players': int(fields[5]),
                        'online': True
                    }
            return None
        except Exception as e:
            print(f"服务器查询错误: {e}")
            return None
        finally:
            try:
                sock.close()
            except:
                pass


class MCDropDownButton(ButtonBehavior, BoxLayout):
    text = StringProperty('')


class MCLoaderDropdown(BoxLayout):
    selected_loader = StringProperty('vanilla')


class MCButton(ButtonBehavior, BoxLayout):
    text = StringProperty('')
    bg_color = ListProperty()
    text_color = ListProperty()


class MCVersionCard(ButtonBehavior, BoxLayout):
    version_name = StringProperty('')
    release_type = StringProperty('release')
    release_date = StringProperty('')
    file_size = StringProperty('0 KB')
    description = StringProperty('')
    selected = BooleanProperty(False)
    selected_loader = StringProperty('vanilla')  # 默认选择原版

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(on_press=self.on_version_selected)
        self.dropdown = None

    def on_version_selected(self, instance):
        # 取消选择所有其他版本
        for card in self.parent.children:
            if isinstance(card, MCVersionCard):
                card.selected = False

        # 选择当前版本
        self.selected = True
        app = App.get_running_app()
        app.root.current_screen.selected_version = self.version_name
        app.root.current_screen.selected_loader = self.selected_loader

    def show_loader_dropdown(self, button):
        """显示加载器下拉菜单"""
        if self.dropdown:
            self.dropdown.dismiss()
            self.dropdown = None

        dropdown = DropDown()
        dropdown.auto_width = False
        dropdown.width = dp(120)

        # 添加加载器选项
        for loader in ['vanilla', 'fabric', 'forge']:
            btn = Button(text=tr(loader),
                         size_hint_y=None,
                         height=dp(40),
                         background_normal='',
                         background_color=(0.5, 0.7, 0.9, 1),
                         color=(1, 1, 1, 1),
                         font_size=sp(16),
                         font_name='ChineseFont')
            btn.bind(on_press=lambda btn_inst, l=loader: self.select_loader(l, dropdown))
            dropdown.add_widget(btn)

        dropdown.open(button)
        self.dropdown = dropdown

    def select_loader(self, loader_type, dropdown):
        """选择加载器类型"""
        self.selected_loader = loader_type
        dropdown.dismiss()
        self.dropdown = None

        # 更新主屏幕的加载器显示
        if self.selected:
            app = App.get_running_app()
            app.root.current_screen.selected_loader = loader_type


class MCServerCard(ButtonBehavior, BoxLayout):
    server_name = StringProperty('')
    server_address = StringProperty('')
    player_count = NumericProperty(0)
    max_players = NumericProperty(20)
    ping = StringProperty('?ms')
    motd = StringProperty('')
    last_query_time = 0
    query_interval = 30  # 查询间隔（秒）

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 启动服务器状态更新线程
        Thread(target=self.update_server_status, daemon=True).start()

    def update_server_status(self):
        """实时更新服务器状态信息"""
        while True:
            try:
                # 检查是否达到查询间隔
                current_time = time.time()
                if current_time - self.last_query_time < self.query_interval:
                    time.sleep(1)
                    continue

                # 记录查询时间
                self.last_query_time = current_time

                # 查询服务器状态
                server_info = MinecraftServerQuery.query_server(self.server_address)

                # 更新UI
                def update_ui():
                    if server_info and server_info.get('online', False):
                        self.player_count = server_info['players']
                        self.max_players = server_info['max_players']
                        self.motd = clean_motd(server_info['motd'])
                        self.ping = f"{random.randint(20, 100)}ms"  # 模拟ping值
                    else:
                        self.motd = tr('server_offline')
                        self.ping = "offline"

                Clock.schedule_once(lambda dt: update_ui())

            except Exception as e:
                print(f"更新服务器状态出错: {e}")

                # 出错时显示离线状态
                def set_offline():
                    self.motd = tr('server_offline')
                    self.ping = "offline"

                Clock.schedule_once(lambda dt: set_offline())


class MCLSettingItem(BoxLayout):
    title = StringProperty('')
    value = StringProperty('')


class MainScreen(Screen):
    selected_version = StringProperty('')
    selected_loader = StringProperty('vanilla')  # 默认选择原版
    status = StringProperty('Ready')
    progress = NumericProperty(0)
    version_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.populate_content, 0.5)

    def populate_content(self, dt):
        # 添加游戏版本
        self.populate_versions()

        # 添加服务器
        self.populate_servers()

    def populate_versions(self):
        """填充版本列表"""
        versions = [
            {'id': '1.20.1', 'type': 'release', 'releaseTime': '2023-06-12T12:34:56+00:00', 'size': 200 * 1024 * 1024},
            {'id': '1.19.4', 'type': 'release', 'releaseTime': '2023-03-14T09:15:22+00:00', 'size': 190 * 1024 * 1024},
            {'id': '1.18.2', 'type': 'release', 'releaseTime': '2022-02-28T10:20:30+00:00', 'size': 180 * 1024 * 1024},
            {'id': '1.17.1', 'type': 'release', 'releaseTime': '2021-07-06T08:45:12+00:00', 'size': 170 * 1024 * 1024},
            {'id': '1.16.5', 'type': 'release', 'releaseTime': '2021-01-15T11:30:45+00:00', 'size': 160 * 1024 * 1024},
            {'id': '23w35a', 'type': 'snapshot', 'releaseTime': '2023-08-30T14:25:36+00:00', 'size': 150 * 1024 * 1024},
        ]

        grid = self.ids.version_grid
        for version in versions:
            card = MCVersionCard(
                version_name=version['id'],
                release_type=version['type'],
                release_date=format_date(version['releaseTime']),
                file_size=format_size(version['size']),
                description=tr('release_desc') if version["type"] == "release" else tr('snapshot_desc')
            )
            grid.add_widget(card)

    def populate_servers(self):
        """填充服务器列表"""
        servers = [
            {'name': 'Hypixel', 'address': 'mc.hypixel.net'},
            {'name': 'Mineplex', 'address': 'us.mineplex.com'},
            {'name': 'The Hive', 'address': 'play.inpvp.net'},
            {'name': 'CubeCraft', 'address': 'play.cubecraft.net'},
            {'name': 'Lifeboat', 'address': 'play.lbsg.net'},
        ]

        server_grid = self.ids.server_grid
        for server in servers:
            card = MCServerCard(
                server_name=server['name'],
                server_address=server['address'],
                player_count=0,
                max_players=100,
                ping='?ms',
                motd=tr('fetching_motd')
            )
            server_grid.add_widget(card)

    def launch_game(self):
        app = App.get_running_app()

        if not self.selected_version:
            self.status = tr('select_version_first')
            return

        self.status = tr('launching_minecraft') + f" ({self.selected_version}, {tr(self.selected_loader)})"
        self.progress = 0

        # 模拟启动过程
        def update_progress(dt):
            if self.progress < 100:
                self.progress += 2
            else:
                self.status = tr('game_running')
                Clock.unschedule(update_progress)

        Clock.schedule_interval(update_progress, 0.05)


class SettingsScreen(Screen):
    pass


class MCLancherApp(App):
    current_language = StringProperty('en')  # 默认英语
    translations = DictProperty({
        'en': {
            'mc_launcher': 'MC Launcher',
            'available_versions': 'AVAILABLE VERSIONS',
            'multiplayer_servers': 'MULTIPLAYER SERVERS',
            'players': 'Players',
            'size': 'Size',
            'type': 'Type',
            'release_date': 'Release',
            'selected': 'Selected',
            'none': 'None',
            'settings': 'SETTINGS',
            'launch_game': 'LAUNCH GAME',
            'status': 'Status',
            'ready': 'Ready',
            'select_version_first': 'Select a version first!',
            'launching_minecraft': 'Launching Minecraft...',
            'game_running': 'Game running! Enjoy!',
            'back': 'BACK',
            'game_settings': 'Game Settings',
            'java_path': 'Java Path',
            'memory_allocation': 'Memory Allocation',
            'resolution': 'Resolution',
            'fullscreen': 'Fullscreen',
            'off': 'Off',
            'account_settings': 'Account Settings',
            'username': 'Username',
            'skin': 'Skin',
            'default': 'Default',
            'launcher_settings': 'Launcher Settings',
            'theme': 'Theme',
            'sky_blue': 'Sky Blue',
            'auto_update': 'Auto Update',
            'enabled': 'Enabled',
            'language': 'LG',
            'english': 'English',
            'chinese': '中文',
            'no_description': 'No description available',
            'release_desc': 'Official stable release',
            'snapshot_desc': 'Experimental snapshot version',
            'fetching_motd': 'Fetching server info...',
            'server_offline': 'Server offline',
            'vanilla': 'Vanilla',
            'fabric': 'Fabric',
            'forge': 'Forge',
            'loader': 'Loader'
        },
        'zh': {
            'mc_launcher': '我的世界启动器',
            'available_versions': '可用版本',
            'multiplayer_servers': '多人游戏服务器',
            'players': '玩家',
            'size': '大小',
            'type': '类型',
            'release_date': '发布日期',
            'selected': '已选择',
            'none': '无',
            'settings': '设置',
            'launch_game': '启动游戏',
            'status': '状态',
            'ready': '就绪',
            'select_version_first': '请先选择一个版本！',
            'launching_minecraft': '正在启动我的世界...',
            'game_running': '游戏运行中！尽情享受吧！',
            'back': '返回',
            'game_settings': '游戏设置',
            'java_path': 'Java路径',
            'memory_allocation': '内存分配',
            'resolution': '分辨率',
            'fullscreen': '全屏',
            'off': '关闭',
            'account_settings': '账户设置',
            'username': '用户名',
            'skin': '皮肤',
            'default': '默认',
            'launcher_settings': '启动器设置',
            'theme': '主题',
            'sky_blue': '天蓝色',
            'auto_update': '自动更新',
            'enabled': '启用',
            'language': '语言',
            'english': 'English',
            'chinese': '中文',
            'no_description': '暂无描述',
            'release_desc': '官方稳定版本',
            'snapshot_desc': '实验性快照版本',
            'fetching_motd': '正在获取服务器信息...',
            'server_offline': '服务器离线',
            'vanilla': '原版',
            'fabric': 'Fabric',
            'forge': 'Forge',
            'loader': '加载器'
        }
    })

    def get_text(self, key):
        """获取当前语言的翻译文本"""
        return self.translations[self.current_language].get(key, key)

    def get_language_display(self):
        """获取当前语言的显示名称"""
        if self.current_language == 'en':
            return 'English'
        return '中文'

    def show_language_dropdown(self, button):
        """显示语言选择下拉菜单"""
        dropdown = DropDown()
        dropdown.auto_width = False
        dropdown.width = dp(180)

        for lang_code, lang_name in [('en', 'English'), ('zh', '中文')]:
            btn = MCDropDownButton(text=lang_name)
            btn.size_hint_y = None
            btn.height = dp(40)

            def select_language(lang, btn_instance):
                self.current_language = lang
                # 刷新UI以应用新语言
                self.refresh_ui()
                dropdown.dismiss()

            btn.bind(on_press=lambda instance, lang=lang_code: select_language(lang, instance))
            dropdown.add_widget(btn)

        dropdown.open(button)

    def refresh_ui(self):
        """刷新所有UI元素以应用新语言"""
        # 刷新主屏幕文本
        main_screen = self.root.get_screen('main')

        # 更新所有文本控件
        main_screen.ids.title_label.text = tr('mc_launcher')
        main_screen.ids.versions_label.text = tr('available_versions')
        main_screen.ids.servers_label.text = tr('multiplayer_servers')
        main_screen.ids.settings_btn.text = tr('settings')
        main_screen.ids.launch_btn.text = tr('launch_game')
        main_screen.ids.status_label.text = tr('status') + ': ' + main_screen.status
        main_screen.ids.lang_btn.text = tr('language') + ': ' + self.get_language_display()
        main_screen.ids.loader_label.text = tr('loader') + ': ' + tr(main_screen.selected_loader)

        # 更新选择标签
        if main_screen.selected_version:
            main_screen.ids.selected_label.text = tr('selected') + ': ' + main_screen.selected_version
        else:
            main_screen.ids.selected_label.text = tr('selected') + ': ' + tr('none')

        # 刷新设置屏幕文本
        settings_screen = self.root.get_screen('settings')
        settings_screen.ids.settings_title.text = tr('settings')
        settings_screen.ids.back_btn.text = tr('back')
        settings_screen.ids.game_settings_title.text = tr('game_settings')
        settings_screen.ids.account_settings_title.text = tr('account_settings')
        settings_screen.ids.launcher_settings_title.text = tr('launcher_settings')

        # 更新设置项
        settings_screen.ids.java_path_item.title = tr('java_path')
        settings_screen.ids.memory_item.title = tr('memory_allocation')
        settings_screen.ids.resolution_item.title = tr('resolution')
        settings_screen.ids.fullscreen_item.title = tr('fullscreen')
        settings_screen.ids.fullscreen_item.value = tr('off')
        settings_screen.ids.username_item.title = tr('username')
        settings_screen.ids.skin_item.title = tr('skin')
        settings_screen.ids.skin_item.value = tr('default')
        settings_screen.ids.theme_item.title = tr('theme')
        settings_screen.ids.theme_item.value = tr('sky_blue')
        settings_screen.ids.auto_update_item.title = tr('auto_update')
        settings_screen.ids.auto_update_item.value = tr('enabled')

    def build(self):
        # 确保最小尺寸在Windows上生效
        Window.minimum_width = 1000
        Window.minimum_height = 600

        # 创建屏幕管理器
        sm = ScreenManager(transition=SlideTransition())

        # 添加主屏幕
        main_screen = MainScreen(name='main')
        main_screen.status = tr('ready')
        sm.add_widget(main_screen)

        # 添加设置屏幕
        settings_screen = SettingsScreen(name='settings')
        sm.add_widget(settings_screen)

        return sm


if __name__ == '__main__':
    # 在Windows上设置控制台编码
    if sys.platform == 'win32':
        try:
            os.system('chcp 65001 > nul')
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            # 尝试设置标准输出编码
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8')
        except Exception as e:
            print(f"编码设置警告: {e}")

    # 创建并运行应用
    app = MCLancherApp()
    app.run()