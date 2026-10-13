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

import datetime
import logging

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt
import qtawesome as qta

from .add_item_name import DialogAddItemName
from .confirm_delete import DialogConfirmDelete
from .helpers import Message
from .memo import DialogMemo
from .select_items import DialogSelectItems

logger = logging.getLogger(__name__)

ALL_KEY = "all"
FOLDER_PREFIX = "folderid:"
FILE_PREFIX = "fid:"

NAME_COL = 0
MEMO_COL = 1
KEY_COL = 2


class FileTreeBase(QtCore.QObject):
    """ Shared behaviour of the Manage files side trees: Name, Id and Memo columns,
    files as leaves, drag and drop between the trees, auto scroll while dragging.
    Host protocol: source (list of file dicts), parent_text_edit, view_file(fid),
    tree_file_selected(fid, ...).
    """

    def __init__(self, app, tree_widget: QtWidgets.QTreeWidget, host, name_header: str):
        super().__init__(tree_widget)
        self.app = app
        self.tree = tree_widget
        self.host = host
        self.peer_trees = []  # Other trees whose items may be dropped here
        self.search_edit = None  # Name filter below the tree, see setup_filter_bar
        self.clear_button = None
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([name_header, _("Memo"), _("Id")])
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.tree_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.viewport().installEventFilter(self)

    # Keys and items

    @staticmethod
    def item_key(item) -> str:
        return item.text(KEY_COL) if item is not None else ""

    @staticmethod
    def key_fid(key):
        if key.startswith(FILE_PREFIX):
            return int(key[len(FILE_PREFIX):])
        return None

    def menu(self) -> QtWidgets.QMenu:
        menu = QtWidgets.QMenu()
        menu.setStyleSheet(f"QMenu {{font-size:{self.app.settings['fontsize']}pt}} ")
        return menu

    def source_by_id(self, fid):
        for s in self.host.source:
            if s['id'] == fid:
                return s
        return None

    def make_file_item(self, source) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([source['name'], "", f"{FILE_PREFIX}{source['id']}"])
        if source.get('icon') is not None:
            item.setIcon(NAME_COL, source['icon'])
        item.setToolTip(NAME_COL, source['name'])
        # Files are leaves, drops onto them resolve to their parent
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled |
                      Qt.ItemFlag.ItemIsDragEnabled)
        return item

    @staticmethod
    def set_memo_cell(item, memo: str):
        """ Show Memo in the memo column, full text in its tooltip. """

        item.setText(MEMO_COL, _("Memo") if memo else "")
        item.setToolTip(MEMO_COL, memo)

    def finish_fill(self):
        self.tree.setColumnHidden(KEY_COL, not self.app.settings['showids'])
        self.tree.resizeColumnToContents(NAME_COL)
        self.tree.resizeColumnToContents(MEMO_COL)

    def selected_fids(self, clicked_fid=None) -> list:
        """ File ids of the selected tree items, plus the clicked file. """

        fids = []
        for item in self.tree.selectedItems():
            fid = self.key_fid(self.item_key(item))
            if fid is not None and fid not in fids:
                fids.append(fid)
        if clicked_fid is not None and clicked_fid not in fids:
            fids.append(clicked_fid)
        return fids

    def select_file(self, fid, parent_key=None):
        """ Highlight a file without changing the tree filter.
        parent_key limits the match to a file under that node. """

        it = QtWidgets.QTreeWidgetItemIterator(self.tree)
        while it.value():
            node = it.value()
            if node.text(KEY_COL) == f"{FILE_PREFIX}{fid}" and \
                    (parent_key is None or self.item_key(node.parent()) == parent_key):
                blocker = QtCore.QSignalBlocker(self.tree)
                self.tree.setCurrentItem(node)
                self.tree.scrollToItem(node)
                blocker.unblock()
                return
            it += 1

    def highlight_key(self, key):
        """ Make the node with this key current without emitting signals. """

        it = QtWidgets.QTreeWidgetItemIterator(self.tree)
        while it.value():
            if it.value().text(KEY_COL) == key:
                blocker = QtCore.QSignalBlocker(self.tree)
                self.tree.setCurrentItem(it.value())
                blocker.unblock()
                return
            it += 1

    def show_root_unselected(self):
        """ Root as current item with nothing highlighted, used when the tree has no filter. """

        blocker = QtCore.QSignalBlocker(self.tree)
        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        self.tree.clearSelection()
        blocker.unblock()

    def clear_filter(self):
        """ Drop the tree filter and its highlight, without emitting signals. """
        raise NotImplementedError

    def has_filter(self) -> bool:
        """ True when the tree selection filters the file table. """
        raise NotImplementedError

    # Filter bar below the tree, as in the codes tree of Code text

    def setup_filter_bar(self, line_edit: QtWidgets.QLineEdit, button: QtWidgets.QPushButton,
                         placeholder: str, clear_tooltip: str):
        self.search_edit = line_edit
        self.clear_button = button
        button.setIcon(qta.icon('mdi6.filter-off-outline', options=[{'scale_factor': 1.3}]))
        button.setToolTip(clear_tooltip)
        # Hidden until a filter is active; keeps its space so the search box does not jump
        policy = button.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        button.setSizePolicy(policy)
        button.setVisible(False)
        button.pressed.connect(self.clear_all_filters)
        line_edit.setPlaceholderText(placeholder)
        line_edit.setClearButtonEnabled(True)
        line_edit.textChanged.connect(self.apply_search)

    def search_text(self) -> str:
        return self.search_edit.text().strip().lower() if self.search_edit is not None else ""

    def apply_search(self):
        """ Show nodes whose name matches, with their ancestors and their contents. """

        text = self.search_text()
        blocker = QtCore.QSignalBlocker(self.tree)

        def visit(item, ancestor_match):
            match = text == "" or text in item.text(NAME_COL).lower()
            child_visible = False
            for i in range(item.childCount()):
                if visit(item.child(i), ancestor_match or match):
                    child_visible = True
            visible = ancestor_match or match or child_visible
            item.setHidden(not visible)
            if text and child_visible:
                item.setExpanded(True)
            return visible

        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            for j in range(root.childCount()):
                visit(root.child(j), False)
            root.setHidden(False)
        blocker.unblock()
        self.update_clear_button()

    def update_clear_button(self):
        """ Blue clear button while the tree selection or the search box filters. """

        if self.clear_button is None:
            return
        active = self.has_filter() or self.search_text() != ""
        self.clear_button.setVisible(active)
        self.clear_button.setStyleSheet("background-color: #1e90ff; color: white;" if active else "")

    def clear_all_filters(self):
        """ Clear the search box and the tree selection, then refresh the table. """

        if self.search_edit is not None:
            self.search_edit.blockSignals(True)
            self.search_edit.clear()
            self.search_edit.blockSignals(False)
            self.apply_search()
        self.clear_filter()
        self.host.folder_selected()

    # Mouse

    def _on_item_clicked(self, item, column):
        if column == MEMO_COL and self.edit_memo(item):
            return
        fid = self.key_fid(self.item_key(item))
        if fid is not None:
            self.file_clicked(item, fid)

    def _on_item_double_clicked(self, item, column):
        fid = self.key_fid(self.item_key(item))
        if fid is not None and column != MEMO_COL:
            self.host.view_file(fid)

    def edit_memo(self, item) -> bool:
        """ Open the memo of a folder or case. Returns True when handled. """
        return False

    def file_clicked(self, item, fid):
        self.host.tree_file_selected(fid)

    # Drag and drop

    def eventFilter(self, object_, event):
        # Event type first: the tree may already be gone when teardown events reach the viewport
        event_type = event.type()
        if event_type not in (QtCore.QEvent.Type.DragEnter, QtCore.QEvent.Type.DragMove,
                              QtCore.QEvent.Type.Drop):
            return False
        if object_ is not self.tree.viewport():
            return False
        source_widget = event.source()
        if source_widget is not self.tree and source_widget not in self.peer_trees:
            return False
        if event_type in (QtCore.QEvent.Type.DragEnter, QtCore.QEvent.Type.DragMove):
            event.acceptProposedAction()
            if event_type == QtCore.QEvent.Type.DragMove:
                self._auto_scroll(event.position().toPoint().y())
            return True
        target = self.tree.itemAt(event.position().toPoint())
        items = source_widget.selectedItems()
        # Ignored on purpose: an accepted move would make the source view delete its rows
        event.ignore()
        self.items_dropped(items, target, source_widget is self.tree)
        return True

    def _auto_scroll(self, y):
        vsb = self.tree.verticalScrollBar()
        top = self.tree.visualRect(self.tree.indexAt(self.tree.rect().topLeft())).bottom()
        bottom = self.tree.viewport().height()
        if y < top + 8:
            vsb.setValue(vsb.value() - 1)
        if y > bottom - 8:
            vsb.setValue(vsb.value() + 1)

    def items_dropped(self, items, target, internal: bool):
        raise NotImplementedError

    def tree_menu(self, position):
        raise NotImplementedError


