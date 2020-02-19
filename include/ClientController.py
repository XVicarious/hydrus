import gc
import hashlib
import os
import signal
import sys
import threading
import time
import traceback

import psutil
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from . import ClientAPI, ClientCaches
from . import ClientConstants as CC
from . import (ClientDaemons, ClientData, ClientDB, ClientDefaults,
               ClientDownloading, ClientFiles, ClientGUI, ClientGUIDialogs,
               ClientGUIDialogsQuick, ClientGUIMenus,
               ClientGUIScrolledPanelsManagement, ClientGUIShortcuts,
               ClientGUIStyle, ClientGUITopLevelWindows,
               ClientImportSubscriptions, ClientManagers, ClientNetworking,
               ClientNetworkingBandwidth, ClientNetworkingDomain,
               ClientNetworkingLogin, ClientNetworkingSessions, ClientOptions,
               ClientPaths, ClientTags, ClientThreading)
from . import HydrusConstants as HC
from . import HydrusController, HydrusData, HydrusExceptions
from . import HydrusGlobals as HG
from . import (HydrusNetworking, HydrusPaths, HydrusSerialisable,
               HydrusThreading, HydrusVideoHandling)
from . import QtPorting as QP

if not HG.twisted_is_broke:

    from twisted.internet import threads, reactor, defer

PubSubEventType = QC.QEvent.Type(QC.QEvent.registerEventType())


class PubSubEvent(QC.QEvent):
    def __init__(self):

        QC.QEvent.__init__(self, PubSubEventType)


class PubSubEventFilter(QC.QObject):
    def __init__(self, parent, pubsub):

        QC.QObject.__init__(self, parent)

        self._pubsub = pubsub

    def eventFilter(self, watched, event):

        if event.type() == PubSubEventType and isinstance(event, PubSubEvent):

            if self._pubsub.WorkToDo():

                self._pubsub.Process()

            event.accept()

            return True

        return False


class App(QW.QApplication):
    def __init__(self, pubsub, *args, **kwargs):

        QW.QApplication.__init__(self, *args, **kwargs)

        self._pubsub = pubsub

        self.setApplicationName('Hydrus Client')
        self.setApplicationVersion(str(HC.SOFTWARE_VERSION))

        # Uncomment this to debug Qt warnings. Set a breakpoint on the print statement in QP.WarningHandler to be able to see where the warnings originate from.
        QC.qInstallMessageHandler(QP.WarningHandler)

        self.setQuitOnLastWindowClosed(True)

        self.call_after_catcher = QC.QObject(self)

        self.call_after_catcher.installEventFilter(
            QP.CallAfterEventFilter(self.call_after_catcher))

        self.pubsub_catcher = QC.QObject(self)

        self.pubsub_catcher.installEventFilter(
            PubSubEventFilter(self.pubsub_catcher, self._pubsub))

        self.aboutToQuit.connect(self.EventEndSession)

    def EventEndSession(self):

        # Since aboutToQuit gets called not only on external shutdown events (like user logging off), but even if we explicitely call QApplication.exit(),
        # this check will make sure that we only do an emergency exit if it's really necessary (i.e. QApplication.exit() wasn't called by us).
        if not QW.QApplication.instance().property('normal_exit'):

            HG.emergency_exit = True

            if HG.client_controller.gui is not None and QP.isValid(
                    HG.client_controller.gui):

                HG.client_controller.gui.SaveAndClose()


