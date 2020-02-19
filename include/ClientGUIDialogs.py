import collections
import gc
import itertools
import os
import queue
import random
import re
import shutil
import stat
import string
import threading
import time
import traceback

import yaml
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from . import ClientCaches
from . import ClientConstants as CC
from . import (ClientData, ClientDefaults, ClientDownloading, ClientDragDrop,
               ClientExporting, ClientFiles, ClientGUIACDropdown,
               ClientGUICommon, ClientGUIDialogsQuick, ClientGUIFrames,
               ClientGUIFunctions, ClientGUIImport, ClientGUIListBoxes,
               ClientGUIListCtrl, ClientGUIPredicates, ClientGUIShortcuts,
               ClientGUITime, ClientGUITopLevelWindows, ClientImporting,
               ClientSearch, ClientTags, ClientThreading)
from . import HydrusConstants as HC
from . import HydrusData, HydrusExceptions, HydrusFileHandling
from . import HydrusGlobals as HG
from . import (HydrusNATPunch, HydrusNetwork, HydrusPaths, HydrusSerialisable,
               HydrusTags, HydrusThreading)
from . import QtPorting as QP

# Option Enums


def SelectServiceKey(service_types=HC.ALL_SERVICES,
                     service_keys=None,
                     unallowed=None):

    if service_keys is None:

        services = HG.client_controller.services_manager.GetServices(
            service_types)

        service_keys = [service.GetServiceKey() for service in services]

    if unallowed is not None:

        service_keys.difference_update(unallowed)

    if len(service_keys) == 0:

        return None

    elif len(service_keys) == 1:

        (service_key, ) = service_keys

        return service_key

    else:

        services = {
            HG.client_controller.services_manager.GetService(service_key)
            for service_key in service_keys
        }

        choice_tuples = [(service.GetName(), service.GetServiceKey())
                         for service in services]

        try:

            service_key = ClientGUIDialogsQuick.SelectFromList(
                HG.client_controller.gui, 'select service', choice_tuples)

            return service_key

        except HydrusExceptions.CancelledException:

            return None


class Dialog(QP.Dialog):
    def __init__(self, parent, title, style=QC.Qt.Dialog, position='topleft'):

        QP.Dialog.__init__(self, parent)

        self.setWindowFlags(style)

        self.setWindowTitle(title)

        if parent is not None and position == 'topleft':

            parent_tlw = self.parentWidget().window()

            (pos_x, pos_y) = parent_tlw.pos().toTuple()

            pos = QC.QPoint(pos_x + 50, pos_y + 50)

        else:

            pos = None

        if pos: self.move(pos)

        self.setWindowFlag(QC.Qt.WindowContextHelpButtonHint, on=False)

        self._new_options = HG.client_controller.new_options

        self.setWindowIcon(QG.QIcon(HG.client_controller.frame_icon_pixmap))

        self._widget_event_filter = QP.WidgetEventFilter(self)

        if parent is not None and position == 'center':

            QP.CallAfter(QP.CenterOnWindow, parent, self)

        HG.client_controller.ResetIdleTimer()

    def keyPressEvent(self, event):

        (modifier,
         key) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple(event)

        if key == QC.Qt.Key_Escape:

            self.done(QW.QDialog.Rejected)

        else:

            QP.Dialog.keyPressEvent(self, event)

    def SetInitialSize(self, size):

        (width, height) = size if isinstance(size, tuple) else size.toTuple()

        display_size = ClientGUITopLevelWindows.GetDisplaySize(self)

        width = min(display_size.width(), width)
        height = min(display_size.height(), height)

        self.resize(QC.QSize(width, height))

        min_width = min(240, width)
        min_height = min(240, height)

        self.setMinimumSize(QC.QSize(min_width, min_height))