class FileFolderTreeController(FileTreeBase):
    """ Folder tree for the Manage files dialog. Folders nest without depth limit,
    files are leaves. Drag and drop moves files and folders, as in the codes tree.
    Signals:
        folder_selected(object) - folder id, or None for all files
        folders_changed(list) - changed database table names
    """

    folder_selected = QtCore.pyqtSignal(object)
    folders_changed = QtCore.pyqtSignal(list)

    def __init__(self, app, tree_widget: QtWidgets.QTreeWidget, host):
        super().__init__(app, tree_widget, host, _("Folders"))
        self.folders = []  # Dictionaries: folderid, name, memo, parent_folderid, owner, date
        self.current_folderid = None  # None = all files
        self.collapsed = set()  # Folder keys collapsed by the user, kept across refills
        self._icon_folder = None
        self._icon_all = None
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.tree.currentItemChanged.connect(self._on_current_item_changed)
        self.tree.itemCollapsed.connect(lambda item: self.collapsed.add(item.text(KEY_COL)))
        self.tree.itemExpanded.connect(lambda item: self.collapsed.discard(item.text(KEY_COL)))

    # Data

    def load_folders(self):
        """ Read all folders from the database. """

        cur = self.app.conn.cursor()
        cur.execute("select folderid, name, ifnull(memo,''), parent_folderid, owner, date from source_folder "
                    "order by upper(name)")
        self.folders = [{'folderid': r[0], 'name': r[1], 'memo': r[2], 'parent_folderid': r[3],
                         'owner': r[4], 'date': r[5]} for r in cur.fetchall()]

    def folder_by_id(self, folderid):
        for f in self.folders:
            if f['folderid'] == folderid:
                return f
        return None

    def folder_path(self, folderid) -> str:
        """ Full path of a folder as Parent / Child / Folder. """

        parts = []
        seen = set()
        folder = self.folder_by_id(folderid)
        while folder is not None and folder['folderid'] not in seen:
            seen.add(folder['folderid'])
            parts.insert(0, folder['name'])
            folder = self.folder_by_id(folder['parent_folderid'])
        return " / ".join(parts)

    def branch_folder_ids(self, folderid) -> set:
        """ The folder and every folder nested below it. """

        ids = {folderid}
        pending = [folderid]
        while pending:
            parent = pending.pop()
            for f in self.folders:
                if f['parent_folderid'] == parent and f['folderid'] not in ids:
                    ids.add(f['folderid'])
                    pending.append(f['folderid'])
        return ids

    def branch_file_ids(self, folderid) -> set:
        """ Ids of the files in a folder and all its sub-folders. """

        folder_ids = self.branch_folder_ids(folderid)
        return {s['id'] for s in self.host.source if s.get('folderid') in folder_ids}

    def folder_is_descendant(self, candidate, ancestor) -> bool:
        """ True when candidate is ancestor or sits anywhere below it. """

        return candidate in self.branch_folder_ids(ancestor)

    def sibling_name_exists(self, name, parent_folderid, exclude_folderid=None) -> bool:
        for f in self.folders:
            if f['parent_folderid'] == parent_folderid and f['name'] == name and \
                    f['folderid'] != exclude_folderid:
                return True
        return False

    def filter_file_ids(self):
        """ Ids of the files in the selected branch, None when all files. """

        if self.current_folderid is None:
            return None
        return self.branch_file_ids(self.current_folderid)

    # Tree fill

    @staticmethod
    def key_folderid(key):
        """ Folder id from a tree key, None for the all files root or a file. """

        if key.startswith(FOLDER_PREFIX):
            return int(key[len(FOLDER_PREFIX):])
        return None

    def _make_folder_item(self, folder) -> QtWidgets.QTreeWidgetItem:
        if self._icon_folder is None:
            self._icon_folder = qta.icon('mdi6.folder-outline')
        item = QtWidgets.QTreeWidgetItem([folder['name'], "", f"{FOLDER_PREFIX}{folder['folderid']}"])
        item.setIcon(NAME_COL, self._icon_folder)
        item.setToolTip(NAME_COL, self.folder_path(folder['folderid']))
        self.set_memo_cell(item, folder['memo'])
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled |
                      Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        return item

    def fill_tree(self):
        """ Fill the tree: All files root, nested folders, files as leaves.
        The current folder selection and collapsed branches survive a refill. """

        self.load_folders()
        if self._icon_all is None:
            self._icon_all = qta.icon('mdi6.folder-multiple-outline')
        blocker = QtCore.QSignalBlocker(self.tree)
        self.tree.clear()
        root = QtWidgets.QTreeWidgetItem([_("All files"), "", ALL_KEY])
        root.setIcon(NAME_COL, self._icon_all)
        root.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        self.tree.addTopLevelItem(root)
        node_index = {None: root}
        pending = list(self.folders)
        # Place each folder under its parent, pass by pass. Leftovers have a missing or
        # cyclic parent and go under the root so no folder is ever lost.
        count = 0
        while pending and count < 10000:
            placed = []
            for folder in pending:
                parent_node = node_index.get(folder['parent_folderid'])
                if parent_node is not None:
                    node = self._make_folder_item(folder)
                    parent_node.addChild(node)
                    node_index[folder['folderid']] = node
                    placed.append(folder)
            if not placed:
                break
            for folder in placed:
                pending.remove(folder)
            count += 1
        for folder in pending:
            node = self._make_folder_item(folder)
            root.addChild(node)
            node_index[folder['folderid']] = node
        for source in self.host.source:
            parent_node = node_index.get(source.get('folderid'), root)
            parent_node.addChild(self.make_file_item(source))
        self.tree.expandAll()
        it = QtWidgets.QTreeWidgetItemIterator(self.tree)
        present = set()
        while it.value():
            node = it.value()
            if node.childCount() > 0:
                present.add(node.text(KEY_COL))
            if node.text(KEY_COL) in self.collapsed:
                node.setExpanded(False)
            it += 1
        self.collapsed &= present
        self.finish_fill()
        # Restore the selected folder, fall back to the root when it was deleted
        target = node_index.get(self.current_folderid)
        if self.current_folderid is not None and target is None:
            self.current_folderid = None
            target = root
        self.tree.setCurrentItem(target)
        if self.current_folderid is None:
            self.tree.clearSelection()
        blocker.unblock()
        self.apply_search()

    def set_current_folder(self, folderid):
        """ Change the folder filter from outside the tree. """

        if folderid is None:
            self.clear_filter()
            return
        self.current_folderid = folderid
        self.highlight_key(f"{FOLDER_PREFIX}{folderid}")

    def clear_filter(self):
        self.current_folderid = None
        self.show_root_unselected()

    def has_filter(self) -> bool:
        return self.current_folderid is not None

    # Selection

    def _on_current_item_changed(self, current, previous):
        """ Folder navigation by mouse or keyboard. Files are handled on click only,
        so starting a drag on a file does not change the folder filter. """

        key = self.item_key(current)
        if key == "" or self.key_fid(key) is not None:
            return
        folderid = self.key_folderid(key)
        if folderid != self.current_folderid:
            self.current_folderid = folderid
            self.folder_selected.emit(folderid)

    def edit_memo(self, item) -> bool:
        folderid = self.key_folderid(self.item_key(item))
        if folderid is None:
            return False
        self.folder_memo(folderid)
        return True

    # Drag and drop

    def drop_target_folderid(self, target):
        """ Folder id a drop lands in. Dropping onto a file means that file's folder,
        onto the root or empty space means top level. """

        key = self.item_key(target)
        fid = self.key_fid(key)
        if fid is not None:
            source = self.source_by_id(fid)
            return source.get('folderid') if source is not None else None
        return self.key_folderid(key)

    def items_dropped(self, items, target, internal=True):
        """ Move the dragged folders and files into the target folder.
        Files dragged from the cases tree are moved too. """

        folderid = self.drop_target_folderid(target)
        fids = []
        folder_ids = []
        for item in items:
            key = self.item_key(item)
            fid = self.key_fid(key)
            if fid is not None:
                if fid not in fids:
                    fids.append(fid)
                continue
            moved = self.key_folderid(key) if internal else None
            if moved is not None:
                folder_ids.append(moved)
        changed = False
        for moved in folder_ids:
            if self.move_folder(moved, folderid, refill=False):
                changed = True
        if fids and self.move_files_to_folder(fids, folderid, refill=False):
            changed = True
        if changed:
            self.fill_tree()

    def move_folder(self, folderid, new_parent, refill=True) -> bool:
        """ Re-parent a folder. Refuses cycles and duplicate sibling names. """

        folder = self.folder_by_id(folderid)
        if folder is None or folderid == new_parent or folder['parent_folderid'] == new_parent:
            return False
        if new_parent is not None and self.folder_is_descendant(new_parent, folderid):
            Message(self.app, _("Cannot move folder"),
                    _("Cannot move a folder under one of its own sub-folders.")).exec()
            return False
        if self.sibling_name_exists(folder['name'], new_parent, exclude_folderid=folderid):
            Message(self.app, _("Cannot move folder"),
                    _("A folder with this name already exists there.")).exec()
            return False
        cur = self.app.conn.cursor()
        cur.execute("update source_folder set parent_folderid=? where folderid=?", [new_parent, folderid])
        self.app.conn.commit()
        folder['parent_folderid'] = new_parent
        self.app.delete_backup = False
        # Paths of the files in the branch changed
        self.host.files_folder_changed(self.branch_file_ids(folderid))
        self.folders_changed.emit(["source_folder"])
        if refill:
            self.fill_tree()
        return True

    def move_files_to_folder(self, fids, folderid, refill=True) -> bool:
        """ Assign files to a folder, None for top level. """

        fids = [fid for fid in fids
                if any(s['id'] == fid and s.get('folderid') != folderid for s in self.host.source)]
        if not fids:
            return False
        cur = self.app.conn.cursor()
        for fid in fids:
            cur.execute("update source set folderid=? where id=?", [folderid, fid])
        self.app.conn.commit()
        for s in self.host.source:
            if s['id'] in fids:
                s['folderid'] = folderid
        self.app.delete_backup = False
        self.host.files_folder_changed(fids)
        self.folders_changed.emit(["source"])
        if refill:
            self.fill_tree()
        return True

    # Context menu

    def tree_menu(self, position):
        selected = self.tree.itemAt(position)
        key = self.item_key(selected)
        fid = self.key_fid(key)
        folderid = self.key_folderid(key)
        menu = self.menu()
        action_new = action_rename = action_memo = action_delete = None
        action_view = action_move = action_unfolder = None
        action_expand = action_collapse = None
        if fid is not None:
            action_view = menu.addAction(_("View file"))
            action_move = menu.addAction(_("Move to folder"))
            if self.drop_target_folderid(selected) is not None:
                action_unfolder = menu.addAction(_("Remove from folder"))
        else:
            action_new = menu.addAction(_("New sub-folder") if folderid is not None else _("New folder"))
            if folderid is not None:
                action_rename = menu.addAction(_("Rename folder"))
                action_memo = menu.addAction(_("Memo"))
                action_move = menu.addAction(_("Move folder"))
                action_delete = menu.addAction(_("Delete folder"))
            action_expand = menu.addAction(_("Expand all"))
            action_collapse = menu.addAction(_("Collapse all"))
        action = menu.exec(self.tree.mapToGlobal(position))
        if action is None:
            return
        if action == action_view:
            self.host.view_file(fid)
        elif action == action_move and fid is not None:
            self.move_files_dialog(self.selected_fids(fid))
        elif action == action_unfolder:
            self.move_files_to_folder(self.selected_fids(fid), None)
        elif action == action_new:
            self.add_folder(folderid)
        elif action == action_rename:
            self.rename_folder(folderid)
        elif action == action_memo:
            self.folder_memo(folderid)
        elif action == action_move:
            self.move_folder_dialog(folderid)
        elif action == action_delete:
            self.delete_folder(folderid)
        elif action == action_expand:
            self.collapsed.clear()
            self.tree.expandAll()
        elif action == action_collapse:
            self.tree.collapseAll()
            self.tree.topLevelItem(0).setExpanded(True)

    def add_folder(self, parent_folderid=None):
        """ Create a folder under parent_folderid, None for top level. """

        siblings = [{'name': f['name']} for f in self.folders if f['parent_folderid'] == parent_folderid]
        ui = DialogAddItemName(self.app, siblings, _("New folder"), _("Folder name"))
        ui.exec()
        name = ui.get_new_name()
        if name is None or name.strip() == "":
            return
        name = name.strip()
        cur = self.app.conn.cursor()
        cur.execute("insert into source_folder (name, memo, parent_folderid, owner, date) values (?,?,?,?,?)",
                    [name, "", parent_folderid, self.app.settings['codername'],
                     datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")])
        self.app.conn.commit()
        self.app.delete_backup = False
        self.host.parent_text_edit.append(_("Folder created: ") + name)
        self.folders_changed.emit(["source_folder"])
        self.fill_tree()

    def rename_folder(self, folderid):
        folder = self.folder_by_id(folderid)
        if folder is None:
            return
        siblings = [{'name': f['name']} for f in self.folders
                    if f['parent_folderid'] == folder['parent_folderid'] and f['folderid'] != folderid]
        ui = DialogAddItemName(self.app, siblings, _("Rename folder"), _("New folder name"))
        ui.ui.lineEdit.setText(folder['name'])
        ui.exec()
        name = ui.get_new_name()
        if name is None or name.strip() == "" or name.strip() == folder['name']:
            return
        name = name.strip()
        cur = self.app.conn.cursor()
        cur.execute("update source_folder set name=? where folderid=?", [name, folderid])
        self.app.conn.commit()
        self.app.delete_backup = False
        self.host.parent_text_edit.append(_("Folder renamed: ") + folder['name'] + " -> " + name)
        folder['name'] = name
        self.host.files_folder_changed(self.branch_file_ids(folderid))
        self.folders_changed.emit(["source_folder"])
        self.fill_tree()

    def folder_memo(self, folderid):
        folder = self.folder_by_id(folderid)
        if folder is None:
            return
        ui = DialogMemo(self.app, _("Memo for folder: ") + folder['name'], folder['memo'])
        ui.exec()
        if ui.memo == folder['memo']:
            return
        self.save_folder_memo(folderid, ui.memo)

    def save_folder_memo(self, folderid, memo: str):
        folder = self.folder_by_id(folderid)
        if folder is None:
            return
        folder['memo'] = memo
        cur = self.app.conn.cursor()
        cur.execute("update source_folder set memo=? where folderid=?", [memo, folderid])
        self.app.conn.commit()
        self.app.delete_backup = False
        if memo != "":
            self.host.parent_text_edit.append(_("Memo for folder: ") + folder['name'])
        self.folders_changed.emit(["source_folder"])
        self.fill_tree()

    def folder_choices(self, exclude_branch=None) -> list:
        """ Folder paths for a selection dialog, top level first.
        exclude_branch: folder id whose whole branch is left out. """

        excluded = self.branch_folder_ids(exclude_branch) if exclude_branch is not None else set()
        choices = [{'name': _("(Top level)"), 'folderid': None}]
        paths = [(self.folder_path(f['folderid']), f['folderid']) for f in self.folders
                 if f['folderid'] not in excluded]
        for path_, folderid in sorted(paths, key=lambda p: p[0].lower()):
            choices.append({'name': path_, 'folderid': folderid})
        return choices

    def choose_folder(self, title, exclude_branch=None):
        """ Returns the chosen folder id, None for top level, or False when cancelled. """

        choices = self.folder_choices(exclude_branch)
        ui = DialogSelectItems(self.app, choices, title, "single")
        if not ui.exec():
            return False
        chosen = ui.get_selected()
        if not chosen:
            return False
        return chosen['folderid']

    def move_folder_dialog(self, folderid):
        chosen = self.choose_folder(_("Move folder to"), exclude_branch=folderid)
        if chosen is False:
            return
        self.move_folder(folderid, chosen)

    def move_files_dialog(self, fids):
        """ Ask for a destination folder and move the files there. """

        if not fids:
            return
        chosen = self.choose_folder(_("Move files to folder"))
        if chosen is False:
            return
        self.move_files_to_folder(fids, chosen)

    def delete_folder(self, folderid):
        """ Delete a folder. Its files and sub-folders move up to the parent folder. """

        folder = self.folder_by_id(folderid)
        if folder is None:
            return
        msg = _("Delete folder") + ": " + self.folder_path(folderid) + "\n"
        msg += _("Files and sub-folders are kept and moved to the parent folder.")
        ui = DialogConfirmDelete(self.app, msg)
        if not ui.exec():
            return
        parent = folder['parent_folderid']
        cur = self.app.conn.cursor()
        cur.execute("update source set folderid=? where folderid=?", [parent, folderid])
        cur.execute("update source_folder set parent_folderid=? where parent_folderid=?", [parent, folderid])
        cur.execute("delete from source_folder where folderid=?", [folderid])
        self.app.conn.commit()
        self.app.delete_backup = False
        # Files of the deleted folder and of its whole branch get new paths
        changed = self.branch_file_ids(folderid)
        for s in self.host.source:
            if s.get('folderid') == folderid:
                s['folderid'] = parent
        self.load_folders()
        if self.current_folderid == folderid:
            self.current_folderid = parent
        self.host.parent_text_edit.append(_("Folder deleted: ") + folder['name'])
        self.host.files_folder_changed(changed)
        self.folders_changed.emit(["source_folder", "source"])
        self.fill_tree()
