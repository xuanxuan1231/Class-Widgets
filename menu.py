import importlib
import json
import os
import subprocess
from pathlib import Path
from shutil import rmtree

from PyQt5 import uic, QtCore
from PyQt5.QtCore import Qt, QTime, QUrl, QDate
from qframelesswindow.webengine import FramelessWebEngineView
import sys

from PyQt5.QtGui import QIcon, QDesktopServices, QPixmap, QColor
from PyQt5.QtWidgets import QApplication, QHeaderView, QTableWidgetItem, QLabel, QHBoxLayout, QSizePolicy, \
    QSpacerItem, QFileDialog, QVBoxLayout, QWidget, QScroller
from qfluentwidgets import (
    Theme, setTheme, FluentWindow, FluentIcon as fIcon, ToolButton, ListWidget, ComboBox, CaptionLabel,
    SpinBox, LineEdit, PrimaryPushButton, TableWidget, Flyout, InfoBarIcon,
    FlyoutAnimationType, NavigationItemPosition, MessageBox, SubtitleLabel, PushButton, SwitchButton,
    CalendarPicker, BodyLabel, ColorDialog, isDarkTheme, TimeEdit, EditableComboBox, MessageBoxBase,
    SearchLineEdit, Slider, PlainTextEdit, ToolTipFilter, ToolTipPosition, RadioButton, HyperlinkLabel,
    PrimaryDropDownPushButton, Action, RoundMenu, CardWidget, ImageLabel, StrongBodyLabel,
    TransparentDropDownToolButton, Dialog, SmoothScrollArea
)
from copy import deepcopy
from network_thread import VersionThread
from loguru import logger
import datetime as dt
import list
import conf
from plugin_plaza import PluginPlaza
import tip_toast
import weather_db
import weather_db as wd

# 适配高DPI缩放
QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

today = dt.date.today()
plugin_plaza = None

plugin_dict = {}  # 插件字典
enabled_plugins = {}  # 启用的插件列表

morning_st = 0
afternoon_st = 0

current_week = 0

filename = conf.read_conf('General', 'schedule')
loaded_data = conf.load_from_json(filename)

schedule_dict = {}  # 对应时间线的课程表
schedule_even_dict = {}  # 对应时间线的课程表（双周）

timeline_dict = {}  # 时间线字典


def open_plaza():
    global plugin_plaza
    try:
        if plugin_plaza is None or not plugin_plaza.isVisible():
            plugin_plaza = PluginPlaza()
            plugin_plaza.show()
            logger.info('打开“插件广场”')
        else:
            plugin_plaza.raise_()
            plugin_plaza.activateWindow()
    except Exception as e:
        plugin_plaza = PluginPlaza()
        plugin_plaza.show()
        logger.info('打开“插件广场”')


def get_timeline():
    global loaded_data
    loaded_data = conf.load_from_json(filename)
    return loaded_data['timeline']


def open_dir(path: str):
    if sys.platform.startswith('win32'):
        os.startfile(path)
    elif sys.platform.startswith('linux'):
        subprocess.run(['xdg-open', path])
    else:
        msg_box = Dialog(
            '无法打开文件夹', f'Class Widgets 在您的系统下不支持自动打开文件夹，请手动打开以下地址：\n{path}'
        )
        msg_box.yesButton.setText('好')
        msg_box.cancelButton.hide()
        msg_box.buttonLayout.insertStretch(0, 1)
        msg_box.setFixedWidth(550)
        msg_box.exec()

 
class selectCity(MessageBoxBase):  # 选择城市
    def __init__(self, parent=None):
        super().__init__(parent)
        title_label = SubtitleLabel('搜索城市')
        subtitle_label = BodyLabel('请输入当地城市名进行搜索')
        self.yesButton.setText('选择此城市')  # 按钮组件汉化
        self.cancelButton.setText('取消')

        self.search_edit = SearchLineEdit()

        self.search_edit.setPlaceholderText('输入城市名')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.search_city)

        self.city_list = ListWidget()
        self.city_list.addItems(wd.search_by_name(''))
        self.get_selected_city()

        # 将组件添加到布局中
        self.viewLayout.addWidget(title_label)
        self.viewLayout.addWidget(subtitle_label)
        self.viewLayout.addWidget(self.search_edit)
        self.viewLayout.addWidget(self.city_list)
        self.widget.setMinimumWidth(500)
        self.widget.setMinimumHeight(600)

    def search_city(self):
        self.city_list.clear()
        self.city_list.addItems(wd.search_by_name(self.search_edit.text()))
        self.city_list.clearSelection()  # 清除选中项

    def get_selected_city(self):
        selected_city = self.city_list.findItems(
            wd.search_by_num(str(conf.read_conf('Weather', 'city'))), QtCore.Qt.MatchFlag.MatchExactly
        )
        if selected_city:  # 若找到该城市
            item = selected_city[0]
            # 选中该项
            self.city_list.setCurrentItem(item)
            # 聚焦该项
            self.city_list.scrollToItem(item)


class licenseDialog(MessageBoxBase):  # 显示软件许可协议
    def __init__(self, parent=None):
        super().__init__(parent)
        title_label = SubtitleLabel('软件许可协议')
        subtitle_label = BodyLabel('此项目 (Class Widgets) 基于 GPL-3.0 许可证授权发布，详情请参阅：')
        self.yesButton.setText('好')  # 按钮组件汉化
        self.cancelButton.hide()
        self.buttonLayout.insertStretch(0, 1)

        self.license_text = PlainTextEdit()
        self.license_text.setPlainText(open('LICENSE', 'r', encoding='utf-8').read())
        self.license_text.setReadOnly(True)

        # 将组件添加到布局中
        self.viewLayout.addWidget(title_label)
        self.viewLayout.addWidget(subtitle_label)
        self.viewLayout.addWidget(self.license_text)
        self.widget.setMinimumWidth(600)
        self.widget.setMinimumHeight(500)


class PluginSettingsDialog(MessageBoxBase):  # 插件设置对话框
    def __init__(self, plugin_dir=None, parent=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        # 加载已定义的UI
        self.plugin_widget = self.parent.plugins_settings[self.plugin_dir]
        self.viewLayout.addWidget(self.plugin_widget)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)

        self.cancelButton.hide()
        self.buttonLayout.insertStretch(0, 1)

        self.widget.setMinimumWidth(875)
        self.widget.setMinimumHeight(625)


