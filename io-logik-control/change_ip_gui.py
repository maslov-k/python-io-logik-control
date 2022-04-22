# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'change_ip_gui.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(222, 100)
        Form.setMinimumSize(QtCore.QSize(222, 100))
        Form.setMaximumSize(QtCore.QSize(222, 100))
        font = QtGui.QFont()
        font.setPointSize(10)
        Form.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/icons/Settings.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Form.setWindowIcon(icon)
        self.gridLayout_2 = QtWidgets.QGridLayout(Form)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.lineEdit_ip = QtWidgets.QLineEdit(Form)
        self.lineEdit_ip.setText("")
        self.lineEdit_ip.setObjectName("lineEdit_ip")
        self.gridLayout.addWidget(self.lineEdit_ip, 0, 1, 1, 2)
        self.label = QtWidgets.QLabel(Form)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 2)
        self.pushButton_cancel = QtWidgets.QPushButton(Form)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pushButton_cancel.setFont(font)
        self.pushButton_cancel.setObjectName("pushButton_cancel")
        self.gridLayout_2.addWidget(self.pushButton_cancel, 2, 1, 1, 1)
        self.pushButton_OK = QtWidgets.QPushButton(Form)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pushButton_OK.setFont(font)
        self.pushButton_OK.setObjectName("pushButton_OK")
        self.gridLayout_2.addWidget(self.pushButton_OK, 2, 0, 1, 1)
        self.label_set = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_set.setFont(font)
        self.label_set.setObjectName("label_set")
        self.gridLayout_2.addWidget(self.label_set, 0, 0, 1, 2, QtCore.Qt.AlignHCenter)

        self.retranslateUi(Form)
        self.pushButton_cancel.clicked.connect(Form.close)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "IP-адрес"))
        self.label.setText(_translate("Form", "IP-адрес:"))
        self.pushButton_cancel.setText(_translate("Form", "Отмена"))
        self.pushButton_OK.setText(_translate("Form", "ОК"))
        self.label_set.setText(_translate("Form", "1 комплект"))
import resources_rc
