import collections
import os

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from . import ClientCaches
from . import ClientConstants as CC
from . import (ClientData, ClientGUICommon, ClientGUIFunctions, ClientGUIMenus,
               ClientGUIShortcuts, ClientGUITopLevelWindows, ClientMedia,
               ClientSearch, ClientSerialisable, ClientTags)
from . import HydrusConstants as HC
from . import HydrusData, HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable, HydrusTags
from . import QtPorting as QP


class AddEditDeleteListBox(QW.QWidget):

    listBoxChanged = QC.Signal()

    def __init__(self, parent, height_num_chars, data_to_pretty_callable,
                 add_callable, edit_callable):

        self._data_to_pretty_callable = data_to_pretty_callable
        self._add_callable = add_callable
        self._edit_callable = edit_callable

        QW.QWidget.__init__(self, parent)

        self._listbox = QW.QListWidget(self)
        self._listbox.setSelectionMode(QW.QListWidget.ExtendedSelection)

        self._add_button = ClientGUICommon.BetterButton(self, 'add', self._Add)
        self._edit_button = ClientGUICommon.BetterButton(
            self, 'edit', self._Edit)
        self._delete_button = ClientGUICommon.BetterButton(
            self, 'delete', self._Delete)

        self._enabled_only_on_selection_buttons = []

        self._permitted_object_types = []

        #

        vbox = QP.VBoxLayout()

        self._buttons_hbox = QP.HBoxLayout()

        QP.AddToLayout(self._buttons_hbox, self._add_button,
                       CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(self._buttons_hbox, self._edit_button,
                       CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(self._buttons_hbox, self._delete_button,
                       CC.FLAGS_EXPAND_BOTH_WAYS)

        QP.AddToLayout(vbox, self._listbox, CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(vbox, self._buttons_hbox, CC.FLAGS_EXPAND_PERPENDICULAR)

        self.setLayout(vbox)

        #

        (width, height) = ClientGUIFunctions.ConvertTextToPixels(
            self._listbox, (20, height_num_chars))

        self._listbox.setMinimumWidth(width)
        self._listbox.setMinimumHeight(height)

        #

        self._ShowHideButtons()

        self._listbox.itemSelectionChanged.connect(self._ShowHideButtons)
        self._listbox.itemDoubleClicked.connect(self._Edit)

    def _Add(self):

        try:

            data = self._add_callable()

        except HydrusExceptions.VetoException:

            return

        self._AddData(data)

    def _AddAllDefaults(self, defaults_callable):

        defaults = defaults_callable()

        for default in defaults:

            self._AddData(default)

    def _AddData(self, data):

        self._SetNoneDupeName(data)

        pretty_data = self._data_to_pretty_callable(data)

        item = QW.QListWidgetItem()
        item.setText(pretty_data)
        item.setData(QC.Qt.UserRole, data)
        self._listbox.addItem(item)

    def _AddSomeDefaults(self, defaults_callable):

        defaults = defaults_callable()

        selected = False

        choice_tuples = [(self._data_to_pretty_callable(default), default,
                          selected) for default in defaults]

        from . import ClientGUITopLevelWindows
        from . import ClientGUIScrolledPanelsEdit

        with ClientGUITopLevelWindows.DialogEdit(
                self, 'select the defaults to add') as dlg:

            panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple(
                dlg, choice_tuples)

            dlg.SetPanel(panel)

            if dlg.exec() == QW.QDialog.Accepted:

                defaults_to_add = panel.GetValue()

                for default in defaults_to_add:

                    self._AddData(default)

    def _Delete(self):

        indices = list(
            map(lambda idx: idx.row(), self._listbox.selectedIndexes()))

        if len(indices) == 0:

            return

        indices.sort(reverse=True)

        from . import ClientGUIDialogsQuick

        result = ClientGUIDialogsQuick.GetYesNo(self, 'Remove all selected?')

        if result == QW.QDialog.Accepted:

            for i in indices:

                QP.ListWidgetDelete(self._listbox, i)

        self.listBoxChanged.emit()

    def _Edit(self):

        for i in range(self._listbox.count()):

            if not QP.ListWidgetIsSelected(self._listbox, i):

                continue

            data = QP.GetClientData(self._listbox, i)

            try:

                new_data = self._edit_callable(data)

            except HydrusExceptions.VetoException:

                break

            QP.ListWidgetDelete(self._listbox, i)

            self._SetNoneDupeName(new_data)

            pretty_new_data = self._data_to_pretty_callable(new_data)

            item = QW.QListWidgetItem()
            item.setText(pretty_new_data)
            item.setData(QC.Qt.UserRole, new_data)
            self._listbox.addItem(item)
            self._listbox.insertItem(i, item)

        self.listBoxChanged.emit()

    def _Duplicate(self):

        dupe_data = self._GetExportObject()

        if dupe_data is not None:

            dupe_data = dupe_data.Duplicate()

            self._ImportObject(dupe_data)

    def _ExportToClipboard(self):

        export_object = self._GetExportObject()

        if export_object is not None:

            json = export_object.DumpToString()

            HG.client_controller.pub('clipboard', 'text', json)

    def _ExportToPng(self):

        export_object = self._GetExportObject()

        if export_object is not None:

            from . import ClientGUITopLevelWindows
            from . import ClientGUISerialisable

            with ClientGUITopLevelWindows.DialogNullipotent(
                    self, 'export to png') as dlg:

                panel = ClientGUISerialisable.PngExportPanel(
                    dlg, export_object)

                dlg.SetPanel(panel)

                dlg.exec()

    def _ExportToPngs(self):

        export_object = self._GetExportObject()

        if export_object is None:

            return

        if not isinstance(export_object, HydrusSerialisable.SerialisableList):

            self._ExportToPng()

            return

        from . import ClientGUITopLevelWindows
        from . import ClientGUISerialisable

        with ClientGUITopLevelWindows.DialogNullipotent(
                self, 'export to pngs') as dlg:

            panel = ClientGUISerialisable.PngsExportPanel(dlg, export_object)

            dlg.SetPanel(panel)

            dlg.exec()

    def _GetExportObject(self):

        to_export = HydrusSerialisable.SerialisableList()

        for obj in self.GetData(only_selected=True):

            to_export.append(obj)

        if len(to_export) == 0:

            return None

        elif len(to_export) == 1:

            return to_export[0]

        else:

            return to_export

    def _ImportFromClipboard(self):

        try:

            raw_text = HG.client_controller.GetClipboardText()

        except HydrusExceptions.DataMissing as e:

            QW.QMessageBox.critical(self, 'Error', str(e))

            return

        try:

            obj = HydrusSerialisable.CreateFromString(raw_text)

            self._ImportObject(obj)

        except Exception as e:

            QW.QMessageBox.critical(
                self, 'Error',
                'I could not understand what was in the clipboard')

    def _ImportFromPng(self):

        with QP.FileDialog(self,
                           'select the png or pngs with the encoded data',
                           acceptMode=QW.QFileDialog.AcceptOpen,
                           fileMode=QW.QFileDialog.ExistingFiles,
                           wildcard='PNG (*.png)|*.png') as dlg:

            if dlg.exec() == QW.QDialog.Accepted:

                for path in dlg.GetPaths():

                    try:

                        payload = ClientSerialisable.LoadFromPng(path)

                    except Exception as e:

                        QW.QMessageBox.critical(self, 'Error', str(e))

                        return

                    try:

                        obj = HydrusSerialisable.CreateFromNetworkBytes(
                            payload)

                        self._ImportObject(obj)

                    except:

                        QW.QMessageBox.critical(
                            self, 'Error',
                            'I could not understand what was encoded in the png!'
                        )

                        return

    def _ImportObject(self, obj):

        bad_object_type_names = set()

        if isinstance(obj, HydrusSerialisable.SerialisableList):

            for sub_obj in obj:

                self._ImportObject(sub_obj)

        else:

            if isinstance(obj, self._permitted_object_types):

                self._AddData(obj)

            else:

                bad_object_type_names.add(HydrusData.GetTypeName(type(obj)))

        if len(bad_object_type_names) > 0:

            message = 'The imported objects included these types:'
            message += os.linesep * 2
            message += os.linesep.join(bad_object_type_names)
            message += os.linesep * 2
            message += 'Whereas this control only allows:'
            message += os.linesep * 2
            message += os.linesep.join((HydrusData.GetTypeName(o)
                                        for o in self._permitted_object_types))

            QW.QMessageBox.critical(self, 'Error', message)

    def _SetNoneDupeName(self, obj):

        pass

    def _ShowHideButtons(self):

        if len(self._listbox.selectedItems()) == 0:

            self._edit_button.setEnabled(False)
            self._delete_button.setEnabled(False)

            for button in self._enabled_only_on_selection_buttons:

                button.setEnabled(False)

        else:

            self._edit_button.setEnabled(True)
            self._delete_button.setEnabled(True)

            for button in self._enabled_only_on_selection_buttons:

                button.setEnabled(True)

    def AddDatas(self, datas):

        for data in datas:

            self._AddData(data)

        self.listBoxChanged.emit()

    def AddDefaultsButton(self, defaults_callable):

        import_menu_items = []

        all_call = HydrusData.Call(self._AddAllDefaults, defaults_callable)
        some_call = HydrusData.Call(self._AddSomeDefaults, defaults_callable)

        import_menu_items.append(
            ('normal', 'add them all', 'Load all the defaults.', all_call))
        import_menu_items.append(('normal', 'select from a list',
                                  'Load some of the defaults.', some_call))

        button = ClientGUICommon.MenuButton(self, 'add defaults',
                                            import_menu_items)

        QP.AddToLayout(self._buttons_hbox, button, CC.FLAGS_VCENTER)

    def AddImportExportButtons(self, permitted_object_types):

        self._permitted_object_types = permitted_object_types

        export_menu_items = []

        export_menu_items.append(
            ('normal', 'to clipboard',
             'Serialise the selected data and put it on your clipboard.',
             self._ExportToClipboard))
        export_menu_items.append((
            'normal', 'to png',
            'Serialise the selected data and encode it to an image file you can easily share with other hydrus users.',
            self._ExportToPng))

        all_objs_are_named = False not in (
            issubclass(o, HydrusSerialisable.SerialisableBaseNamed)
            for o in self._permitted_object_types)

        if all_objs_are_named:

            export_menu_items.append((
                'normal', 'to pngs',
                'Serialise the selected data and encode it to multiple image files you can easily share with other hydrus users.',
                self._ExportToPngs))

        import_menu_items = []

        import_menu_items.append(('normal', 'from clipboard',
                                  'Load a data from text in your clipboard.',
                                  self._ImportFromClipboard))
        import_menu_items.append(
            ('normal', 'from pngs', 'Load a data from an encoded png.',
             self._ImportFromPng))

        button = ClientGUICommon.MenuButton(self, 'export', export_menu_items)
        QP.AddToLayout(self._buttons_hbox, button, CC.FLAGS_VCENTER)
        self._enabled_only_on_selection_buttons.append(button)

        button = ClientGUICommon.MenuButton(self, 'import', import_menu_items)
        QP.AddToLayout(self._buttons_hbox, button, CC.FLAGS_VCENTER)

        button = ClientGUICommon.BetterButton(self, 'duplicate',
                                              self._Duplicate)
        QP.AddToLayout(self._buttons_hbox, button, CC.FLAGS_VCENTER)
        self._enabled_only_on_selection_buttons.append(button)

        self._ShowHideButtons()

    def AddSeparator(self):

        QP.AddToLayout(self._buttons_hbox, (20, 20),
                       CC.FLAGS_EXPAND_PERPENDICULAR)

    def GetCount(self):

        return self._listbox.count()

    def GetData(self, only_selected=False):

        datas = []

        for i in range(self._listbox.count()):

            if only_selected and not QP.ListWidgetIsSelected(self._listbox, i):

                continue

            data = QP.GetClientData(self._listbox, i)

            datas.append(data)

        return datas

    def GetValue(self):

        return self.GetData()


class AddEditDeleteListBoxUniqueNamedObjects(AddEditDeleteListBox):
    def _SetNoneDupeName(self, obj):

        disallowed_names = {o.GetName() for o in self.GetData()}

        HydrusSerialisable.SetNonDupeName(obj, disallowed_names)


class QueueListBox(QW.QWidget):

    listBoxChanged = QC.Signal()

    def __init__(self,
                 parent,
                 height_num_chars,
                 data_to_pretty_callable,
                 add_callable=None,
                 edit_callable=None):

        self._data_to_pretty_callable = data_to_pretty_callable
        self._add_callable = add_callable
        self._edit_callable = edit_callable

        QW.QWidget.__init__(self, parent)

        self._listbox = QW.QListWidget(self)
        self._listbox.setSelectionMode(QW.QListWidget.ExtendedSelection)

        self._up_button = ClientGUICommon.BetterButton(self, '\u2191',
                                                       self._Up)

        self._delete_button = ClientGUICommon.BetterButton(
            self, 'X', self._Delete)

        self._down_button = ClientGUICommon.BetterButton(
            self, '\u2193', self._Down)

        self._add_button = ClientGUICommon.BetterButton(self, 'add', self._Add)
        self._edit_button = ClientGUICommon.BetterButton(
            self, 'edit', self._Edit)

        if self._add_callable is None:

            self._add_button.hide()

        if self._edit_callable is None:

            self._edit_button.hide()

        #

        vbox = QP.VBoxLayout()

        buttons_vbox = QP.VBoxLayout()

        QP.AddToLayout(buttons_vbox, self._up_button, CC.FLAGS_VCENTER)
        QP.AddToLayout(buttons_vbox, self._delete_button, CC.FLAGS_VCENTER)
        QP.AddToLayout(buttons_vbox, self._down_button, CC.FLAGS_VCENTER)

        hbox = QP.HBoxLayout()

        QP.AddToLayout(hbox, self._listbox, CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(hbox, buttons_vbox, CC.FLAGS_VCENTER)

        buttons_hbox = QP.HBoxLayout()

        QP.AddToLayout(buttons_hbox, self._add_button,
                       CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(buttons_hbox, self._edit_button,
                       CC.FLAGS_EXPAND_BOTH_WAYS)

        QP.AddToLayout(vbox, hbox, CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(vbox, buttons_hbox, CC.FLAGS_EXPAND_PERPENDICULAR)

        self.setLayout(vbox)

        #

        (width, height) = ClientGUIFunctions.ConvertTextToPixels(
            self._listbox, (20, height_num_chars))

        self._listbox.setMinimumWidth(width)
        self._listbox.setMinimumHeight(height)

        #

        self._listbox.itemSelectionChanged.connect(self.EventSelection)
        self._listbox.itemDoubleClicked.connect(self._Edit)

    def _Add(self):

        try:

            data = self._add_callable()

        except HydrusExceptions.VetoException:

            return

        self._AddData(data)

    def _AddData(self, data):

        pretty_data = self._data_to_pretty_callable(data)

        item = QW.QListWidgetItem()
        item.setText(pretty_data)
        item.setData(QC.Qt.UserRole, data)
        self._listbox.addItem(item)

    def _Delete(self):

        indices = list(self._listbox.selectedIndexes())

        if len(indices) == 0:

            return

        indices.sort(reverse=True)

        from . import ClientGUIDialogsQuick

        result = ClientGUIDialogsQuick.GetYesNo(self, 'Remove all selected?')

        if result == QW.QDialog.Accepted:

            for i in indices:

                QP.ListWidgetDelete(self._listbox, i)

            self.listBoxChanged.emit()

    def _Down(self):

        indices = list(
            map(lambda idx: idx.row(), self._listbox.selectedIndexes()))

        indices.sort(reverse=True)

        for i in indices:

            if i < self._listbox.count() - 1:

                if not QP.ListWidgetIsSelected(
                        self._listbox,
                        i + 1):  # is the one below not selected?

                    self._SwapRows(i, i + 1)

        self.listBoxChanged.emit()

    def _Edit(self):

        for i in range(self._listbox.count()):

            if not QP.ListWidgetIsSelected(self._listbox, i):

                continue

            data = QP.GetClientData(self._listbox, i)

            try:

                new_data = self._edit_callable(data)

            except HydrusExceptions.VetoException:

                break

            QP.ListWidgetDelete(self._listbox, i)

            pretty_new_data = self._data_to_pretty_callable(new_data)

            new_item = QW.QListWidgetItem()
            new_item.setText(pretty_new_data)
            new_item.setData(QC.Qt.UserRole, new_data)

            self._listbox.insertItem(i, new_item)

        self.listBoxChanged.emit()

    def _SwapRows(self, index_a, index_b):

        a_was_selected = QP.ListWidgetIsSelected(self._listbox, index_a)
        b_was_selected = QP.ListWidgetIsSelected(self._listbox, index_b)

        data_a = QP.GetClientData(self._listbox, index_a)
        data_b = QP.GetClientData(self._listbox, index_b)

        pretty_data_a = self._data_to_pretty_callable(data_a)
        pretty_data_b = self._data_to_pretty_callable(data_b)

        QP.ListWidgetDelete(self._listbox, index_a)

        item_b = QW.QListWidgetItem()
        item_b.setText(pretty_data_b)
        item_b.setData(QC.Qt.UserRole, data_b)
        self._listbox.insertItem(index_a, item_b)

        QP.ListWidgetDelete(self._listbox, index_b)

        item_a = QW.QListWidgetItem()
        item_a.setText(pretty_data_a)
        item_a.setData(QC.Qt.UserRole, data_a)
        self._listbox.insertItem(index_b, item_a)

        if b_was_selected:

            QP.ListWidgetSetSelection(self._listbox, index_a)

        if a_was_selected:

            QP.ListWidgetSetSelection(self._listbox, index_b)

    def _Up(self):

        indices = map(lambda idx: idx.row(), self._listbox.selectedIndexes())

        for i in indices:

            if i > 0:

                if not QP.ListWidgetIsSelected(
                        self._listbox,
                        i - 1):  # is the one above not selected?

                    self._SwapRows(i, i - 1)

        self.listBoxChanged.emit()

    def AddDatas(self, datas):

        for data in datas:

            self._AddData(data)

        self.listBoxChanged.emit()

    def EventSelection(self):

        if len(self._listbox.selectedIndexes()) == 0:

            self._up_button.setEnabled(False)
            self._delete_button.setEnabled(False)
            self._down_button.setEnabled(False)

            self._edit_button.setEnabled(False)

        else:

            self._up_button.setEnabled(True)
            self._delete_button.setEnabled(True)
            self._down_button.setEnabled(True)

            self._edit_button.setEnabled(True)

    def GetCount(self):

        return self._listbox.count()

    def GetData(self, only_selected=False):

        datas = []

        for i in range(self._listbox.count()):

            data = QP.GetClientData(self._listbox, i)

            datas.append(data)

        return datas

    def Pop(self):

        if self._listbox.count() == 0:

            return None

        data = QP.GetClientData(self._listbox, 0)

        QP.ListWidgetDelete(self._listbox, 0)

        return data


class ListBox(QW.QScrollArea):

    listBoxChanged = QC.Signal()

    TEXT_X_PADDING = 3

    def __init__(self, parent, height_num_chars=10):

        QW.QScrollArea.__init__(self, parent)
        self.setFrameStyle(QW.QFrame.Panel | QW.QFrame.Sunken)
        self.setHorizontalScrollBarPolicy(QC.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QC.Qt.ScrollBarAsNeeded)
        self.setWidget(ListBox._InnerWidget(self))
        self.setWidgetResizable(True)

        self._background_colour = QG.QColor(255, 255, 255)

        self._terms = set()
        self._ordered_terms = []
        self._selected_terms = set()
        self._terms_to_texts = {}

        self._last_hit_index = None

        self._last_view_start = None

        self._height_num_chars = height_num_chars
        self._minimum_height_num_chars = 8

        self._num_rows_per_page = 0

        self.setFont(QW.QApplication.font())

        self._widget_event_filter = QP.WidgetEventFilter(self.widget())

        self._widget_event_filter.EVT_LEFT_DOWN(self.EventMouseSelect)
        self._widget_event_filter.EVT_RIGHT_DOWN(self.EventMouseSelect)
        self._widget_event_filter.EVT_LEFT_DCLICK(self.EventDClick)

    def __len__(self):

        return len(self._ordered_terms)

    def __bool__(self):

        return QP.isValid(self)

    def _Activate(self):

        pass

    def _DeleteActivate(self):

        pass

    def _AppendTerm(self, term):

        was_selected_before = term in self._selected_terms

        if term in self._terms:

            self._RemoveTerm(term)

        self._terms.add(term)
        self._ordered_terms.append(term)

        self._terms_to_texts[term] = self._GetTextFromTerm(term)

        if was_selected_before:

            self._selected_terms.add(term)

    def _CanHitIndex(self, index):

        return True

    def _CanSelectIndex(self, index):

        return True

    def _Clear(self):

        self._terms = set()
        self._ordered_terms = []
        self._selected_terms = set()
        self._terms_to_texts = {}

        self._last_hit_index = None

        self._last_view_start = None

    def _DataHasChanged(self):

        self._SetVirtualSize()

        self.widget().update()

        self.listBoxChanged.emit()

    def _Deselect(self, index):

        term = self._GetTerm(index)

        self._selected_terms.discard(term)

    def _DeselectAll(self):

        self._selected_terms = set()

    def _GetIndexUnderMouse(self, mouse_event):

        y = mouse_event.pos().y()

        text_height = self.fontMetrics().height()

        row_index = y // text_height

        if row_index >= len(self._ordered_terms):

            return None

        return row_index

    def _GetSelectedIncludeExcludePredicates(self):

        include_predicates = []
        exclude_predicates = []

        for term in self._selected_terms:

            if isinstance(term, ClientSearch.Predicate):

                include_predicates.append(term)

                possible_inverse = term.GetInverseCopy()

                if possible_inverse is not None:

                    exclude_predicates.append(possible_inverse)

            else:

                s = term

                include_predicates.append(
                    ClientSearch.Predicate(HC.PREDICATE_TYPE_TAG, term))
                exclude_predicates.append(
                    ClientSearch.Predicate(HC.PREDICATE_TYPE_TAG, term, False))

        return (include_predicates, exclude_predicates)

    def _GetTerm(self, index):

        if index < 0 or index > len(self._ordered_terms) - 1:

            raise HydrusExceptions.DataMissing('No term for index ' +
                                               str(index))

        return self._ordered_terms[index]

    def _GetTextsAndColours(self, term):

        text = self._terms_to_texts[term]

        return [(text, (0, 111, 250))]

    def _GetSafeHitIndex(self, hit_index, direction=None):

        if direction is None:

            if hit_index == 0:

                direction = 1

            else:

                direction = -1

        num_terms = len(self._ordered_terms)

        if num_terms == 0:

            return None

        original_hit_index = hit_index

        if hit_index is not None:

            # if click/selection is out of bounds, fix it
            if hit_index == -1 or hit_index > num_terms:

                hit_index = num_terms - 1

            elif hit_index == num_terms or hit_index < -1:

                hit_index = 0

            # while it is not ok to hit, move index

            while not self._CanHitIndex(hit_index):

                hit_index = (hit_index + direction) % num_terms

                if hit_index == original_hit_index:

                    # bail out if we circled around not finding an ok one to hit

                    return None

        return hit_index

    def _GetSimplifiedTextFromTerm(self, term):

        return self._GetTextFromTerm(term)

    def _GetTextFromTerm(self, term):

        raise NotImplementedError()

    def _HandleClick(self, event):

        hit_index = self._GetIndexUnderMouse(event)

        shift = event.modifiers() & QC.Qt.ShiftModifier
        ctrl = event.modifiers() & QC.Qt.ControlModifier

        self._Hit(shift, ctrl, hit_index)

    def _Hit(self, shift, ctrl, hit_index):

        hit_index = self._GetSafeHitIndex(hit_index)

        to_select = set()
        to_deselect = set()

        deselect_all = False

        if shift:

            if hit_index is not None:

                if self._last_hit_index is not None:

                    lower = min(hit_index, self._last_hit_index)
                    upper = max(hit_index, self._last_hit_index)

                    to_select = list(range(lower, upper + 1))

                else:

                    to_select.add(hit_index)

        elif ctrl:

            if hit_index is not None:

                if self._IsSelected(hit_index):

                    to_deselect.add(hit_index)

                else:

                    to_select.add(hit_index)

        else:

            if hit_index is None:

                deselect_all = True

            else:

                if not self._IsSelected(hit_index):

                    deselect_all = True
                    to_select.add(hit_index)

        if deselect_all:

            self._DeselectAll()

        for index in to_select:

            self._Select(index)

        for index in to_deselect:

            self._Deselect(index)

        self._last_hit_index = hit_index

        if self._last_hit_index is not None:

            text_height = self.fontMetrics().height()

            y = text_height * self._last_hit_index

            visible_rect = QP.ScrollAreaVisibleRect(self)

            visible_rect_y = visible_rect.y()

            visible_rect_height = visible_rect.height()

            if y < visible_rect_y:

                self.ensureVisible(0, y, 0, 0)

            elif y > visible_rect_y + visible_rect_height - text_height:

                self.ensureVisible(0, y + text_height, 0, 0)

        self.widget().update()

    def _IsSelected(self, index):

        try:

            term = self._GetTerm(index)

        except HydrusExceptions.DataMissing:

            return False

        return term in self._selected_terms

    def _Redraw(self, painter):

        text_height = self.fontMetrics().height()

        visible_rect = QP.ScrollAreaVisibleRect(self)

        visible_rect_y = visible_rect.y()

        visible_rect_width = visible_rect.width()
        visible_rect_height = visible_rect.height()

        first_visible_index = visible_rect_y // text_height

        last_visible_index = (visible_rect_y +
                              visible_rect_height) // text_height

        if (visible_rect_y + visible_rect_height) % text_height != 0:

            last_visible_index += 1

        last_visible_index = min(last_visible_index,
                                 len(self._ordered_terms) - 1)

        painter.setBackground(QG.QBrush(self._background_colour))

        painter.eraseRect(painter.viewport())

        for (i, current_index) in enumerate(
                range(first_visible_index, last_visible_index + 1)):

            term = self._GetTerm(current_index)

            texts_and_colours = self._GetTextsAndColours(term)

            there_is_more_than_one_text = len(texts_and_colours) > 1

            x_start = self.TEXT_X_PADDING

            for (text, (r, g, b)) in texts_and_colours:

                text_colour = QG.QColor(r, g, b)

                if term in self._selected_terms:

                    painter.setBrush(QG.QBrush(text_colour))

                    painter.setPen(QC.Qt.NoPen)

                    if x_start == self.TEXT_X_PADDING:

                        background_colour_x = 0

                    else:

                        background_colour_x = x_start

                    painter.drawRect(background_colour_x,
                                     current_index * text_height,
                                     visible_rect_width, text_height)

                    text_colour = self._background_colour

                painter.setPen(QG.QPen(text_colour))

                (x, y) = (x_start, current_index * text_height)

                (this_text_width,
                 this_text_height) = painter.fontMetrics().size(
                     QC.Qt.TextSingleLine, text).toTuple()

                painter.drawText(
                    QC.QRectF(x, y, this_text_width, this_text_height), text)

                if there_is_more_than_one_text:

                    x_start += this_text_width

    def _RefreshTexts(self):

        self._terms_to_texts = {
            term: self._GetTextFromTerm(term)
            for term in self._terms
        }

        self.widget().update()

    def _RemoveSelectedTerms(self):

        for term in list(self._selected_terms):

            self._RemoveTerm(term)

    def _RemoveTerm(self, term):

        if term in self._terms:

            self._terms.discard(term)

            self._ordered_terms.remove(term)

            self._selected_terms.discard(term)

            del self._terms_to_texts[term]

    def _Select(self, index):

        if not self._CanSelectIndex(index):

            return

        term = self._GetTerm(index)

        self._selected_terms.add(term)

    def _SelectAll(self):

        self._selected_terms = set(self._terms)

    def _SetVirtualSize(self):

        self.setWidgetResizable(True)

        (my_x, my_y) = self.widget().size().toTuple()

        text_height = self.fontMetrics().height()

        ideal_virtual_size = QC.QSize(my_x,
                                      text_height * len(self._ordered_terms))

        if ideal_virtual_size != self.widget().size():

            self.widget().setMinimumSize(ideal_virtual_size)

    def _SortByText(self):
        def lexicographic_key(term):

            return self._terms_to_texts[term]

        self._ordered_terms.sort(key=lexicographic_key)

    def keyPressEvent(self, event):

        shift = event.modifiers() & QC.Qt.ShiftModifier
        ctrl = event.modifiers() & QC.Qt.ControlModifier

        key_code = event.key()

        if self.hasFocus() and key_code in CC.DELETE_KEYS:

            self._DeleteActivate()

        elif key_code in (QC.Qt.Key_Enter, QC.Qt.Key_Return):

            self._Activate()

        else:

            if ctrl and key_code in (ord('A'), ord('a')):

                self._SelectAll()

                self.widget().update()

            else:

                hit_index = None

                if len(self._ordered_terms) > 1:

                    roll_up = False
                    roll_down = False

                    if key_code in (QC.Qt.Key_Home, ):

                        hit_index = 0

                    elif key_code in (QC.Qt.Key_End, ):

                        hit_index = len(self._ordered_terms) - 1

                        roll_up = True

                    elif self._last_hit_index is not None:

                        if key_code in (QC.Qt.Key_Up, ):

                            hit_index = self._last_hit_index - 1

                            roll_up = True

                        elif key_code in (QC.Qt.Key_Down, ):

                            hit_index = self._last_hit_index + 1

                            roll_down = True

                        elif key_code in (QC.Qt.Key_PageUp, ):

                            hit_index = max(
                                0,
                                self._last_hit_index - self._num_rows_per_page)

                            roll_up = True

                        elif key_code in (QC.Qt.Key_PageDown, ):

                            hit_index = min(
                                len(self._ordered_terms) - 1,
                                self._last_hit_index + self._num_rows_per_page)

                            roll_down = True

                if hit_index is None:

                    # don't send to parent, which will do silly scroll window business with arrow key presses
                    event.ignore()

                else:

                    if roll_up:

                        hit_index = self._GetSafeHitIndex(hit_index, -1)

                    if roll_down:

                        hit_index = self._GetSafeHitIndex(hit_index, 1)

                    self._Hit(shift, ctrl, hit_index)

    def EventDClick(self, event):

        self._Activate()

    def EventMouseSelect(self, event):

        self._HandleClick(event)

        return True  # was: event.ignore()

    class _InnerWidget(QW.QWidget):
        def __init__(self, parent):

            QW.QWidget.__init__(self, parent)

            self._parent = parent

        def paintEvent(self, event):

            self._parent._SetVirtualSize()

            painter = QG.QPainter(self)

            self._parent._Redraw(painter)

    def resizeEvent(self, event):

        text_height = self.fontMetrics().height()

        visible_rect = QP.ScrollAreaVisibleRect(self)

        self.verticalScrollBar().setSingleStep(text_height)

        visible_rect_height = visible_rect.height()

        self._num_rows_per_page = visible_rect_height // text_height

        self._SetVirtualSize()

        self.widget().update()

    def GetClientData(self, index=None):

        if index is None:

            return set(self._terms)

        else:

            return self._GetTerm(index)

    def GetIdealHeight(self):

        text_height = self.fontMetrics().height()

        return text_height * len(self._ordered_terms) + 20

    def HasValues(self):

        return len(self._ordered_terms) > 0

    def minimumSizeHint(self):

        size_hint = QW.QScrollArea.minimumSizeHint(self)

        text_height = self.fontMetrics().height()

        minimum_height = self._minimum_height_num_chars * text_height + (
            self.frameWidth() * 2)

        size_hint.setHeight(minimum_height)

        return size_hint

    def MoveSelectionDown(self):

        if len(self._ordered_terms) > 1 and self._last_hit_index is not None:

            hit_index = (self._last_hit_index + 1) % len(self._ordered_terms)

            hit_index = self._GetSafeHitIndex(hit_index, 1)

            self._Hit(False, False, hit_index)

    def MoveSelectionUp(self):

        if len(self._ordered_terms) > 1 and self._last_hit_index is not None:

            hit_index = (self._last_hit_index - 1) % len(self._ordered_terms)

            hit_index = self._GetSafeHitIndex(hit_index, -1)

            self._Hit(False, False, hit_index)

    def SetMinimumHeightNumChars(self, minimum_height_num_chars):

        self._minimum_height_num_chars = minimum_height_num_chars

    def sizeHint(self):

        size_hint = QW.QScrollArea.sizeHint(self)

        text_height = self.fontMetrics().height()

        ideal_height = self._height_num_chars * text_height + (
            self.frameWidth() * 2)

        size_hint.setHeight(ideal_height)

        return size_hint


class ListBoxTags(ListBox):

    ors_are_under_construction = False
    has_counts = False

    can_spawn_new_windows = True

    def __init__(self, *args, **kwargs):

        ListBox.__init__(self, *args, **kwargs)

        self._get_current_predicates_callable = None

        self._tag_display_type = ClientTags.TAG_DISPLAY_STORAGE

        self._page_key = None  # placeholder. if a subclass sets this, it changes menu behaviour to allow 'select this tag' menu pubsubs

        self._UpdateBackgroundColour()

        self._widget_event_filter.EVT_MIDDLE_DOWN(self.EventMouseMiddleClick)

        HG.client_controller.sub(self, 'ForceTagRecalc',
                                 'refresh_all_tag_presentation_gui')
        HG.client_controller.sub(self, '_UpdateBackgroundColour',
                                 'notify_new_colourset')

    def _GetNamespaceColours(self):

        return HC.options['namespace_colours']

    def _GetAllTagsForClipboard(self, with_counts=False):

        texts = [self._terms_to_texts[term] for term in self._ordered_terms]

        return texts

    def _GetNamespaceFromTerm(self, term):

        raise NotImplementedError()

    def _GetTagFromTerm(self, term):

        if isinstance(term, ClientSearch.Predicate):

            if term.GetType() == HC.PREDICATE_TYPE_TAG:

                return term.GetValue()

            else:

                return None

        else:

            return term

    def _GetTextsAndColours(self, term):

        namespace_colours = self._GetNamespaceColours()

        if isinstance(term, ClientSearch.Predicate) and term.GetType(
        ) == HC.PREDICATE_TYPE_OR_CONTAINER:

            texts_and_namespaces = term.GetTextsAndNamespaces(
                or_under_construction=self.ors_are_under_construction)

        else:

            text = self._terms_to_texts[term]

            namespace = self._GetNamespaceFromTerm(term)

            texts_and_namespaces = [(text, namespace)]

        texts_and_colours = []

        for (text, namespace) in texts_and_namespaces:

            if namespace in namespace_colours:

                (r, g, b) = namespace_colours[namespace]

            else:

                (r, g, b) = namespace_colours[None]

            texts_and_colours.append((text, (r, g, b)))

        return texts_and_colours

    def _NewSearchPage(self):

        predicates = []

        for term in self._selected_terms:

            if isinstance(term, ClientSearch.Predicate):

                predicates.append(term)

            else:

                predicates.append(
                    ClientSearch.Predicate(HC.PREDICATE_TYPE_TAG, term))

        predicates = HG.client_controller.gui.FleshOutPredicates(predicates)

        if len(predicates) > 0:

            s = [predicate.ToString() for predicate in predicates]

            s.sort()

            page_name = ', '.join(s)

            activate_window = HG.client_controller.new_options.GetBoolean(
                'activate_window_on_tag_search_page_activation')

            HG.client_controller.pub('new_page_query',
                                     CC.LOCAL_FILE_SERVICE_KEY,
                                     initial_predicates=predicates,
                                     page_name=page_name,
                                     activate_window=activate_window)

    def _NewSearchPageForEach(self):

        predicates = []

        for term in self._selected_terms:

            if isinstance(term, ClientSearch.Predicate):

                predicates.append(term)

            else:

                predicates.append(
                    ClientSearch.Predicate(HC.PREDICATE_TYPE_TAG, term))

        predicates = HG.client_controller.gui.FleshOutPredicates(predicates)

        for predicate in predicates:

            page_name = predicate.ToString()

            HG.client_controller.pub('new_page_query',
                                     CC.LOCAL_FILE_SERVICE_KEY,
                                     initial_predicates=(predicate, ),
                                     page_name=page_name)

    def _ProcessMenuCopyEvent(self, command):

        if command in ('copy_terms', 'copy_sub_terms'):

            texts = []

            for term in self._selected_terms:

                if isinstance(term, ClientSearch.Predicate):

                    text = term.ToString(with_count=False)

                else:

                    text = str(term)

                if command == 'copy_sub_terms':

                    (namespace_gumpf, text) = HydrusTags.SplitTag(text)

                texts.append(text)

            texts.sort()

            text = os.linesep.join(texts)

        elif command in ('copy_all_tags', 'copy_all_tags_with_counts'):

            if command == 'copy_all_tags':

                with_counts = False

            else:

                with_counts = True

            texts = self._GetAllTagsForClipboard(with_counts=with_counts)

            text = os.linesep.join(texts)

        HG.client_controller.pub('clipboard', 'text', text)

    def _ProcessMenuPredicateEvent(self, command):

        pass

    def _ProcessMenuTagEvent(self, command):

        tags = [self._GetTagFromTerm(term) for term in self._selected_terms]

        tags = [tag for tag in tags if tag is not None]

        if command in ('hide', 'hide_namespace'):

            if len(tags) == 1:

                (tag, ) = tags

                if command == 'hide':

                    HG.client_controller.tag_display_manager.HideTag(
                        self._tag_display_type, CC.COMBINED_TAG_SERVICE_KEY,
                        tag)

                elif command == 'hide_namespace':

                    (namespace, subtag) = HydrusTags.SplitTag(tag)

                    if namespace != '':

                        namespace += ':'

                    HG.client_controller.tag_display_manager.HideTag(
                        self._tag_display_type, CC.COMBINED_TAG_SERVICE_KEY,
                        namespace)

                HG.client_controller.pub('notify_new_tag_display_rules')

        else:

            from . import ClientGUITags

            if command == 'parent':

                title = 'manage tag parents'

            elif command == 'sibling':

                title = 'manage tag siblings'

            with ClientGUITopLevelWindows.DialogManage(self, title) as dlg:

                if command == 'parent':

                    panel = ClientGUITags.ManageTagParents(dlg, tags)

                elif command == 'sibling':

                    panel = ClientGUITags.ManageTagSiblings(dlg, tags)

                dlg.SetPanel(panel)

                dlg.exec()

    def _UpdateBackgroundColour(self):

        new_options = HG.client_controller.new_options

        self._background_colour = new_options.GetColour(CC.COLOUR_TAGS_BOX)

        self.widget().update()

    def EventMouseMiddleClick(self, event):

        self._HandleClick(event)

        if self.can_spawn_new_windows:

            self._NewSearchPage()

    def contextMenuEvent(self, event):

        if event.reason() == QG.QContextMenuEvent.Keyboard:

            self.ShowMenu()

    def mouseReleaseEvent(self, event):

        if event.button() != QC.Qt.RightButton:

            ListBox.mouseReleaseEvent(self, event)

            return

        self.ShowMenu()

    def ShowMenu(self):

        if len(self._ordered_terms) > 0:

            menu = QW.QMenu()

            copy_menu = QW.QMenu(menu)

            selected_tags = set()

            if len(self._selected_terms) > 0:

                for term in self._selected_terms:

                    if isinstance(term, ClientSearch.Predicate):

                        if term.GetType(
                        ) == HC.PREDICATE_TYPE_TAG and term.IsInclusive():

                            selected_tags.add(term.GetValue())

                    else:

                        selected_tags.add(term)

                siblings = []

                if len(selected_tags) == 1:

                    (selected_tag, ) = selected_tags

                    (selected_namespace,
                     selected_subtag) = HydrusTags.SplitTag(selected_tag)

                    siblings = set(
                        HG.client_controller.tag_siblings_manager.
                        GetAllSiblings(CC.COMBINED_TAG_SERVICE_KEY,
                                       selected_tag))

                    siblings.discard(selected_tag)
                    siblings.discard(selected_subtag)

                    siblings = list(siblings)

                    HydrusTags.SortNumericTags(siblings)

                if len(self._selected_terms) == 1:

                    (term, ) = self._selected_terms

                    if isinstance(term, ClientSearch.Predicate):

                        selection_string = term.ToString(with_count=False)

                    else:

                        selection_string = str(term)

                else:

                    selection_string = 'selected'

                ClientGUIMenus.AppendMenuItem(
                    copy_menu, selection_string,
                    'Copy the selected predicates to your clipboard.',
                    self._ProcessMenuCopyEvent, 'copy_terms')

                if len(self._selected_terms) == 1:

                    (namespace, subtag) = HydrusTags.SplitTag(selection_string)

                    if namespace != '':

                        sub_selection_string = subtag

                        ClientGUIMenus.AppendMenuItem(
                            copy_menu, sub_selection_string,
                            'Copy the selected sub-predicate to your clipboard.',
                            self._ProcessMenuCopyEvent, 'copy_sub_terms')

                else:

                    ClientGUIMenus.AppendMenuItem(
                        copy_menu, 'selected subtags',
                        'Copy the selected sub-predicates to your clipboard.',
                        self._ProcessMenuCopyEvent, 'copy_sub_terms')

                if len(siblings) > 0:

                    siblings_menu = QW.QMenu(copy_menu)

                    for sibling in siblings:

                        ClientGUIMenus.AppendMenuItem(
                            siblings_menu, sibling,
                            'Copy the selected tag sibling to your clipboard.',
                            HG.client_controller.pub, 'clipboard', 'text',
                            sibling)

                        if len(self._selected_terms) == 1:

                            (sibling_namespace,
                             sibling_subtag) = HydrusTags.SplitTag(sibling)

                            if sibling_namespace != '':

                                ClientGUIMenus.AppendMenuItem(
                                    siblings_menu, sibling_subtag,
                                    'Copy the selected sibling subtag to your clipboard.',
                                    HG.client_controller.pub, 'clipboard',
                                    'text', sibling_subtag)

                    ClientGUIMenus.AppendMenu(copy_menu, siblings_menu,
                                              'siblings')

            if len(self._ordered_terms) > len(self._selected_terms):

                ClientGUIMenus.AppendSeparator(copy_menu)

                ClientGUIMenus.AppendMenuItem(
                    copy_menu, 'all tags',
                    'Copy all the predicates in this list to your clipboard.',
                    self._ProcessMenuCopyEvent, 'copy_all_tags')

                if self.has_counts:

                    ClientGUIMenus.AppendMenuItem(
                        copy_menu, 'all tags with counts',
                        'Copy all the predicates in this list, with their counts, to your clipboard.',
                        self._ProcessMenuCopyEvent,
                        'copy_all_tags_with_counts')

            if len(self._ordered_terms) > 0:

                ClientGUIMenus.AppendMenu(menu, copy_menu, 'copy')

            if len(self._selected_terms) > 0:

                if len(selected_tags) > 0:

                    if self._page_key is not None:

                        select_menu = QW.QMenu(menu)

                        tags_sorted_to_show_on_menu = HydrusTags.SortNumericTags(
                            selected_tags)

                        tags_sorted_to_show_on_menu_string = ', '.join(
                            tags_sorted_to_show_on_menu)

                        while len(tags_sorted_to_show_on_menu_string) > 64:

                            if len(tags_sorted_to_show_on_menu) == 1:

                                tags_sorted_to_show_on_menu_string = '(many/long tags)'

                            else:

                                tags_sorted_to_show_on_menu.pop(-1)

                                tags_sorted_to_show_on_menu_string = ', '.join(
                                    tags_sorted_to_show_on_menu + ['\u2026'])

                        if len(selected_tags) == 1:

                            label = 'files with "{}"'.format(
                                tags_sorted_to_show_on_menu_string)

                        else:

                            label = 'files with all of "{}"'.format(
                                tags_sorted_to_show_on_menu_string)

                        ClientGUIMenus.AppendMenuItem(
                            select_menu, label,
                            'Select the files with these tags.',
                            HG.client_controller.pub, 'select_files_with_tags',
                            self._page_key, 'AND', set(selected_tags))

                        if len(selected_tags) > 1:

                            label = 'files with any of "{}"'.format(
                                tags_sorted_to_show_on_menu_string)

                            ClientGUIMenus.AppendMenuItem(
                                select_menu, label,
                                'Select the files with any of these tags.',
                                HG.client_controller.pub,
                                'select_files_with_tags', self._page_key, 'OR',
                                set(selected_tags))

                        ClientGUIMenus.AppendMenu(menu, select_menu, 'select')

                if self.can_spawn_new_windows:

                    ClientGUIMenus.AppendSeparator(menu)

                    ClientGUIMenus.AppendMenuItem(
                        menu, 'open a new search page for ' + selection_string,
                        'Open a new search page starting with the selected predicates.',
                        self._NewSearchPage)

                    if len(self._selected_terms) > 1:

                        ClientGUIMenus.AppendMenuItem(
                            menu,
                            'open new search pages for each in selection',
                            'Open one new search page for each selected predicate.',
                            self._NewSearchPageForEach)

                if self._get_current_predicates_callable is not None:

                    ClientGUIMenus.AppendSeparator(menu)

                    current_predicates = self._get_current_predicates_callable(
                    )

                    if current_predicates is not None:

                        (include_predicates, exclude_predicates
                         ) = self._GetSelectedIncludeExcludePredicates()

                        if True in (
                                include_predicate in current_predicates
                                for include_predicate in include_predicates):

                            ClientGUIMenus.AppendMenuItem(
                                menu, 'discard ' + selection_string +
                                ' from current search',
                                'Remove the selected predicates from the current search.',
                                self._ProcessMenuPredicateEvent,
                                'remove_include_predicates')

                        if True in (
                                include_predicate not in current_predicates
                                for include_predicate in include_predicates):

                            ClientGUIMenus.AppendMenuItem(
                                menu, 'require ' + selection_string +
                                ' for current search',
                                'Add the selected predicates from the current search.',
                                self._ProcessMenuPredicateEvent,
                                'add_include_predicates')

                        if True in (
                                exclude_predicate in current_predicates
                                for exclude_predicate in exclude_predicates):

                            ClientGUIMenus.AppendMenuItem(
                                menu, 'permit ' + selection_string +
                                ' for current search',
                                'Stop disallowing the selected predicates from the current search.',
                                self._ProcessMenuPredicateEvent,
                                'remove_exclude_predicates')

                        if True in (
                                exclude_predicate not in current_predicates
                                for exclude_predicate in exclude_predicates):

                            ClientGUIMenus.AppendMenuItem(
                                menu, 'exclude ' + selection_string +
                                ' from current search',
                                'Disallow the selected predicates for the current search.',
                                self._ProcessMenuPredicateEvent,
                                'add_exclude_predicates')

            if len(selected_tags) == 1:

                (tag, ) = selected_tags

                if self._tag_display_type in (
                        ClientTags.TAG_DISPLAY_SINGLE_MEDIA,
                        ClientTags.TAG_DISPLAY_SELECTION_LIST):

                    ClientGUIMenus.AppendSeparator(menu)

                    (namespace, subtag) = HydrusTags.SplitTag(tag)

                    hide_menu = QW.QMenu(menu)

                    ClientGUIMenus.AppendMenuItem(
                        hide_menu, '"{}" tags from here'.format(
                            ClientTags.RenderNamespaceForUser(namespace)),
                        'Hide this namespace from view in future.',
                        self._ProcessMenuTagEvent, 'hide_namespace')
                    ClientGUIMenus.AppendMenuItem(
                        hide_menu, '"{}" from here'.format(tag),
                        'Hide this tag from view in future.',
                        self._ProcessMenuTagEvent, 'hide')

                    ClientGUIMenus.AppendMenu(menu, hide_menu, 'hide')

                    ClientGUIMenus.AppendSeparator(menu)

                ClientGUIMenus.AppendSeparator(menu)

                favourite_tags = list(
                    HG.client_controller.new_options.GetStringList(
                        'favourite_tags'))

                def set_favourite_tags(favourite_tags):

                    HG.client_controller.new_options.SetStringList(
                        'favourite_tags', favourite_tags)

                    HG.client_controller.pub('notify_new_favourite_tags')

                if tag in favourite_tags:

                    favourite_tags.remove(tag)

                    label = 'remove "{}" from favourites'.format(tag)
                    description = 'Remove this tag from your favourites'

                else:

                    favourite_tags.append(tag)

                    label = 'add "{}" to favourites'.format(tag)
                    description = 'Add this tag from your favourites'

                ClientGUIMenus.AppendMenuItem(menu, label, description,
                                              set_favourite_tags,
                                              favourite_tags)

            if len(selected_tags) > 0 and self.can_spawn_new_windows:

                ClientGUIMenus.AppendSeparator(menu)

                if len(selected_tags) == 1:

                    (tag, ) = selected_tags

                    text = tag

                else:

                    text = 'selection'

                ClientGUIMenus.AppendMenuItem(menu, 'add parents to ' + text,
                                              'Add a parent to this tag.',
                                              self._ProcessMenuTagEvent,
                                              'parent')
                ClientGUIMenus.AppendMenuItem(menu, 'add siblings to ' + text,
                                              'Add a sibling to this tag.',
                                              self._ProcessMenuTagEvent,
                                              'sibling')

            HG.client_controller.PopupMenu(self, menu)

    def GetSelectedTags(self):

        return set(self._selected_terms)

    def ForceTagRecalc(self):

        pass


class ListBoxTagsPredicates(ListBoxTags):

    has_counts = True

    def _CanHitIndex(self, index):

        result = ListBoxTags._CanHitIndex(self, index)

        if not result:

            return False

        term = self._GetTerm(index)

        if term.GetType() in (HC.PREDICATE_TYPE_LABEL,
                              HC.PREDICATE_TYPE_PARENT):

            return False

        return True

    def _CanSelectIndex(self, index):

        result = ListBoxTags._CanSelectIndex(self, index)

        if not result:

            return False

        term = self._GetTerm(index)

        if term.GetType() == HC.PREDICATE_TYPE_LABEL:

            return False

        return True

    def _Deselect(self, index):

        to_deselect = self._GetWithParentIndices(index)

        for index in to_deselect:

            ListBoxTags._Deselect(self, index)

    def _GetAllTagsForClipboard(self, with_counts=False):

        return [term.ToString(with_counts) for term in self._ordered_terms]

    def _GetMutuallyExclusivePredicates(self, predicate):

        m_e_predicates = {
            existing_predicate
            for existing_predicate in self._terms
            if existing_predicate.IsMutuallyExclusive(predicate)
        }

        return m_e_predicates

    def _GetNamespaceFromTerm(self, term):

        predicate = term

        namespace = predicate.GetNamespace()

        return namespace

    def _GetSimplifiedTextFromTerm(self, term):

        predicate = term

        return predicate.ToString(with_counts=False)

    def _GetTextFromTerm(self, term):

        predicate = term

        return predicate.ToString()

    def _GetWithParentIndices(self, index):

        indices = [index]

        index += 1

        while index < len(self._ordered_terms):

            term = self._GetTerm(index)

            if term.GetType() == HC.PREDICATE_TYPE_PARENT:

                indices.append(index)

            else:

                break

            index += 1

        return indices

    def _HasPredicate(self, predicate):

        return predicate in self._terms

    def _Hit(self, shift, ctrl, hit_index):

        hit_index = self._GetSafeHitIndex(hit_index)

        ListBoxTags._Hit(self, shift, ctrl, hit_index)

    def _Select(self, index):

        to_select = self._GetWithParentIndices(index)

        for index in to_select:

            ListBoxTags._Select(self, index)

    def GetPredicates(self):

        return set(self._terms)


class ListBoxTagsActiveSearchPredicates(ListBoxTagsPredicates):

    has_counts = False

    def __init__(self, parent, page_key, initial_predicates=None):

        if initial_predicates is None:

            initial_predicates = []

        ListBoxTagsPredicates.__init__(self, parent, height_num_chars=6)

        self._page_key = page_key
        self._get_current_predicates_callable = self.GetPredicates

        if len(initial_predicates) > 0:

            for predicate in initial_predicates:

                self._AppendTerm(predicate)

            self._DataHasChanged()

        HG.client_controller.sub(self, 'EnterPredicates', 'enter_predicates')

    def _Activate(self):

        if len(self._selected_terms) > 0:

            self._EnterPredicates(set(self._selected_terms))

    def _DeleteActivate(self):

        self._Activate()

    def _EnterPredicates(self,
                         predicates,
                         permit_add=True,
                         permit_remove=True):

        if len(predicates) == 0:

            return

        predicates_to_be_added = set()
        predicates_to_be_removed = set()

        for predicate in predicates:

            predicate = predicate.GetCountlessCopy()

            if self._HasPredicate(predicate):

                if permit_remove:

                    predicates_to_be_removed.add(predicate)

            else:

                if permit_add:

                    predicates_to_be_added.add(predicate)

                    predicates_to_be_removed.update(
                        self._GetMutuallyExclusivePredicates(predicate))

        for predicate in predicates_to_be_added:

            self._AppendTerm(predicate)

        for predicate in predicates_to_be_removed:

            self._RemoveTerm(predicate)

        self._SortByText()

        self._DataHasChanged()

        HG.client_controller.pub('refresh_query', self._page_key)

    def _GetTextFromTerm(self, term):

        predicate = term

        return predicate.ToString(render_for_user=True)

    def _ProcessMenuPredicateEvent(self, command):

        (include_predicates,
         exclude_predicates) = self._GetSelectedIncludeExcludePredicates()

        if command == 'add_include_predicates':

            self._EnterPredicates(include_predicates, permit_remove=False)

        elif command == 'remove_include_predicates':

            self._EnterPredicates(include_predicates, permit_add=False)

        elif command == 'add_exclude_predicates':

            self._EnterPredicates(exclude_predicates, permit_remove=False)

        elif command == 'remove_exclude_predicates':

            self._EnterPredicates(exclude_predicates, permit_add=False)

    def EnterPredicates(self,
                        page_key,
                        predicates,
                        permit_add=True,
                        permit_remove=True):

        if page_key == self._page_key:

            self._EnterPredicates(predicates,
                                  permit_add=permit_add,
                                  permit_remove=permit_remove)


class ListBoxTagsAC(ListBoxTagsPredicates):
    def __init__(self, parent, callable, service_key, **kwargs):

        ListBoxTagsPredicates.__init__(self, parent, **kwargs)

        self._callable = callable
        self._service_key = service_key

        self._predicates = {}

    def _Activate(self):

        shift_down = QW.QApplication.keyboardModifiers() & QC.Qt.ShiftModifier

        predicates = [
            term for term in self._selected_terms
            if term.GetType() != HC.PREDICATE_TYPE_PARENT
        ]

        predicates = HG.client_controller.gui.FleshOutPredicates(predicates)

        if len(predicates) > 0:

            self._callable(predicates, shift_down)

    def SetPredicates(self, predicates):

        # need to do a clever compare, since normal predicate compare doesn't take count into account

        they_are_the_same = True

        if len(predicates) == len(self._predicates):

            for index in range(len(predicates)):

                p_1 = predicates[index]
                p_2 = self._predicates[index]

                if p_1 != p_2 or p_1.GetCount() != p_2.GetCount():

                    they_are_the_same = False

                    break

        else:

            they_are_the_same = False

        if not they_are_the_same:

            # important to make own copy, as same object originals can be altered (e.g. set non-inclusive) in cache, and we need to notice that change just above
            self._predicates = [
                predicate.GetCopy() for predicate in predicates
            ]

            self._Clear()

            for predicate in predicates:

                self._AppendTerm(predicate)

            self._DataHasChanged()

            if len(predicates) > 0:

                hit_index = 0

                if len(predicates) > 1:

                    skip_ors = True

                    skip_countless = HG.client_controller.new_options.GetBoolean(
                        'ac_select_first_with_count')

                    for (index, predicate) in enumerate(predicates):

                        # now only apply this to simple tags, not wildcards and system tags

                        if skip_ors and predicate.GetType(
                        ) == HC.PREDICATE_TYPE_OR_CONTAINER:

                            continue

                        if skip_countless and predicate.GetType() in (
                                HC.PREDICATE_TYPE_PARENT, HC.PREDICATE_TYPE_TAG
                        ) and predicate.GetCount() == 0:

                            continue

                        hit_index = index

                        break

                self._Hit(False, False, hit_index)

    def SetTagService(self, service_key):

        self._service_key = service_key


class ListBoxTagsACRead(ListBoxTagsAC):

    ors_are_under_construction = True

    def _GetTextFromTerm(self, term):

        predicate = term

        return predicate.ToString(
            render_for_user=True,
            or_under_construction=self.ors_are_under_construction)


class ListBoxTagsACWrite(ListBoxTagsAC):
    def _GetTextFromTerm(self, term):

        predicate = term

        return predicate.ToString(sibling_service_key=self._service_key)


class ListBoxTagsCensorship(ListBoxTags):
    def __init__(self, parent, removed_callable=None):

        ListBoxTags.__init__(self, parent)

        self._removed_callable = removed_callable

    def _Activate(self):

        if len(self._selected_terms) > 0:

            tags = set(self._selected_terms)

            for tag in tags:

                self._RemoveTerm(tag)

            if self._removed_callable is not None:

                self._removed_callable(tags)

            self._ordered_terms.sort()

            self._DataHasChanged()

    def _GetNamespaceFromTerm(self, term):

        tag = term

        if tag == ':':

            return None

        else:

            (namespace, subtag) = HydrusTags.SplitTag(tag)

            return namespace

    def _GetTextFromTerm(self, term):

        tag_slice = term

        return ClientTags.ConvertTagSliceToString(tag_slice)

    def AddTags(self, tags):

        for tag in tags:

            self._AppendTerm(tag)

        self._ordered_terms.sort()

        self._DataHasChanged()

    def EnterTags(self, tags):

        for tag in tags:

            if tag in self._terms:

                self._RemoveTerm(tag)

            else:

                self._AppendTerm(tag)

        self._ordered_terms.sort()

        self._DataHasChanged()

    def GetTags(self):

        return list(self._ordered_terms)

    def RemoveTags(self, tags):

        for tag in tags:

            self._RemoveTerm(tag)

        self._ordered_terms.sort()

        self._DataHasChanged()

    def SetTags(self, tags):

        self._Clear()

        self.AddTags(tags)


class ListBoxTagsColourOptions(ListBoxTags):

    PROTECTED_TERMS = (None, '')
    can_spawn_new_windows = False

    def __init__(self, parent, initial_namespace_colours):

        ListBoxTags.__init__(self, parent)

        for (namespace, colour) in initial_namespace_colours.items():

            colour = tuple(
                colour
            )  # tuple to convert from list, for oooold users who have list colours

            self._AppendTerm((namespace, colour))

        self._SortByText()

        self._DataHasChanged()

    def _Activate(self):

        namespaces = [
            namespace for (namespace, colour) in self._selected_terms
        ]

        if len(namespaces) > 0:

            from . import ClientGUIDialogsQuick

            result = ClientGUIDialogsQuick.GetYesNo(
                self, 'Delete all selected colours?')

            if result == QW.QDialog.Accepted:

                self._RemoveNamespaces(namespaces)

    def _DeleteActivate(self):

        self._Activate()

    def _GetTextFromTerm(self, term):

        (namespace, colour) = term

        if namespace is None:

            namespace_string = 'default namespace:tag'

        elif namespace == '':

            namespace_string = 'unnamespaced tag'

        else:

            namespace_string = namespace + ':tag'

        return namespace_string

    def _GetNamespaceColours(self):

        return dict(self._terms)

    def _GetNamespaceFromTerm(self, term):

        (namespace, colour) = term

        return namespace

    def _RemoveNamespaces(self, namespaces):

        namespaces = [
            namespace for namespace in namespaces
            if namespace not in self.PROTECTED_TERMS
        ]

        removees = [(existing_namespace, existing_colour)
                    for (existing_namespace, existing_colour) in self._terms
                    if existing_namespace in namespaces]

        for removee in removees:

            self._RemoveTerm(removee)

        self._DataHasChanged()

    def SetNamespaceColour(self, namespace, colour):

        (r, g, b, a) = colour.toTuple()

        colour_tuple = (r, g, b)

        for (existing_namespace, existing_colour) in self._terms:

            if existing_namespace == namespace:

                self._RemoveTerm((existing_namespace, existing_colour))

                break

        self._AppendTerm((namespace, colour_tuple))

        self._SortByText()

        self._DataHasChanged()

    def GetNamespaceColours(self):

        return self._GetNamespaceColours()

    def GetSelectedNamespaceColours(self):

        namespace_colours = dict(self._selected_terms)

        return namespace_colours


class ListBoxTagsStrings(ListBoxTags):
    def __init__(self,
                 parent,
                 service_key=None,
                 show_sibling_text=True,
                 sort_tags=True):

        ListBoxTags.__init__(self, parent)

        if service_key is not None:

            service_key = CC.COMBINED_TAG_SERVICE_KEY

        self._service_key = service_key
        self._show_sibling_text = show_sibling_text
        self._sort_tags = sort_tags

    def _GetNamespaceFromTerm(self, term):

        tag = term

        (namespace, subtag) = HydrusTags.SplitTag(tag)

        return namespace

    def _GetSimplifiedTextFromTerm(self, term):

        tag = term

        return str(tag)

    def _GetTextFromTerm(self, term):

        siblings_manager = HG.client_controller.tag_siblings_manager

        tag = term

        tag_string = ClientTags.RenderTag(tag, True)

        if self._show_sibling_text:

            sibling = siblings_manager.GetSibling(self._service_key, tag)

            if sibling is not None:

                tag_string += ' (will display as ' + ClientTags.RenderTag(
                    sibling, True) + ')'

        return tag_string

    def _RecalcTags(self):

        self._RefreshTexts()

        if self._sort_tags:

            self._SortByText()

        self._DataHasChanged()

    def GetTags(self):

        return set(self._terms)

    def SetTagServiceKey(self, service_key):

        self._service_key = service_key

        self._RecalcTags()

    def SetTags(self, tags):

        self._Clear()

        for tag in tags:

            self._AppendTerm(tag)

        self._RecalcTags()

    def ForceTagRecalc(self):

        if self.window().isMinimized():

            return

        self._RecalcTags()


class ListBoxTagsStringsAddRemove(ListBoxTagsStrings):
    def __init__(self,
                 parent,
                 service_key=None,
                 removed_callable=None,
                 show_sibling_text=True):

        ListBoxTagsStrings.__init__(self,
                                    parent,
                                    service_key=service_key,
                                    show_sibling_text=show_sibling_text)

        self._removed_callable = removed_callable

    def _Activate(self):

        if len(self._selected_terms) > 0:

            tags = set(self._selected_terms)

            self._RemoveTags(tags)

    def _RemoveTags(self, tags):

        for tag in tags:

            self._RemoveTerm(tag)

        self._RecalcTags()

        if self._removed_callable is not None:

            self._removed_callable(tags)

    def AddTags(self, tags):

        for tag in tags:

            self._AppendTerm(tag)

        self._RecalcTags()

    def Clear(self):

        self._Clear()

        self._RecalcTags()

    def EnterTags(self, tags):

        removed = set()

        for tag in tags:

            if tag in self._terms:

                self._RemoveTerm(tag)

                removed.add(tag)

            else:

                self._AppendTerm(tag)

        self._RecalcTags()

        if len(removed) > 0 and self._removed_callable is not None:

            self._removed_callable(removed)

    def keyPressEvent(self, event):

        (modifier,
         key) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple(event)

        if key in CC.DELETE_KEYS:

            self._Activate()

        else:

            ListBoxTagsStrings.keyPressEvent(self, event)

    def RemoveTags(self, tags):

        self._RemoveTags(tags)


class ListBoxTagsSelection(ListBoxTags):

    render_for_user = True
    has_counts = True

    def __init__(self,
                 parent,
                 tag_display_type,
                 include_counts=True,
                 show_sibling_description=False):

        ListBoxTags.__init__(self, parent, height_num_chars=24)

        self._sort = HC.options['default_tag_sort']

        self._last_media = set()

        self._tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
        self._tag_display_type = tag_display_type

        self._include_counts = include_counts
        self._show_sibling_description = show_sibling_description

        self._current_tags_to_count = collections.Counter()
        self._deleted_tags_to_count = collections.Counter()
        self._pending_tags_to_count = collections.Counter()
        self._petitioned_tags_to_count = collections.Counter()

        self._show_current = True
        self._show_deleted = False
        self._show_pending = True
        self._show_petitioned = True

    def _GetAllTagsForClipboard(self, with_counts=False):

        if with_counts:

            return [self._terms_to_texts[term] for term in self._ordered_terms]

        else:

            return list(self._ordered_terms)

    def _GetNamespaceFromTerm(self, term):

        tag = term

        (namespace, subtag) = HydrusTags.SplitTag(tag)

        return namespace

    def _GetSimplifiedTextFromTerm(self, term):

        tag = term

        return str(tag)

    def _GetTextFromTerm(self, term):

        tag = term

        tag_string = ClientTags.RenderTag(tag, self.render_for_user)

        if self._include_counts:

            if self._show_current and tag in self._current_tags_to_count:
                tag_string += ' (' + HydrusData.ToHumanInt(
                    self._current_tags_to_count[tag]) + ')'
            if self._show_pending and tag in self._pending_tags_to_count:
                tag_string += ' (+' + HydrusData.ToHumanInt(
                    self._pending_tags_to_count[tag]) + ')'
            if self._show_petitioned and tag in self._petitioned_tags_to_count:
                tag_string += ' (-' + HydrusData.ToHumanInt(
                    self._petitioned_tags_to_count[tag]) + ')'
            if self._show_deleted and tag in self._deleted_tags_to_count:
                tag_string += ' (X' + HydrusData.ToHumanInt(
                    self._deleted_tags_to_count[tag]) + ')'

        else:

            if self._show_pending and tag in self._pending_tags_to_count:
                tag_string += ' (+)'
            if self._show_petitioned and tag in self._petitioned_tags_to_count:
                tag_string += ' (-)'
            if self._show_deleted and tag in self._deleted_tags_to_count:
                tag_string += ' (X)'

        if self._show_sibling_description:

            sibling = HG.client_controller.tag_siblings_manager.GetSibling(
                self._tag_service_key, tag)

            if sibling is not None:

                sibling = ClientTags.RenderTag(sibling, self.render_for_user)

                tag_string += ' (will display as ' + sibling + ')'

        return tag_string

    def _RecalcStrings(self, limit_to_these_tags=None):

        previous_selected_terms = set(self._selected_terms)

        if limit_to_these_tags is None:

            self._Clear()

            nonzero_tags = set()

            if self._show_current:
                nonzero_tags.update(
                    (tag
                     for (tag,
                          count) in list(self._current_tags_to_count.items())
                     if count > 0))
            if self._show_deleted:
                nonzero_tags.update(
                    (tag
                     for (tag,
                          count) in list(self._deleted_tags_to_count.items())
                     if count > 0))
            if self._show_pending:
                nonzero_tags.update(
                    (tag
                     for (tag,
                          count) in list(self._pending_tags_to_count.items())
                     if count > 0))
            if self._show_petitioned:
                nonzero_tags.update((tag for (
                    tag, count) in list(self._petitioned_tags_to_count.items())
                                     if count > 0))

            for tag in nonzero_tags:

                self._AppendTerm(tag)

        else:

            if not isinstance(limit_to_these_tags, set):

                limit_to_these_tags = set(limit_to_these_tags)

            for tag in limit_to_these_tags:

                self._RemoveTerm(tag)

            nonzero_tags = set()

            if self._show_current:
                nonzero_tags.update(
                    (tag
                     for (tag,
                          count) in list(self._current_tags_to_count.items())
                     if count > 0 and tag in limit_to_these_tags))
            if self._show_deleted:
                nonzero_tags.update(
                    (tag
                     for (tag,
                          count) in list(self._deleted_tags_to_count.items())
                     if count > 0 and tag in limit_to_these_tags))
            if self._show_pending:
                nonzero_tags.update(
                    (tag
                     for (tag,
                          count) in list(self._pending_tags_to_count.items())
                     if count > 0 and tag in limit_to_these_tags))
            if self._show_petitioned:
                nonzero_tags.update((
                    tag
                    for (tag,
                         count) in list(self._petitioned_tags_to_count.items())
                    if count > 0 and tag in limit_to_these_tags))

            for tag in nonzero_tags:

                self._AppendTerm(tag)

        for term in previous_selected_terms:

            if term in self._terms:

                self._selected_terms.add(term)

        self._SortTags()

    def _SortTags(self):

        tags_to_count = collections.Counter()

        if self._show_current:
            tags_to_count.update(self._current_tags_to_count)
        if self._show_deleted:
            tags_to_count.update(self._deleted_tags_to_count)
        if self._show_pending:
            tags_to_count.update(self._pending_tags_to_count)
        if self._show_petitioned:
            tags_to_count.update(self._petitioned_tags_to_count)

        ClientTags.SortTags(self._sort, self._ordered_terms, tags_to_count)

        self._DataHasChanged()

    def ChangeTagService(self, service_key):

        self._tag_service_key = service_key

        self.SetTagsByMedia(self._last_media, force_reload=True)

    def SetSort(self, sort):

        self._sort = sort

        self._SortTags()

    def SetShow(self, show_type, value):

        if show_type == 'current': self._show_current = value
        elif show_type == 'deleted': self._show_deleted = value
        elif show_type == 'pending': self._show_pending = value
        elif show_type == 'petitioned': self._show_petitioned = value

        self._RecalcStrings()

    def IncrementTagsByMedia(self, media):

        media = set(media)
        media = media.difference(self._last_media)

        (current_tags_to_count, deleted_tags_to_count, pending_tags_to_count,
         petitioned_tags_to_count) = ClientMedia.GetMediasTagCount(
             media, self._tag_service_key, self._tag_display_type)

        self._current_tags_to_count.update(current_tags_to_count)
        self._deleted_tags_to_count.update(deleted_tags_to_count)
        self._pending_tags_to_count.update(pending_tags_to_count)
        self._petitioned_tags_to_count.update(petitioned_tags_to_count)

        tags_changed = set()

        if self._show_current:
            tags_changed.update(list(current_tags_to_count.keys()))
        if self._show_deleted:
            tags_changed.update(list(deleted_tags_to_count.keys()))
        if self._show_pending:
            tags_changed.update(list(pending_tags_to_count.keys()))
        if self._show_petitioned:
            tags_changed.update(list(petitioned_tags_to_count.keys()))

        if len(tags_changed) > 0:

            self._RecalcStrings(tags_changed)

        self._last_media.update(media)

    def SetTagsByMedia(self, media, force_reload=False):

        media = set(media)

        if len(media) < len(
                self._last_media
        ) // 10:  # if we are dropping to a much smaller selection (e.g. 5000 -> 1), we should just recalculate from scratch

            force_reload = True

        if force_reload:

            (current_tags_to_count, deleted_tags_to_count,
             pending_tags_to_count,
             petitioned_tags_to_count) = ClientMedia.GetMediasTagCount(
                 media, self._tag_service_key, self._tag_display_type)

            self._current_tags_to_count = current_tags_to_count
            self._deleted_tags_to_count = deleted_tags_to_count
            self._pending_tags_to_count = pending_tags_to_count
            self._petitioned_tags_to_count = petitioned_tags_to_count

            self._RecalcStrings()

        else:

            removees = self._last_media.difference(media)
            adds = media.difference(self._last_media)

            (current_tags_to_count, deleted_tags_to_count,
             pending_tags_to_count,
             petitioned_tags_to_count) = ClientMedia.GetMediasTagCount(
                 removees, self._tag_service_key, self._tag_display_type)

            self._current_tags_to_count.subtract(current_tags_to_count)
            self._deleted_tags_to_count.subtract(deleted_tags_to_count)
            self._pending_tags_to_count.subtract(pending_tags_to_count)
            self._petitioned_tags_to_count.subtract(petitioned_tags_to_count)

            (current_tags_to_count, deleted_tags_to_count,
             pending_tags_to_count,
             petitioned_tags_to_count) = ClientMedia.GetMediasTagCount(
                 adds, self._tag_service_key, self._tag_display_type)

            self._current_tags_to_count.update(current_tags_to_count)
            self._deleted_tags_to_count.update(deleted_tags_to_count)
            self._pending_tags_to_count.update(pending_tags_to_count)
            self._petitioned_tags_to_count.update(petitioned_tags_to_count)

            for counter in (self._current_tags_to_count,
                            self._deleted_tags_to_count,
                            self._pending_tags_to_count,
                            self._petitioned_tags_to_count):

                tags = list(counter.keys())

                for tag in tags:

                    if counter[tag] == 0:

                        del counter[tag]

            if len(removees) == 0:

                tags_changed = set()

                if self._show_current:
                    tags_changed.update(list(current_tags_to_count.keys()))
                if self._show_deleted:
                    tags_changed.update(list(deleted_tags_to_count.keys()))
                if self._show_pending:
                    tags_changed.update(list(pending_tags_to_count.keys()))
                if self._show_petitioned:
                    tags_changed.update(list(petitioned_tags_to_count.keys()))

                if len(tags_changed) > 0:

                    self._RecalcStrings(tags_changed)

            else:

                self._RecalcStrings()

        self._last_media = media

        self._DataHasChanged()

    def ForceTagRecalc(self):

        if self.window().isMinimized():

            return

        self.SetTagsByMedia(self._last_media, force_reload=True)


class ListBoxTagsSelectionHoverFrame(ListBoxTagsSelection):
    def __init__(self, parent, canvas_key):

        ListBoxTagsSelection.__init__(self,
                                      parent,
                                      ClientTags.TAG_DISPLAY_SINGLE_MEDIA,
                                      include_counts=False)

        self._canvas_key = canvas_key

    def _Activate(self):

        HG.client_controller.pub('canvas_manage_tags', self._canvas_key)


class ListBoxTagsSelectionManagementPanel(ListBoxTagsSelection):
    def __init__(self,
                 parent,
                 page_key,
                 tag_display_type,
                 predicates_callable=None):

        ListBoxTagsSelection.__init__(self,
                                      parent,
                                      tag_display_type,
                                      include_counts=True)

        self._minimum_height_num_chars = 15

        self._page_key = page_key
        self._get_current_predicates_callable = predicates_callable

        HG.client_controller.sub(self, 'IncrementTagsByMediaPubsub',
                                 'increment_tags_selection')
        HG.client_controller.sub(self, 'SetTagsByMediaPubsub',
                                 'new_tags_selection')
        HG.client_controller.sub(self, 'ChangeTagServicePubsub',
                                 'change_tag_service')

    def _Activate(self):

        predicates = [
            ClientSearch.Predicate(HC.PREDICATE_TYPE_TAG, term)
            for term in self._selected_terms
        ]

        if len(predicates) > 0:

            HG.client_controller.pub('enter_predicates', self._page_key,
                                     predicates)

    def _ProcessMenuPredicateEvent(self, command):

        (include_predicates,
         exclude_predicates) = self._GetSelectedIncludeExcludePredicates()

        if command == 'add_include_predicates':

            HG.client_controller.pub('enter_predicates',
                                     self._page_key,
                                     include_predicates,
                                     permit_remove=False)

        elif command == 'remove_include_predicates':

            HG.client_controller.pub('enter_predicates',
                                     self._page_key,
                                     include_predicates,
                                     permit_add=False)

        elif command == 'add_exclude_predicates':

            HG.client_controller.pub('enter_predicates',
                                     self._page_key,
                                     exclude_predicates,
                                     permit_remove=False)

        elif command == 'remove_exclude_predicates':

            HG.client_controller.pub('enter_predicates',
                                     self._page_key,
                                     exclude_predicates,
                                     permit_add=False)

    def ChangeTagServicePubsub(self, page_key, service_key):

        if page_key == self._page_key:

            self.ChangeTagService(service_key)

    def IncrementTagsByMediaPubsub(self, page_key, media):

        if page_key == self._page_key:

            self.IncrementTagsByMedia(media)

    def SetTagsByMediaPubsub(self, page_key, media, force_reload=False):

        if page_key == self._page_key:

            self.SetTagsByMedia(media, force_reload=force_reload)


class ListBoxTagsSelectionTagsDialog(ListBoxTagsSelection):

    render_for_user = False

    def __init__(self, parent, enter_func, delete_func):

        ListBoxTagsSelection.__init__(self,
                                      parent,
                                      ClientTags.TAG_DISPLAY_STORAGE,
                                      include_counts=True,
                                      show_sibling_description=True)

        self._enter_func = enter_func
        self._delete_func = delete_func

    def _Activate(self):

        if len(self._selected_terms) > 0:

            self._enter_func(set(self._selected_terms))

    def _DeleteActivate(self):

        if len(self._selected_terms) > 0:

            self._delete_func(set(self._selected_terms))
