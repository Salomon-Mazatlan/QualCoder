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

Author: Colin Curtain C, Kai Dröge, Justin Missaghieh--Poncet, Lorenzo Salomón
https://github.com/ccbogel/QualCoder
https://qualcoder.wordpress.com/
https://qualcoder-org.github.io
https://qualcoder.org/
"""

import configparser
import hashlib
import logging
import sqlite3

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
import qtawesome as qta

from .code_tree import CodeTreeController
from .color_selector import TextColor
from .GUI.ui_dialog_code_picker import Ui_Dialog_code_picker
from .helpers import init_persistent_tree_header

logger = logging.getLogger(__name__)

# config.ini key holding the pinned codes of every project seen so far
PINNED_SETTING = "codepicker_pinned_codes"
# Id texts used in tree column 1. Codes and categories keep the code_tree texts
PINNED_PREFIX = "pin:"
PINNED_ROOT = "pinned:"
# Projects kept in config.ini, oldest entries drop out
MAX_PINNED_PROJECTS = 20


def project_pin_key(app):
    """ Short stable key for the open project, so pinned codes never leak between projects.
    Args:
        app: App object
    Returns:
        String, hex digest of the project path
    """

    path = str(getattr(app, "project_path", "") or "")
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]


def load_pinned_cids(app):
    """ Read the pinned code ids of the current project from config.ini.
    Args:
        app: App object
    Returns:
        List of integer code ids, in pinned order
    """

    raw = str(app.settings.get(PINNED_SETTING, "") or "")
    key = project_pin_key(app)
    for entry in raw.split(";"):
        entry_key, separator, cids_text = entry.partition(":")
        if separator == "" or entry_key != key:
            continue
        cids = []
        for value in cids_text.split(","):
            try:
                cid = int(value)
            except ValueError:
                continue
            if cid not in cids:
                cids.append(cid)
        return cids
    return []


def save_pinned_cids(app, cids):
    """ Store the pinned code ids of the current project in config.ini.
    Entries of other projects are kept, the current project is moved to the front.
    Args:
        app: App object
        cids: List of integer code ids
    """

    key = project_pin_key(app)
    entries = []
    if cids:
        entries.append(key + ":" + ",".join(str(cid) for cid in cids))
    raw = str(app.settings.get(PINNED_SETTING, "") or "")
    for entry in raw.split(";"):
        entry_key, separator, _cids_text = entry.partition(":")
        if separator == "" or entry_key == key:
            continue
        entries.append(entry)
    app.settings[PINNED_SETTING] = ";".join(entries[:MAX_PINNED_PROJECTS])
    try:
        app.write_config_ini(app.settings, app.ai_models)
    except (OSError, ValueError, configparser.Error) as err:  # pins stay for this session only
        logger.warning(f"Could not store pinned codes. {err}")


class DialogCodePicker(QtWidgets.QDialog):
    """ Searchable code picker used to find and apply a code without browsing the whole tree.

    The tree is loaded by the shared CodeTreeController, exactly as in the coding dialogs,
    but the context menu is reduced to applying, pinning and renaming.
    Pinned codes are shown in a branch at the top of the tree and persist in config.ini.

    Usage:
        ui = DialogCodePicker(app, parent_textEdit, parent_dialog)
        if ui.exec():
            code = ui.selected_code  # dictionary from app.get_codes_categories, or None
        if ui.codes_edited:  # a rename changed the database
            ...refresh the calling dialog...
    """

    def __init__(self, app, parent_textEdit, parent=None):
        """
        Args:
            app: App object
            parent_textEdit: QTextEdit for the action log, required by CodeTreeController
            parent: Parent QWidget or None
        """

        super().__init__(parent)
        self.app = app
        self.parent_textEdit = parent_textEdit
        self.codes = []
        self.categories = []
        self.selected_code = None
        self.codes_edited = False  # True when a rename changed the database
        self.code_counts = {}
        self.filter_text = ""
        self.ui = Ui_Dialog_code_picker()
        self.ui.setupUi(self)
        try:
            w = int(self.app.settings['dialogcodepicker_w'])
            h = int(self.app.settings['dialogcodepicker_h'])
            if w > 50 and h > 50:
                self.resize(w, h)
        except (KeyError, TypeError, ValueError):
            pass
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        font = f'font: {self.app.settings["fontsize"]}pt "{self.app.settings["font"]}";'
        self.setStyleSheet(font)
        tree_font = f'font: {self.app.settings["treefontsize"]}pt "{self.app.settings["font"]}";'
        self.ui.treeWidget.setStyleSheet(tree_font)
        self.get_codes_and_categories()
        self.pinned_cids = [cid for cid in load_pinned_cids(self.app)
                            if cid in [c['cid'] for c in self.codes]]

        self.ui.pushButton_clear_filter.setIcon(
            qta.icon('mdi6.filter-off-outline', options=[{'scale_factor': 1.3}]))
        self.ui.pushButton_clear_filter.pressed.connect(self.clear_filter)
        self.ui.pushButton_clear_filter.setVisible(False)  # hidden until a filter is active
        self.ui.pushButton_pinned_only.setIcon(qta.icon('mdi6.pin-outline', options=[{'scale_factor': 1.3}]))
        self.ui.pushButton_pinned_only.toggled.connect(self.apply_filter)
        self.ui.lineEdit_search.textChanged.connect(self.apply_filter)
        self.ui.lineEdit_search.installEventFilter(self)
        self.ui.treeWidget.itemDoubleClicked.connect(self.item_double_clicked)
        self.ui.treeWidget.itemSelectionChanged.connect(self.selection_changed)
        self.ui.treeWidget.customContextMenuRequested.connect(self.tree_menu)
        init_persistent_tree_header(self.ui.treeWidget, self.app, 'dialogcodepicker_tree_widths')
        # Shared tree controller: same tree fill as the coding dialogs
        # The picker reads app.collapsed_categories through the controller but never writes it:
        # expandAll in fill_tree emits itemExpanded for every category, so a handler connected
        # to that signal empties the shared list on each refill.
        self.code_tree = CodeTreeController(self.app, self.ui.treeWidget, self)
        self.code_tree.fill_counts_callback = self.fill_code_counts_in_tree
        self.code_tree.codes_changed.connect(self.update_dialog_codes_and_categories)
        self.fill_tree()
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.selection_changed()
        self.ui.lineEdit_search.setFocus()

    # Data

    def get_codes_and_categories(self):
        """ Load codes and categories. Read live by the tree controller. """

        self.codes, self.categories = self.app.get_codes_categories()

    def update_dialog_codes_and_categories(self, tables):
        """ Reload after a rename made through the tree controller.
        Args:
            tables: List of changed database table names
        """

        if tables:
            self.codes_edited = True
        self.get_codes_and_categories()
        self.fill_tree()

    def fill_tree(self):
        """ Fill the tree through the controller, then add the pinned branch and the filter. """

        current_cid = self.current_cid()
        self.code_tree.fill_tree()
        self.add_pinned_branch()
        self.apply_filter()
        if current_cid is not None:
            self.select_cid(current_cid)
        self.selection_changed()

    def fill_code_counts_in_tree(self):
        """ Fill the Count column with the codings of each code in the whole project.
        Categories show the total of their branch. Called back by the tree controller. """

        self.code_counts = {}
        cur = self.app.conn.cursor()
        for table in ("code_text_visible", "code_image_visible", "code_av_visible"):
            try:
                cur.execute(f"select cid, count(cid) from {table} group by cid")
            except sqlite3.OperationalError as err:  # view missing in an old project database
                logger.debug(f"Code counts, {table}. {err}")
                continue
            for cid, count in cur.fetchall():
                self.code_counts[cid] = self.code_counts.get(cid, 0) + count
        root = self.ui.treeWidget.invisibleRootItem()
        for i in range(root.childCount()):
            self.recursive_fill_counts(root.child(i))

    def recursive_fill_counts(self, item):
        """ Set the Count column of this item and return the total of its branch.
        Args:
            item: QTreeWidgetItem
        Returns:
            Integer, codings of this item and its descendants
        """

        total = 0
        cid = self.item_cid(item)
        if cid is not None:
            total = self.code_counts.get(cid, 0)
        branch_total = total
        for i in range(item.childCount()):
            branch_total += self.recursive_fill_counts(item.child(i))
        if cid is None:
            item.setText(3, str(branch_total) if branch_total else "")
        else:
            item.setText(3, str(total) if total else "")
        return branch_total

    # Pinned codes

    def add_pinned_branch(self):
        """ Add the pinned codes as a branch at the top of the tree and mark the pinned
        codes in their own position with a pin icon. """

        self.ui.pushButton_pinned_only.setEnabled(bool(self.pinned_cids))
        if not self.pinned_cids:
            self.ui.pushButton_pinned_only.setChecked(False)
            return
        pin_icon = qta.icon('mdi6.pin')
        root_item = QtWidgets.QTreeWidgetItem([_("Pinned codes"), PINNED_ROOT, ""])
        root_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        root_item.setIcon(0, pin_icon)
        for cid in self.pinned_cids:
            code_ = next((c for c in self.codes if c['cid'] == cid), None)
            if code_ is None:
                continue
            source_item = self.find_item_by_id(f"cid:{cid}")
            if source_item is not None:
                source_item.setIcon(0, pin_icon)
            memo = _("Memo") if code_['memo'] != "" else ""
            child = QtWidgets.QTreeWidgetItem([code_['name'], f"{PINNED_PREFIX}{cid}", memo])
            child.setToolTip(2, code_['memo'])
            child.setToolTip(0, self.code_path_text(code_))
            child.setBackground(0, QtGui.QBrush(QtGui.QColor(code_['color']), Qt.BrushStyle.SolidPattern))
            child.setForeground(0, QtGui.QBrush(QtGui.QColor(TextColor(code_['color']).recommendation)))
            child.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            count = self.code_counts.get(cid, 0)
            child.setText(3, str(count) if count else "")
            root_item.addChild(child)
        self.ui.treeWidget.insertTopLevelItem(0, root_item)
        root_item.setExpanded(True)

    def toggle_pin(self, cid):
        """ Pin or unpin this code and store the change in config.ini.
        Args:
            cid: Integer code id
        """

        if cid in self.pinned_cids:
            self.pinned_cids.remove(cid)
        else:
            self.pinned_cids.append(cid)
        save_pinned_cids(self.app, self.pinned_cids)
        self.fill_tree()

    def unpin_all(self):
        """ Remove every pinned code of this project. """

        self.pinned_cids = []
        save_pinned_cids(self.app, self.pinned_cids)
        self.fill_tree()

    # Tree helpers

    @staticmethod
    def item_cid(item):
        """ Code id of a tree item, for code items and for pinned copies.
        Args:
            item: QTreeWidgetItem
        Returns:
            Integer code id or None for categories and for the pinned branch root
        """

        id_text = item.text(1)
        if id_text[0:4] == "cid:":
            prefix_length = 4
        elif id_text[0:len(PINNED_PREFIX)] == PINNED_PREFIX and id_text != PINNED_ROOT:
            prefix_length = len(PINNED_PREFIX)
        else:
            return None
        try:
            return int(id_text[prefix_length:])
        except ValueError:
            return None

    def find_item_by_id(self, id_text):
        """ First tree item with this column 1 text.
        Args:
            id_text: String, such as cid:3 or catid:2
        Returns:
            QTreeWidgetItem or None
        """

        iterator = QtWidgets.QTreeWidgetItemIterator(self.ui.treeWidget)
        while iterator.value():
            if iterator.value().text(1) == id_text:
                return iterator.value()
            iterator += 1
        return None

    def current_cid(self):
        """ Code id of the selected item, or None. """

        item = self.ui.treeWidget.currentItem()
        if item is None:
            return None
        return self.item_cid(item)

    def select_cid(self, cid):
        """ Select the code item of this code id, preferring a visible item.
        Args:
            cid: Integer code id
        """

        for id_text in (f"cid:{cid}", f"{PINNED_PREFIX}{cid}"):
            item = self.find_item_by_id(id_text)
            if item is not None and not self.item_is_hidden(item):
                self.ui.treeWidget.setCurrentItem(item)
                return

    def category_path(self, catid, seen=None):
        """ Names of the category ancestry, safe with a corrupted circular path.
        Args:
            catid: Integer category id or None
            seen: Set of visited category ids
        Returns:
            List of category names, top level first
        """

        if catid is None:
            return []
        if seen is None:
            seen = set()
        if catid in seen:
            return []
        seen.add(catid)
        category = next((c for c in self.categories if c['catid'] == catid), None)
        if category is None:
            return []
        return self.category_path(category['supercatid'], seen) + [category['name']]

    def code_path(self, code_, seen=None):
        """ Names of the category and parent code ancestry, without the code name itself.
        Args:
            code_: Dictionary of a code
            seen: Set of visited code ids
        Returns:
            List of names, top level first
        """

        if seen is None:
            seen = set()
        if code_['cid'] in seen:
            return []
        seen.add(code_['cid'])
        supercid = code_.get('supercid')
        if supercid is not None:
            parent_code = next((c for c in self.codes if c['cid'] == supercid), None)
            if parent_code is not None:
                return self.code_path(parent_code, seen) + [parent_code['name']]
        return self.category_path(code_['catid'])

    def code_path_text(self, code_):
        """ Hierarchy of a code as one line of text.
        Args:
            code_: Dictionary of a code
        Returns:
            String
        """

        path = self.code_path(code_)
        if not path:
            return code_['name']
        return " > ".join(path) + " > " + code_['name']

    # Filtering

    def apply_filter(self):
        """ Hide the codes that do not match the filter text, keeping their categories and
        parent codes visible, as in the code text dialog. The pinned only button restricts
        the tree to the pinned branch. """

        self.filter_text = self.ui.lineEdit_search.text()
        pinned_only = self.ui.pushButton_pinned_only.isChecked()
        root = self.ui.treeWidget.invisibleRootItem()
        iterator = QtWidgets.QTreeWidgetItemIterator(self.ui.treeWidget)
        while iterator.value():  # reset, categories can be hidden by the pinned only button
            iterator.value().setHidden(False)
            iterator += 1
        if self.filter_text != "":
            self.recursive_traverse(root, self.filter_text)
        if pinned_only:
            for i in range(root.childCount()):
                item = root.child(i)
                item.setHidden(item.text(1) != PINNED_ROOT)
        if self.filter_text == "" and not pinned_only:
            self.ui.label_filter_icon.setPixmap(QtGui.QPixmap())
            self.ui.label_filter_icon.setToolTip("")
            self.ui.pushButton_clear_filter.setVisible(False)
            self.ui.pushButton_clear_filter.setStyleSheet("")
        else:
            self.ui.label_filter_icon.setPixmap(qta.icon('mdi6.filter-outline').pixmap(22, 22))
            tooltip = _("Filtered: ") + self.filter_text if self.filter_text else _("Pinned codes only")
            self.ui.label_filter_icon.setToolTip(tooltip)
            self.ui.pushButton_clear_filter.setVisible(True)
            self.ui.pushButton_clear_filter.setStyleSheet("background-color: #1e90ff; color: white;")
        self.ui.pushButton_pinned_only.setIcon(
            qta.icon('mdi6.pin' if pinned_only else 'mdi6.pin-outline', options=[{'scale_factor': 1.3}]))
        if self.current_item_is_hidden() or not self.current_code_matches_filter():
            self.select_first_matching_code()

    def recursive_traverse(self, item, text_):
        """ Hide or show codes of this item based on the filter text. A code stays visible
        if it matches or if any of its sub-codes matches, so a match is never hidden under a
        non matching parent code. Categories are never hidden.
        Args:
            item: QTreeWidgetItem
            text_: String to match with code names, blank shows all
        Returns:
            True when this item or a descendant matches
        """

        any_visible_descendant = False
        for i in range(item.childCount()):
            child = item.child(i)
            cid = self.item_cid(child)
            descendant_match = self.recursive_traverse(child, text_)
            if text_ == "":
                if cid is not None:
                    child.setHidden(False)
                any_visible_descendant = True
                continue
            self_match = False
            if cid is not None:
                code_ = next((c for c in self.codes if c['cid'] == cid), None)
                if code_ is not None:
                    self_match = text_.lower() in code_['name'].lower()
            visible = self_match or descendant_match
            if cid is not None:
                child.setHidden(not visible)
            if visible:
                any_visible_descendant = True
        return any_visible_descendant

    def clear_filter(self):
        """ Clear the code filter and the pinned only button. """

        self.ui.lineEdit_search.blockSignals(True)
        self.ui.lineEdit_search.setText("")
        self.ui.lineEdit_search.blockSignals(False)
        self.ui.pushButton_pinned_only.blockSignals(True)
        self.ui.pushButton_pinned_only.setChecked(False)
        self.ui.pushButton_pinned_only.blockSignals(False)
        self.apply_filter()

    @staticmethod
    def item_is_hidden(item):
        """ True when this item or any of its ancestors is hidden. Qt only stores the hidden
        flag on the item itself, the children of a hidden item report False.
        Args:
            item: QTreeWidgetItem
        """

        while item is not None:
            if item.isHidden():
                return True
            item = item.parent()
        return False

    def current_item_is_hidden(self):
        """ True when there is no current item or it is hidden by the filter. """

        item = self.ui.treeWidget.currentItem()
        if item is None:
            return True
        return self.item_is_hidden(item)

    def visible_code_items(self):
        """ Code items that the filter leaves visible, in tree order.
        Returns:
            List of QTreeWidgetItem
        """

        items = []
        iterator = QtWidgets.QTreeWidgetItemIterator(self.ui.treeWidget)
        while iterator.value():
            item = iterator.value()
            if self.item_cid(item) is not None and not self.item_is_hidden(item):
                items.append(item)
            iterator += 1
        return items

    def current_code_matches_filter(self):
        """ True with no filter text, or when the selected code name contains it. A parent code
        left visible only by a matching sub-code does not keep the selection. """

        if self.filter_text == "":
            return True
        cid = self.current_cid()
        if cid is None:
            return False
        code_ = next((c for c in self.codes if c['cid'] == cid), None)
        if code_ is None:
            return False
        return self.filter_text.lower() in code_['name'].lower()

    def select_first_matching_code(self):
        """ Select the first code that matches the filter text, so Enter applies at once.
        A parent code left visible only by a matching sub-code is not the first choice. """

        items = self.visible_code_items()
        if not items:
            self.ui.treeWidget.setCurrentItem(None)
            self.selection_changed()
            return
        if self.filter_text != "":
            text_ = self.filter_text.lower()
            for item in items:
                code_ = next((c for c in self.codes if c['cid'] == self.item_cid(item)), None)
                if code_ is not None and text_ in code_['name'].lower():
                    self.ui.treeWidget.setCurrentItem(item)
                    return
        self.ui.treeWidget.setCurrentItem(items[0])

    def move_selection(self, step):
        """ Move the selection through the visible codes, keeping the focus in the search field.
        Args:
            step: Integer, number of codes to move, negative moves up
        """

        items = self.visible_code_items()
        if not items:
            return
        current = self.ui.treeWidget.currentItem()
        try:
            index = items.index(current)
        except ValueError:
            index = -1 if step > 0 else 0
        index = max(0, min(len(items) - 1, index + step))
        self.ui.treeWidget.setCurrentItem(items[index])
        self.ui.treeWidget.scrollToItem(
            items[index], QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible)

    # Selection and application

    def selection_changed(self):
        """ Show the hierarchy of the selected code and enable the Ok button only for codes. """

        ok_button = self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        cid = self.current_cid()
        code_ = None
        if cid is not None:
            code_ = next((c for c in self.codes if c['cid'] == cid), None)
        if code_ is None:
            self.ui.label_status.setText("")
            if ok_button is not None:
                ok_button.setEnabled(False)
            return
        text_ = self.code_path_text(code_)
        count = self.code_counts.get(cid, 0)
        if count:
            text_ += f"    ({count} " + _("codings") + ")"
        self.ui.label_status.setText(text_)
        if ok_button is not None:
            ok_button.setEnabled(True)

    def item_double_clicked(self, item, _column):
        """ Apply the code of the double clicked item.
        Args:
            item: QTreeWidgetItem
            _column: Integer, unused
        """

        if self.item_cid(item) is not None:
            self.accept()

    def accept(self):
        """ Store the selected code, then close. Categories cannot be applied. """

        cid = self.current_cid()
        if cid is None:
            return
        self.selected_code = next((c for c in self.codes if c['cid'] == cid), None)
        if self.selected_code is None:
            return
        super().accept()

    # Menu, keys and dialog

    def tree_menu(self, position):
        """ Reduced context menu: pin, apply and rename.
        Args:
            position: QPoint of the right click
        """

        selected = self.ui.treeWidget.currentItem()
        menu = QtWidgets.QMenu()
        menu.setStyleSheet(f"QMenu {{font-size:{self.app.settings['fontsize']}pt}} ")
        cid = None if selected is None else self.item_cid(selected)
        action_pin = None
        action_unpin_all = None
        if cid is not None:
            if cid in self.pinned_cids:
                action_pin = menu.addAction(_("Unpin code"))
            else:
                action_pin = menu.addAction(_("Pin code"))
        if self.pinned_cids:
            action_unpin_all = menu.addAction(_("Unpin all codes"))
        if menu.actions():
            menu.addSeparator()
        action_apply = None
        if cid is not None:
            action_apply = menu.addAction(_("Apply code"))
        action_rename = None
        if selected is not None and (cid is not None or selected.text(1)[0:3] == 'cat'):
            action_rename = menu.addAction(_("Rename F2"))
        action_expand_collapse = None
        if selected is not None and selected.childCount() > 0:
            action_expand_collapse = menu.addAction(_("Expand or collapse branch"))
        if not menu.actions():
            return
        action = menu.exec(self.ui.treeWidget.mapToGlobal(position))
        if action is None:
            return
        if action == action_pin:
            self.toggle_pin(cid)
            return
        if action == action_unpin_all:
            self.unpin_all()
            return
        if action == action_apply:
            self.accept()
            return
        if action == action_rename:
            self.rename_selected()
            return
        if action == action_expand_collapse:
            self.code_tree.recursive_expand_collapse_branch(selected, not selected.isExpanded())

    def rename_selected(self):
        """ Rename the selected code or category through the shared tree controller.
        A pinned copy is renamed through its code item in the tree. """

        selected = self.ui.treeWidget.currentItem()
        if selected is None:
            return
        cid = self.item_cid(selected)
        if cid is not None:
            selected = self.find_item_by_id(f"cid:{cid}")
            if selected is None:
                return
        self.code_tree.rename_category_or_code(selected)

    def eventFilter(self, watched, event):
        """ Navigate the tree with the keyboard while typing in the search field.
        Args:
            watched: QObject
            event: QEvent
        Returns:
            True when the key was consumed
        """

        if watched is self.ui.lineEdit_search and event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            if key == QtCore.Qt.Key.Key_Down:
                self.move_selection(1)
                return True
            if key == QtCore.Qt.Key.Key_Up:
                self.move_selection(-1)
                return True
            if key == QtCore.Qt.Key.Key_PageDown:
                self.move_selection(10)
                return True
            if key == QtCore.Qt.Key.Key_PageUp:
                self.move_selection(-10)
                return True
            if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
                self.accept()
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        """
        Enter Apply the selected code
        F2 Rename code or category
        Ctrl P Pin or unpin the selected code
        Esc Close
        """

        key = event.key()
        mods = event.modifiers()
        if key == QtCore.Qt.Key.Key_F2:
            self.rename_selected()
            return
        if key == QtCore.Qt.Key.Key_P and mods == QtCore.Qt.KeyboardModifier.ControlModifier:
            cid = self.current_cid()
            if cid is not None:
                self.toggle_pin(cid)
            return
        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self.accept()
            return
        super().keyPressEvent(event)

    def done(self, result):
        """ Save dialog dimensions on every exit path.
        Args:
            result: Integer dialog result code
        """

        self.app.settings['dialogcodepicker_w'] = self.size().width()
        self.app.settings['dialogcodepicker_h'] = self.size().height()
        super().done(result)
