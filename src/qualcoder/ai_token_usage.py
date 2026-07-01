# -*- coding: utf-8 -*-

"""
This file is part of QualCoder.

QualCoder is free software: you can redistribute it and/or modify it under the
terms of the GNU Lesser General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.

QualCoder is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with QualCoder.
If not, see <https://www.gnu.org/licenses/>.

https://github.com/ccbogel/QualCoder
https://qualcoder.wordpress.com/
https://qualcoder.org/
"""

import csv
import logging
import os

from PyQt6 import QtWidgets, QtCore

from .GUI.ui_ai_token_usage import Ui_Dialog_AiTokenUsage
from .helpers import Message
from .ai_usage import (AiUsageTracker, TASK_CHAT, TASK_SEARCH_DESCRIPTIONS,
                       TASK_SEARCH_ANALYZE, TASK_OTHER)

path = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


def _task_label(task):
    """Human readable name for the internal task codes."""
    labels = {
        TASK_CHAT: _('AI Chat'),
        TASK_SEARCH_DESCRIPTIONS: _('AI search: code variants'),
        TASK_SEARCH_ANALYZE: _('AI search: data analysis'),
        TASK_OTHER: _('Other'),
    }
    return labels.get(task, task if task else _('Other'))


class DialogAiTokenUsage(QtWidgets.QDialog):
    """ Shows how many AI tokens have been consumed in the current project,
    grouped by provider/model and by QualCoder feature.

    Token counts reported directly by the provider are shown as measured.
    When a provider does not report usage (for example while streaming), the
    amount is estimated from the model tokenizer and clearly marked as such.
    """

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        # Reuse the tracker that already lives in the AI subsystem, so that
        # "this session" is measured from when the AI started (program launch /
        # project open), not from when this dialog was opened. Fall back to a new
        # tracker only if the AI has not been initialized yet.
        if getattr(self.app, 'ai', None) is not None and \
                getattr(self.app.ai, 'usage_tracker', None) is not None:
            self.tracker = self.app.ai.usage_tracker
        else:
            self.tracker = AiUsageTracker(app)
        self.ui = Ui_Dialog_AiTokenUsage()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        # Styling, consistent with the rest of QualCoder
        font = f'font: {app.settings["fontsize"]}pt "{app.settings["font"]}";'
        self.setStyleSheet(font)
        font_bold = f'{font}\nfont-weight: bold;\n color: {self.app.highlight_color()}'
        self.ui.label_title.setStyleSheet(font_bold)
        self.ui.label_title.setText(_('AI token consumption'))
        # Tables
        self._setup_models_table()
        self._setup_tasks_table()
        # Buttons
        self.ui.pushButton_refresh.clicked.connect(self.load_data)
        self.ui.pushButton_export.clicked.connect(self.export_csv)
        self.ui.pushButton_reset.clicked.connect(self.reset_usage)
        self.load_data()

    # ------------------------------------------------------------- table setup
    def _setup_models_table(self):
        headers = [_('Provider'), _('Model'), _('Calls'), _('Input'),
                   _('Output'), _('Reasoning/other'), _('Total'), _('Estimated'), _('Last used')]
        table = self.ui.tableWidget_models
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

    def _setup_tasks_table(self):
        headers = [_('Feature'), _('Calls'), _('Input'), _('Output'), _('Reasoning/other'), _('Total')]
        table = self.ui.tableWidget_tasks
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

    # ------------------------------------------------------------- data loading
    @staticmethod
    def _num_item(value):
        """A right aligned, thousands separated, non editable numeric cell."""
        item = QtWidgets.QTableWidgetItem(f'{int(value):,}')
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        return item

    def load_data(self):
        if self.app.conn is None:
            self.ui.label_summary.setText(_('No project is open.'))
            self.ui.tableWidget_models.setRowCount(0)
            self.ui.tableWidget_tasks.setRowCount(0)
            return
        self._load_summary()
        self._load_models_table()
        self._load_tasks_table()

    def _load_summary(self):
        totals = self.tracker.totals()
        session = self.tracker.totals(since=self.tracker.session_start)
        # Context window of the currently selected large model (per request budget)
        context_window = None
        try:
            idx = int(self.app.settings.get('ai_model_index', -1))
            if 0 <= idx < len(self.app.ai_models):
                context_window = int(self.app.ai_models[idx].get('large_model_context_window', 0))
        except Exception:
            context_window = None
        other_total = totals['total'] - totals['input'] - totals['output']
        other_session = session['total'] - session['input'] - session['output']
        lines = [
            _('Total in this project') +
            f": <b>{totals['total']:,}</b> " + _('tokens') +
            f" ({_('input')}: {totals['input']:,}, {_('output')}: {totals['output']:,}, " +
            f"{_('reasoning/other')}: {other_total:,}, {_('calls')}: {totals['calls']:,})",
            _('This session') +
            f": <b>{session['total']:,}</b> " + _('tokens') +
            f" ({_('input')}: {session['input']:,}, {_('output')}: {session['output']:,}, " +
            f"{_('reasoning/other')}: {other_session:,}, {_('calls')}: {session['calls']:,})",
        ]
        if context_window:
            lines.append(_('Context window of the current model') +
                         f": {context_window:,} " + _('tokens per request'))
        self.ui.label_summary.setText('<br>'.join(lines))

    def _load_models_table(self):
        rows = self.tracker.totals_by_model()
        table = self.ui.tableWidget_models
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            # Reasoning/other = provider total minus the plain input/output. It
            # captures token categories the provider counts in the total but
            # reports apart (reasoning/"thinking" tokens, cache accounting, ...),
            # so that input + output + reasoning/other equals total.
            other = int(row['total']) - int(row['input']) - int(row['output'])
            table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(row['provider'])))
            table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(row['model'])))
            table.setItem(r, 2, self._num_item(row['calls']))
            table.setItem(r, 3, self._num_item(row['input']))
            table.setItem(r, 4, self._num_item(row['output']))
            table.setItem(r, 5, self._num_item(other))
            table.setItem(r, 6, self._num_item(row['total']))
            # Estimated marker: how many of the calls are estimates
            if row['estimated_calls'] == 0:
                est_text = _('No (measured)')
            elif row['estimated_calls'] == row['calls']:
                est_text = _('Yes (estimated)')
            else:
                est_text = _('Partly') + f" ({row['estimated_calls']}/{row['calls']})"
            table.setItem(r, 7, QtWidgets.QTableWidgetItem(est_text))
            table.setItem(r, 8, QtWidgets.QTableWidgetItem(str(row['last_used'] or '')))
        table.resizeColumnsToContents()
        try:
            table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass

    def _load_tasks_table(self):
        rows = self.tracker.totals_by_task()
        table = self.ui.tableWidget_tasks
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            other = int(row['total']) - int(row['input']) - int(row['output'])
            table.setItem(r, 0, QtWidgets.QTableWidgetItem(_task_label(row['task'])))
            table.setItem(r, 1, self._num_item(row['calls']))
            table.setItem(r, 2, self._num_item(row['input']))
            table.setItem(r, 3, self._num_item(row['output']))
            table.setItem(r, 4, self._num_item(other))
            table.setItem(r, 5, self._num_item(row['total']))
        table.resizeColumnsToContents()
        try:
            table.horizontalHeader().setStretchLastSection(True)
        except Exception:
            pass

    # ------------------------------------------------------------------ actions
    def export_csv(self):
        rows = self.tracker.all_rows()
        if not rows:
            Message(self.app, _('Export CSV'), _('There is no usage data to export yet.')).exec()
            return
        filepath, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, _('Save usage as CSV'), self.app.last_export_directory, "CSV Files(*.csv)")
        if not ok or filepath == '':
            return
        if filepath[-4:].lower() != '.csv':
            filepath += '.csv'
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                writer.writerow(['date', 'provider', 'model', 'task', 'input_tokens',
                                 'output_tokens', 'reasoning_other_tokens', 'total_tokens', 'estimated'])
                for row in rows:
                    other = int(row['total']) - int(row['input']) - int(row['output'])
                    writer.writerow([row['date'], row['provider'], row['model'],
                                     _task_label(row['task']), row['input'], row['output'],
                                     other, row['total'], 'yes' if row['estimated'] else 'no'])
            self.app.last_export_directory = os.path.dirname(filepath)
            Message(self.app, _('Export CSV'),
                    _('Usage data exported to:') + f'\n{filepath}').exec()
        except Exception as e:
            Message(self.app, _('Export CSV'), _('Could not export file:') + f'\n{e}', 'warning').exec()

    def reset_usage(self):
        mb = QtWidgets.QMessageBox(self)
        mb.setWindowTitle(_('Reset AI usage'))
        mb.setText(_('This will permanently delete all recorded AI token usage '
                     'for this project. This cannot be undone. Continue?'))
        mb.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok |
                              QtWidgets.QMessageBox.StandardButton.Cancel)
        mb.setStyleSheet(f'* {{font-size: {self.app.settings["fontsize"]}pt}}')
        if mb.exec() == QtWidgets.QMessageBox.StandardButton.Ok:
            self.tracker.reset()
            self.load_data()