class PluginCard(CardWidget):  # 插件卡片
    def __init__(
            self, icon, title='Unknown', content='Unknown', version='1.0.0', plugin_dir='', author=None, parent=None,
            settings=None
    ):
        super().__init__(parent)
        icon_radius = 5
        self.plugin_dir = plugin_dir
        self.title = title
        self.parent = parent

        self.iconWidget = ImageLabel(icon)  # 插件图标
        self.titleLabel = StrongBodyLabel(title, self)  # 插件名
        self.versionLabel = BodyLabel(version, self)  # 插件版本
        self.authorLabel = BodyLabel(author, self)  # 插件作者
        self.contentLabel = CaptionLabel(content, self)  # 插件描述
        self.enableButton = SwitchButton()
        self.moreButton = TransparentDropDownToolButton()
        self.moreMenu = RoundMenu(parent=self.moreButton)

        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout_Title = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout(self)

        self.moreMenu.addActions([
            Action(
                fIcon.FOLDER, f'打开“{title}”插件文件夹',
                triggered=lambda: open_dir(os.path.join(os.getcwd(), conf.PLUGINS_DIR, self.plugin_dir))
            ),
            Action(
                fIcon.DELETE, f'卸载“{title}”插件',
                triggered=self.remove_plugin
            )
        ])
        if settings:
            self.moreMenu.addSeparator()
            self.moreMenu.addAction(Action(fIcon.SETTING, f'“{title}”插件设置', triggered=self.show_settings))

        if plugin_dir in enabled_plugins['enabled_plugins']:  # 插件是否启用
            self.enableButton.setChecked(True)

        self.setFixedHeight(73)
        self.iconWidget.setFixedSize(48, 48)
        self.moreButton.setFixedSize(34, 34)
        self.iconWidget.setBorderRadius(icon_radius, icon_radius, icon_radius, icon_radius)  # 圆角
        self.contentLabel.setTextColor("#606060", "#d2d2d2")
        self.versionLabel.setTextColor("#999999", "#999999")
        self.authorLabel.setTextColor("#606060", "#d2d2d2")
        self.enableButton.checkedChanged.connect(self.set_enable)
        self.enableButton.setOffText('禁用')
        self.enableButton.setOnText('启用')
        self.moreButton.setMenu(self.moreMenu)

        self.hBoxLayout.setContentsMargins(20, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)
        self.hBoxLayout.addWidget(self.iconWidget)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addLayout(self.hBoxLayout_Title)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.hBoxLayout_Title.setSpacing(12)
        self.hBoxLayout_Title.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.hBoxLayout_Title.addWidget(self.authorLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        self.hBoxLayout_Title.addWidget(self.versionLabel, 0, Qt.AlignmentFlag.AlignVCenter)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.enableButton, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addWidget(self.moreButton, 0, Qt.AlignmentFlag.AlignRight)

    def set_enable(self):
        global enabled_plugins
        if self.enableButton.isChecked():
            enabled_plugins['enabled_plugins'].append(self.plugin_dir)
            conf.save_plugin_config(enabled_plugins)
        else:
            enabled_plugins['enabled_plugins'].remove(self.plugin_dir)
            conf.save_plugin_config(enabled_plugins)

    def show_settings(self):
        w = PluginSettingsDialog(self.plugin_dir, self.parent)
        w.exec()

    def remove_plugin(self):
        alert = MessageBox(f"您确定要删除插件“{self.title}”吗？", "删除此插件后，将无法恢复。", self.parent)
        alert.yesButton.setText('永久删除')
        alert.yesButton.setStyleSheet("""
                PushButton{
                    border-radius: 5px;
                    padding: 5px 12px 6px 12px;
                    outline: none;
                }
                PrimaryPushButton{
                    color: white;
                    background-color: #FF6167;
                    border: 1px solid #FF8585;
                    border-bottom: 1px solid #943333;
                }
                PrimaryPushButton:hover{
                    background-color: #FF7E83;
                    border: 1px solid #FF8084;
                    border-bottom: 1px solid #B13939;
                }
                PrimaryPushButton:pressed{
                    color: rgba(255, 255, 255, 0.63);
                    background-color: #DB5359;
                    border: 1px solid #DB5359;
                }
            """)
        alert.cancelButton.setText('我再想想……')
        if alert.exec():
            global enabled_plugins
            if self.plugin_dir in enabled_plugins:  # 移除启动项
                enabled_plugins['enabled_plugins'].remove(self.plugin_dir)
                conf.save_plugin_config(enabled_plugins)
            try:
                with open("plugins/plugins_from_pp.json", 'r', encoding='utf-8') as f:  # 移除插件广场安装记录
                    installed_plugins = json.load(f).get('plugins')
                    installed_plugins.remove(self.plugin_dir)
                with open("plugins/plugins_from_pp.json", 'w', encoding='utf-8') as f2:  # 移除插件广场安装记录
                    json.dump({"plugins": installed_plugins}, f2, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"保存已安装插件失败：{e}")
            try:
                rmtree(os.path.join(os.getcwd(), conf.PLUGINS_DIR, self.plugin_dir))  # 删除插件
                self.setParent(None)
                self.deleteLater()  # 删除卡片
            except Exception as e:
                logger.error(f'删除插件“{self.title}”时发生错误：{e}')


class SettingsMenu(FluentWindow):
    def __init__(self):
        super().__init__()
        self.plugins_settings = {}
        try:
            # 创建子页面
            self.spInterface = uic.loadUi('menu-preview.ui')  # 预览
            self.spInterface.setObjectName("spInterface")
            self.teInterface = uic.loadUi('menu-timeline_edit.ui')  # 时间线编辑
            self.teInterface.setObjectName("teInterface")
            self.seInterface = uic.loadUi('menu-schedule_edit.ui')  # 课程表编辑
            self.seInterface.setObjectName("seInterface")
            self.adInterface = uic.loadUi('menu-advance.ui')  # 高级选项
            self.adInterface.setObjectName("adInterface")
            self.ifInterface = uic.loadUi('menu-about.ui')  # 关于
            self.ifInterface.setObjectName("ifInterface")
            self.ctInterface = uic.loadUi('menu-custom.ui')  # 自定义
            self.ctInterface.setObjectName("ctInterface")
            self.cfInterface = uic.loadUi('menu-configs.ui')  # 配置文件
            self.cfInterface.setObjectName("cfInterface")
            self.sdInterface = uic.loadUi('menu-sound.ui')  # 通知
            self.sdInterface.setObjectName("sdInterface")
            self.hdInterface = uic.loadUi('menu-help.ui')  # 帮助
            self.hdInterface.setObjectName("hdInterface")
            self.plInterface = uic.loadUi('menu-plugin_mgr.ui')  # 插件
            self.plInterface.setObjectName("plInterface")

            self.init_nav()
            self.init_window()
        except Exception as e:
            logger.error(f'初始化设置界面时发生错误：{e}')

    def init_font(self):  # 设置字体
        self.setStyleSheet("""QLabel {
                    font-family: 'Microsoft YaHei';
                }""")

    def load_all_item(self):
        self.setup_timeline_edit()
        self.setup_schedule_edit()
        self.setup_schedule_preview()
        self.setup_advance_interface()
        self.setup_about_interface()
        self.setup_customization_interface()
        self.setup_configs_interface()
        self.setup_sound_interface()
        self.setup_help_interface()
        self.setup_plugin_mgr_interface()

    # 初始化界面
    def setup_plugin_mgr_interface(self):
        pm_scroll = self.findChild(SmoothScrollArea, 'pm_scroll')
        QScroller.grabGesture(pm_scroll.viewport(), QScroller.LeftMouseButtonGesture)  # 触摸屏适配

        global plugin_dict, enabled_plugins
        enabled_plugins = conf.load_plugin_config()  # 加载启用的插件
        plugin_dict = (conf.load_plugins())  # 加载插件信息

        open_pp = self.findChild(PushButton, 'open_plugin_plaza')
        open_pp.clicked.connect(open_plaza)  # 打开插件广场

        auto_delay = self.findChild(SpinBox, 'auto_delay')
        auto_delay.setValue(int(conf.read_conf('Plugin', 'auto_delay')))
        auto_delay.valueChanged.connect(lambda: conf.write_conf('Plugin', 'auto_delay', str(auto_delay.value())))
        # 设置自动化延迟

        plugin_card_layout = self.findChild(QVBoxLayout, 'plugin_card_layout')
        open_plugin_folder = self.findChild(PushButton, 'open_plugin_folder')
        open_plugin_folder.clicked.connect(lambda: open_dir(os.path.join(os.getcwd(), conf.PLUGINS_DIR)))  # 打开插件目录
        for plugin in plugin_dict:
            try:
                module = importlib.import_module(f'{conf.PLUGINS_DIR}.{plugin}')
                if hasattr(module, 'Settings'):
                    plugin_class = getattr(module, "Settings")  # 获取 Plugin 类
                    # 实例化插件
                    self.plugins_settings[plugin] = plugin_class(f'{conf.PLUGINS_DIR}/{plugin}')
                logger.success(f"加载插件成功：{plugin}")
            except Exception as e:
                logger.error(f"加载插件失败：{e}")

            if (Path(conf.PLUGINS_DIR) / plugin / 'icon.png').exists():  # 若插件目录存在icon.png
                icon_path = f'plugins/{plugin}/icon.png'
            else:
                icon_path = 'img/settings/plugin-icon.png'
            card = PluginCard(
                icon=icon_path,
                title=plugin_dict[plugin]['name'],
                version=plugin_dict[plugin]['version'],
                author=plugin_dict[plugin]['author'],
                plugin_dir=plugin,
                content=plugin_dict[plugin]['description'],
                settings=plugin_dict[plugin]['settings'],
                parent=self
            )
            plugin_card_layout.addWidget(card)

        tips_plugin_empty = self.findChild(QLabel, 'tips_plugin_empty')
        if plugin_dict:
            tips_plugin_empty.hide()

    def setup_help_interface(self):
        help_docu = FramelessWebEngineView(self)
        help_docu.load(QUrl("https://www.yuque.com/rinlit/class-widgets_help"))
        help_docu.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        open_by_browser = self.findChild(PushButton, 'open_by_browser')
        open_by_browser.setIcon(fIcon.LINK)
        open_by_browser.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(
            'https://www.yuque.com/rinlit/class-widgets_help'
        )))

        web_layout = self.findChild(QVBoxLayout, 'web')
        web_layout.addWidget(help_docu)

    def setup_sound_interface(self):
        sd_scroll = self.findChild(SmoothScrollArea, 'sd_scroll')  # 触摸屏适配
        QScroller.grabGesture(sd_scroll.viewport(), QScroller.LeftMouseButtonGesture)

        switch_enable_toast = self.findChild(SwitchButton, 'switch_enable_attend')
        switch_enable_toast.setChecked(int(conf.read_conf('Toast', 'attend_class')))
        switch_enable_toast.checkedChanged.connect(self.switch_enable_attend)  # 上课提醒开关

        switch_enable_finish = self.findChild(SwitchButton, 'switch_enable_finish')
        switch_enable_finish.setChecked(int(conf.read_conf('Toast', 'finish_class')))
        switch_enable_finish.checkedChanged.connect(self.switch_enable_finish)  # 下课提醒开关

        switch_enable_prepare = self.findChild(SwitchButton, 'switch_enable_prepare')
        switch_enable_prepare.setChecked(int(conf.read_conf('Toast', 'prepare_class')))
        switch_enable_prepare.checkedChanged.connect(self.switch_enable_prepare)  # 预备铃开关

        switch_enable_pin_toast = self.findChild(SwitchButton, 'switch_enable_pin_toast')
        switch_enable_pin_toast.setChecked(int(conf.read_conf('Toast', 'pin_on_top')))
        switch_enable_pin_toast.checkedChanged.connect(self.switch_enable_pin_toast)  # 置顶开关

        slider_volume = self.findChild(Slider, 'slider_volume')
        slider_volume.setValue(int(conf.read_conf('Audio', 'volume')))
        slider_volume.valueChanged.connect(self.save_volume)  # 音量滑块

        preview_toast_button = self.findChild(PrimaryDropDownPushButton, 'preview')

        pre_toast_menu = RoundMenu(parent=preview_toast_button)
        pre_toast_menu.addActions([
            Action(fIcon.EDUCATION, '上课提醒',
                   triggered=lambda: tip_toast.push_notification(1, lesson_name='信息技术')),
            Action(fIcon.CAFE, '下课提醒',
                   triggered=lambda: tip_toast.push_notification(0, lesson_name='信息技术')),
            Action(fIcon.BOOK_SHELF, '预备提醒',
                   triggered=lambda: tip_toast.push_notification(3, lesson_name='信息技术')),
            Action(fIcon.CODE, '其他提醒',
                   triggered=lambda: tip_toast.push_notification(4, title='通知', subtitle='测试通知示例',
                                                content='这是一条测试通知ヾ(≧▽≦*)o'))
        ])
        preview_toast_button.setMenu(pre_toast_menu)  # 预览通知栏

        switch_wave_effect = self.findChild(SwitchButton, 'switch_enable_wave')
        switch_wave_effect.setChecked(int(conf.read_conf('Toast', 'wave')))
        switch_wave_effect.checkedChanged.connect(self.switch_wave_effect)  # 波纹开关

        spin_prepare_time = self.findChild(SpinBox, 'spin_prepare_class')
        spin_prepare_time.setValue(int(conf.read_conf('Toast', 'prepare_minutes')))
        spin_prepare_time.valueChanged.connect(self.save_prepare_time)  # 准备时间

    def setup_configs_interface(self):  # 配置界面
        cf_import_schedule = self.findChild(PushButton, 'im_schedule')
        cf_import_schedule.clicked.connect(self.cf_import_schedule)  # 导入课程表
        cf_export_schedule = self.findChild(PushButton, 'ex_schedule')
        cf_export_schedule.clicked.connect(self.cf_export_schedule)  # 导出课程表
        cf_open_schedule_folder = self.findChild(PushButton, 'open_schedule_folder')  # 打开课程表文件夹
        cf_open_schedule_folder.clicked.connect(lambda: open_dir(os.path.join(os.getcwd(), 'config/schedule')))

    def setup_customization_interface(self):
        ct_scroll = self.findChild(SmoothScrollArea, 'ct_scroll')  # 触摸屏适配
        QScroller.grabGesture(ct_scroll.viewport(), QScroller.LeftMouseButtonGesture)

        self.ct_update_preview()

        widgets_list_widgets = self.findChild(ListWidget, 'widgets_list')
        widgets_list = []
        for key in list.get_widget_config():
            try:
                widgets_list.append(list.widget_name[key])
            except KeyError:
                logger.warning(f'未知的组件：{key}')
            except:
                logger.error(f'获取组件名称时发生错误：{sys.exc_info()[0]}')
        widgets_list_widgets.addItems(widgets_list)
        widgets_list_widgets.sizePolicy().setVerticalPolicy(QSizePolicy.Policy.MinimumExpanding)

        save_config_button = self.findChild(PrimaryPushButton, 'save_config')
        save_config_button.clicked.connect(self.ct_save_widget_config)

        set_wcc_title = self.findChild(LineEdit, 'set_wcc_title')  # 倒计时标题
        set_wcc_title.setText(conf.read_conf('Date', 'cd_text_custom'))
        set_wcc_title.textChanged.connect(lambda: conf.write_conf('Date', 'cd_text_custom', set_wcc_title.text()))

        set_countdown_date = self.findChild(CalendarPicker, 'set_countdown_date')  # 倒计时日期
        if conf.read_conf('Date', 'countdown_date') != '':
            set_countdown_date.setDate(QDate.fromString(conf.read_conf('Date', 'countdown_date'), 'yyyy-M-d'))
        set_countdown_date.dateChanged.connect(
            lambda: conf.write_conf(
                'Date', 'countdown_date', set_countdown_date.date.toString('yyyy-M-d'))
        )

        set_ac_color = self.findChild(PushButton, 'set_ac_color')  # 主题色
        set_ac_color.clicked.connect(self.ct_set_ac_color)
        set_fc_color = self.findChild(PushButton, 'set_fc_color')
        set_fc_color.clicked.connect(self.ct_set_fc_color)

        open_theme_folder = self.findChild(HyperlinkLabel, 'open_theme_folder')  # 打开主题文件夹
        open_theme_folder.clicked.connect(lambda: open_dir(os.path.join(os.getcwd(), 'ui')))

        select_theme_combo = self.findChild(ComboBox, 'combo_theme_select')  # 主题选择
        select_theme_combo.addItems(list.theme_names)
        select_theme_combo.setCurrentIndex(list.get_current_theme_num())
        select_theme_combo.currentIndexChanged.connect(
            lambda: conf.write_conf('General', 'theme', list.get_theme_ui_path(select_theme_combo.currentText())))

        color_mode_combo = self.findChild(ComboBox, 'combo_color_mode')  # 颜色模式选择
        color_mode_combo.addItems(list.color_mode)
        color_mode_combo.setCurrentIndex(int(conf.read_conf('General', 'color_mode')))
        color_mode_combo.currentIndexChanged.connect(self.ct_change_color_mode)

        widgets_combo = self.findChild(ComboBox, 'widgets_combo')  # 组件选择
        widgets_combo.addItems(list.get_widget_names())

        search_city_button = self.findChild(PushButton, 'select_city')
        search_city_button.clicked.connect(self.show_search_city)

        add_widget_button = self.findChild(PrimaryPushButton, 'add_widget')
        add_widget_button.clicked.connect(self.ct_add_widget)

        remove_widget_button = self.findChild(PushButton, 'remove_widget')
        remove_widget_button.clicked.connect(self.ct_remove_widget)

        slider_opacity = self.findChild(Slider, 'slider_opacity')
        slider_opacity.setValue(int(conf.read_conf('General', 'opacity')))
        slider_opacity.valueChanged.connect(
            lambda: conf.write_conf('General', 'opacity', str(slider_opacity.value()))
        )  # 透明度

        blur_countdown = self.findChild(SwitchButton, 'switch_blur_countdown')
        blur_countdown.setChecked(int(conf.read_conf('General', 'blur_countdown')))
        blur_countdown.checkedChanged.connect(self.switch_blur_countdown)  # 模糊倒计时

        select_weather_api = self.findChild(ComboBox, 'select_weather_api')  # 天气API选择
        select_weather_api.addItems(weather_db.api_config['weather_api_list_zhCN'])
        select_weather_api.setCurrentIndex(weather_db.api_config['weather_api_list'].index(
            conf.read_conf('Weather', 'api')
        ))
        select_weather_api.currentIndexChanged.connect(
            lambda: conf.write_conf('Weather', 'api',
                                    weather_db.api_config['weather_api_list'][select_weather_api.currentIndex()])
        )

        api_key_edit = self.findChild(LineEdit, 'api_key_edit')  # API密钥
        api_key_edit.setText(conf.read_conf('Weather', 'api_key'))
        api_key_edit.textChanged.connect(lambda: conf.write_conf('Weather', 'api_key', api_key_edit.text()))

    def setup_about_interface(self):
        self.version = self.findChild(BodyLabel, 'version')
        self.version.setText(f'当前版本：{conf.read_conf("Other", "version")}\n正在检查最新版本…')

        self.version_thread = VersionThread()
        self.version_thread.version_signal.connect(self.ab_check_update)
        self.version_thread.start()

        github_page = self.findChild(PushButton, "button_github")
        github_page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(
            'https://github.com/RinLit-233-shiroko/Class-Widgets')))

        bilibili_page = self.findChild(PushButton, 'button_bilibili')
        bilibili_page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(
            'https://space.bilibili.com/569522843')))

        license_button = self.findChild(PushButton, 'button_show_license')
        license_button.clicked.connect(self.show_license)

        thanks_button = self.findChild(PushButton, 'button_thanks')
        thanks_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(
            'https://github.com/RinLit-233-shiroko/Class-Widgets?tab=readme-ov-file#致谢')))

    def setup_advance_interface(self):
        adv_scroll = self.findChild(SmoothScrollArea, 'adv_scroll')  # 触摸屏适配
        QScroller.grabGesture(adv_scroll.viewport(), QScroller.LeftMouseButtonGesture)

        margin_spin = self.findChild(SpinBox, 'margin_spin')
        margin_spin.setValue(int(conf.read_conf('General', 'margin')))
        margin_spin.valueChanged.connect(
            lambda: conf.write_conf('General', 'margin', str(margin_spin.value()))
        )  # 保存边距设定

        conf_combo = self.findChild(ComboBox, 'conf_combo')
        conf_combo.addItems(list.get_schedule_config())
        conf_combo.setCurrentIndex(list.get_schedule_config().index(conf.read_conf('General', 'schedule')))
        conf_combo.currentIndexChanged.connect(self.ad_change_file)  # 切换配置文件

        conf_name = self.findChild(LineEdit, 'conf_name')
        conf_name.setText(filename[:-5])
        conf_name.textChanged.connect(self.ad_change_file_name)

        switch_pin_button = self.findChild(SwitchButton, 'switch_pin_button')
        switch_pin_button.setChecked(int(conf.read_conf('General', 'pin_on_top')))
        switch_pin_button.checkedChanged.connect(self.switch_pin)  # 置顶开关

        switch_startup = self.findChild(SwitchButton, 'switch_startup')
        switch_startup.setChecked(int(conf.read_conf('General', 'auto_startup')))
        switch_startup.checkedChanged.connect(self.switch_startup)  # 开机自启
        if os.name != 'nt':
            switch_startup.setEnabled(False)

        hide_mode_combo = self.findChild(ComboBox, 'hide_mode_combo')
        hide_mode_combo.addItems(list.hide_mode if os.name == 'nt' else list.non_nt_hide_mode)
        hide_mode_combo.setCurrentIndex(int(conf.read_conf('General', 'hide')))
        hide_mode_combo.currentIndexChanged.connect(
            lambda: conf.write_conf('General', 'hide', str(hide_mode_combo.currentIndex()))
        )  # 隐藏模式

        hide_method_default = self.findChild(RadioButton, 'hide_method_default')
        hide_method_default.setChecked(conf.read_conf('General', 'hide_method') == '0')
        hide_method_default.toggled.connect(lambda: conf.write_conf('General', 'hide_method', '0'))
        if os.name != 'nt':
            hide_method_default.setEnabled(False)
        # 默认隐藏

        hide_method_all = self.findChild(RadioButton, 'hide_method_all')
        hide_method_all.setChecked(conf.read_conf('General', 'hide_method') == '1')
        hide_method_all.toggled.connect(lambda: conf.write_conf('General', 'hide_method', '1'))
        # 单击全部隐藏

        hide_method_floating = self.findChild(RadioButton, 'hide_method_floating')
        hide_method_floating.setChecked(conf.read_conf('General', 'hide_method') == '2')
        hide_method_floating.toggled.connect(lambda: conf.write_conf('General', 'hide_method', '2'))
        # 最小化为浮窗

        switch_enable_alt_schedule = self.findChild(SwitchButton, 'switch_enable_alt_schedule')
        switch_enable_alt_schedule.setChecked(int(conf.read_conf('General', 'enable_alt_schedule')))
        switch_enable_alt_schedule.checkedChanged.connect(self.switch_enable_alt_schedule)  # 单双周开关

        switch_enable_multiple_programs = self.findChild(SwitchButton, 'switch_multiple_programs')
        switch_enable_multiple_programs.setChecked(int(conf.read_conf('Other', 'multiple_programs')))
        switch_enable_multiple_programs.checkedChanged.connect(self.switch_enable_multiple_programs)  # 多开

        switch_disable_log = self.findChild(SwitchButton, 'switch_disable_log')
        switch_disable_log.setChecked(int(conf.read_conf('Other', 'do_not_log')))
        switch_disable_log.checkedChanged.connect(self.switch_disable_log)  # 禁用日志

        button_clear_log = self.findChild(PushButton, 'button_clear_log')
        button_clear_log.clicked.connect(self.clear_log)  # 清空日志

        set_start_date = self.findChild(CalendarPicker, 'set_start_date')  # 日期
        if conf.read_conf('Date', 'start_date') != '':
            set_start_date.setDate(QDate.fromString(conf.read_conf('Date', 'start_date'), 'yyyy-M-d'))
        set_start_date.dateChanged.connect(
            lambda: conf.write_conf('Date', 'start_date', set_start_date.date.toString('yyyy-M-d')))  # 开学日期

        offset_spin = self.findChild(SpinBox, 'offset_spin')
        offset_spin.setValue(int(conf.read_conf('General', 'time_offset')))
        offset_spin.valueChanged.connect(
            lambda: conf.write_conf('General', 'time_offset', str(offset_spin.value()))
        )  # 保存时差偏移

    def setup_schedule_edit(self):
        self.se_load_item()
        se_set_button = self.findChild(ToolButton, 'set_button')
        se_set_button.setIcon(fIcon.EDIT)
        se_set_button.setToolTip('编辑课程')
        se_set_button.installEventFilter(ToolTipFilter(se_set_button, showDelay=300, position=ToolTipPosition.TOP))
        se_set_button.clicked.connect(self.se_edit_item)

        se_clear_button = self.findChild(ToolButton, 'clear_button')
        se_clear_button.setIcon(fIcon.DELETE)
        se_clear_button.setToolTip('清空课程')
        se_clear_button.installEventFilter(ToolTipFilter(se_clear_button, showDelay=300, position=ToolTipPosition.TOP))
        se_clear_button.clicked.connect(self.se_delete_item)

        se_class_kind_combo = self.findChild(ComboBox, 'class_combo')  # 课程类型
        se_class_kind_combo.addItems(list.class_kind)

        se_week_combo = self.findChild(ComboBox, 'week_combo')  # 星期
        se_week_combo.addItems(list.week)
        se_week_combo.currentIndexChanged.connect(self.se_upload_list)

        se_schedule_list = self.findChild(ListWidget, 'schedule_list')
        se_schedule_list.addItems(schedule_dict[str(current_week)])
        se_schedule_list.itemChanged.connect(self.se_upload_item)
        QScroller.grabGesture(se_schedule_list.viewport(), QScroller.LeftMouseButtonGesture)  # 触摸屏适配

        se_save_button = self.findChild(PrimaryPushButton, 'save_schedule')
        se_save_button.clicked.connect(self.se_save_item)

        se_week_type_combo = self.findChild(ComboBox, 'week_type_combo')
        se_week_type_combo.addItems(list.week_type)
        se_week_type_combo.currentIndexChanged.connect(self.se_upload_list)

        se_copy_schedule_button = self.findChild(PushButton, 'copy_schedule')
        se_copy_schedule_button.hide()
        se_copy_schedule_button.clicked.connect(self.se_copy_odd_schedule)

        quick_set_schedule = self.findChild(ListWidget, 'subject_list')
        quick_set_schedule.addItems(list.class_kind[1:])
        quick_set_schedule.itemClicked.connect(self.se_quick_set_schedule)

        quick_select_week_button = self.findChild(PushButton, 'quick_select_week')
        quick_select_week_button.clicked.connect(self.se_quick_select_week)

    def setup_timeline_edit(self):  # 底层大改
        self.te_load_item()  # 加载时段
        # teInterface
        te_add_button = self.findChild(ToolButton, 'add_button')  # 添加
        te_add_button.setIcon(fIcon.ADD)
        te_add_button.setToolTip('添加时间线')  # 增加提示
        te_add_button.installEventFilter(ToolTipFilter(te_add_button, showDelay=300, position=ToolTipPosition.TOP))
        te_add_button.clicked.connect(self.te_add_item)
        te_add_button.clicked.connect(self.te_upload_item)

        te_add_part_button = self.findChild(ToolButton, 'add_part_button')  # 添加节点
        te_add_part_button.setIcon(fIcon.ADD)
        te_add_part_button.setToolTip('添加节点')
        te_add_part_button.installEventFilter(
            ToolTipFilter(te_add_part_button, showDelay=300, position=ToolTipPosition.TOP))
        te_add_part_button.clicked.connect(self.te_add_part)

        te_name_edit = self.findChild(EditableComboBox, 'name_part_combo')  # 名称
        te_name_edit.addItems(list.time)

        te_delete_part_button = self.findChild(ToolButton, 'delete_part_button')  # 删除节点
        te_delete_part_button.setIcon(fIcon.DELETE)
        te_delete_part_button.setToolTip('删除节点')
        te_delete_part_button.installEventFilter(
            ToolTipFilter(te_delete_part_button, showDelay=300, position=ToolTipPosition.TOP))
        te_delete_part_button.clicked.connect(self.te_delete_part)

        te_edit_button = self.findChild(ToolButton, 'edit_button')  # 编辑
        te_edit_button.setIcon(fIcon.EDIT)
        te_edit_button.setToolTip('编辑时间线')
        te_edit_button.installEventFilter(ToolTipFilter(te_edit_button, showDelay=300, position=ToolTipPosition.TOP))
        te_edit_button.clicked.connect(self.te_edit_item)

        te_delete_button = self.findChild(ToolButton, 'delete_button')  # 删除
        te_delete_button.setIcon(fIcon.DELETE)
        te_delete_button.setToolTip('删除时间线')
        te_delete_button.installEventFilter(
            ToolTipFilter(te_delete_button, showDelay=300, position=ToolTipPosition.TOP))
        te_delete_button.clicked.connect(self.te_delete_item)
        te_delete_button.clicked.connect(self.te_upload_item)

        te_class_activity_combo = self.findChild(ComboBox, 'class_activity')  # 活动类型
        te_class_activity_combo.addItems(list.class_activity)
        te_class_activity_combo.setToolTip('选择活动类型（“课程”或“课间”）')
        te_class_activity_combo.currentIndexChanged.connect(self.te_sync_time)

        te_select_timeline = self.findChild(ComboBox, 'select_timeline')  # 选择时间线
        te_select_timeline.addItem('默认')
        te_select_timeline.addItems(list.week)
        te_select_timeline.setToolTip('选择一周内的某一天的时间线')
        te_select_timeline.currentIndexChanged.connect(self.te_upload_list)

        te_timeline_list = self.findChild(ListWidget, 'timeline_list')  # 所选时间线列表
        te_timeline_list.addItems(timeline_dict['default'])
        te_timeline_list.itemChanged.connect(self.te_upload_item)

        te_save_button = self.findChild(PrimaryPushButton, 'save')  # 保存
        te_save_button.clicked.connect(self.te_save_item)

        part_list = self.findChild(ListWidget, 'part_list')
        QScroller.grabGesture(te_timeline_list.viewport(), QScroller.LeftMouseButtonGesture)  # 触摸屏适配
        QScroller.grabGesture(part_list.viewport(), QScroller.LeftMouseButtonGesture)  # 触摸屏适配
        self.te_detect_item()
        self.te_detect_part()  # 修复在启动时无法添加时段到下拉框的问题

    def setup_schedule_preview(self):
        subtitle = self.findChild(SubtitleLabel, 'subtitle_file')
        subtitle.setText(f'预览  -  {filename[:-5]}')

        schedule_view = self.findChild(TableWidget, 'schedule_view')
        schedule_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # 使列表自动等宽

        sp_week_type_combo = self.findChild(ComboBox, 'pre_week_type_combo')
        sp_week_type_combo.addItems(list.week_type)
        sp_week_type_combo.currentIndexChanged.connect(self.sp_fill_grid_row)

        # 设置表格
        schedule_view.setColumnCount(7)
        schedule_view.setHorizontalHeaderLabels(list.week[0:7])
        schedule_view.setBorderVisible(True)
        schedule_view.verticalHeader().hide()
        schedule_view.setBorderRadius(8)
        QScroller.grabGesture(schedule_view.viewport(), QScroller.LeftMouseButtonGesture)  # 触摸屏适配
        self.sp_fill_grid_row()

    def save_volume(self):
        slider_volume = self.findChild(Slider, 'slider_volume')
        conf.write_conf('Audio', 'volume', str(slider_volume.value()))

    def show_search_city(self):
        search_city_dialog = selectCity(self)
        if search_city_dialog.exec():
            selected_city = search_city_dialog.city_list.selectedItems()
            if selected_city:
                conf.write_conf('Weather', 'city', wd.search_code_by_name(selected_city[0].text()))

    def show_license(self):
        license_dialog = licenseDialog(self)
        license_dialog.exec()

    def switch_disable_log(self):
        switch_disable_log = self.findChild(SwitchButton, 'switch_disable_log')
        if switch_disable_log.isChecked():
            conf.write_conf('Other', 'do_not_log', '1')
        else:
            conf.write_conf('Other', 'do_not_log', '0')

    def switch_blur_countdown(self):
        switch_blur_countdown = self.findChild(SwitchButton, 'switch_blur_countdown')
        if switch_blur_countdown.isChecked():
            conf.write_conf('General', 'blur_countdown', '1')
        else:
            conf.write_conf('General', 'blur_countdown', '0')

    def switch_pin(self):
        switch_pin_button = self.findChild(SwitchButton, 'switch_pin_button')
        if switch_pin_button.isChecked():
            conf.write_conf('General', 'pin_on_top', '1')
        else:
            conf.write_conf('General', 'pin_on_top', '0')

    def switch_wave_effect(self):
        switch_wave_effect = self.findChild(SwitchButton, 'switch_enable_wave')
        if switch_wave_effect.isChecked():
            conf.write_conf('Toast', 'wave', '1')
        else:
            conf.write_conf('Toast', 'wave', '0')

    def switch_startup(self):
        switch_startup = self.findChild(SwitchButton, 'switch_startup')
        if switch_startup.isChecked():
            conf.write_conf('General', 'auto_startup', '1')
            conf.add_to_startup('ClassWidgets.exe', 'img/favicon.ico')
        else:
            conf.write_conf('General', 'auto_startup', '0')
            conf.remove_from_startup()

    def switch_enable_attend(self):
        switch_enable_toast = self.findChild(SwitchButton, 'switch_enable_attend')
        if switch_enable_toast.isChecked():
            conf.write_conf('Toast', 'attend_class', '1')
        else:
            conf.write_conf('Toast', 'attend_class', '0')

    def switch_enable_finish(self):
        switch_enable_toast = self.findChild(SwitchButton, 'switch_enable_finish')
        if switch_enable_toast.isChecked():
            conf.write_conf('Toast', 'finish_class', '1')
        else:
            conf.write_conf('Toast', 'finish_class', '0')

    def switch_enable_prepare(self):
        switch_enable_toast = self.findChild(SwitchButton, 'switch_enable_prepare')
        if switch_enable_toast.isChecked():
            conf.write_conf('Toast', 'prepare_class', '1')
        else:
            conf.write_conf('Toast', 'prepare_class', '0')

    def switch_enable_pin_toast(self):
        switch_enable_toast = self.findChild(SwitchButton, 'switch_enable_pin_toast')
        if switch_enable_toast.isChecked():
            conf.write_conf('Toast', 'pin_on_top', '1')
        else:
            conf.write_conf('Toast', 'pin_on_top', '0')

    def switch_enable_alt_schedule(self):
        switch_enable_alt_schedule = self.findChild(SwitchButton, 'switch_enable_alt_schedule')
        if switch_enable_alt_schedule.isChecked():
            conf.write_conf('General', 'enable_alt_schedule', '1')
        else:
            conf.write_conf('General', 'enable_alt_schedule', '0')

    def switch_enable_multiple_programs(self):
        switch_enable_multiple_programs = self.findChild(SwitchButton, 'switch_multiple_programs')
        if switch_enable_multiple_programs.isChecked():
            conf.write_conf('Other', 'multiple_programs', '1')
        else:
            conf.write_conf('Other', 'multiple_programs', '0')

    def save_prepare_time(self):
        prepare_time_spin = self.findChild(SpinBox, 'spin_prepare_class')
        conf.write_conf('Toast', 'prepare_minutes', str(prepare_time_spin.value()))

    def clear_log(self):  # 清空日志
        def get_directory_size(path):  # 计算目录大小
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(file_path)
            total_size /= 1024
            return round(total_size, 2)

        button_clear_log = self.findChild(PushButton, 'button_clear_log')
        try:
            if os.path.exists('log'):
                size = get_directory_size('log')
                rmtree('log')
                Flyout.create(
                    icon=InfoBarIcon.SUCCESS,
                    title='已清除日志',
                    content=f"已清空所有日志文件，约 {size} KB",
                    target=button_clear_log,
                    parent=self,
                    isClosable=True,
                    aniType=FlyoutAnimationType.PULL_UP
                )
            else:
                Flyout.create(
                    icon=InfoBarIcon.INFORMATION,
                    title='未找到日志',
                    content="日志目录下为空，已清理完成。",
                    target=button_clear_log,
                    parent=self,
                    isClosable=True,
                    aniType=FlyoutAnimationType.PULL_UP
                )
        except OSError:  # 遇到程序正在使用的log，忽略
            Flyout.create(
                icon=InfoBarIcon.SUCCESS,
                title='已清除日志',
                content=f"已清空所有日志文件，约 {size} KB",
                target=button_clear_log,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
        except Exception as e:
            Flyout.create(
                icon=InfoBarIcon.ERROR,
                title='清除日志失败！',
                content=f"清除日志失败：{e}",
                target=button_clear_log,
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )

    def ct_change_color_mode(self):
        color_mode_combo = self.findChild(ComboBox, 'combo_color_mode')
        conf.write_conf('General', 'color_mode', str(color_mode_combo.currentIndex()))
        if color_mode_combo.currentIndex() == 0:
            tg_theme = Theme.LIGHT
        elif color_mode_combo.currentIndex() == 1:
            tg_theme = Theme.DARK
        else:
            tg_theme = Theme.AUTO
        setTheme(tg_theme)
        self.ct_update_preview()

    def ct_add_widget(self):
        widgets_list = self.findChild(ListWidget, 'widgets_list')
        widgets_combo = self.findChild(ComboBox, 'widgets_combo')
        if not widgets_list.findItems(widgets_combo.currentText(), QtCore.Qt.MatchFlag.MatchExactly):
            widgets_list.addItem(widgets_combo.currentText())
        self.ct_update_preview()

    def ct_remove_widget(self):
        widgets_list = self.findChild(ListWidget, 'widgets_list')
        if widgets_list.count() > 2:
            widgets_list.takeItem(widgets_list.currentRow())
            self.ct_update_preview()
        else:
            w = MessageBox('无法删除', '至少需要保留两个小组件。', self)
            w.cancelButton.hide()  # 隐藏取消按钮
            w.buttonLayout.insertStretch(0, 1)
            w.exec()

    def ct_set_ac_color(self):
        current_color = QColor(f'#{conf.read_conf("Color", "attend_class")}')
        w = ColorDialog(current_color, "更改上课时主题色", self, enableAlpha=False)
        w.colorChanged.connect(lambda color: conf.write_conf('Color', 'attend_class', color.name()[1:]))
        w.exec()

    def ct_set_fc_color(self):
        current_color = QColor(f'#{conf.read_conf("Color", "finish_class")}')
        w = ColorDialog(current_color, "更改课间时主题色", self, enableAlpha=False)
        w.colorChanged.connect(lambda color: conf.write_conf('Color', 'finish_class', color.name()[1:]))
        w.exec()

    def cf_export_schedule(self):  # 导出课程表
        file_path, _ = QFileDialog.getSaveFileName(self, "保存文件", filename, "Json 配置文件 (*.json)")
        if file_path:
            if list.export_schedule(file_path, filename):
                alert = MessageBox('您已成功导出课程表配置文件',
                                   f'文件将导出于{file_path}', self)
                alert.cancelButton.hide()
                alert.buttonLayout.insertStretch(0, 1)
                if alert.exec():
                    return 0
            else:
                print('导出失败！')
                alert = MessageBox('导出失败！',
                                   '课程表文件导出失败，\n'
                                   '可能为文件损坏，请将此情况反馈给开发者。', self)
                alert.cancelButton.hide()
                alert.buttonLayout.insertStretch(0, 1)
                if alert.exec():
                    return 0

    def ab_check_update(self, version):  # 检查更新
        if version[1:] == conf.read_conf("Other", "version"):
            self.version.setText(f'当前版本：{version}\n当前为最新版本')
        else:
            self.version.setText(f'当前版本：{conf.read_conf("Other", "version")}\n最新版本：{version}')

    def cf_import_schedule(self):  # 导入课程表
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "Json 配置文件 (*.json)")
        if file_path:
            file_name = file_path.split("/")[-1]
            if list.import_schedule(file_path, file_name):
                alert = MessageBox('您已成功导入课程表配置文件',
                                   '软件将在您确认后关闭，\n'
                                   '您需重新启动以应用您切换的配置文件。', self)
                alert.cancelButton.hide()  # 隐藏取消按钮，必须重启
                alert.buttonLayout.insertStretch(0, 1)
                if alert.exec():
                    sys.exit()
            else:
                print('导入失败！')
                alert = MessageBox('导入失败！',
                                   '课程表文件导入失败！\n'
                                   '可能为格式错误或文件损坏，请检查此文件是否为 Class Widgets 课程表文件。\n'
                                   '详情请查看Log日志，日志位于./log/下。', self)
                alert.cancelButton.hide()  # 隐藏取消按钮
                alert.buttonLayout.insertStretch(0, 1)
                if alert.exec():
                    return 0

    def ct_save_widget_config(self):
        widgets_list = self.findChild(ListWidget, 'widgets_list')
        widget_config = {'widgets': []}
        for i in range(widgets_list.count()):
            widget_config['widgets'].append(list.widget_conf[widgets_list.item(i).text()])
        if conf.save_widget_conf_to_json(widget_config):
            self.ct_update_preview()
            Flyout.create(
                icon=InfoBarIcon.SUCCESS,
                title='保存成功',
                content=f"已保存至 ./config/widget.json",
                target=self.findChild(PrimaryPushButton, 'save_config'),
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )

    def ct_update_preview(self):
        try:
            widgets_preview = self.findChild(QHBoxLayout, 'widgets_preview')
            # 获取配置列表
            widget_config = list.get_widget_config()
            while widgets_preview.count() > 0:  # 清空预览界面
                item = widgets_preview.itemAt(0)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                    widgets_preview.removeItem(item)

            left_spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            widgets_preview.addItem(left_spacer)
            for i in range(len(widget_config)):
                widget_name = widget_config[i]
                if isDarkTheme() and conf.load_theme_config(conf.read_conf("General", "theme"))['support_dark_mode']:
                    path = f'ui/{conf.read_conf("General", "theme")}/dark/preview/{widget_name[:-3]}.png'
                else:
                    path = f'ui/{conf.read_conf("General", "theme")}/preview/{widget_name[:-3]}.png'
                label = QLabel()
                label.setPixmap(QPixmap(path))
                widgets_preview.addWidget(label)
                widget_config[i] = label
            right_spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            widgets_preview.addItem(right_spacer)
        except Exception as e:
            print(f'更新预览界面时发生错误：{e}')
            logger.error(f'更新预览界面时发生错误：{e}')

    def ad_change_file_name(self):
        global filename
        try:
            conf_name = self.findChild(LineEdit, 'conf_name')
            old_name = filename
            new_name = conf_name.text()
            os.rename(f'config/schedule/{old_name}', f'config/schedule/{new_name}.json')  # 重命名
            conf.write_conf('General', 'schedule', f'{new_name}.json')
            filename = new_name + '.json'
            conf_combo = self.findChild(ComboBox, 'conf_combo')
            conf_combo.clear()
            conf_combo.addItems(list.get_schedule_config())
            conf_combo.setCurrentIndex(list.get_schedule_config().index(f'{new_name}.json'))
        except Exception as e:
            print(f'修改课程文件名称时发生错误：{e}')
            logger.error(f'修改课程文件名称时发生错误：{e}')

    def ad_change_file(self):  # 切换课程文件
        try:
            conf_combo = self.findChild(ComboBox, 'conf_combo')
            conf_name = self.findChild(LineEdit, 'conf_name')
            # 添加新课表
            if conf_combo.currentText() == '添加新课表':
                new_name = f'新课表 - {list.return_default_schedule_number() + 1}'
                list.create_new_profile(f'{new_name}.json')
                conf_combo.clear()
                conf_combo.addItems(list.get_schedule_config())
                conf.write_conf('General', 'schedule', f'{new_name}.json')
                conf_combo.setCurrentIndex(list.get_schedule_config().index(conf.read_conf('General', 'schedule')))
                conf_name.setText(new_name)

            elif conf_combo.currentText().endswith('.json'):
                new_name = conf_combo.currentText()
                conf.write_conf('General', 'schedule', new_name)
                conf_name.setText(new_name[:-5])

            else:
                logger.error(f'切换课程文件时列表选择异常：{conf_combo.currentText()}')
                Flyout.create(
                    icon=InfoBarIcon.ERROR,
                    title='错误！',
                    content=f"列表选项异常！{conf_combo.currentText()}",
                    target=conf_combo,
                    parent=self,
                    isClosable=True,
                    aniType=FlyoutAnimationType.PULL_UP
                )
                return

            global filename
            filename = conf.read_conf('General', 'schedule')
            self.te_load_item()
            self.te_upload_list()
            self.se_load_item()
            self.se_upload_list()
            self.sp_fill_grid_row()
        except Exception as e:
            print(f'切换配置文件时发生错误：{e}')
            logger.error(f'切换配置文件时发生错误：{e}')

    def sp_fill_grid_row(self):  # 填充预览表格
        subtitle = self.findChild(SubtitleLabel, 'subtitle_file')
        subtitle.setText(f'预览  -  {filename[:-5]}')
        sp_week_type_combo = self.findChild(ComboBox, 'pre_week_type_combo')
        schedule_view = self.findChild(TableWidget, 'schedule_view')
        schedule_view.setRowCount(sp_get_class_num())
        if sp_week_type_combo.currentIndex() == 1:
            schedule_dict_sp = schedule_even_dict
        else:
            schedule_dict_sp = schedule_dict
        for i in range(len(schedule_dict_sp)):
            for j in range(len(schedule_dict_sp[str(i)])):
                item_text = schedule_dict_sp[str(i)][j].split('-')[0]
                if item_text != '未添加':
                    item = QTableWidgetItem(item_text)
                else:
                    item = QTableWidgetItem('')
                schedule_view.setItem(j, i, item)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # 设置单元格文本居中对齐

    # 加载时间线
    def te_load_item(self):
        global morning_st, afternoon_st, loaded_data, timeline_dict
        loaded_data = conf.load_from_json(filename)
        part = loaded_data.get('part')
        part_name = loaded_data.get('part_name')
        timeline = get_timeline()
        # 找控件
        te_timeline_list = self.findChild(ListWidget, 'timeline_list')
        te_timeline_list.clear()
        part_list = self.findChild(ListWidget, 'part_list')
        part_list.clear()

        for part_num, part_time in part.items():  # 加载节点
            prefix = part_name[part_num]
            time = QTime(int(part_time[0]), int(part_time[1])).toString('h:mm')
            period = time
            text = f'{prefix} - {period}'
            part_list.addItem(text)

        for week, _ in timeline.items():  # 加载节点
            all_line = []
            for item_name, time in timeline[week].items():  # 加载时间线
                prefix = ''
                item_time = f'{timeline[week][item_name]}分钟'
                # 判断前缀和时段
                if item_name.startswith('a'):
                    prefix = '课程'
                elif item_name.startswith('f'):
                    prefix = '课间'
                period = part_name[item_name[1]]

                # 还原 item_text
                item_text = f"{prefix} - {item_time} - {period}"
                all_line.append(item_text)
            timeline_dict[week] = all_line

    # 加载课表
    def se_load_item(self):
        global schedule_dict
        global schedule_even_dict
        global loaded_data
        loaded_data = conf.load_from_json(filename)
        part_name = loaded_data.get('part_name')
        part = loaded_data.get('part')
        schedule = loaded_data.get('schedule')
        schedule_even = loaded_data.get('schedule_even')
        for week, item in schedule.items():
            all_class = []
            count = []  # 初始化计数器
            for i in range(len(part)):
                count.append(0)
            if str(week) in loaded_data['timeline'] and loaded_data['timeline'][str(week)]:
                timeline = get_timeline()[str(week)]
            else:
                timeline = get_timeline()['default']
            for item_name, item_time in timeline.items():
                if item_name.startswith('a'):
                    try:
                        if int(item_name[1]) == 0:
                            count_num = 0
                        else:
                            count_num = sum(count[:int(item_name[1])])

                        prefix = item[int(item_name[-1]) - 1 + count_num]
                        period = part_name[str(item_name[1])]
                        all_class.append(f'{prefix}-{period}')
                    except Exception as e:
                        prefix = '未添加'
                        period = part_name[str(item_name[1])]
                        all_class.append(f'{prefix}-{period}')
                    count[int(item_name[1])] += 1
            schedule_dict[week] = all_class
        for week, item in schedule_even.items():
            all_class = []
            count = []  # 初始化计数器
            for i in range(len(part)):
                count.append(0)
            if str(week) in loaded_data['timeline'] and loaded_data['timeline'][str(week)]:
                timeline = get_timeline()[str(week)]
            else:
                timeline = get_timeline()['default']
            for item_name, item_time in timeline.items():
                if item_name.startswith('a'):
                    try:
                        if int(item_name[1]) == 0:
                            count_num = 0
                        else:
                            count_num = sum(count[:int(item_name[1])])

                        prefix = item[int(item_name[-1]) - 1 + count_num]
                        period = part_name[str(item_name[1])]
                        all_class.append(f'{prefix}-{period}')
                    except Exception as e:
                        prefix = '未添加'
                        period = part_name[str(item_name[1])]
                        all_class.append(f'{prefix}-{period}')
                    count[int(item_name[1])] += 1
            schedule_even_dict[week] = all_class

    def se_copy_odd_schedule(self):
        logger.info('复制单周课表')
        global schedule_dict, schedule_even_dict
        schedule_even_dict = deepcopy(schedule_dict)
        self.se_upload_list()

    def te_upload_list(self):  # 更新时间线到列表组件
        logger.info('更新列表：时间线编辑')
        te_timeline_list = self.findChild(ListWidget, 'timeline_list')
        te_select_timeline = self.findChild(ComboBox, 'select_timeline')
        try:
            if te_select_timeline.currentIndex() == 0:
                te_timeline_list.clear()
                te_timeline_list.addItems(timeline_dict['default'])
            else:
                te_timeline_list.clear()
                te_timeline_list.addItems(timeline_dict[str(te_select_timeline.currentIndex() - 1)])
            self.te_detect_item()
        except Exception as e:
            print(f'加载时间线时发生错误：{e}')

    # 上传课表到列表组件
    def se_upload_list(self):  # 更新课表到列表组件
        logger.info('更新列表：课程表编辑')
        se_schedule_list = self.findChild(ListWidget, 'schedule_list')
        se_schedule_list.clearSelection()
        se_week_combo = self.findChild(ComboBox, 'week_combo')
        se_week_type_combo = self.findChild(ComboBox, 'week_type_combo')
        se_copy_schedule_button = self.findChild(PushButton, 'copy_schedule')
        global current_week
        try:
            if se_week_type_combo.currentIndex() == 1:
                se_copy_schedule_button.show()
                current_week = se_week_combo.currentIndex()
                se_schedule_list.clear()
                se_schedule_list.addItems(schedule_even_dict[str(current_week)])
            else:
                se_copy_schedule_button.hide()
                current_week = se_week_combo.currentIndex()
                se_schedule_list.clear()
                se_schedule_list.addItems(schedule_dict[str(current_week)])
        except Exception as e:
            print(f'加载课表时发生错误：{e}')

    def se_upload_item(self):  # 保存列表内容到课表文件
        se_schedule_list = self.findChild(ListWidget, 'schedule_list')
        se_week_type_combo = self.findChild(ComboBox, 'week_type_combo')
        if se_week_type_combo.currentIndex() == 1:
            global schedule_even_dict
            try:
                cache_list = []
                for i in range(se_schedule_list.count()):
                    item_text = se_schedule_list.item(i).text()
                    cache_list.append(item_text)
                schedule_even_dict[str(current_week)][:] = cache_list
            except Exception as e:
                print(f'加载双周课表时发生错误：{e}')
        else:
            global schedule_dict
            cache_list = []
            for i in range(se_schedule_list.count()):
                item_text = se_schedule_list.item(i).text()
                cache_list.append(item_text)
            schedule_dict[str(current_week)][:] = cache_list

    # 保存课表
    def se_save_item(self):
        try:
            data_dict = deepcopy(schedule_dict)
            data_dict_even = deepcopy(schedule_even_dict)  # 单双周保存
            for week, item in data_dict.items():
                cache_list = item
                replace_list = []
                for activity_num in range(len(cache_list)):
                    item_info = cache_list[int(activity_num)].split('-')
                    replace_list.append(item_info[0])
                data_dict[str(week)] = replace_list
            for week, item in data_dict_even.items():
                cache_list = item
                replace_list = []
                for activity_num in range(len(cache_list)):
                    item_info = cache_list[int(activity_num)].split('-')
                    replace_list.append(item_info[0])
                data_dict_even[str(week)] = replace_list
            # 写入
            data_dict_even = {"schedule_even": data_dict_even}
            conf.save_data_to_json(data_dict_even, filename)
            data_dict = {"schedule": data_dict}
            conf.save_data_to_json(data_dict, filename)
            Flyout.create(
                icon=InfoBarIcon.SUCCESS,
                title='保存成功',
                content=f"已保存至 ./config/schedule/{filename}",
                target=self.findChild(PrimaryPushButton, 'save_schedule'),
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            self.sp_fill_grid_row()
        except Exception as e:
            logger.error(f'保存课表时发生错误: {e}')

    def te_upload_item(self):  # 上传时间线到列表组件
        te_timeline_list = self.findChild(ListWidget, 'timeline_list')
        te_select_timeline = self.findChild(ComboBox, 'select_timeline')
        global timeline_dict
        cache_list = []
        for i in range(te_timeline_list.count()):
            item_text = te_timeline_list.item(i).text()
            cache_list.append(item_text)
        if te_select_timeline.currentIndex() == 0:
            timeline_dict['default'] = cache_list
        else:
            timeline_dict[str(te_select_timeline.currentIndex() - 1)] = cache_list

    # 保存时间线
    def te_save_item(self):
        te_part_list = self.findChild(ListWidget, 'part_list')
        data_dict = {"part": {}, "part_name": {}, "timeline": {'default': {}, **{str(w): {} for w in range(7)}}}
        data_timeline_dict = deepcopy(timeline_dict)
        # 逐条把列表里的信息整理保存
        for i in range(te_part_list.count()):
            item_text = te_part_list.item(i).text()
            item_info = item_text.split(' - ')
            time_tostring = item_info[1].split(':')
            data_dict['part'][str(i)] = [int(time_tostring[0]), int(time_tostring[1])]
            data_dict['part_name'][str(i)] = item_info[0]

        try:
            for week, _ in data_timeline_dict.items():
                counter = []  # 初始化计数器
                for i in range(len(data_dict['part'])):
                    counter.append(0)
                counter_key = 0
                lesson_num = 0
                for i in range(len(data_timeline_dict[week])):
                    item_text = data_timeline_dict[week][i]
                    item_info = item_text.split(' - ')
                    item_name = ''
                    if item_info[0] == '课程':
                        item_name += 'a'
                        lesson_num += 1
                    if item_info[0] == '课间':
                        item_name += 'f'

                    for key, value in data_dict['part_name'].items():  # 节点计数
                        if value == item_info[2]:
                            item_name += str(key)  # +节点序数
                            counter_key = int(key)  # 记录节点序数
                            break

                    if item_name.startswith('a'):
                        counter[counter_key] += 1

                    item_name += str(lesson_num - sum(counter[:counter_key]))  # 课程序数
                    item_time = item_info[1][0:len(item_info[1]) - 2]
                    data_dict['timeline'][str(week)][item_name] = item_time

            conf.save_data_to_json(data_dict, filename)
            self.te_detect_item()
            self.se_load_item()
            self.se_upload_list()
            self.se_upload_item()
            self.te_upload_item()
            self.sp_fill_grid_row()
            Flyout.create(
                icon=InfoBarIcon.SUCCESS,
                title='保存成功',
                content=f"已保存至 ./config/schedule/{filename}",
                target=self.findChild(PrimaryPushButton, 'save'),
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
        except Exception as e:
            logger.error(f'保存时间线时发生错误: {e}')
            Flyout.create(
                icon=InfoBarIcon.ERROR,
                title='保存失败!',
                content=f"{e}\n保存失败，请将 ./log/ 中的日志提交给开发者以反馈问题。",
                target=self.findChild(PrimaryPushButton, 'save'),
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )

    def te_sync_time(self):
        te_class_activity_combo = self.findChild(ComboBox, 'class_activity')
        spin_time = self.findChild(SpinBox, 'spin_time')
        if te_class_activity_combo.currentIndex() == 0:
            spin_time.setValue(40)
        if te_class_activity_combo.currentIndex() == 1:
            spin_time.setValue(10)

    def te_detect_item(self):
        timeline_list = self.findChild(ListWidget, 'timeline_list')
        part_list = self.findChild(ListWidget, 'part_list')
        tips = self.findChild(CaptionLabel, 'tips_2')
        tips_part = self.findChild(CaptionLabel, 'tips_1')
        # self.se_load_item()
        if part_list.count() > 0:
            tips_part.hide()
        else:
            tips_part.show()
        if timeline_list.count() > 0:
            tips.hide()
        else:
            tips.show()

    def te_add_item(self):
        te_timeline_list = self.findChild(ListWidget, 'timeline_list')
        class_activity = self.findChild(ComboBox, 'class_activity')
        spin_time = self.findChild(SpinBox, 'spin_time')
        time_period = self.findChild(ComboBox, 'time_period')
        if time_period.currentText() == "":  # 时间段不能为空 修复 #184
            Flyout.create(
                icon=InfoBarIcon.WARNING,
                title='无法添加时间线 o(TヘTo)',
                content='在添加时间线前，先任意添加一个节点',
                target=self.findChild(ToolButton, 'add_button'),
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
            return  # 时间段不能为空
        te_timeline_list.addItem(
            f'{class_activity.currentText()} - {spin_time.value()}分钟 - {time_period.currentText()}'
        )
        self.te_detect_item()

    def te_add_part(self):
        te_part_list = self.findChild(ListWidget, 'part_list')
        te_name_part = self.findChild(EditableComboBox, 'name_part_combo')
        te_part_time = self.findChild(TimeEdit, 'part_time')
        if te_part_list.count() < 10:
            te_part_list.addItem(
                f'{te_name_part.currentText()} - {te_part_time.time().toString("h:mm")}'
            )
        else:  # 最多只能添加9个节点
            Flyout.create(
                icon=InfoBarIcon.WARNING,
                title='没办法继续添加了 o(TヘTo)',
                content='Class Widgets 最多只能添加10个“节点”！',
                target=self.findChild(ToolButton, 'add_part_button'),
                parent=self,
                isClosable=True,
                aniType=FlyoutAnimationType.PULL_UP
            )
        self.te_detect_item()
        self.te_detect_part()

    def te_delete_part(self):
        alert = MessageBox("您确定要删除这个时段吗？", "删除该节点后，将一并删除该节点下所有课程安排，且无法恢复。", self)
        alert.yesButton.setText('删除')
        alert.yesButton.setStyleSheet("""
        PushButton{
            border-radius: 5px;
            padding: 5px 12px 6px 12px;
            outline: none;
        }
        PrimaryPushButton{
            color: white;
            background-color: #FF6167;
            border: 1px solid #FF8585;
            border-bottom: 1px solid #943333;
        }
        PrimaryPushButton:hover{
            background-color: #FF7E83;
            border: 1px solid #FF8084;
            border-bottom: 1px solid #B13939;
        }
        PrimaryPushButton:pressed{
            color: rgba(255, 255, 255, 0.63);
            background-color: #DB5359;
            border: 1px solid #DB5359;
        }
    """)
        alert.cancelButton.setText('取消')
        if alert.exec():
            global timeline_dict, schedule_dict
            te_part_list = self.findChild(ListWidget, 'part_list')
            selected_items = te_part_list.selectedItems()
            deleted_part_name = selected_items[0].text().split(' - ')[0]
            for item in selected_items:
                te_part_list.takeItem(te_part_list.row(item))

            # 修复了删除时段没能同步删除时间线的Bug #123
            for day in timeline_dict:  # 删除时间线
                count = 0
                break_count = 0
                delete_schedule_list = []
                delete_schedule_even_list = []
                delete_part_list = []
                for i in range(len(timeline_dict[day])):
                    act = timeline_dict[day][i]
                    count += 1
                    item_info = act.split(' - ')

                    if item_info[0] == '课间':
                        break_count += 1

                    if item_info[2] == deleted_part_name:
                        delete_part_list.append(act)
                        if item_info[0] != '课间':
                            if day != 'default':
                                delete_schedule_list.append(schedule_dict[day][count - break_count - 1])
                                delete_schedule_even_list.append(schedule_even_dict[day][count - break_count - 1])
                            else:
                                for j in range(7):
                                    try:
                                        for item in schedule_dict[str(j)]:
                                            if item.split('-')[1] == deleted_part_name:
                                                delete_schedule_list.append(
                                                    schedule_dict[str(j)][count - break_count - 1])
                                        for item in schedule_even_dict[str(j)]:
                                            if item.split('-')[1] == deleted_part_name:
                                                delete_schedule_even_list.append(
                                                    schedule_dict[str(j)][count - break_count - 1])
                                    except Exception as e:
                                        logger.warning(f'删除时段时发生错误：{e}')

                for item in delete_part_list:  # 删除时间线
                    timeline_dict[day].remove(item)
                if day != 'default':  # 删除课表
                    for item in delete_schedule_list:
                        schedule_dict[day].remove(item)

            for day in range(7):  # 删除默认课程表
                delete_schedule_list = []
                delete_schedule_even_list = []
                for item in schedule_dict[str(day)]:  # 单周
                    if item.split('-')[1] == deleted_part_name:
                        delete_schedule_list.append(item)
                for item in delete_schedule_list:
                    schedule_dict[str(day)].remove(item)

                for item in schedule_even_dict[str(day)]:  # 双周
                    if item.split('-')[1] == deleted_part_name:
                        delete_schedule_even_list.append(item)
                for item in delete_schedule_even_list:
                    schedule_even_dict[str(day)].remove(item)

            self.te_upload_list()
            self.se_upload_list()
            self.te_detect_part()
        else:
            return

    def te_detect_part(self):
        rl = []
        te_time_combo = self.findChild(ComboBox, 'time_period')  # 时段
        te_time_combo.clear()
        part_list = self.findChild(ListWidget, 'part_list')
        for i in range(part_list.count()):
            info = part_list.item(i).text().split(' - ')
            rl.append(info[0])
        te_time_combo.addItems(rl)

    def te_edit_item(self):
        te_timeline_list = self.findChild(ListWidget, 'timeline_list')
        class_activity = self.findChild(ComboBox, 'class_activity')
        spin_time = self.findChild(SpinBox, 'spin_time')
        time_period = self.findChild(ComboBox, 'time_period')
        selected_items = te_timeline_list.selectedItems()

        if selected_items:
            selected_item = selected_items[0]  # 取第一个选中的项目
            selected_item.setText(
                f'{class_activity.currentText()} - {spin_time.value()}分钟 - {time_period.currentText()}'
            )

    def se_edit_item(self):
        se_schedule_list = self.findChild(ListWidget, 'schedule_list')
        se_class_combo = self.findChild(ComboBox, 'class_combo')
        se_custom_class_text = self.findChild(LineEdit, 'custom_class')
        selected_items = se_schedule_list.selectedItems()

        if selected_items:
            selected_item = selected_items[0]
            name_list = selected_item.text().split('-')
            if se_class_combo.currentIndex() != 0:
                selected_item.setText(
                    f'{se_class_combo.currentText()}-{name_list[1]}'
                )
            else:
                if se_custom_class_text.text() != '':
                    selected_item.setText(
                        f'{se_custom_class_text.text()}-{name_list[1]}'
                    )
                    se_class_combo.addItem(se_custom_class_text.text())

    def se_quick_set_schedule(self):  # 快速设置课表
        se_schedule_list = self.findChild(ListWidget, 'schedule_list')
        quick_set_schedule = self.findChild(ListWidget, 'subject_list')
        selected_items = se_schedule_list.selectedItems()
        selected_subject = quick_set_schedule.currentItem().text()
        if se_schedule_list.count() > 0:
            if not selected_items:
                se_schedule_list.setCurrentRow(0)

            selected_row = se_schedule_list.currentRow()
            selected_item = se_schedule_list.item(selected_row)
            name_list = selected_item.text().split('-')
            selected_item.setText(
                f'{selected_subject}-{name_list[1]}'
            )

            if se_schedule_list.count() > selected_row + 1:  # 选择下一行
                se_schedule_list.setCurrentRow(selected_row + 1)

    def se_quick_select_week(self):  # 快速选择周
        se_week_combo = self.findChild(ComboBox, 'week_combo')
        if se_week_combo.currentIndex() != 6:
            se_week_combo.setCurrentIndex(se_week_combo.currentIndex() + 1)

    def te_delete_item(self):
        te_timeline_list = self.findChild(ListWidget, 'timeline_list')
        selected_items = te_timeline_list.selectedItems()
        for item in selected_items:
            te_timeline_list.takeItem(te_timeline_list.row(item))
        self.te_detect_item()

    def se_delete_item(self):
        se_schedule_list = self.findChild(ListWidget, 'schedule_list')
        selected_items = se_schedule_list.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            name_list = selected_item.text().split('-')
            selected_item.setText(
                f'未添加-{name_list[1]}'
            )

    def m_start_time_changed(self):
        global morning_st
        te_m_start_time = self.findChild(TimeEdit, 'morningStartTime')
        unformatted_time = te_m_start_time.time()
        h = unformatted_time.hour()
        m = unformatted_time.minute()
        morning_st = (h, m)

    def a_start_time_changed(self):
        global afternoon_st
        te_m_start_time = self.findChild(TimeEdit, 'afternoonStartTime')
        unformatted_time = te_m_start_time.time()
        h = unformatted_time.hour()
        m = unformatted_time.minute()
        afternoon_st = (h, m)

    def init_nav(self):
        self.addSubInterface(self.spInterface, fIcon.HOME, '课表预览')
        self.addSubInterface(self.teInterface, fIcon.DATE_TIME, '时间线编辑')
        self.addSubInterface(self.seInterface, fIcon.EDUCATION, '课程表编辑')
        self.addSubInterface(self.cfInterface, fIcon.FOLDER, '配置文件')
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.hdInterface, fIcon.QUESTION, '帮助')
        self.addSubInterface(self.plInterface, fIcon.APPLICATION, '插件', NavigationItemPosition.BOTTOM)
        self.navigationInterface.addSeparator(NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.ctInterface, fIcon.BRUSH, '自定义', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.sdInterface, fIcon.RINGER, '提醒', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.adInterface, fIcon.SETTING, '高级选项', NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.ifInterface, fIcon.INFO, '关于本产品', NavigationItemPosition.BOTTOM)

    def init_window(self):
        self.stackedWidget.setCurrentIndex(0)  # 设置初始页面
        self.load_all_item()
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        self.navigationInterface.setExpandWidth(250)
        self.navigationInterface.setCollapsible(False)
        self.setMicaEffectEnabled(True)

        # 修复设置窗口在各个屏幕分辨率DPI下的窗口大小
        screen_geometry = QApplication.primaryScreen().geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        width = int(screen_width * 0.6)
        height = int(screen_height * 0.7)

        self.move(int(screen_width / 2 - width / 2), 150)
        self.resize(width, height)

        self.setWindowTitle('Class Widgets - 设置')
        self.setWindowIcon(QIcon('img/logo/favicon-settings.ico'))

        self.init_font()  # 设置字体

    def closeEvent(self, event):
        event.ignore()
        self.deleteLater()
        self.hide()


def sp_get_class_num():  # 获取当前周课程数（未完成）
    timeline = get_timeline()['default']
    count = 0
    for item_name, item_time in timeline.items():
        if item_name.startswith('a'):
            count += 1
    return count


if __name__ == '__main__':
    app = QApplication(sys.argv)
    settings = SettingsMenu()
    settings.show()
    # settings.setMicaEffectEnabled(True)
    sys.exit(app.exec())