class DialogChooseNewServiceMethod(Dialog):
    def __init__(self, parent):

        Dialog.__init__(self,
                        parent,
                        'how to set up the account?',
                        position='center')

        register_message = 'I want to initialise a new account with the server. I have a registration key (a key starting with \'r\').'

        self._register = QW.QPushButton(register_message, self)
        self._register.clicked.connect(self.EventRegister)

        setup_message = 'The account is already initialised; I just want to add it to this client. I have a normal access key.'

        self._setup = QW.QPushButton(setup_message, self)
        self._setup.clicked.connect(self.accept)

        vbox = QP.VBoxLayout()

        QP.AddToLayout(vbox, self._register, CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(
            vbox,
            QP.MakeQLabelWithAlignment('-or-', self, QC.Qt.AlignHCenter
                                       | QC.Qt.AlignVCenter),
            CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(vbox, self._setup, CC.FLAGS_EXPAND_PERPENDICULAR)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        QP.SetInitialSize(self, size_hint)

        self._should_register = False

        QP.CallAfter(self._register.setFocus, QC.Qt.OtherFocusReason)

    def EventRegister(self):

        self._should_register = True

        self.done(QW.QDialog.Accepted)

    def GetRegister(self):

        return self._should_register


class DialogGenerateNewAccounts(Dialog):
    def __init__(self, parent, service_key):

        Dialog.__init__(self, parent, 'configure new accounts')

        self._service_key = service_key

        self._num = QP.MakeQSpinBox(self, min=1, max=10000, width=80)

        self._account_types = ClientGUICommon.BetterChoice(self)

        self._lifetime = ClientGUICommon.BetterChoice(self)

        self._ok = QW.QPushButton('OK', self)
        self._ok.clicked.connect(self.EventOK)
        QP.SetForegroundColour(self._ok, (0, 128, 0))

        self._cancel = QW.QPushButton('Cancel', self)
        self._cancel.clicked.connect(self.reject)
        QP.SetForegroundColour(self._cancel, (128, 0, 0))

        #

        self._num.setValue(1)

        service = HG.client_controller.services_manager.GetService(service_key)

        response = service.Request(HC.GET, 'account_types')

        account_types = response['account_types']

        for account_type in account_types:

            self._account_types.addItem(account_type.GetTitle(), account_type)

        self._account_types.setCurrentIndex(0)

        for (s, value) in HC.lifetimes:

            self._lifetime.addItem(s, value)

        self._lifetime.setCurrentIndex(3)  # one year

        #

        ctrl_box = QP.HBoxLayout()

        QP.AddToLayout(ctrl_box,
                       ClientGUICommon.BetterStaticText(self, 'generate'),
                       CC.FLAGS_VCENTER)
        QP.AddToLayout(ctrl_box, self._num, CC.FLAGS_VCENTER)
        QP.AddToLayout(ctrl_box, self._account_types, CC.FLAGS_VCENTER)
        QP.AddToLayout(
            ctrl_box,
            ClientGUICommon.BetterStaticText(self, 'accounts, to expire in'),
            CC.FLAGS_VCENTER)
        QP.AddToLayout(ctrl_box, self._lifetime, CC.FLAGS_VCENTER)

        b_box = QP.HBoxLayout()
        QP.AddToLayout(b_box, self._ok, CC.FLAGS_VCENTER)
        QP.AddToLayout(b_box, self._cancel, CC.FLAGS_VCENTER)

        vbox = QP.VBoxLayout()

        QP.AddToLayout(vbox, ctrl_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR)
        QP.AddToLayout(vbox, b_box, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        QP.SetInitialSize(self, size_hint)

        QP.CallAfter(self._ok.setFocus, QC.Qt.OtherFocusReason)

    def EventOK(self):

        num = self._num.value()

        account_type = self._account_types.GetValue()

        account_type_key = account_type.GetAccountTypeKey()

        lifetime = self._lifetime.GetValue()

        if lifetime is None:

            expires = None

        else:

            expires = HydrusData.GetNow() + lifetime

        service = HG.client_controller.services_manager.GetService(
            self._service_key)

        try:

            request_args = {'num': num, 'account_type_key': account_type_key}

            if expires is not None:

                request_args['expires'] = expires

            response = service.Request(HC.GET, 'registration_keys',
                                       request_args)

            registration_keys = response['registration_keys']

            ClientGUIFrames.ShowKeys('registration', registration_keys)

        finally:

            self.done(QW.QDialog.Accepted)


class DialogInputLocalBooruShare(Dialog):
    def __init__(self,
                 parent,
                 share_key,
                 name,
                 text,
                 timeout,
                 hashes,
                 new_share=False):

        Dialog.__init__(self, parent, 'configure local booru share')

        self._name = QW.QLineEdit(self)

        self._text = QW.QPlainTextEdit(self)
        self._text.setMinimumHeight(100)

        message = 'expires in'

        self._timeout_number = ClientGUICommon.NoneableSpinCtrl(
            self,
            message,
            none_phrase='no expiration',
            max=1000000,
            multiplier=1)

        self._timeout_multiplier = ClientGUICommon.BetterChoice(self)
        self._timeout_multiplier.addItem('minutes', 60)
        self._timeout_multiplier.addItem('hours', 60 * 60)
        self._timeout_multiplier.addItem('days', 60 * 60 * 24)

        self._copy_internal_share_link = QW.QPushButton(
            'copy internal share link', self)
        self._copy_internal_share_link.clicked.connect(
            self.EventCopyInternalShareURL)

        self._copy_external_share_link = QW.QPushButton(
            'copy external share link', self)
        self._copy_external_share_link.clicked.connect(
            self.EventCopyExternalShareURL)

        self._ok = QW.QPushButton('ok', self)
        self._ok.clicked.connect(self.accept)
        QP.SetForegroundColour(self._ok, (0, 128, 0))

        self._cancel = QW.QPushButton('cancel', self)
        self._cancel.clicked.connect(self.reject)
        QP.SetForegroundColour(self._cancel, (128, 0, 0))

        #

        self._share_key = share_key
        self._name.setText(name)
        self._text.setPlainText(text)

        if timeout is None:

            self._timeout_number.SetValue(None)

            self._timeout_multiplier.SetValue(60)

        else:

            time_left = HydrusData.GetTimeDeltaUntilTime(timeout)

            if time_left < 60 * 60 * 12: time_value = 60
            elif time_left < 60 * 60 * 24 * 7: time_value = 60 * 60
            else: time_value = 60 * 60 * 24

            self._timeout_number.SetValue(time_left // time_value)

            self._timeout_multiplier.SetValue(time_value)

        self._hashes = hashes

        self._service = HG.client_controller.services_manager.GetService(
            CC.LOCAL_BOORU_SERVICE_KEY)

        internal_port = self._service.GetPort()

        if internal_port is None:

            self._copy_internal_share_link.setEnabled(False)
            self._copy_external_share_link.setEnabled(False)

        #

        rows = []

        rows.append(('share name: ', self._name))
        rows.append(('share text: ', self._text))

        gridbox = ClientGUICommon.WrapInGrid(self, rows)

        timeout_box = QP.HBoxLayout()
        QP.AddToLayout(timeout_box, self._timeout_number,
                       CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(timeout_box, self._timeout_multiplier,
                       CC.FLAGS_EXPAND_BOTH_WAYS)

        link_box = QP.HBoxLayout()
        QP.AddToLayout(link_box, self._copy_internal_share_link,
                       CC.FLAGS_VCENTER)
        QP.AddToLayout(link_box, self._copy_external_share_link,
                       CC.FLAGS_VCENTER)

        b_box = QP.HBoxLayout()
        QP.AddToLayout(b_box, self._ok, CC.FLAGS_VCENTER)
        QP.AddToLayout(b_box, self._cancel, CC.FLAGS_VCENTER)

        vbox = QP.VBoxLayout()

        intro = 'Sharing ' + HydrusData.ToHumanInt(len(
            self._hashes)) + ' files.'
        intro += os.linesep + 'Title and text are optional.'

        if new_share:
            intro += os.linesep + 'The link will not work until you ok this dialog.'

        QP.AddToLayout(vbox, ClientGUICommon.BetterStaticText(self, intro),
                       CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR)
        QP.AddToLayout(vbox, timeout_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR)
        QP.AddToLayout(vbox, link_box, CC.FLAGS_BUTTON_SIZER)
        QP.AddToLayout(vbox, b_box, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        size_hint.setWidth(max(size_hint.width(), 350))

        QP.SetInitialSize(self, size_hint)

        QP.CallAfter(self._ok.setFocus, QC.Qt.OtherFocusReason)

    def EventCopyExternalShareURL(self):

        internal_port = self._service.GetPort()

        if internal_port is None:

            QW.QMessageBox.warning(
                self, 'Warning', 'The local booru is not currently running!')

        try:

            url = self._service.GetExternalShareURL(self._share_key)

        except Exception as e:

            HydrusData.ShowException(e)

            QW.QMessageBox.critical(
                self, 'Error',
                'Unfortunately, could not generate an external URL: {}'.format(
                    e))

            return

        HG.client_controller.pub('clipboard', 'text', url)

    def EventCopyInternalShareURL(self):

        self._service = HG.client_controller.services_manager.GetService(
            CC.LOCAL_BOORU_SERVICE_KEY)

        internal_ip = '127.0.0.1'

        internal_port = self._service.GetPort()

        url = 'http://' + internal_ip + ':' + str(
            internal_port) + '/gallery?share_key=' + self._share_key.hex()

        HG.client_controller.pub('clipboard', 'text', url)

    def GetInfo(self):

        name = self._name.text()

        text = self._text.toPlainText()

        timeout = self._timeout_number.GetValue()

        if timeout is not None:
            timeout = timeout * self._timeout_multiplier.GetValue(
            ) + HydrusData.GetNow()

        return (self._share_key, name, text, timeout, self._hashes)


class DialogInputNamespaceRegex(Dialog):
    def __init__(self, parent, namespace='', regex=''):

        Dialog.__init__(self, parent, 'configure quick namespace')

        self._namespace = QW.QLineEdit(self)

        self._regex = QW.QLineEdit(self)

        self._shortcuts = ClientGUICommon.RegexButton(self)

        self._regex_intro_link = ClientGUICommon.BetterHyperLink(
            self, 'a good regex introduction',
            'http://www.aivosto.com/vbtips/regex.html')
        self._regex_practise_link = ClientGUICommon.BetterHyperLink(
            self, 'regex practise', 'http://regexr.com/3cvmf')

        self._ok = QW.QPushButton('OK', self)
        self._ok.clicked.connect(self.EventOK)
        QP.SetForegroundColour(self._ok, (0, 128, 0))

        self._cancel = QW.QPushButton('Cancel', self)
        self._cancel.clicked.connect(self.reject)
        QP.SetForegroundColour(self._cancel, (128, 0, 0))

        #

        self._namespace.setText(namespace)
        self._regex.setText(regex)

        #

        control_box = QP.HBoxLayout()

        QP.AddToLayout(control_box, self._namespace, CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(control_box,
                       ClientGUICommon.BetterStaticText(self,
                                                        ':'), CC.FLAGS_VCENTER)
        QP.AddToLayout(control_box, self._regex, CC.FLAGS_EXPAND_BOTH_WAYS)

        b_box = QP.HBoxLayout()
        QP.AddToLayout(b_box, self._ok, CC.FLAGS_VCENTER)
        QP.AddToLayout(b_box, self._cancel, CC.FLAGS_VCENTER)

        vbox = QP.VBoxLayout()

        intro = r'Put the namespace (e.g. page) on the left.' + os.linesep + r'Put the regex (e.g. [1-9]+\d*(?=.{4}$)) on the right.' + os.linesep + r'All files will be tagged with "namespace:regex".'

        QP.AddToLayout(vbox, ClientGUICommon.BetterStaticText(self, intro),
                       CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(vbox, control_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR)
        QP.AddToLayout(vbox, self._shortcuts, CC.FLAGS_LONE_BUTTON)
        QP.AddToLayout(vbox, self._regex_intro_link, CC.FLAGS_LONE_BUTTON)
        QP.AddToLayout(vbox, self._regex_practise_link, CC.FLAGS_LONE_BUTTON)
        QP.AddToLayout(vbox, b_box, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        QP.SetInitialSize(self, size_hint)

        QP.CallAfter(self._ok.setFocus, QC.Qt.OtherFocusReason)

    def EventOK(self):

        (namespace, regex) = self.GetInfo()

        if namespace == '':

            QW.QMessageBox.warning(
                self, 'Warning', 'Please enter something for the namespace.')

            return

        try:

            re.compile(regex)

        except Exception as e:

            text = 'That regex would not compile!'
            text += os.linesep * 2
            text += str(e)

            QW.QMessageBox.critical(self, 'Error', text)

            return

        self.done(QW.QDialog.Accepted)

    def GetInfo(self):

        namespace = self._namespace.text()

        regex = self._regex.text()

        return (namespace, regex)


class DialogInputTags(Dialog):
    def __init__(self, parent, service_key, tags, message=''):

        Dialog.__init__(self, parent, 'input tags')

        self._service_key = service_key

        self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove(
            self, service_key=service_key)

        expand_parents = True

        self._tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite(
            self,
            self.EnterTags,
            expand_parents,
            CC.LOCAL_FILE_SERVICE_KEY,
            service_key,
            null_entry_callable=self.OK,
            show_paste_button=True)

        self._ok = ClientGUICommon.BetterButton(self, 'OK', self.done,
                                                QW.QDialog.Accepted)
        QP.SetForegroundColour(self._ok, (0, 128, 0))

        self._cancel = QW.QPushButton('Cancel', self)
        self._cancel.clicked.connect(self.reject)
        QP.SetForegroundColour(self._cancel, (128, 0, 0))

        #

        self._tags.SetTags(tags)

        #

        b_box = QP.HBoxLayout()

        QP.AddToLayout(b_box, self._ok, CC.FLAGS_VCENTER)
        QP.AddToLayout(b_box, self._cancel, CC.FLAGS_VCENTER)

        vbox = QP.VBoxLayout()

        if message != '':

            QP.AddToLayout(vbox,
                           ClientGUICommon.BetterStaticText(self, message),
                           CC.FLAGS_EXPAND_PERPENDICULAR)

        QP.AddToLayout(vbox, self._tags, CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(vbox, self._tag_box)
        QP.AddToLayout(vbox, b_box, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        size_hint.setWidth(max(size_hint.width(), 300))

        QP.SetInitialSize(self, size_hint)

        QP.CallAfter(self._tag_box.setFocus, QC.Qt.OtherFocusReason)

    def EnterTags(self, tags):

        tag_parents_manager = HG.client_controller.tag_parents_manager

        parents = set()

        for tag in tags:

            some_parents = tag_parents_manager.GetParents(
                self._service_key, tag)

            parents.update(some_parents)

        if len(tags) > 0:

            self._tags.EnterTags(tags)
            self._tags.AddTags(parents)

    def GetTags(self):

        return self._tags.GetTags()

    def OK(self):

        self.done(QW.QDialog.Accepted)


class DialogInputUPnPMapping(Dialog):
    def __init__(self, parent, external_port, protocol_type, internal_port,
                 description, duration):

        Dialog.__init__(self, parent, 'configure upnp mapping')

        self._external_port = QP.MakeQSpinBox(self, min=0, max=65535)

        self._protocol_type = ClientGUICommon.BetterChoice(self)
        self._protocol_type.addItem('TCP', 'TCP')
        self._protocol_type.addItem('UDP', 'UDP')

        self._internal_port = QP.MakeQSpinBox(self, min=0, max=65535)
        self._description = QW.QLineEdit(self)
        self._duration = QP.MakeQSpinBox(self, min=0, max=86400)

        self._ok = ClientGUICommon.BetterButton(self, 'OK', self.done,
                                                QW.QDialog.Accepted)
        QP.SetForegroundColour(self._ok, (0, 128, 0))

        self._cancel = QW.QPushButton('Cancel', self)
        self._cancel.clicked.connect(self.reject)
        QP.SetForegroundColour(self._cancel, (128, 0, 0))

        #

        self._external_port.setValue(external_port)

        if protocol_type == 'TCP': self._protocol_type.setCurrentIndex(0)
        elif protocol_type == 'UDP': self._protocol_type.setCurrentIndex(1)

        self._internal_port.setValue(internal_port)
        self._description.setText(description)
        self._duration.setValue(duration)

        #

        rows = []

        rows.append(('external port: ', self._external_port))
        rows.append(('protocol type: ', self._protocol_type))
        rows.append(('internal port: ', self._internal_port))
        rows.append(('description: ', self._description))
        rows.append(('duration (0 = indefinite): ', self._duration))

        gridbox = ClientGUICommon.WrapInGrid(self, rows)

        b_box = QP.HBoxLayout()
        QP.AddToLayout(b_box, self._ok, CC.FLAGS_VCENTER)
        QP.AddToLayout(b_box, self._cancel, CC.FLAGS_VCENTER)

        vbox = QP.VBoxLayout()

        QP.AddToLayout(vbox, gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS)
        QP.AddToLayout(vbox, b_box, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        QP.SetInitialSize(self, size_hint)

        QP.CallAfter(self._ok.setFocus, QC.Qt.OtherFocusReason)

    def GetInfo(self):

        external_port = self._external_port.value()
        protocol_type = self._protocol_type.GetValue()
        internal_port = self._internal_port.value()
        description = self._description.text()
        duration = self._duration.value()

        return (external_port, protocol_type, internal_port, description,
                duration)


class DialogModifyAccounts(Dialog):
    def __init__(self, parent, service_key, subject_identifiers):

        Dialog.__init__(self, parent, 'modify account')

        self._service = HG.client_controller.services_manager.GetService(
            service_key)
        self._subject_identifiers = list(subject_identifiers)

        #

        self._account_info_panel = ClientGUICommon.StaticBox(
            self, 'account info')

        self._subject_text = QW.QLabel(self._account_info_panel)

        #

        self._account_types_panel = ClientGUICommon.StaticBox(
            self, 'account types')

        self._account_types = QW.QComboBox(self._account_types_panel)

        self._account_types_ok = QW.QPushButton('OK',
                                                self._account_types_panel)
        self._account_types_ok.clicked.connect(self.EventChangeAccountType)

        #

        self._expiration_panel = ClientGUICommon.StaticBox(
            self, 'change expiration')

        self._add_to_expires = QW.QComboBox(self._expiration_panel)

        self._add_to_expires_ok = QW.QPushButton('OK', self._expiration_panel)
        self._add_to_expires.clicked.connect(self.EventAddToExpires)

        self._set_expires = QW.QComboBox(self._expiration_panel)

        self._set_expires_ok = QW.QPushButton('OK', self._expiration_panel)
        self._set_expires_ok.clicked.connect(self.EventSetExpires)

        #

        self._ban_panel = ClientGUICommon.StaticBox(self, 'bans')

        self._ban = QW.QPushButton('ban user', self._ban_panel)
        self._ban.clicked.connect(self.EventBan)
        QP.SetBackgroundColour(self._ban, (255, 0, 0))
        QP.SetForegroundColour(self._ban, (255, 255, 0))

        self._superban = QW.QPushButton(
            'ban user and delete every contribution they have ever made',
            self._ban_panel)
        self._superban.clicked.connect(self.EventSuperban)
        QP.SetBackgroundColour(self._superban, (255, 0, 0))
        QP.SetForegroundColour(self._superban, (255, 255, 0))

        self._exit = QW.QPushButton('Exit', self)
        self._exit.clicked.connect(self.reject)

        #

        if len(self._subject_identifiers) == 1:

            (subject_identifier, ) = self._subject_identifiers

            response = self._service.Request(
                HC.GET, 'account_info',
                {'subject_identifier': subject_identifier})

            subject_string = str(response['account_info'])

        else:

            subject_string = 'modifying ' + HydrusData.ToHumanInt(
                len(self._subject_identifiers)) + ' accounts'

        self._subject_text.setText(subject_string)

        #

        response = self._service.Request(HC.GET, 'account_types')

        account_types = response['account_types']

        for account_type in account_types:
            self._account_types.addItem(account_type.ConvertToString(),
                                        account_type)

        self._account_types.setCurrentIndex(0)

        #

        for (string, value) in HC.lifetimes:

            if value is not None:

                self._add_to_expires.addItem(
                    string, value)  # don't want 'add no limit'

        self._add_to_expires.setCurrentIndex(1)  # three months

        for (string, value) in HC.lifetimes:
            self._set_expires.addItem(string, value)
        self._set_expires.setCurrentIndex(1)  # three months

        #

        self._account_info_panel.Add(self._subject_text,
                                     CC.FLAGS_EXPAND_PERPENDICULAR)

        account_types_hbox = QP.HBoxLayout()

        QP.AddToLayout(account_types_hbox, self._account_types,
                       CC.FLAGS_VCENTER)
        QP.AddToLayout(account_types_hbox, self._account_types_ok,
                       CC.FLAGS_VCENTER)

        self._account_types_panel.Add(account_types_hbox,
                                      CC.FLAGS_EXPAND_PERPENDICULAR)

        add_to_expires_box = QP.HBoxLayout()

        QP.AddToLayout(add_to_expires_box,
                       QW.QLabel('add to expires: ', self._expiration_panel),
                       CC.FLAGS_VCENTER)
        QP.AddToLayout(add_to_expires_box, self._add_to_expires,
                       CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(add_to_expires_box, self._add_to_expires_ok,
                       CC.FLAGS_VCENTER)

        set_expires_box = QP.HBoxLayout()

        QP.AddToLayout(set_expires_box,
                       QW.QLabel('set expires to: ', self._expiration_panel),
                       CC.FLAGS_VCENTER)
        QP.AddToLayout(set_expires_box, self._set_expires,
                       CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(set_expires_box, self._set_expires_ok, CC.FLAGS_VCENTER)

        self._expiration_panel.Add(add_to_expires_box,
                                   CC.FLAGS_EXPAND_PERPENDICULAR)
        self._expiration_panel.Add(set_expires_box,
                                   CC.FLAGS_EXPAND_PERPENDICULAR)

        self._ban_panel.Add(self._ban, CC.FLAGS_EXPAND_PERPENDICULAR)
        self._ban_panel.Add(self._superban, CC.FLAGS_EXPAND_PERPENDICULAR)

        vbox = QP.VBoxLayout()
        QP.AddToLayout(vbox, self._account_info_panel,
                       CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(vbox, self._account_types_panel,
                       CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(vbox, self._expiration_panel,
                       CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(vbox, self._ban_panel, CC.FLAGS_EXPAND_PERPENDICULAR)
        QP.AddToLayout(vbox, self._exit, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        QP.SetInitialSize(self, size_hint)

        QP.CallAfter(self._exit.setFocus, QC.Qt.OtherFocusReason)

    def _DoModification(self):

        # change this to saveaccounts or whatever. the previous func changes the accounts, and then we push that change
        # generate accounts, with the modification having occurred

        self._service.Request(HC.POST, 'account', {'accounts': self._accounts})

        if len(self._subject_identifiers) == 1:

            (subject_identifier, ) = self._subject_identifiers

            response = self._service.Request(
                HC.GET, 'account_info',
                {'subject_identifier': subject_identifier})

            account_info = response['account_info']

            self._subject_text.setText(str(account_info))

        if len(self._subject_identifiers) > 1:

            QW.QMessageBox.information(self, 'Information', 'Done!')

    def EventAddToExpires(self):

        raise NotImplementedError()
        #self._DoModification( HC.ADD_TO_EXPIRES, timespan = self._add_to_expires.GetClientData( self._add_to_expires.GetSelection() ) )

    def EventBan(self):

        with DialogTextEntry(self, 'Enter reason for the ban.') as dlg:

            if dlg.exec() == QW.QDialog.Accepted:
                raise NotImplementedError()
                #self._DoModification( HC.BAN, reason = dlg.GetValue() )

    def EventChangeAccountType(self):

        raise NotImplementedError()
        #self._DoModification( HC.CHANGE_ACCOUNT_TYPE, account_type_key = self._account_types.GetValue() )

    def EventSetExpires(self):

        expires = QP.GetClientData(self._set_expires,
                                   self._set_expires.currentIndex())

        if expires is not None:

            expires += HydrusData.GetNow()

        raise NotImplementedError()
        #self._DoModification( HC.SET_EXPIRES, expires = expires )

    def EventSuperban(self):

        with DialogTextEntry(self, 'Enter reason for the superban.') as dlg:

            if dlg.exec() == QW.QDialog.Accepted:

                raise NotImplementedError()
                #self._DoModification( HC.SUPERBAN, reason = dlg.GetValue() )


class DialogSelectFromURLTree(Dialog):
    def __init__(self, parent, url_tree):

        Dialog.__init__(self, parent, 'select items')

        self._tree = QP.TreeWidgetWithInheritedCheckState(self)

        self._ok = ClientGUICommon.BetterButton(self, 'OK', self.done,
                                                QW.QDialog.Accepted)
        QP.SetForegroundColour(self._ok, (0, 128, 0))

        self._cancel = QW.QPushButton('Cancel', self)
        self._cancel.clicked.connect(self.reject)
        QP.SetForegroundColour(self._cancel, (128, 0, 0))

        #

        (text_gumpf, name, size, children) = url_tree

        root_name = self._RenderItemName(name, size)

        root_item = QW.QTreeWidgetItem()
        root_item.setText(0, root_name)
        root_item.setCheckState(0, QC.Qt.Checked)
        self._tree.addTopLevelItem(root_item)

        self._AddDirectory(root_item, children)

        root_item.setExpanded(True)

        #

        button_hbox = QP.HBoxLayout()

        QP.AddToLayout(button_hbox, self._ok, CC.FLAGS_VCENTER)
        QP.AddToLayout(button_hbox, self._cancel, CC.FLAGS_VCENTER)

        vbox = QP.VBoxLayout()

        QP.AddToLayout(vbox, self._tree, CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(vbox, button_hbox, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        size_hint.setWidth(max(size_hint.width(), 640))
        size_hint.setHeight(max(size_hint.height(), 640))

        QP.SetInitialSize(self, size_hint)

    def _AddDirectory(self, root, children):

        for (child_type, name, size, data) in children:

            item_name = self._RenderItemName(name, size)

            if child_type == 'file':

                item = QW.QTreeWidgetItem()
                item.setText(0, item_name)
                item.setCheckState(0, root.checkState(0))
                item.setData(0, QC.Qt.UserRole, data)
                root.addChild(item)

            else:

                subroot = QW.QTreeWidgetItem()
                subroot.setText(0, item_name)
                subroot.setCheckState(0, root.checkState(0))
                root.addChild(subroot)

                self._AddDirectory(subroot, data)

    def _GetSelectedChildrenData(self, parent_item):

        result = []

        for i in range(parent_item.childCount()):

            child_item = parent_item.child(i)

            if child_item.checkState(0) == QC.Qt.Checked:

                data = child_item.data(0, QC.Qt.UserRole)

                if data is not None:

                    result.append(data)

            result.extend(self._GetSelectedChildrenData(child_item))

        return result

    def _RenderItemName(self, name, size):

        return name + ' - ' + HydrusData.ToHumanBytes(size)

    def GetURLs(self):

        root_item = self._tree.topLevelItem(0)

        urls = self._GetSelectedChildrenData(root_item)

        return urls


class DialogSelectImageboard(Dialog):
    def __init__(self, parent):

        Dialog.__init__(self, parent, 'select imageboard')

        self._tree = QW.QTreeWidget(self)
        self._tree.itemActivated.connect(self.EventActivate)

        #

        all_imageboards = HG.client_controller.Read('imageboards')

        root_item = QW.QTreeWidgetItem()
        root_item.setText(0, 'all sites')
        self._tree.addTopLevelItem(root_item)

        for (site, imageboards) in list(all_imageboards.items()):

            site_item = QW.QTreeWidgetItem()
            site_item.setText(0, site)
            root_item.addChild(site_item)

            for imageboard in imageboards:

                name = imageboard.GetName()

                imageboard_item = QW.QTreeWidgetItem()
                imageboard_item.setText(0, name)
                imageboard_item.setData(0, QC.Qt.UserRole, imageboard)
                site_item.addChild(imageboard_item)

        root_item.setExpanded(True)

        #

        vbox = QP.VBoxLayout()

        QP.AddToLayout(vbox, self._tree, CC.FLAGS_EXPAND_BOTH_WAYS)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        size_hint.setWidth(max(size_hint.width(), 320))
        size_hint.setHeight(max(size_hint.height(), 640))

        QP.SetInitialSize(self, size_hint)

    def EventActivate(self, item, column):

        data_object = item.data(0, QC.Qt.UserRole)

        if data_object is None: item.setExpanded(not item.isExpanded())
        else: self.done(QW.QDialog.Accepted)

    def GetImageboard(self):

        items = self._tree.selectedItems()

        if len(items):

            return items[0].data(0, QC.Qt.UserRole).GetData()


class DialogTextEntry(Dialog):
    def __init__(self,
                 parent,
                 message,
                 default='',
                 placeholder=None,
                 allow_blank=False,
                 suggestions=None,
                 max_chars=None,
                 password_entry=False):

        if suggestions is None:

            suggestions = []

        Dialog.__init__(self, parent, 'enter text', position='center')

        self._chosen_suggestion = None
        self._allow_blank = allow_blank
        self._max_chars = max_chars

        button_choices = []

        for text in suggestions:

            button_choices.append(
                ClientGUICommon.BetterButton(self, text, self.ButtonChoice,
                                             text))

        self._text = QW.QLineEdit(self)
        self._text.textChanged.connect(self.EventText)
        self._text.installEventFilter(
            ClientGUICommon.TextCatchEnterEventFilter(self._text,
                                                      self.EnterText))

        if password_entry:

            self._text.setEchoMode(QW.QLineEdit.Password)

        if self._max_chars is not None:

            self._text.setMaxLength(self._max_chars)

        self._ok = ClientGUICommon.BetterButton(self, 'ok', self.done,
                                                QW.QDialog.Accepted)
        QP.SetForegroundColour(self._ok, (0, 128, 0))

        self._cancel = QW.QPushButton('cancel', self)
        self._cancel.clicked.connect(self.reject)
        QP.SetForegroundColour(self._cancel, (128, 0, 0))

        #

        self._text.setText(default)
        if placeholder is not None: self._text.setPlaceholderText(placeholder)

        self._CheckText()

        #

        hbox = QP.HBoxLayout()

        QP.AddToLayout(hbox, self._ok, CC.FLAGS_SMALL_INDENT)
        QP.AddToLayout(hbox, self._cancel, CC.FLAGS_SMALL_INDENT)

        st_message = ClientGUICommon.BetterStaticText(self, message)
        st_message.setWordWrap(True)

        vbox = QP.VBoxLayout()

        QP.AddToLayout(vbox, st_message, CC.FLAGS_BIG_INDENT)

        for button in button_choices:

            QP.AddToLayout(vbox, button, CC.FLAGS_EXPAND_PERPENDICULAR)

        QP.AddToLayout(vbox, self._text, CC.FLAGS_EXPAND_BOTH_WAYS)
        QP.AddToLayout(vbox, hbox, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        size_hint.setWidth(max(size_hint.width(), 250))

        QP.SetInitialSize(self, size_hint)

    def _CheckText(self):

        if not self._allow_blank:

            if self._text.text() == '':

                self._ok.setEnabled(False)

            else:

                self._ok.setEnabled(True)

    def ButtonChoice(self, text):

        self._chosen_suggestion = text

        self.done(QW.QDialog.Accepted)

    def EventText(self, text):

        QP.CallAfter(self._CheckText)

    def EnterText(self):

        if self._ok.isEnabled():

            self.done(QW.QDialog.Accepted)

    def GetValue(self):

        if self._chosen_suggestion is None:

            return self._text.text()

        else:

            return self._chosen_suggestion


class DialogYesYesNo(Dialog):
    def __init__(self,
                 parent,
                 message,
                 title='Are you sure?',
                 yes_tuples=None,
                 no_label='no'):

        if yes_tuples is None:

            yes_tuples = [('yes', 'yes')]

        Dialog.__init__(self, parent, title, position='center')

        self._value = None

        yes_buttons = []

        for (label, data) in yes_tuples:

            yes_button = ClientGUICommon.BetterButton(self, label, self._DoYes,
                                                      data)
            QP.SetForegroundColour(yes_button, (0, 128, 0))

            yes_buttons.append(yes_button)

        self._no = ClientGUICommon.BetterButton(self, no_label, self.done,
                                                QW.QDialog.Rejected)
        QP.SetForegroundColour(self._no, (128, 0, 0))

        #

        hbox = QP.HBoxLayout()

        for yes_button in yes_buttons:

            QP.AddToLayout(hbox, yes_button, CC.FLAGS_SMALL_INDENT)

        QP.AddToLayout(hbox, self._no, CC.FLAGS_SMALL_INDENT)

        vbox = QP.VBoxLayout()

        text = ClientGUICommon.BetterStaticText(self, message)
        text.setWordWrap(True)

        QP.AddToLayout(vbox, text, CC.FLAGS_BIG_INDENT)
        QP.AddToLayout(vbox, hbox, CC.FLAGS_BUTTON_SIZER)

        self.setLayout(vbox)

        size_hint = self.sizeHint()

        size_hint.setWidth(max(size_hint.width(), 250))

        QP.SetInitialSize(self, size_hint)

        QP.CallAfter(yes_buttons[0].setFocus, QC.Qt.OtherFocusReason)

    def _DoYes(self, value):

        self._value = value

        self.done(QW.QDialog.Accepted)

    def GetValue(self):

        return self._value
