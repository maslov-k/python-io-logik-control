import sys
import os
import traceback
import datetime
import time
import re
import threading
import psutil
from numpy import arange

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QSettings, QCoreApplication, QSize, QThread, pyqtSignal
from pyModbusTCP.client import ModbusClient

import main_window_gui
import change_ip_gui
import settings_gui
import about_gui
import instruction_gui
import stylesheets


QCoreApplication.setOrganizationName('Maslov')
QCoreApplication.setApplicationName('ioLogikControl')
QCoreApplication.setOrganizationDomain('ksmaslov@mail.ru')

N_SET = 0

SETTINGS = QSettings()
IP = [SETTINGS.value('IP_1', '192.168.10.84', str), SETTINGS.value('IP_2', '192.168.10.85', str)]
THRU_LOSS = [SETTINGS.value('thru_loss_1', 4.5, float), SETTINGS.value('thru_loss_2', 4.5, float)]
LOGGING = bool(SETTINGS.value('logging', False, bool))
STYLE = SETTINGS.value('style', 'Dark Orange', str)


LOCK = threading.Lock()


def logging(text):
    if LOGGING:
        date_time = datetime.datetime.now()
        date = date_time.strftime('%Y%m%d')
        date_time = date_time.strftime(f'%d.%m.%Y %H:%M:%S.{str(date_time.microsecond // 1000).rjust(3, "0")}')
        with open(os.path.join('ioLogik_logs', f'{date}.txt'), 'a') as log_file:
            log_file.write(f'[{date_time}] - {text}\n')


def check_logging_dir():
    os.makedirs('ioLogik_logs', exist_ok=True)


if LOGGING:
    check_logging_dir()


def log_uncaught_exceptions(ex_cls, ex, tb):
    error = f'{ex_cls.__name__}: {ex}:\n'
    error += ''.join(traceback.format_tb(tb))
    print(error)
    logging(error)
    QtWidgets.QMessageBox.critical(None, 'Error', f'Непредвиденная ошибка!\n\n{error}')
    sys.exit()


sys.excepthook = log_uncaught_exceptions


def check_duplicates():
    # names = [i.info['name'] for i in psutil.process_iter(['name'])]
    # name = psutil.Process().name()
    # if name in names:
    #     print('Программа уже запущена')

    global SETTINGS
    old_pid = SETTINGS.value('pid', 0, int)
    if old_pid != 0 and psutil.pid_exists(old_pid):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setWindowTitle('Внимание!')
        msg.setText('Программа уже запущена. Запуск двух копий запрещен!')
        msg.addButton('OK', QtWidgets.QMessageBox.AcceptRole)
        sys.exit(msg.exec())

    SETTINGS.setValue('pid', os.getpid())


def memory_control():
    while True:
        time.sleep(600)
        mem_info = psutil.Process().memory_info()
        logging(f'Используется памяти: {mem_info[0]}({mem_info[3]}) байт')