class Controller(HydrusController.HydrusController):
    def __init__(self, db_dir):

        self._last_shutdown_was_bad = False

        self._is_booted = False

        self._splash = None

        self.gui = None

        HydrusController.HydrusController.__init__(self, db_dir)

        self._name = 'client'

        HG.client_controller = self

        # just to set up some defaults, in case some db update expects something for an odd yaml-loading reason
        self.options = ClientDefaults.GetClientDefaultOptions()
        self.new_options = ClientOptions.ClientOptions()

        HC.options = self.options

        self._page_key_lock = threading.Lock()

        self._thread_slots['watcher_files'] = (0, 15)
        self._thread_slots['watcher_check'] = (0, 5)
        self._thread_slots['gallery_files'] = (0, 15)
        self._thread_slots['gallery_search'] = (0, 5)

        self._alive_page_keys = set()
        self._closed_page_keys = set()

        self._last_last_session_hash = None

        self._last_mouse_position = None
        self._menu_open = False
        self._previously_idle = False
        self._idle_started = None

        self.client_files_manager = None
        self.services_manager = None

    def _InitDB(self):

        return ClientDB.DB(self, self.db_dir, 'client')

    def _InitTempDir(self):

        self.temp_dir = HydrusPaths.GetTempDir()

    def _DestroySplash(self):
        def qt_code(splash):

            if splash and QP.isValid(splash):

                splash.hide()

                splash.close()

        if self._splash is not None:

            splash = self._splash

            self._splash = None

            QP.CallAfter(qt_code, splash)

    def _GetPubsubValidCallable(self):

        return QP.isValid

    def _GetUPnPServices(self):

        return self.services_manager.GetServices(
            (HC.LOCAL_BOORU, HC.CLIENT_API_SERVICE))

    def _ReportShutdownDaemonsStatus(self):

        names = {daemon.name for daemon in self._daemons if daemon.is_alive()}

        names = list(names)

        names.sort()

        self.pub('splash_set_status_subtext', ', '.join(names))

    def _ReportShutdownException(self):

        text = 'A serious error occurred while trying to exit the program. Its traceback may be shown next. It should have also been written to client.log. You may need to quit the program from task manager.'

        HydrusData.DebugPrint(text)

        HydrusData.DebugPrint(traceback.format_exc())

        self.SafeShowCriticalMessage('shutdown error', text)
        self.SafeShowCriticalMessage('shutdown error', traceback.format_exc())

    def _ShutdownSubscriptionsManager(self):

        self.subscriptions_manager.Shutdown()

        started = HydrusData.GetNow()

        while not self.subscriptions_manager.IsShutdown():

            time.sleep(0.1)

            if HydrusData.TimeHasPassed(started + 30):

                break

    def AcquirePageKey(self):

        with self._page_key_lock:

            page_key = HydrusData.GenerateKey()

            self._alive_page_keys.add(page_key)

            return page_key

    def CallBlockingToQt(self, win, func, *args, **kwargs):
        def qt_code(win, job_key):

            try:

                if win is not None and not QP.isValid(win):

                    if HG.view_shutdown:

                        raise HydrusExceptions.ShutdownException(
                            'Application is shutting down!')

                    else:

                        raise HydrusExceptions.QtDeadWindowException(
                            'Parent Window was destroyed before Qt command was called!'
                        )

                result = func(*args, **kwargs)

                job_key.SetVariable('result', result)

            except (HydrusExceptions.QtDeadWindowException,
                    HydrusExceptions.InsufficientCredentialsException,
                    HydrusExceptions.ShutdownException) as e:

                job_key.SetVariable('error', e)

            except Exception as e:

                job_key.SetVariable('error', e)

                HydrusData.Print('CallBlockingToQt just caught this error:')
                HydrusData.DebugPrint(traceback.format_exc())

            finally:

                job_key.Finish()

        job_key = ClientThreading.JobKey(cancel_on_shutdown=False)

        job_key.Begin()

        QP.CallAfter(qt_code, win, job_key)

        while not job_key.IsDone():

            if not HG.qt_app_running:

                raise HydrusExceptions.ShutdownException(
                    'Application is shutting down!')

            time.sleep(0.02)

        if job_key.HasVariable('result'):

            # result can be None, for qt_code that has no return variable

            result = job_key.GetIfHasVariable('result')

            return result

        error = job_key.GetIfHasVariable('error')

        if error is not None:

            raise error

        raise HydrusExceptions.ShutdownException()

    def CallLaterQtSafe(self, window, initial_delay, func, *args, **kwargs):

        job_scheduler = self._GetAppropriateJobScheduler(initial_delay)

        call = HydrusData.Call(func, *args, **kwargs)

        job = ClientThreading.QtAwareJob(self, job_scheduler, window,
                                         initial_delay, call)

        if job_scheduler is not None:

            job_scheduler.AddJob(job)

        return job

    def CallRepeatingQtSafe(self, window, initial_delay, period, func, *args,
                            **kwargs):

        job_scheduler = self._GetAppropriateJobScheduler(period)

        call = HydrusData.Call(func, *args, **kwargs)

        job = ClientThreading.QtAwareRepeatingJob(self, job_scheduler, window,
                                                  initial_delay, period, call)

        if job_scheduler is not None:

            job_scheduler.AddJob(job)

        return job

    def CatchSignal(self, sig, frame):

        if sig in (signal.SIGINT, signal.SIGTERM):

            if sig == signal.SIGTERM:

                HG.emergency_exit = True

            if hasattr(self, 'gui'):

                event = QG.QCloseEvent()

                QW.QApplication.postEvent(self.gui, event)

    def CheckAlreadyRunning(self):

        while HydrusData.IsAlreadyRunning(self.db_dir, 'client'):

            self.pub('splash_set_status_text', 'client already running')

            def qt_code():

                message = 'It looks like another instance of this client is already running, so this instance cannot start.'
                message += os.linesep * 2
                message += 'If the old instance is closing and does not quit for a _very_ long time, it is usually safe to force-close it from task manager.'

                result = ClientGUIDialogsQuick.GetYesNo(
                    self._splash,
                    message,
                    title='The client is already running.',
                    yes_label='wait a bit, then try again',
                    no_label='forget it')

                if result != QW.QDialog.Accepted:

                    HG.shutting_down_due_to_already_running = True

                    raise HydrusExceptions.ShutdownException()

            self.CallBlockingToQt(self._splash, qt_code)

            for i in range(10, 0, -1):

                if not HydrusData.IsAlreadyRunning(self.db_dir, 'client'):

                    break

                self.pub('splash_set_status_text',
                         'waiting ' + str(i) + ' seconds')

                time.sleep(1)

    def CheckMouseIdle(self):

        mouse_position = QG.QCursor.pos()

        if self._last_mouse_position is None:

            self._last_mouse_position = mouse_position

        elif mouse_position != self._last_mouse_position:

            idle_before_position_update = self.CurrentlyIdle()

            self._timestamps['last_mouse_action'] = HydrusData.GetNow()

            self._last_mouse_position = mouse_position

            idle_after_position_update = self.CurrentlyIdle()

            move_knocked_us_out_of_idle = (
                not idle_before_position_update) and idle_after_position_update

            if move_knocked_us_out_of_idle:

                self.pub('set_status_bar_dirty')

    def ClosePageKeys(self, page_keys):

        with self._page_key_lock:

            self._closed_page_keys.update(page_keys)

    def CreateSplash(self):

        try:

            self._splash = ClientGUI.FrameSplash(self)

        except:

            HydrusData.Print(
                'There was an error trying to start the splash screen!')

            HydrusData.Print(traceback.format_exc())

            raise

    def CurrentlyIdle(self):

        if HG.program_is_shutting_down:

            return False

        if HG.force_idle_mode:

            self._idle_started = 0

            return True

        if not HydrusData.TimeHasPassed(self._timestamps['boot'] + 120):

            return False

        idle_normal = self.options['idle_normal']
        idle_period = self.options['idle_period']
        idle_mouse_period = self.options['idle_mouse_period']

        if idle_normal:

            currently_idle = True

            if idle_period is not None:

                if not HydrusData.TimeHasPassed(
                        self._timestamps['last_user_action'] + idle_period):

                    currently_idle = False

            if idle_mouse_period is not None:

                if not HydrusData.TimeHasPassed(
                        self._timestamps['last_mouse_action'] +
                        idle_mouse_period):

                    currently_idle = False

        else:

            currently_idle = False

        turning_idle = currently_idle and not self._previously_idle

        self._previously_idle = currently_idle

        if turning_idle:

            self._idle_started = HydrusData.GetNow()

            self.pub('wake_daemons')

        if not currently_idle:

            self._idle_started = None

        return currently_idle

    def CurrentlyVeryIdle(self):

        if HG.program_is_shutting_down:

            return False

        if self._idle_started is not None and HydrusData.TimeHasPassed(
                self._idle_started + 3600):

            return True

        return False

    def DoIdleShutdownWork(self):

        self.pub('splash_set_status_subtext', 'db')

        stop_time = HydrusData.GetNow() + (
            self.options['idle_shutdown_max_minutes'] * 60)

        self.MaintainDB(maintenance_mode=HC.MAINTENANCE_SHUTDOWN,
                        stop_time=stop_time)

        if not self.options['pause_repo_sync']:

            services = self.services_manager.GetServices(HC.REPOSITORIES)

            for service in services:

                if HydrusData.TimeHasPassed(stop_time):

                    return

                self.pub('splash_set_status_subtext',
                         '{} processing'.format(service.GetName()))

                service.SyncProcessUpdates(
                    maintenance_mode=HC.MAINTENANCE_SHUTDOWN,
                    stop_time=stop_time)

        self.Write('last_shutdown_work_time', HydrusData.GetNow())

    def Exit(self):

        if not self._is_booted:

            HG.emergency_exit = True

        HG.program_is_shutting_down = True

        if HG.emergency_exit:

            HydrusData.DebugPrint('doing fast shutdown\u2026')

            self.ShutdownView()
            self.ShutdownModel()

            HydrusData.CleanRunningFile(self.db_dir, 'client')

        else:

            try:

                last_shutdown_work_time = self.Read('last_shutdown_work_time')

                idle_shutdown_action = self.options['idle_shutdown']

                auto_shutdown_work_ok_by_user = idle_shutdown_action in (
                    CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST)

                shutdown_work_period = self.new_options.GetInteger(
                    'shutdown_work_period')

                auto_shutdown_work_due = HydrusData.TimeHasPassed(
                    last_shutdown_work_time + shutdown_work_period)

                manual_shutdown_work_not_already_set = not HG.do_idle_shutdown_work

                we_can_turn_on_auto_shutdown_work = auto_shutdown_work_ok_by_user and auto_shutdown_work_due and manual_shutdown_work_not_already_set

                if we_can_turn_on_auto_shutdown_work:

                    idle_shutdown_max_minutes = self.options[
                        'idle_shutdown_max_minutes']

                    time_to_stop = HydrusData.GetNow() + (
                        idle_shutdown_max_minutes * 60)

                    work_to_do = self.GetIdleShutdownWorkDue(time_to_stop)

                    if len(work_to_do) > 0:

                        if idle_shutdown_action == CC.IDLE_ON_SHUTDOWN_ASK_FIRST:

                            from . import ClientGUIDialogsQuick

                            text = 'Is now a good time for the client to do up to ' + HydrusData.ToHumanInt(
                                idle_shutdown_max_minutes
                            ) + ' minutes\' maintenance work? (Will auto-no in 15 seconds)'
                            text += os.linesep * 2
                            text += 'The outstanding jobs appear to be:'
                            text += os.linesep * 2
                            text += os.linesep.join(work_to_do)

                            result = ClientGUIDialogsQuick.GetYesNo(
                                self._splash,
                                text,
                                title='Maintenance is due',
                                auto_no_time=15)

                            if result == QW.QDialog.Accepted:

                                HG.do_idle_shutdown_work = True

                            else:

                                # if they said no, don't keep asking
                                self.Write('last_shutdown_work_time',
                                           HydrusData.GetNow())

                        else:

                            HG.do_idle_shutdown_work = True

                if HG.do_idle_shutdown_work:

                    self._splash.MakeCancelShutdownButton()

                self.CallToThreadLongRunning(self.THREADExitEverything)

            except:

                self._DestroySplash()

                HydrusData.DebugPrint(traceback.format_exc())

                HG.emergency_exit = True

                self.Exit()

    def GetClipboardText(self):

        clipboard_text = QW.QApplication.clipboard().text()

        if not clipboard_text:

            raise HydrusExceptions.DataMissing('No text on the clipboard!')

        return clipboard_text

    def GetCommandFromShortcut(self, shortcut_names, shortcut):

        return self.shortcuts_manager.GetCommand(shortcut_names, shortcut)

    def GetIdleShutdownWorkDue(self, time_to_stop):

        work_to_do = []

        work_to_do.extend(self.Read('maintenance_due', time_to_stop))

        services = self.services_manager.GetServices(HC.REPOSITORIES)

        for service in services:

            if service.CanDoIdleShutdownWork():

                work_to_do.append(service.GetName() + ' repository processing')

        return work_to_do

    def GetNewOptions(self):

        return self.new_options

    def InitClientFilesManager(self):
        def qt_code(missing_locations):

            with ClientGUITopLevelWindows.DialogManage(
                    None, 'repair file system') as dlg:

                panel = ClientGUIScrolledPanelsManagement.RepairFileSystemPanel(
                    dlg, missing_locations)

                dlg.SetPanel(panel)

                if dlg.exec() == QW.QDialog.Accepted:

                    self.client_files_manager = ClientFiles.ClientFilesManager(
                        self)

                    missing_locations = self.client_files_manager.GetMissing()

                else:

                    raise HydrusExceptions.ShutdownException(
                        'File system failed, user chose to quit.')

            return missing_locations

        self.client_files_manager = ClientFiles.ClientFilesManager(self)

        self.files_maintenance_manager = ClientFiles.FilesMaintenanceManager(
            self)

        missing_locations = self.client_files_manager.GetMissing()

        while len(missing_locations) > 0:

            missing_locations = self.CallBlockingToQt(self._splash, qt_code,
                                                      missing_locations)

    def InitModel(self):

        self.pub('splash_set_title_text', 'booting db\u2026')

        HydrusController.HydrusController.InitModel(self)

        self.pub('splash_set_status_text', 'initialising managers')

        self.pub('splash_set_status_subtext', 'services')

        self.services_manager = ClientManagers.ServicesManager(self)

        self.pub('splash_set_status_subtext', 'options')

        self.options = self.Read('options')
        self.new_options = self.Read(
            'serialisable',
            HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS)

        HC.options = self.options

        if self.new_options.GetBoolean('use_system_ffmpeg'):

            if HydrusVideoHandling.FFMPEG_PATH.startswith(HC.BIN_DIR):

                HydrusVideoHandling.FFMPEG_PATH = os.path.basename(
                    HydrusVideoHandling.FFMPEG_PATH)

        self.pub('splash_set_status_subtext', 'client files')

        self.InitClientFilesManager()

        #

        self.pub('splash_set_status_subtext', 'network')

        self.parsing_cache = ClientCaches.ParsingCache()

        client_api_manager = self.Read(
            'serialisable',
            HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_API_MANAGER)

        if client_api_manager is None:

            client_api_manager = ClientAPI.APIManager()

            client_api_manager._dirty = True

            self.SafeShowCriticalMessage(
                'Problem loading object',
                'Your client api manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.'
            )

        self.client_api_manager = client_api_manager

        bandwidth_manager = self.Read(
            'serialisable',
            HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER)

        if bandwidth_manager is None:

            bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager(
            )

            ClientDefaults.SetDefaultBandwidthManagerRules(bandwidth_manager)

            bandwidth_manager._dirty = True

            self.SafeShowCriticalMessage(
                'Problem loading object',
                'Your bandwidth manager was missing on boot! I have recreated a new empty one with default rules. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.'
            )

        session_manager = self.Read(
            'serialisable',
            HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER)

        if session_manager is None:

            session_manager = ClientNetworkingSessions.NetworkSessionManager()

            session_manager._dirty = True

            self.SafeShowCriticalMessage(
                'Problem loading object',
                'Your session manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.'
            )

        domain_manager = self.Read(
            'serialisable',
            HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER)

        if domain_manager is None:

            domain_manager = ClientNetworkingDomain.NetworkDomainManager()

            ClientDefaults.SetDefaultDomainManagerData(domain_manager)

            domain_manager._dirty = True

            self.SafeShowCriticalMessage(
                'Problem loading object',
                'Your domain manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.'
            )

        domain_manager.Initialise()

        login_manager = self.Read(
            'serialisable',
            HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER)

        if login_manager is None:

            login_manager = ClientNetworkingLogin.NetworkLoginManager()

            ClientDefaults.SetDefaultLoginManagerScripts(login_manager)

            login_manager._dirty = True

            self.SafeShowCriticalMessage(
                'Problem loading object',
                'Your login manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.'
            )

        login_manager.Initialise()

        self.network_engine = ClientNetworking.NetworkEngine(
            self, bandwidth_manager, session_manager, domain_manager,
            login_manager)

        self.CallToThreadLongRunning(self.network_engine.MainLoop)

        #

        self.quick_download_manager = ClientDownloading.QuickDownloadManager(
            self)

        self.CallToThreadLongRunning(self.quick_download_manager.MainLoop)

        #

        self.shortcuts_manager = ClientGUIShortcuts.ShortcutsManager(self)

        self.local_booru_manager = ClientCaches.LocalBooruCache(self)

        self.file_viewing_stats_manager = ClientManagers.FileViewingStatsManager(
            self)

        self.pub('splash_set_status_subtext', 'tag display')

        tag_display_manager = self.Read(
            'serialisable',
            HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER)

        if tag_display_manager is None:

            tag_display_manager = ClientTags.TagDisplayManager()

            tag_display_manager._dirty = True

            self.SafeShowCriticalMessage(
                'Problem loading object',
                'Your tag display manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.'
            )

        self.tag_display_manager = tag_display_manager

        self.pub('splash_set_status_subtext', 'tag siblings')

        self.tag_siblings_manager = ClientManagers.TagSiblingsManager(self)

        self.pub('splash_set_status_subtext', 'tag parents')

        self.tag_parents_manager = ClientManagers.TagParentsManager(self)
        self._managers['undo'] = ClientManagers.UndoManager(self)

        def qt_code():

            self._caches['images'] = ClientCaches.RenderedImageCache(self)
            self._caches['thumbnail'] = ClientCaches.ThumbnailCache(self)

            self.bitmap_manager = ClientManagers.BitmapManager(self)

            CC.GlobalPixmaps.STATICInitialise()

        self.pub('splash_set_status_subtext', 'image caches')

        self.CallBlockingToQt(self._splash, qt_code)

        self.sub(self, 'ToClipboard', 'clipboard')

    def InitView(self):

        if self.options['password'] is not None:

            self.pub('splash_set_status_text', 'waiting for password')

            def qt_code_password():

                while True:

                    with ClientGUIDialogs.DialogTextEntry(
                            self._splash,
                            'Enter your password.',
                            allow_blank=True,
                            password_entry=True) as dlg:

                        if dlg.exec() == QW.QDialog.Accepted:

                            password_bytes = bytes(dlg.GetValue(), 'utf-8')

                            if hashlib.sha256(password_bytes).digest(
                            ) == self.options['password']:

                                break

                        else:

                            raise HydrusExceptions.InsufficientCredentialsException(
                                'Bad password check')

            self.CallBlockingToQt(self._splash, qt_code_password)

        self.pub('splash_set_title_text', 'booting gui\u2026')

        self.subscriptions_manager = ClientImportSubscriptions.SubscriptionsManager(
            self)

        def qt_code_gui():

            ClientGUIStyle.InitialiseDefaults()

            qt_style_name = self.new_options.GetNoneableString('qt_style_name')

            if qt_style_name is not None:

                try:

                    ClientGUIStyle.SetStyleFromName(qt_style_name)

                except Exception as e:

                    HydrusData.Print('Could not load Qt style: {}'.format(e))

            qt_stylesheet_name = self.new_options.GetNoneableString(
                'qt_stylesheet_name')

            if qt_stylesheet_name is not None:

                try:

                    ClientGUIStyle.SetStylesheetFromPath(qt_stylesheet_name)

                except Exception as e:

                    HydrusData.Print(
                        'Could not load Qt stylesheet: {}'.format(e))

            self.gui = ClientGUI.FrameGUI(self)

            self.ResetIdleTimer()

        self.CallBlockingToQt(self._splash, qt_code_gui)

        # ShowText will now popup as a message, as popup message manager has overwritten the hooks

        HydrusController.HydrusController.InitView(self)

        self._service_keys_to_connected_ports = {}

        self.RestartClientServerServices()

        if not HG.no_daemons:

            self._daemons.append(
                HydrusThreading.DAEMONForegroundWorker(
                    self,
                    'MaintainTrash',
                    ClientDaemons.DAEMONMaintainTrash,
                    init_wait=120))
            self._daemons.append(
                HydrusThreading.DAEMONForegroundWorker(
                    self,
                    'SynchroniseRepositories',
                    ClientDaemons.DAEMONSynchroniseRepositories,
                    ('notify_restart_repo_sync_daemon',
                     'notify_new_permissions', 'wake_idle_workers'),
                    period=4 * 3600,
                    pre_call_wait=1))

        self.files_maintenance_manager.Start()

        job = self.CallRepeating(0.0, 30.0, self.SaveDirtyObjects)
        job.WakeOnPubSub('important_dirt_to_clean')
        self._daemon_jobs['save_dirty_objects'] = job

        job = self.CallRepeating(5.0, 3600.0, self.SynchroniseAccounts)
        job.ShouldDelayOnWakeup(True)
        job.WakeOnPubSub('notify_unknown_accounts')
        self._daemon_jobs['synchronise_accounts'] = job

        job = self.CallRepeatingQtSafe(self, 10.0, 10.0, self.CheckMouseIdle)
        self._daemon_jobs['check_mouse_idle'] = job

        if self.db.IsFirstStart():

            message = 'Hi, this looks like the first time you have started the hydrus client.'
            message += os.linesep * 2
            message += 'Don\'t forget to check out the help if you haven\'t already--it has an extensive \'getting started\' section, including how to update and the importance of backing up your database.'
            message += os.linesep * 2
            message += 'To dismiss popup messages like this, right-click them.'

            HydrusData.ShowText(message)

        if self.db.IsDBUpdated():

            HydrusData.ShowText('The client has updated to version ' +
                                str(HC.SOFTWARE_VERSION) + '!')

        for message in self.db.GetInitialMessages():

            HydrusData.ShowText(message)

    def IsBooted(self):

        return self._is_booted

    def LastShutdownWasBad(self):

        return self._last_shutdown_was_bad

    def MaintainDB(self, maintenance_mode=HC.MAINTENANCE_IDLE, stop_time=None):

        if maintenance_mode == HC.MAINTENANCE_IDLE and not self.GoodTimeToStartBackgroundWork(
        ):

            return

        if self.ShouldStopThisWork(maintenance_mode, stop_time=stop_time):

            return

        tree_stop_time = stop_time

        if tree_stop_time is None:

            tree_stop_time = HydrusData.GetNow() + 30

        self.WriteSynchronous('maintain_similar_files_tree',
                              stop_time=tree_stop_time)

        if self.ShouldStopThisWork(maintenance_mode, stop_time=stop_time):

            return

        if self.new_options.GetBoolean(
                'maintain_similar_files_duplicate_pairs_during_idle'):

            search_distance = self.new_options.GetInteger(
                'similar_files_duplicate_pairs_search_distance')

            search_stop_time = stop_time

            if search_stop_time is None:

                search_stop_time = HydrusData.GetNow() + 60

            self.WriteSynchronous(
                'maintain_similar_files_search_for_potential_duplicates',
                search_distance,
                stop_time=search_stop_time)

        if self.ShouldStopThisWork(maintenance_mode, stop_time=stop_time):

            return

        self.WriteSynchronous('vacuum',
                              maintenance_mode=maintenance_mode,
                              stop_time=stop_time)

        if self.ShouldStopThisWork(maintenance_mode, stop_time=stop_time):

            return

        self.WriteSynchronous('analyze',
                              maintenance_mode=maintenance_mode,
                              stop_time=stop_time)

        if self.ShouldStopThisWork(maintenance_mode, stop_time=stop_time):

            return

    def MaintainMemoryFast(self):

        HydrusController.HydrusController.MaintainMemoryFast(self)

        self.parsing_cache.CleanCache()

    def MaintainMemorySlow(self):

        HydrusController.HydrusController.MaintainMemorySlow(self)

        if HydrusData.TimeHasPassed(self._timestamps['last_page_change'] +
                                    30 * 60):

            self.pub('delete_old_closed_pages')

            self._timestamps['last_page_change'] = HydrusData.GetNow()

        disk_cache_maintenance_mb = self.new_options.GetNoneableInteger(
            'disk_cache_maintenance_mb')

        if disk_cache_maintenance_mb is not None and not HG.view_shutdown:

            cache_period = 3600
            disk_cache_stop_time = HydrusData.GetNow() + 2

            if HydrusData.TimeHasPassed(
                    self._timestamps['last_disk_cache_population'] +
                    cache_period):

                self.Read('load_into_disk_cache',
                          stop_time=disk_cache_stop_time,
                          caller_limit=disk_cache_maintenance_mb * 1024 * 1024)

                self._timestamps[
                    'last_disk_cache_population'] = HydrusData.GetNow()

        def do_gui_refs(gui):

            if self.gui is not None and QP.isValid(self.gui):

                self.gui.MaintainCanvasFrameReferences()

        QP.CallAfter(do_gui_refs, self.gui)

    def MenubarMenuIsOpen(self):

        self._menu_open = True

    def MenubarMenuIsClosed(self):

        self._menu_open = False

    def MenuIsOpen(self):

        return self._menu_open

    def PageAlive(self, page_key):

        with self._page_key_lock:

            return page_key in self._alive_page_keys

    def PageClosedButNotDestroyed(self, page_key):

        with self._page_key_lock:

            return page_key in self._closed_page_keys

    def PopupMenu(self, window, menu):

        if not menu.isEmpty():

            self._menu_open = True

            menu.exec_(
                QG.QCursor.pos()
            )  # This could also be window.mapToGlobal( QC.QPoint( 0, 0 ) ), but in practice, popping up at the current cursor position feels better.

            self._menu_open = False

        ClientGUIMenus.DestroyMenu(window, menu)

    def PrepStringForDisplay(self, text):

        return text.lower()

    def ProcessPubSub(self):

        self.CallBlockingToQt(self.app, self._pubsub.Process)

        # this needs to be blocking in some way or the pubsub daemon goes nuts
        #QW.QApplication.instance().postEvent( QW.QApplication.instance().pubsub_catcher, PubSubEvent( self._pubsub ) )

    def RefreshServices(self):

        self.services_manager.RefreshServices()

    def pub(self, *args, **kwargs):

        HydrusController.HydrusController.pub(self, *args, **kwargs)

        QW.QApplication.instance().postEvent(
            QW.QApplication.instance().pubsub_catcher, PubSubEvent())

    def ReleasePageKey(self, page_key):

        with self._page_key_lock:

            self._alive_page_keys.discard(page_key)
            self._closed_page_keys.discard(page_key)

    def ReportFirstSessionLoaded(self):

        job = self.CallRepeating(5.0, 180.0,
                                 ClientDaemons.DAEMONCheckImportFolders)
        job.WakeOnPubSub('notify_restart_import_folders_daemon')
        job.WakeOnPubSub('notify_new_import_folders')
        job.ShouldDelayOnWakeup(True)
        self._daemon_jobs['import_folders'] = job

        job = self.CallRepeating(5.0, 180.0,
                                 ClientDaemons.DAEMONCheckExportFolders)
        job.WakeOnPubSub('notify_restart_export_folders_daemon')
        job.WakeOnPubSub('notify_new_export_folders')
        job.ShouldDelayOnWakeup(True)
        self._daemon_jobs['export_folders'] = job

        self.subscriptions_manager.Start()

    def ResetPageChangeTimer(self):

        self._timestamps['last_page_change'] = HydrusData.GetNow()

    def RestartClientServerServices(self):

        services = [
            self.services_manager.GetService(service_key)
            for service_key in (CC.LOCAL_BOORU_SERVICE_KEY,
                                CC.CLIENT_API_SERVICE_KEY)
        ]

        services = [
            service for service in services if service.GetPort() is not None
        ]

        self.CallToThread(self.SetRunningTwistedServices, services)

    def RestoreDatabase(self):

        from . import ClientGUIDialogsQuick

        with QP.DirDialog(self.gui, 'Select backup location.') as dlg:

            if dlg.exec() == QW.QDialog.Accepted:

                path = dlg.GetPath()

                text = 'Are you sure you want to restore a backup from "' + path + '"?'
                text += os.linesep * 2
                text += 'Everything in your current database will be deleted!'
                text += os.linesep * 2
                text += 'The gui will shut down, and then it will take a while to complete the restore. Once it is done, the client will restart.'

                result = ClientGUIDialogsQuick.GetYesNo(self.gui, text)

                if result == QW.QDialog.Accepted:

                    def THREADRestart():

                        while not self.db.LoopIsFinished():

                            time.sleep(0.1)

                        self.db.RestoreBackup(path)

                        while not HG.shutdown_complete:

                            time.sleep(0.1)

                        HydrusData.RestartProcess()

                    self.CallToThreadLongRunning(THREADRestart)

                    QP.CallAfter(self.gui.SaveAndClose)

    def Run(self):

        QP.MonkeyPatchMissingMethods()

        self.app = App(self._pubsub, sys.argv)

        HydrusData.Print('booting controller\u2026')

        self.frame_icon_pixmap = QG.QPixmap(
            os.path.join(HC.STATIC_DIR, 'hydrus_32_non-transparent.png'))

        self.CreateSplash()

        signal.signal(signal.SIGINT, self.CatchSignal)
        signal.signal(signal.SIGTERM, self.CatchSignal)

        self.CallToThreadLongRunning(self.THREADBootEverything)

        HG.qt_app_running = True

        try:

            self.app.exec_()

        finally:

            HG.qt_app_running = False

        HydrusData.DebugPrint('shutting down controller\u2026')

    def SafeShowCriticalMessage(self, title, message):

        HydrusData.DebugPrint(title)
        HydrusData.DebugPrint(message)

        if QC.QThread.currentThread() == QW.QApplication.instance().thread():

            QW.QMessageBox.critical(None, title, message)

        else:

            self.CallBlockingToQt(self.app, QW.QMessageBox.critical, None,
                                  title, message)

    def SaveDirtyObjects(self):

        with HG.dirty_object_lock:

            dirty_services = [
                service for service in self.services_manager.GetServices()
                if service.IsDirty()
            ]

            if len(dirty_services) > 0:

                self.pub('splash_set_status_subtext', 'services')

                self.WriteSynchronous('dirty_services', dirty_services)

            if self.client_api_manager.IsDirty():

                self.pub('splash_set_status_subtext', 'client api manager')

                self.WriteSynchronous('serialisable', self.client_api_manager)

                self.client_api_manager.SetClean()

            if self.network_engine.bandwidth_manager.IsDirty():

                self.pub('splash_set_status_subtext', 'bandwidth manager')

                self.WriteSynchronous('serialisable',
                                      self.network_engine.bandwidth_manager)

                self.network_engine.bandwidth_manager.SetClean()

            if self.network_engine.domain_manager.IsDirty():

                self.pub('splash_set_status_subtext', 'domain manager')

                self.WriteSynchronous('serialisable',
                                      self.network_engine.domain_manager)

                self.network_engine.domain_manager.SetClean()

            if self.network_engine.login_manager.IsDirty():

                self.pub('splash_set_status_subtext', 'login manager')

                self.WriteSynchronous('serialisable',
                                      self.network_engine.login_manager)

                self.network_engine.login_manager.SetClean()

            if self.network_engine.session_manager.IsDirty():

                self.pub('splash_set_status_subtext', 'session manager')

                self.WriteSynchronous('serialisable',
                                      self.network_engine.session_manager)

                self.network_engine.session_manager.SetClean()

            if self.tag_display_manager.IsDirty():

                self.pub('splash_set_status_subtext', 'tag display manager')

                self.WriteSynchronous('serialisable', self.tag_display_manager)

                self.tag_display_manager.SetClean()

    def SaveGUISession(self, session):

        name = session.GetName()

        if name == 'last session':

            session_hash = hashlib.sha256(
                bytes(session.DumpToString(), 'utf-8')).digest()

            if session_hash == self._last_last_session_hash:

                return

            self._last_last_session_hash = session_hash

        self.WriteSynchronous('serialisable', session)

        self.pub('notify_new_sessions')

    def SetRunningTwistedServices(self, services):
        def TWISTEDDoIt():
            def StartServices(*args, **kwargs):

                HydrusData.Print('starting services\u2026')

                for service in services:

                    service_key = service.GetServiceKey()
                    service_type = service.GetServiceType()

                    name = service.GetName()

                    port = service.GetPort()
                    allow_non_local_connections = service.AllowsNonLocalConnections(
                    )

                    if port is None:

                        continue

                    try:

                        from . import ClientLocalServer

                        if service_type == HC.LOCAL_BOORU:

                            http_factory = ClientLocalServer.HydrusServiceBooru(
                                service,
                                allow_non_local_connections=
                                allow_non_local_connections)

                        elif service_type == HC.CLIENT_API_SERVICE:

                            http_factory = ClientLocalServer.HydrusServiceClientAPI(
                                service,
                                allow_non_local_connections=
                                allow_non_local_connections)

                        self._service_keys_to_connected_ports[
                            service_key] = reactor.listenTCP(
                                port, http_factory)

                        if not HydrusNetworking.LocalPortInUse(port):

                            HydrusData.ShowText(
                                'Tried to bind port {} for "{}" but it failed.'
                                .format(port, name))

                    except Exception as e:

                        HydrusData.ShowText(
                            'Could not start "{}":'.format(name))
                        HydrusData.ShowException(e)

                HydrusData.Print('services started')

            if len(self._service_keys_to_connected_ports) > 0:

                HydrusData.Print('stopping services\u2026')

                deferreds = []

                for port in self._service_keys_to_connected_ports.values():

                    deferred = defer.maybeDeferred(port.stopListening)

                    deferreds.append(deferred)

                self._service_keys_to_connected_ports = {}

                deferred = defer.DeferredList(deferreds)

                if len(services) > 0:

                    deferred.addCallback(StartServices)

            elif len(services) > 0:

                StartServices()

        if HG.twisted_is_broke:

            if True in (service.GetPort() is not None for service in services):

                HydrusData.ShowText(
                    'Twisted failed to import, so could not start the local booru/client api! Please contact hydrus dev!'
                )

        else:

            threads.blockingCallFromThread(reactor, TWISTEDDoIt)

    def SetServices(self, services):

        with HG.dirty_object_lock:

            upnp_services = [
                service for service in services
                if service.GetServiceType() in (HC.LOCAL_BOORU,
                                                HC.CLIENT_API_SERVICE)
            ]

            self.CallToThread(self.services_upnp_manager.SetServices,
                              upnp_services)

            self.WriteSynchronous('update_services', services)

            self.services_manager.RefreshServices()

        self.RestartClientServerServices()

    def ShutdownModel(self):

        self.pub('splash_set_status_text', 'saving and exiting objects')

        if self._is_booted:

            self.pub('splash_set_status_subtext', 'file viewing stats flush')

            self.file_viewing_stats_manager.Flush()

            self.pub('splash_set_status_subtext', '')

            self.SaveDirtyObjects()

        HydrusController.HydrusController.ShutdownModel(self)

    def ShutdownView(self):

        if not HG.emergency_exit:

            self.pub('splash_set_status_text',
                     'waiting for subscriptions to exit')

            self._ShutdownSubscriptionsManager()

            self.pub('splash_set_status_text', 'waiting for daemons to exit')

            self._ShutdownDaemons()

            self.pub('splash_set_status_subtext', '')

            if HG.do_idle_shutdown_work:

                self.pub('splash_set_status_text',
                         'waiting for idle shutdown work')

                try:

                    self.DoIdleShutdownWork()

                    self.pub('splash_set_status_subtext', '')

                except:

                    self._ReportShutdownException()

            self.pub('splash_set_status_subtext', 'files maintenance manager')

            self.files_maintenance_manager.Shutdown()

            self.pub('splash_set_status_subtext', 'download manager')

            self.quick_download_manager.Shutdown()

            self.pub('splash_set_status_subtext', '')

            try:

                self.pub('splash_set_status_text',
                         'waiting for twisted to exit')

                self.SetRunningTwistedServices([])

            except:

                pass  # sometimes this throws a wobbler, screw it

        HydrusController.HydrusController.ShutdownView(self)

    def SynchroniseAccounts(self):

        services = self.services_manager.GetServices(HC.RESTRICTED_SERVICES)

        for service in services:

            if HydrusThreading.IsThreadShuttingDown():

                return

            service.SyncAccount()

    def SystemBusy(self):

        if HG.force_idle_mode:

            return False

        max_cpu = self.options['idle_cpu_max']

        if max_cpu is None:

            self._system_busy = False

        else:

            if HydrusData.TimeHasPassed(self._timestamps['last_cpu_check'] +
                                        60):

                cpu_times = psutil.cpu_percent(percpu=True)

                if True in (cpu_time > max_cpu for cpu_time in cpu_times):

                    self._system_busy = True

                else:

                    self._system_busy = False

                self._timestamps['last_cpu_check'] = HydrusData.GetNow()

        return self._system_busy

    def THREADBootEverything(self):

        try:

            self.CheckAlreadyRunning()

        except HydrusExceptions.ShutdownException:

            self._DestroySplash()

            return

        try:

            self._last_shutdown_was_bad = HydrusData.LastShutdownWasBad(
                self.db_dir, 'client')

            HydrusData.RecordRunningStart(self.db_dir, 'client')

            self.InitModel()

            self.InitView()

            self._is_booted = True

        except (HydrusExceptions.InsufficientCredentialsException,
                HydrusExceptions.ShutdownException) as e:

            HydrusData.Print(e)

            HydrusData.CleanRunningFile(self.db_dir, 'client')

            QP.CallAfter(QW.QApplication.exit, 0)

        except Exception as e:

            text = 'A serious error occurred while trying to start the program. The error will be shown next in a window. More information may have been written to client.log.'

            HydrusData.DebugPrint(
                'If the db crashed, another error may be written just above ^.'
            )
            HydrusData.DebugPrint(text)

            HydrusData.DebugPrint(traceback.format_exc())

            self.SafeShowCriticalMessage('boot error', text)

            self.SafeShowCriticalMessage('boot error', traceback.format_exc())

            QP.CallAfter(QW.QApplication.exit, 0)

        finally:

            self._DestroySplash()

    def THREADExitEverything(self):

        try:

            gc.collect()

            self.pub('splash_set_title_text', 'shutting down gui\u2026')

            self.ShutdownView()

            self.pub('splash_set_title_text', 'shutting down db\u2026')

            self.ShutdownModel()

            self.pub('splash_set_title_text', 'cleaning up\u2026')

            HydrusData.CleanRunningFile(self.db_dir, 'client')

        except (HydrusExceptions.InsufficientCredentialsException,
                HydrusExceptions.ShutdownException):

            pass

        except:

            self._ReportShutdownException()

        finally:

            QW.QApplication.instance().setProperty('normal_exit', True)

            self._DestroySplash()

            QP.CallAfter(QW.QApplication.exit)

    def ToClipboard(self, data_type, data):

        # need this cause can't do it in a non-gui thread

        if data_type == 'paths':

            paths = []

            for path in data:

                paths.append(QC.QUrl.fromLocalFile(path))

            mime_data = QC.QMimeData()

            mime_data.setUrls(paths)

            QW.QApplication.clipboard().setMimeData(mime_data)

        elif data_type == 'text':

            text = data

            QW.QApplication.clipboard().setText(text)

        elif data_type == 'bmp':

            media = data

            image_renderer = self.GetCache('images').GetImageRenderer(media)

            def CopyToClipboard():

                qt_image = image_renderer.GetQtImage().copy()

                QW.QApplication.clipboard().setImage(qt_image)

            def THREADWait():

                start_time = time.time()

                while not image_renderer.IsReady():

                    if HydrusData.TimeHasPassed(start_time + 15):

                        HydrusData.ShowText(
                            'The image did not render in fifteen seconds, so the attempt to copy it to the clipboard was abandoned.'
                        )

                        return

                    time.sleep(0.1)

                QP.CallAfter(CopyToClipboard)

            self.CallToThread(THREADWait)

    def UnclosePageKeys(self, page_keys):

        with self._page_key_lock:

            self._closed_page_keys.difference_update(page_keys)

    def WaitUntilViewFree(self):

        self.WaitUntilModelFree()

        self.WaitUntilThumbnailsFree()

    def WaitUntilThumbnailsFree(self):

        self._caches['thumbnail'].WaitUntilFree()

    def Write(self, action, *args, **kwargs):

        if action == 'content_updates':

            self._managers['undo'].AddCommand('content_updates', *args,
                                              **kwargs)

        return HydrusController.HydrusController.Write(self, action, *args,
                                                       **kwargs)
