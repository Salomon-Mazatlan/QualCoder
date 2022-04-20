# Form implementation generated from reading ui file 'ui_dialog_charts.ui'
#
# Created by: PyQt6 UI code generator 6.2.3
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_DialogCharts(object):
    def setupUi(self, DialogCharts):
        DialogCharts.setObjectName("DialogCharts")
        DialogCharts.resize(858, 419)
        self.label_info = QtWidgets.QLabel(DialogCharts)
        self.label_info.setGeometry(QtCore.QRect(9, 9, 481, 20))
        self.label_info.setObjectName("label_info")
        self.label_pie = QtWidgets.QLabel(DialogCharts)
        self.label_pie.setGeometry(QtCore.QRect(10, 42, 291, 22))
        self.label_pie.setObjectName("label_pie")
        self.label_bar = QtWidgets.QLabel(DialogCharts)
        self.label_bar.setGeometry(QtCore.QRect(10, 157, 291, 22))
        self.label_bar.setObjectName("label_bar")
        self.label_tree = QtWidgets.QLabel(DialogCharts)
        self.label_tree.setGeometry(QtCore.QRect(10, 219, 291, 22))
        self.label_tree.setObjectName("label_tree")
        self.comboBox_pie_charts = QtWidgets.QComboBox(DialogCharts)
        self.comboBox_pie_charts.setGeometry(QtCore.QRect(10, 65, 291, 25))
        self.comboBox_pie_charts.setObjectName("comboBox_pie_charts")
        self.comboBox_bar_charts = QtWidgets.QComboBox(DialogCharts)
        self.comboBox_bar_charts.setGeometry(QtCore.QRect(10, 185, 291, 25))
        self.comboBox_bar_charts.setObjectName("comboBox_bar_charts")
        self.comboBox_tree_charts = QtWidgets.QComboBox(DialogCharts)
        self.comboBox_tree_charts.setGeometry(QtCore.QRect(10, 249, 291, 25))
        self.comboBox_tree_charts.setObjectName("comboBox_tree_charts")
        self.comboBox_sunburst_charts = QtWidgets.QComboBox(DialogCharts)
        self.comboBox_sunburst_charts.setGeometry(QtCore.QRect(10, 123, 291, 25))
        self.comboBox_sunburst_charts.setObjectName("comboBox_sunburst_charts")
        self.label_hierarchy = QtWidgets.QLabel(DialogCharts)
        self.label_hierarchy.setGeometry(QtCore.QRect(14, 98, 291, 22))
        self.label_hierarchy.setObjectName("label_hierarchy")
        self.label_coder = QtWidgets.QLabel(DialogCharts)
        self.label_coder.setGeometry(QtCore.QRect(340, 40, 151, 22))
        self.label_coder.setObjectName("label_coder")
        self.comboBox_coders = QtWidgets.QComboBox(DialogCharts)
        self.comboBox_coders.setGeometry(QtCore.QRect(340, 64, 231, 25))
        self.comboBox_coders.setObjectName("comboBox_coders")
        self.comboBox_file = QtWidgets.QComboBox(DialogCharts)
        self.comboBox_file.setGeometry(QtCore.QRect(340, 124, 231, 25))
        self.comboBox_file.setObjectName("comboBox_file")
        self.label_select_file = QtWidgets.QLabel(DialogCharts)
        self.label_select_file.setGeometry(QtCore.QRect(340, 100, 231, 22))
        self.label_select_file.setObjectName("label_select_file")
        self.comboBox_case = QtWidgets.QComboBox(DialogCharts)
        self.comboBox_case.setGeometry(QtCore.QRect(340, 184, 231, 25))
        self.comboBox_case.setObjectName("comboBox_case")
        self.label_select_case = QtWidgets.QLabel(DialogCharts)
        self.label_select_case.setGeometry(QtCore.QRect(340, 160, 231, 22))
        self.label_select_case.setObjectName("label_select_case")
        self.pushButton_attributes = QtWidgets.QPushButton(DialogCharts)
        self.pushButton_attributes.setGeometry(QtCore.QRect(340, 220, 231, 25))
        self.pushButton_attributes.setObjectName("pushButton_attributes")
        self.label_filter = QtWidgets.QLabel(DialogCharts)
        self.label_filter.setGeometry(QtCore.QRect(10, 290, 201, 17))
        self.label_filter.setObjectName("label_filter")
        self.lineEdit_filter = QtWidgets.QLineEdit(DialogCharts)
        self.lineEdit_filter.setGeometry(QtCore.QRect(212, 290, 91, 25))
        self.lineEdit_filter.setObjectName("lineEdit_filter")

        self.retranslateUi(DialogCharts)
        QtCore.QMetaObject.connectSlotsByName(DialogCharts)

    def retranslateUi(self, DialogCharts):
        _translate = QtCore.QCoreApplication.translate
        DialogCharts.setWindowTitle(_translate("DialogCharts", "Charts"))
        self.label_info.setText(_translate("DialogCharts", "Charts are displayed in the default web browser"))
        self.label_pie.setText(_translate("DialogCharts", "Pie charts"))
        self.label_bar.setText(_translate("DialogCharts", "Bar charts"))
        self.label_tree.setText(_translate("DialogCharts", "Tree charts"))
        self.label_hierarchy.setText(_translate("DialogCharts", "Sunburst and treemap charts"))
        self.label_coder.setText(_translate("DialogCharts", "Select coder"))
        self.label_select_file.setText(_translate("DialogCharts", "Select file"))
        self.label_select_case.setText(_translate("DialogCharts", "Select case - all files "))
        self.pushButton_attributes.setText(_translate("DialogCharts", "Select attributes"))
        self.label_filter.setText(_translate("DialogCharts", "Filter out values below:"))
        self.lineEdit_filter.setToolTip(_translate("DialogCharts", "Enter number for filter cut off"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DialogCharts = QtWidgets.QDialog()
    ui = Ui_DialogCharts()
    ui.setupUi(DialogCharts)
    DialogCharts.show()
    sys.exit(app.exec())