class IoLogikControl(QtWidgets.QMainWindow):
    def __init__(self):
        super(IoLogikControl, self).__init__()

        self.ui = main_window_gui.Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowFlags(Qt.CustomizeWindowHint |
                            Qt.WindowCloseButtonHint |
                            Qt.WindowMinimizeButtonHint)
        # self.setWindowFlags(Qt.FramelessWindowHint)

        for item in arange(THRU_LOSS[0], 32 + THRU_LOSS[0], 0.5):
            self.ui.comboBox_1.addItem(f'{str(item)} дБ', item)
        for item in arange(THRU_LOSS[1], 32 + THRU_LOSS[1], 0.5):
            self.ui.comboBox_2.addItem(f'{str(item)} дБ', item)
        self.ui.pushButton_def_1.setText(f'По умолчанию: {THRU_LOSS[0]} дБ')
        self.ui.pushButton_def_2.setText(f'По умолчанию: {THRU_LOSS[1]} дБ')

        self.cb_color = 'black'

        self.ui.pushButton_minus_1.clicked.connect(lambda: self.att_plus_minus(1, -1))
        self.ui.pushButton_plus_1.clicked.connect(lambda: self.att_plus_minus(1, 1))
        self.ui.pushButton_minus_2.clicked.connect(lambda: self.att_plus_minus(2, -1))
        self.ui.pushButton_plus_2.clicked.connect(lambda: self.att_plus_minus(2, 1))

        self.ui.pushButton_minus_1.setIcon(QtGui.QIcon(':/icons/icons/minus.png'))
        self.ui.pushButton_minus_2.setIcon(QtGui.QIcon(':/icons/icons/minus.png'))
        self.ui.pushButton_plus_1.setIcon(QtGui.QIcon(':/icons/icons/plus.png'))
        self.ui.pushButton_plus_2.setIcon(QtGui.QIcon(':/icons/icons/plus.png'))

        self.ui.pushButton_minus_1.pressed.connect(lambda: self.ui.pushButton_minus_1.setIconSize(QSize(16, 16)))
        self.ui.pushButton_minus_1.released.connect(lambda: self.ui.pushButton_minus_1.setIconSize(QSize(18, 18)))
        self.ui.pushButton_minus_2.pressed.connect(lambda: self.ui.pushButton_minus_2.setIconSize(QSize(16, 16)))
        self.ui.pushButton_minus_2.released.connect(lambda: self.ui.pushButton_minus_2.setIconSize(QSize(18, 18)))
        self.ui.pushButton_plus_1.pressed.connect(lambda: self.ui.pushButton_plus_1.setIconSize(QSize(16, 16)))
        self.ui.pushButton_plus_1.released.connect(lambda: self.ui.pushButton_plus_1.setIconSize(QSize(18, 18)))
        self.ui.pushButton_plus_2.pressed.connect(lambda: self.ui.pushButton_plus_2.setIconSize(QSize(16, 16)))
        self.ui.pushButton_plus_2.released.connect(lambda: self.ui.pushButton_plus_2.setIconSize(QSize(18, 18)))

        self.set_current_att_1 = SetAttenuation(target=self.set_att, args=[1, 'current'])
        self.set_current_att_2 = SetAttenuation(target=self.set_att, args=[2, 'current'])
        self.to_default_att_1 = SetAttenuation(target=self.set_att, args=[1, 'to_default'])
        self.to_default_att_2 = SetAttenuation(target=self.set_att, args=[2, 'to_default'])
        self.set_default_att_1 = SetAttenuation(target=self.set_att, args=[1, 'set_default'])
        self.set_default_att_2 = SetAttenuation(target=self.set_att, args=[2, 'set_default'])

        self.ui.comboBox_1.currentIndexChanged.connect(self.set_current_att_1.start)
        self.ui.comboBox_2.currentIndexChanged.connect(self.set_current_att_2.start)
        self.ui.pushButton_def_1.clicked.connect(self.to_default_att_1.start)
        self.ui.pushButton_def_2.clicked.connect(self.to_default_att_2.start)
        self.ui.pushButton_set_def_1.clicked.connect(self.set_default_att_1.start)
        self.ui.pushButton_set_def_2.clicked.connect(self.set_default_att_2.start)

        self.ui.pushButton_ip_1.clicked.connect(lambda: self.change_ip(1))
        self.ui.pushButton_ip_2.clicked.connect(lambda: self.change_ip(2))

        self.app_about = AboutWidget()
        self.app_instruction = InstructionWidget()

        self.app_change_ip = ChangeIP()
        self.app_change_ip.ui.pushButton_OK.clicked.connect(self.set_ip)

        self.app_settings = SettingsWidget()
        self.app_settings.ui.lineEdit_ip_1.setText(IP[0])
        self.app_settings.ui.lineEdit_ip_2.setText(IP[1])
        self.app_settings.ui.lineEdit_tl_1.setText(str(THRU_LOSS[0]))
        self.app_settings.ui.lineEdit_tl_2.setText(str(THRU_LOSS[1]))
        self.app_settings.ui.checkBox_logs.setChecked(LOGGING)
        self.app_settings.ui.pushButton_cancel.clicked.connect(self.app_settings.close)
        self.app_settings.ui.pushButton_save.clicked.connect(self.set_settings)

        self.app_settings.ui.comboBox_style.addItems(['Classic', 'Dark Orange'])
        self.app_settings.ui.comboBox_style.currentIndexChanged.connect(self.change_style)
        self.app_settings.ui.comboBox_style.setCurrentText(STYLE)

        self.change_style()

        self.ui.action_settings.triggered.connect(self.app_settings.show)
        self.ui.action_exit.triggered.connect(self.close)
        self.ui.action_about.triggered.connect(self.app_about.show)
        self.ui.action_instruction.triggered.connect(self.app_instruction.show)

        self.ui.pushButton_ip_1.setText(f'         IP: {IP[0]}    ')
        self.ui.pushButton_ip_2.setText(f'         IP: {IP[1]}    ')

        self.status = [0, 0]
        self.coils = [[], []]

        self.connection_1 = ConnectionThread(1)
        self.connection_2 = ConnectionThread(2)
        self.connection_1.signal_connect.connect(self.connection_resp)
        self.connection_2.signal_connect.connect(self.connection_resp)
        self.connection_1.start()
        self.connection_2.start()

        threading.Thread(target=memory_control, daemon=True).start()

    def closeEvent(self, event):
        SETTINGS.setValue('pid', 0)

        logging('Работа программы завершена.')

    def change_style(self):
        global STYLE
        style = self.app_settings.ui.comboBox_style.currentText()
        STYLE = style
        if style == 'Dark Orange':
            self.setStyleSheet(stylesheets.dark_orange_stylesheet)
            self.cb_color = '#b1b1b1'
            self.ui.pushButton_minus_1.setIcon(QtGui.QIcon(':/icons/icons/minus.png'))
            self.ui.pushButton_minus_2.setIcon(QtGui.QIcon(':/icons/icons/minus.png'))
            self.ui.pushButton_plus_1.setIcon(QtGui.QIcon(':/icons/icons/plus.png'))
            self.ui.pushButton_plus_2.setIcon(QtGui.QIcon(':/icons/icons/plus.png'))

            self.app_settings.setStyleSheet(stylesheets.dark_orange_stylesheet + 'QWidget {font-size: 10pt;}')

            self.app_change_ip.setStyleSheet(stylesheets.dark_orange_stylesheet + 'QWidget {font-size: 10pt;}')

            self.app_about.setStyleSheet(stylesheets.dark_orange_stylesheet + 'QWidget {font-size: 12pt;}')

            self.app_instruction.setStyleSheet(stylesheets.dark_orange_stylesheet + 'QWidget {font-size: 10pt;}')
            self.app_instruction.ui.label.setStyleSheet('font-size: 12pt')

        elif style == 'Classic':
            self.setStyleSheet('')
            self.cb_color = 'black'
            self.ui.pushButton_minus_1.setIcon(QtGui.QIcon(':/icons/icons/minus_black.png'))
            self.ui.pushButton_minus_2.setIcon(QtGui.QIcon(':/icons/icons/minus_black.png'))
            self.ui.pushButton_plus_1.setIcon(QtGui.QIcon(':/icons/icons/plus_black.png'))
            self.ui.pushButton_plus_2.setIcon(QtGui.QIcon(':/icons/icons/plus_black.png'))

            self.app_settings.setStyleSheet('QWidget {font-size: 10pt;}')

            self.app_change_ip.setStyleSheet('QWidget {font-size: 10pt;}')

            self.app_about.setStyleSheet('QWidget {font-size: 12pt;}')

            self.app_instruction.setStyleSheet('QWidget {font-size: 10pt;}')
            self.app_instruction.ui.label.setStyleSheet('font-size: 12pt')

    def change_icon_size(self, button, size):
        button.setIconSize(QSize(size, size))

    def connection_resp(self, n, status, coils_int, checkback):
        pushButtons_def = [self.ui.pushButton_def_1, self.ui.pushButton_def_2]
        pushButtons_ip = [self.ui.pushButton_ip_1, self.ui.pushButton_ip_2]
        comboBoxes = [self.ui.comboBox_1, self.ui.comboBox_2]
        icons = [QtGui.QIcon(':/icons/icons/led_red.png'), QtGui.QIcon(':/icons/icons/led_green.png')]
        con_log = ['потеряно', 'установлено']
        styles = ['QComboBox {color: red}', 'QComboBox {color: ' + self.cb_color + '}']

        comboBoxes[n - 1].setStyleSheet(styles[checkback])

        if status != self.status[n - 1]:
            self.status[n - 1] = status
            pushButtons_ip[n - 1].setIcon(icons[status])
            if status:
                self.coils[n - 1] = coils_int
                att_current = abs(int(''.join(map(str, reversed(coils_int[0:6]))), 2) - 63) / 2
                att_default = abs(int(''.join(map(str, reversed(coils_int[6:]))), 2) - 63) / 2
                if comboBoxes[n - 1].currentData() != att_current + THRU_LOSS[n - 1]:
                    comboBoxes[n - 1].setCurrentText(f'{att_current + THRU_LOSS[n - 1]} дБ')
                    pushButtons_def[n - 1].setText(f'По умолчанию: {att_default + THRU_LOSS[n - 1]} дБ')

            logging(f'[{n}К] Соединение {con_log[status]} (IP: {IP[n - 1]}).')

    def set_att(self, n, mode):
        with LOCK:
            global IP
            host = [IP[0], IP[1]]
            comboBoxes = [self.ui.comboBox_1, self.ui.comboBox_2]
            pushButtons_def = [self.ui.pushButton_def_1, self.ui.pushButton_def_2]

            att_pattern = r'[\d|\.]{3,4}'
            att_def = float(re.findall(att_pattern, pushButtons_def[n - 1].text())[0])
            att = comboBoxes[n - 1].currentData()

            if self.status[n - 1]:
                if mode == 'current':
                    coils = list(map(int, list(f'{63 - int((att - THRU_LOSS[n - 1]) * 2):06b}'[::-1])))
                    c = ModbusClient(host=host[n - 1], auto_open=True, auto_close=True, timeout=1)
                    c.write_multiple_coils(0, coils)

                    logging(f'[{n}К] Задано ослабление {att} дБ.')
                elif mode == 'to_default':
                    comboBoxes[n - 1].setCurrentText(f'{att_def} дБ')
                elif mode == 'set_default':
                    coils = list(map(int, list(f'{63 - int((att - THRU_LOSS[n - 1]) * 2):06b}'[::-1])))
                    c = ModbusClient(host=host[n - 1], auto_open=True, auto_close=True, timeout=1)
                    pushButtons_def[n - 1].setText(f'По умолчанию: {att} дБ')
                    c.write_multiple_coils(6, coils)

                    logging(f'[{n}К] Задано ослабление по умолчанию {att} дБ.')

    def att_plus_minus(self, n, step):
        buttons = [self.ui.comboBox_1, self.ui.comboBox_2]
        next_index = buttons[n - 1].currentIndex() + step
        if next_index in range(0, 64):
            buttons[n - 1].setCurrentIndex(next_index)

    def change_ip(self, n):
        global N_SET
        N_SET = n
        self.app_change_ip.ui.label_set.setText(f'{n} комплект')
        ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        pushButtons_ip = [self.ui.pushButton_ip_1, self.ui.pushButton_ip_2]
        ip = re.findall(ip_pattern, pushButtons_ip[n - 1].text())[0]
        self.app_change_ip.ui.lineEdit_ip.setText(ip)
        self.app_change_ip.show()

    def set_ip(self):
        global N_SET
        try:
            ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
            ip = re.fullmatch(ip_pattern, self.app_change_ip.ui.lineEdit_ip.text()).string
        except AttributeError:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Информация')
            msg.setText('Неверный формат IP-адреса')
            msg.addButton('OK', QtWidgets.QMessageBox.AcceptRole)
            msg.exec()
            return

        IP[N_SET - 1] = ip

        logging(f'[{N_SET}К] Задан IP-адрес: {ip}.')

        pushButtons_ip = [self.ui.pushButton_ip_1, self.ui.pushButton_ip_2]
        pushButtons_ip[N_SET - 1].setText(f'         IP: {ip}    ')
        lineEdits_settings = [self.app_settings.ui.lineEdit_ip_1, self.app_settings.ui.lineEdit_ip_2]
        lineEdits_settings[N_SET - 1].setText(ip)

        self.app_change_ip.close()
        self.save_settings()

    def set_settings(self):
        global IP, THRU_LOSS, LOGGING
        try:
            ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
            IP[0] = re.fullmatch(ip_pattern, self.app_settings.ui.lineEdit_ip_1.text()).string
            IP[1] = re.fullmatch(ip_pattern, self.app_settings.ui.lineEdit_ip_2.text()).string

            self.ui.pushButton_ip_1.setText(f'         IP: {IP[0]}    ')
            self.ui.pushButton_ip_2.setText(f'         IP: {IP[1]}    ')
        except AttributeError:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Информация')
            msg.setText('Неверный формат IP-адреса')
            msg.addButton('OK', QtWidgets.QMessageBox.AcceptRole)
            msg.exec()
            return
        try:
            att_pattern = r'[\d|\.]{3,4}'
            att_def_1 = float(re.findall(att_pattern, self.ui.pushButton_def_1.text())[0]) - THRU_LOSS[0]
            att_def_2 = float(re.findall(att_pattern, self.ui.pushButton_def_2.text())[0]) - THRU_LOSS[1]
            THRU_LOSS[0] = float(self.app_settings.ui.lineEdit_tl_1.text())
            THRU_LOSS[1] = float(self.app_settings.ui.lineEdit_tl_2.text())
            self.ui.pushButton_def_1.setText(f'По умолчанию: {att_def_1 + THRU_LOSS[0]} дБ')
            self.ui.pushButton_def_2.setText(f'По умолчанию: {att_def_2 + THRU_LOSS[1]} дБ')

            for i in range(self.ui.comboBox_1.count()):
                self.ui.comboBox_1.setItemText(i, f'{str(i / 2 + THRU_LOSS[0])} дБ')
                self.ui.comboBox_1.setItemData(i, i / 2 + THRU_LOSS[0])
                self.ui.comboBox_2.setItemText(i, f'{str(i / 2 + THRU_LOSS[1])} дБ')
                self.ui.comboBox_2.setItemData(i, i / 2 + THRU_LOSS[1])

            LOGGING = self.app_settings.ui.checkBox_logs.isChecked()
            if LOGGING:
                check_logging_dir()
        except ValueError:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle('Информация')
            msg.setText('Неверный формат затухания')
            msg.addButton('OK', QtWidgets.QMessageBox.AcceptRole)
            msg.exec()
            return

        self.app_settings.close()
        self.save_settings()

    def save_settings(self):
        SETTINGS.setValue('IP_1', IP[0])
        SETTINGS.setValue('IP_2', IP[1])
        SETTINGS.setValue('logging', LOGGING)
        SETTINGS.setValue('thru_loss_1', THRU_LOSS[0])
        SETTINGS.setValue('thru_loss_2', THRU_LOSS[1])
        SETTINGS.setValue('style', STYLE)


