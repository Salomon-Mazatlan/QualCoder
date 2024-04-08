# Form implementation generated from reading ui file 'ui_dialog_charts.ui'
#
# Created by: PyQt6 UI code generator 6.5.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_DialogCharts(object):
    def setupUi(self, DialogCharts):
        DialogCharts.setObjectName("DialogCharts")
        DialogCharts.resize(1011, 597)
        self.label_info = QtWidgets.QLabel(parent=DialogCharts)
        self.label_info.setGeometry(QtCore.QRect(9, 9, 391, 22))
        self.label_info.setObjectName("label_info")
        self.label_pie = QtWidgets.QLabel(parent=DialogCharts)
        self.label_pie.setGeometry(QtCore.QRect(10, 80, 321, 22))
        self.label_pie.setObjectName("label_pie")
        self.label_bar = QtWidgets.QLabel(parent=DialogCharts)
        self.label_bar.setGeometry(QtCore.QRect(10, 143, 321, 22))
        self.label_bar.setObjectName("label_bar")
        self.comboBox_pie_charts = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_pie_charts.setGeometry(QtCore.QRect(10, 110, 321, 25))
        self.comboBox_pie_charts.setObjectName("comboBox_pie_charts")
        self.comboBox_bar_charts = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_bar_charts.setGeometry(QtCore.QRect(10, 170, 321, 25))
        self.comboBox_bar_charts.setObjectName("comboBox_bar_charts")
        self.comboBox_sunburst_charts = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_sunburst_charts.setGeometry(QtCore.QRect(10, 225, 321, 25))
        self.comboBox_sunburst_charts.setObjectName("comboBox_sunburst_charts")
        self.label_hierarchy = QtWidgets.QLabel(parent=DialogCharts)
        self.label_hierarchy.setGeometry(QtCore.QRect(10, 200, 321, 22))
        self.label_hierarchy.setObjectName("label_hierarchy")
        self.label_coder = QtWidgets.QLabel(parent=DialogCharts)
        self.label_coder.setGeometry(QtCore.QRect(380, 103, 321, 22))
        self.label_coder.setObjectName("label_coder")
        self.comboBox_coders = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_coders.setGeometry(QtCore.QRect(380, 130, 321, 25))
        self.comboBox_coders.setObjectName("comboBox_coders")
        self.comboBox_file = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_file.setGeometry(QtCore.QRect(380, 180, 321, 25))
        self.comboBox_file.setObjectName("comboBox_file")
        self.label_select_file = QtWidgets.QLabel(parent=DialogCharts)
        self.label_select_file.setGeometry(QtCore.QRect(380, 160, 321, 22))
        self.label_select_file.setObjectName("label_select_file")
        self.comboBox_case = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_case.setGeometry(QtCore.QRect(380, 230, 321, 25))
        self.comboBox_case.setObjectName("comboBox_case")
        self.label_select_case = QtWidgets.QLabel(parent=DialogCharts)
        self.label_select_case.setGeometry(QtCore.QRect(380, 210, 321, 22))
        self.label_select_case.setObjectName("label_select_case")
        self.pushButton_attributes = QtWidgets.QPushButton(parent=DialogCharts)
        self.pushButton_attributes.setGeometry(QtCore.QRect(380, 310, 231, 25))
        self.pushButton_attributes.setObjectName("pushButton_attributes")
        self.label_filter = QtWidgets.QLabel(parent=DialogCharts)
        self.label_filter.setGeometry(QtCore.QRect(378, 76, 201, 22))
        self.label_filter.setObjectName("label_filter")
        self.lineEdit_filter = QtWidgets.QLineEdit(parent=DialogCharts)
        self.lineEdit_filter.setGeometry(QtCore.QRect(610, 77, 91, 25))
        self.lineEdit_filter.setText("")
        self.lineEdit_filter.setObjectName("lineEdit_filter")
        self.label_filters = QtWidgets.QLabel(parent=DialogCharts)
        self.label_filters.setGeometry(QtCore.QRect(380, 50, 321, 22))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self.label_filters.setFont(font)
        self.label_filters.setObjectName("label_filters")
        self.label_chart_options = QtWidgets.QLabel(parent=DialogCharts)
        self.label_chart_options.setGeometry(QtCore.QRect(10, 50, 311, 22))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self.label_chart_options.setFont(font)
        self.label_chart_options.setObjectName("label_chart_options")
        self.comboBox_category = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_category.setGeometry(QtCore.QRect(380, 280, 321, 25))
        self.comboBox_category.setObjectName("comboBox_category")
        self.label_category = QtWidgets.QLabel(parent=DialogCharts)
        self.label_category.setGeometry(QtCore.QRect(380, 260, 321, 22))
        self.label_category.setObjectName("label_category")
        self.line = QtWidgets.QFrame(parent=DialogCharts)
        self.line.setGeometry(QtCore.QRect(340, 50, 20, 521))
        self.line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.label_chart_attributes = QtWidgets.QLabel(parent=DialogCharts)
        self.label_chart_attributes.setGeometry(QtCore.QRect(10, 390, 261, 22))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self.label_chart_attributes.setFont(font)
        self.label_chart_attributes.setObjectName("label_chart_attributes")
        self.label_num_attr = QtWidgets.QLabel(parent=DialogCharts)
        self.label_num_attr.setGeometry(QtCore.QRect(10, 516, 321, 22))
        self.label_num_attr.setObjectName("label_num_attr")
        self.label_char_attr = QtWidgets.QLabel(parent=DialogCharts)
        self.label_char_attr.setGeometry(QtCore.QRect(10, 457, 321, 22))
        self.label_char_attr.setObjectName("label_char_attr")
        self.comboBox_num_attributes = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_num_attributes.setGeometry(QtCore.QRect(10, 543, 321, 25))
        self.comboBox_num_attributes.setObjectName("comboBox_num_attributes")
        self.comboBox_char_attributes = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_char_attributes.setGeometry(QtCore.QRect(10, 480, 321, 25))
        self.comboBox_char_attributes.setObjectName("comboBox_char_attributes")
        self.line_2 = QtWidgets.QFrame(parent=DialogCharts)
        self.line_2.setGeometry(QtCore.QRect(10, 370, 331, 16))
        self.line_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_2.setObjectName("line_2")
        self.groupBox = QtWidgets.QGroupBox(parent=DialogCharts)
        self.groupBox.setGeometry(QtCore.QRect(10, 391, 321, 61))
        self.groupBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.radioButton_file = QtWidgets.QRadioButton(parent=self.groupBox)
        self.radioButton_file.setGeometry(QtCore.QRect(0, 30, 112, 23))
        self.radioButton_file.setChecked(True)
        self.radioButton_file.setObjectName("radioButton_file")
        self.radioButton_case = QtWidgets.QRadioButton(parent=self.groupBox)
        self.radioButton_case.setGeometry(QtCore.QRect(120, 30, 112, 23))
        self.radioButton_case.setObjectName("radioButton_case")
        self.checkBox_export_html = QtWidgets.QCheckBox(parent=DialogCharts)
        self.checkBox_export_html.setGeometry(QtCore.QRect(430, 10, 301, 23))
        self.checkBox_export_html.setObjectName("checkBox_export_html")
        self.label_chart_options_2 = QtWidgets.QLabel(parent=DialogCharts)
        self.label_chart_options_2.setGeometry(QtCore.QRect(10, 280, 321, 22))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self.label_chart_options_2.setFont(font)
        self.label_chart_options_2.setObjectName("label_chart_options_2")
        self.line_3 = QtWidgets.QFrame(parent=DialogCharts)
        self.line_3.setGeometry(QtCore.QRect(10, 30, 721, 16))
        self.line_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_3.setObjectName("line_3")
        self.line_4 = QtWidgets.QFrame(parent=DialogCharts)
        self.line_4.setGeometry(QtCore.QRect(10, 260, 331, 16))
        self.line_4.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_4.setObjectName("line_4")
        self.comboBox_heatmap = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_heatmap.setGeometry(QtCore.QRect(10, 334, 321, 25))
        self.comboBox_heatmap.setObjectName("comboBox_heatmap")
        self.line_5 = QtWidgets.QFrame(parent=DialogCharts)
        self.line_5.setGeometry(QtCore.QRect(380, 340, 331, 16))
        self.line_5.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_5.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_5.setObjectName("line_5")
        self.label_word_clouds = QtWidgets.QLabel(parent=DialogCharts)
        self.label_word_clouds.setGeometry(QtCore.QRect(380, 350, 321, 22))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_word_clouds.setFont(font)
        self.label_word_clouds.setObjectName("label_word_clouds")
        self.comboBox_wordcloud_background = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_wordcloud_background.setGeometry(QtCore.QRect(380, 380, 321, 25))
        self.comboBox_wordcloud_background.setObjectName("comboBox_wordcloud_background")
        self.comboBox_wordcloud_foreground = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_wordcloud_foreground.setGeometry(QtCore.QRect(380, 410, 321, 25))
        self.comboBox_wordcloud_foreground.setObjectName("comboBox_wordcloud_foreground")
        self.pushButton_wordcloud = QtWidgets.QPushButton(parent=DialogCharts)
        self.pushButton_wordcloud.setGeometry(QtCore.QRect(582, 490, 120, 50))
        self.pushButton_wordcloud.setObjectName("pushButton_wordcloud")
        self.label_width = QtWidgets.QLabel(parent=DialogCharts)
        self.label_width.setGeometry(QtCore.QRect(380, 442, 55, 16))
        self.label_width.setObjectName("label_width")
        self.label_height = QtWidgets.QLabel(parent=DialogCharts)
        self.label_height.setGeometry(QtCore.QRect(450, 442, 55, 16))
        self.label_height.setObjectName("label_height")
        self.label_max_words = QtWidgets.QLabel(parent=DialogCharts)
        self.label_max_words.setGeometry(QtCore.QRect(510, 440, 91, 20))
        self.label_max_words.setObjectName("label_max_words")
        self.spinBox_cloud_width = QtWidgets.QSpinBox(parent=DialogCharts)
        self.spinBox_cloud_width.setGeometry(QtCore.QRect(380, 460, 61, 22))
        self.spinBox_cloud_width.setMinimum(400)
        self.spinBox_cloud_width.setMaximum(2000)
        self.spinBox_cloud_width.setSingleStep(100)
        self.spinBox_cloud_width.setProperty("value", 800)
        self.spinBox_cloud_width.setObjectName("spinBox_cloud_width")
        self.spinBox_cloud_height = QtWidgets.QSpinBox(parent=DialogCharts)
        self.spinBox_cloud_height.setGeometry(QtCore.QRect(450, 460, 61, 22))
        self.spinBox_cloud_height.setMinimum(200)
        self.spinBox_cloud_height.setMaximum(2000)
        self.spinBox_cloud_height.setSingleStep(100)
        self.spinBox_cloud_height.setProperty("value", 600)
        self.spinBox_cloud_height.setObjectName("spinBox_cloud_height")
        self.spinBox_cloud_max_words = QtWidgets.QSpinBox(parent=DialogCharts)
        self.spinBox_cloud_max_words.setGeometry(QtCore.QRect(520, 460, 61, 22))
        self.spinBox_cloud_max_words.setMinimum(50)
        self.spinBox_cloud_max_words.setMaximum(500)
        self.spinBox_cloud_max_words.setSingleStep(50)
        self.spinBox_cloud_max_words.setProperty("value", 200)
        self.spinBox_cloud_max_words.setObjectName("spinBox_cloud_max_words")
        self.checkBox_reverse_range = QtWidgets.QCheckBox(parent=DialogCharts)
        self.checkBox_reverse_range.setGeometry(QtCore.QRect(380, 490, 21, 20))
        self.checkBox_reverse_range.setText("")
        self.checkBox_reverse_range.setObjectName("checkBox_reverse_range")
        self.label_reverse_range = QtWidgets.QLabel(parent=DialogCharts)
        self.label_reverse_range.setGeometry(QtCore.QRect(410, 490, 151, 25))
        self.label_reverse_range.setObjectName("label_reverse_range")
        self.label_ngrams = QtWidgets.QLabel(parent=DialogCharts)
        self.label_ngrams.setGeometry(QtCore.QRect(425, 523, 151, 25))
        self.label_ngrams.setObjectName("label_ngrams")
        self.comboBox_ngrams = QtWidgets.QComboBox(parent=DialogCharts)
        self.comboBox_ngrams.setGeometry(QtCore.QRect(380, 520, 40, 30))
        self.comboBox_ngrams.setObjectName("comboBox_ngrams")
        self.label_upper_count = QtWidgets.QLabel(parent=DialogCharts)
        self.label_upper_count.setGeometry(QtCore.QRect(10, 300, 131, 24))
        self.label_upper_count.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.label_upper_count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_upper_count.setObjectName("label_upper_count")
        self.spinBox_count_max = QtWidgets.QSpinBox(parent=DialogCharts)
        self.spinBox_count_max.setGeometry(QtCore.QRect(154, 301, 61, 26))
        self.spinBox_count_max.setMaximum(500)
        self.spinBox_count_max.setSingleStep(50)
        self.spinBox_count_max.setObjectName("spinBox_count_max")
        self.groupBox.raise_()
        self.label_info.raise_()
        self.label_pie.raise_()
        self.label_bar.raise_()
        self.comboBox_pie_charts.raise_()
        self.comboBox_bar_charts.raise_()
        self.comboBox_sunburst_charts.raise_()
        self.label_hierarchy.raise_()
        self.label_coder.raise_()
        self.comboBox_coders.raise_()
        self.comboBox_file.raise_()
        self.label_select_file.raise_()
        self.comboBox_case.raise_()
        self.label_select_case.raise_()
        self.pushButton_attributes.raise_()
        self.label_filter.raise_()
        self.lineEdit_filter.raise_()
        self.label_filters.raise_()
        self.label_chart_options.raise_()
        self.comboBox_category.raise_()
        self.label_category.raise_()
        self.line.raise_()
        self.label_chart_attributes.raise_()
        self.label_num_attr.raise_()
        self.label_char_attr.raise_()
        self.comboBox_num_attributes.raise_()
        self.comboBox_char_attributes.raise_()
        self.line_2.raise_()
        self.checkBox_export_html.raise_()
        self.label_chart_options_2.raise_()
        self.line_3.raise_()
        self.line_4.raise_()
        self.comboBox_heatmap.raise_()
        self.line_5.raise_()
        self.label_word_clouds.raise_()
        self.comboBox_wordcloud_background.raise_()
        self.comboBox_wordcloud_foreground.raise_()
        self.pushButton_wordcloud.raise_()
        self.label_width.raise_()
        self.label_height.raise_()
        self.label_max_words.raise_()
        self.spinBox_cloud_width.raise_()
        self.spinBox_cloud_height.raise_()
        self.spinBox_cloud_max_words.raise_()
        self.checkBox_reverse_range.raise_()
        self.label_reverse_range.raise_()
        self.label_ngrams.raise_()
        self.comboBox_ngrams.raise_()
        self.label_upper_count.raise_()
        self.spinBox_count_max.raise_()

        self.retranslateUi(DialogCharts)
        QtCore.QMetaObject.connectSlotsByName(DialogCharts)
        DialogCharts.setTabOrder(self.checkBox_export_html, self.comboBox_pie_charts)
        DialogCharts.setTabOrder(self.comboBox_pie_charts, self.comboBox_bar_charts)
        DialogCharts.setTabOrder(self.comboBox_bar_charts, self.comboBox_sunburst_charts)
        DialogCharts.setTabOrder(self.comboBox_sunburst_charts, self.comboBox_heatmap)
        DialogCharts.setTabOrder(self.comboBox_heatmap, self.radioButton_file)
        DialogCharts.setTabOrder(self.radioButton_file, self.radioButton_case)
        DialogCharts.setTabOrder(self.radioButton_case, self.comboBox_char_attributes)
        DialogCharts.setTabOrder(self.comboBox_char_attributes, self.comboBox_num_attributes)
        DialogCharts.setTabOrder(self.comboBox_num_attributes, self.lineEdit_filter)
        DialogCharts.setTabOrder(self.lineEdit_filter, self.comboBox_coders)
        DialogCharts.setTabOrder(self.comboBox_coders, self.comboBox_file)
        DialogCharts.setTabOrder(self.comboBox_file, self.comboBox_case)
        DialogCharts.setTabOrder(self.comboBox_case, self.comboBox_category)
        DialogCharts.setTabOrder(self.comboBox_category, self.pushButton_attributes)

    def retranslateUi(self, DialogCharts):
        _translate = QtCore.QCoreApplication.translate
        DialogCharts.setWindowTitle(_translate("DialogCharts", "Charts"))
        self.label_info.setText(_translate("DialogCharts", "Charts displayed in the default web browser"))
        self.label_pie.setText(_translate("DialogCharts", "Pie charts"))
        self.label_bar.setText(_translate("DialogCharts", "Bar charts"))
        self.label_hierarchy.setText(_translate("DialogCharts", "Sunburst and treemap charts"))
        self.label_coder.setText(_translate("DialogCharts", "Select coder"))
        self.label_select_file.setText(_translate("DialogCharts", "Select file"))
        self.comboBox_case.setToolTip(_translate("DialogCharts", "If portions of a text file are assigned to a case, the code frequency and total text characters may be incorrect.\n"
"Codings from the entire text file are used for the calculations."))
        self.label_select_case.setToolTip(_translate("DialogCharts", "If portions of a text file are assigned to a case, the code frequency and total text characters may be incorrect.\n"
"Codings from the entire text file are used for the calculations."))
        self.label_select_case.setText(_translate("DialogCharts", "Select case"))
        self.pushButton_attributes.setText(_translate("DialogCharts", "Select attributes"))
        self.label_filter.setText(_translate("DialogCharts", "Filter out values below:"))
        self.lineEdit_filter.setToolTip(_translate("DialogCharts", "Enter number for filter cut off"))
        self.label_filters.setText(_translate("DialogCharts", "<b>Data filters</b>"))
        self.label_chart_options.setText(_translate("DialogCharts", "<b>Coding charts</b>"))
        self.label_category.setText(_translate("DialogCharts", "Select category"))
        self.label_chart_attributes.setText(_translate("DialogCharts", "<b>Attribute charts</b>"))
        self.label_num_attr.setText(_translate("DialogCharts", "Numeric attributes"))
        self.label_char_attr.setText(_translate("DialogCharts", "Character attributes"))
        self.radioButton_file.setText(_translate("DialogCharts", "File"))
        self.radioButton_case.setText(_translate("DialogCharts", "Case"))
        self.checkBox_export_html.setText(_translate("DialogCharts", "Export HTML file"))
        self.label_chart_options_2.setText(_translate("DialogCharts", "<b>Heatmap charts</b>"))
        self.label_word_clouds.setText(_translate("DialogCharts", "Word cloud"))
        self.comboBox_wordcloud_background.setToolTip(_translate("DialogCharts", "<html><head/><body><p>Background</p></body></html>"))
        self.comboBox_wordcloud_foreground.setToolTip(_translate("DialogCharts", "<html><head/><body><p>Foreground</p></body></html>"))
        self.pushButton_wordcloud.setText(_translate("DialogCharts", "Make\n"
"wordcloud"))
        self.label_width.setText(_translate("DialogCharts", "Width"))
        self.label_height.setText(_translate("DialogCharts", "Height"))
        self.label_max_words.setText(_translate("DialogCharts", "Max words"))
        self.checkBox_reverse_range.setToolTip(_translate("DialogCharts", "Reverse colour range"))
        self.label_reverse_range.setToolTip(_translate("DialogCharts", "Reverse colour range"))
        self.label_reverse_range.setText(_translate("DialogCharts", "Reverse range"))
        self.label_ngrams.setToolTip(_translate("DialogCharts", "Number of conjoined words in phrase. Stopwords applies to selection of 1 word only."))
        self.label_ngrams.setText(_translate("DialogCharts", "n-grams"))
        self.comboBox_ngrams.setToolTip(_translate("DialogCharts", "1=One word, 3=3 word phrase, 4=4 word phrase"))
        self.label_upper_count.setToolTip(_translate("DialogCharts", "<html><head/><body><p>This is to allow a wider spread of head map colours when there are extreme count differences.</p><p>0 represents no limit.</p></body></html>"))
        self.label_upper_count.setText(_translate("DialogCharts", "Upper count limiter"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DialogCharts = QtWidgets.QDialog()
    ui = Ui_DialogCharts()
    ui.setupUi(DialogCharts)
    DialogCharts.show()
    sys.exit(app.exec())