class ChangeIP(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.ui = change_ip_gui.Ui_Form()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.ApplicationModal)

        self.ui.pushButton_OK.setShortcut(Qt.Key_Return)
        self.ui.pushButton_cancel.setShortcut(Qt.Key_Escape)


class SettingsWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.ui = settings_gui.Ui_Form()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.ApplicationModal)


class AboutWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.ui = about_gui.Ui_Form()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.ApplicationModal)


class InstructionWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.ui = instruction_gui.Ui_Form()
        self.ui.setupUi(self)
        self.setWindowModality(Qt.ApplicationModal)


class ConnectionThread(QThread):
    signal_connect = pyqtSignal(int, int, list, int)

    def __init__(self, n):
        super().__init__()
        self.n = n

    def run(self):
        while True:
            ip = IP[self.n - 1]
            try:
                c = ModbusClient(host=ip, auto_open=True, auto_close=True, timeout=2)
            except ValueError:
                self.signal_connect.emit(self.n, 0, [], 1)
                time.sleep(2)
                continue
            if not c.open():
                time.sleep(2)
                self.signal_connect.emit(self.n, 0, [], 1)
                continue

            try:
                coils = c.read_coils(0, 12)
                checkback_coils = c.read_discrete_inputs(0, 6)
                coils_int = list(map(int, coils))
                self.signal_connect.emit(self.n, 1, coils_int, coils[:6] == checkback_coils)

            except TypeError:
                self.signal_connect.emit(self.n, 0, [], 1)
                time.sleep(2)
                continue
            time.sleep(2)


class SetAttenuation(QThread):

    def __init__(self, target, args):
        super().__init__()
        self.set_att = target
        self.args = args

    def run(self):
        self.set_att(*self.args)


def main():
    app = QtWidgets.QApplication(sys.argv)
    application = IoLogikControl()

    check_duplicates()
    if LOGGING:
        logging('Программа запущена.')

    application.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
