import os
import random
import time

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from . import ClientConstants as CC
from . import (ClientGUIDialogsQuick, ClientGUIMenus, ClientMedia, ClientPaths,
               ClientThreading, HydrusData, HydrusExceptions)
from . import HydrusGlobals as HG
from . import HydrusPaths
from . import QtPorting as QP


def CopyMediaURLs(medias):

    urls = set()

    for media in medias:

        media_urls = media.GetLocationsManager().GetURLs()

        urls.update(media_urls)

    urls = list(urls)

    urls.sort()

    urls_string = os.linesep.join(urls)

    HG.client_controller.pub('clipboard', 'text', urls_string)


def CopyMediaURLClassURLs(medias, url_class):

    urls = set()

    for media in medias:

        media_urls = media.GetLocationsManager().GetURLs()

        for url in media_urls:

            if url_class.Matches(url):

                urls.add(url)

    urls = list(urls)

    urls.sort()

    urls_string = os.linesep.join(urls)

    HG.client_controller.pub('clipboard', 'text', urls_string)


def DoOpenKnownURLFromShortcut(win, media):

    urls = media.GetLocationsManager().GetURLs()

    matched_labels_and_urls = []
    unmatched_urls = []

    if len(urls) > 0:

        for url in urls:

            url_class = HG.client_controller.network_engine.domain_manager.GetURLClass(
                url)

            if url_class is None:

                unmatched_urls.append(url)

            else:

                label = url_class.GetName() + ': ' + url

                matched_labels_and_urls.append((label, url))

        matched_labels_and_urls.sort()
        unmatched_urls.sort()

    if len(matched_labels_and_urls) == 0:

        return

    elif len(matched_labels_and_urls) == 1:

        url = matched_labels_and_urls[0][1]

    else:

        matched_labels_and_urls.extend((url, url) for url in unmatched_urls)

        try:

            url = ClientGUIDialogsQuick.SelectFromList(win,
                                                       'Select which URL',
                                                       matched_labels_and_urls,
                                                       sort_tuples=False)

        except HydrusExceptions.CancelledException:

            return

    ClientPaths.LaunchURLInWebBrowser(url)


def OpenExternally(media):

    hash = media.GetHash()
    mime = media.GetMime()

    client_files_manager = HG.client_controller.client_files_manager

    path = client_files_manager.GetFilePath(hash, mime)

    new_options = HG.client_controller.new_options

    launch_path = new_options.GetMimeLaunch(mime)

    HydrusPaths.LaunchFile(path, launch_path)


def OpenURLs(urls):

    urls = list(urls)

    urls.sort()

    if len(urls) > 1:

        message = 'Open the {} URLs in your web browser?'.format(len(urls))

        if len(urls) > 10:

            message += ' This will take some time.'

        result = ClientGUIDialogsQuick.GetYesNo(HG.client_controller.gui,
                                                message)

        if result != QW.QDialog.Accepted:

            return

    def do_it(urls):

        job_key = None

        num_urls = len(urls)

        if num_urls > 5:

            job_key = ClientThreading.JobKey(pausable=True, cancellable=True)

            job_key.SetVariable('popup_title', 'Opening URLs')

            HG.client_controller.pub('message', job_key)

        try:

            for (i, url) in enumerate(urls):

                if job_key is not None:

                    (i_paused, should_quit) = job_key.WaitIfNeeded()

                    if should_quit:

                        return

                    job_key.SetVariable(
                        'popup_text_1',
                        HydrusData.ConvertValueRangeToPrettyString(
                            i + 1, num_urls))
                    job_key.SetVariable('popup_gauge_1', (i + 1, num_urls))

                ClientPaths.LaunchURLInWebBrowser(url)

                time.sleep(1)

        finally:

            if job_key is not None:

                job_key.Finish()

                job_key.Delete(1)

    HG.client_controller.CallToThread(do_it, urls)


def OpenMediaURLs(medias):

    urls = set()

    for media in medias:

        media_urls = media.GetLocationsManager().GetURLs()

        urls.update(media_urls)

    OpenURLs(urls)


def OpenMediaURLClassURLs(medias, url_class):

    urls = set()

    for media in medias:

        media_urls = media.GetLocationsManager().GetURLs()

        for url in media_urls:

            if url_class.Matches(url):

                urls.add(url)

    OpenURLs(urls)


def AddFileViewingStatsMenu(menu, focus_media):

    view_style = HG.client_controller.new_options.GetInteger(
        'file_viewing_stats_menu_display')

    if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_NONE:

        return

    fvsm = focus_media.GetFileViewingStatsManager()

    if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED:

        combined_line = fvsm.GetPrettyCombinedLine()

        ClientGUIMenus.AppendMenuLabel(menu, combined_line)

    else:

        media_line = fvsm.GetPrettyMediaLine()
        preview_line = fvsm.GetPrettyPreviewLine()

        if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY:

            ClientGUIMenus.AppendMenuLabel(menu, media_line)

        elif view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU:

            submenu = QW.QMenu(menu)

            ClientGUIMenus.AppendMenuLabel(submenu, preview_line)

            ClientGUIMenus.AppendMenu(menu, submenu, media_line)

        elif view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_STACKED:

            ClientGUIMenus.AppendMenuLabel(menu, media_line)
            ClientGUIMenus.AppendMenuLabel(menu, preview_line)


def AddKnownURLsViewCopyMenu(win, menu, focus_media, selected_media=None):

    # figure out which urls this focused file has

    focus_urls = focus_media.GetLocationsManager().GetURLs()

    focus_matched_labels_and_urls = []
    focus_unmatched_urls = []
    focus_labels_and_urls = []

    if len(focus_urls) > 0:

        for url in focus_urls:

            url_class = HG.client_controller.network_engine.domain_manager.GetURLClass(
                url)

            if url_class is None:

                focus_unmatched_urls.append(url)

            else:

                label = url_class.GetName() + ': ' + url

                focus_matched_labels_and_urls.append((label, url))

        focus_matched_labels_and_urls.sort()
        focus_unmatched_urls.sort()

        focus_labels_and_urls = list(focus_matched_labels_and_urls)

        focus_labels_and_urls.extend(
            ((url, url) for url in focus_unmatched_urls))

    # figure out which urls these selected files have

    selected_media_url_classes = set()
    multiple_or_unmatching_selection_url_classes = False

    if selected_media is not None and len(selected_media) > 1:

        selected_media = ClientMedia.FlattenMedia(selected_media)

        SAMPLE_SIZE = 256

        if len(selected_media) > SAMPLE_SIZE:

            selected_media_sample = random.sample(selected_media, SAMPLE_SIZE)

        else:

            selected_media_sample = selected_media

        for media in selected_media_sample:

            media_urls = media.GetLocationsManager().GetURLs()

            for url in media_urls:

                url_class = HG.client_controller.network_engine.domain_manager.GetURLClass(
                    url)

                if url_class is None:

                    multiple_or_unmatching_selection_url_classes = True

                else:

                    selected_media_url_classes.add(url_class)

        if len(selected_media_url_classes) > 1:

            multiple_or_unmatching_selection_url_classes = True

    if len(focus_labels_and_urls) > 0 or len(
            selected_media_url_classes
    ) > 0 or multiple_or_unmatching_selection_url_classes:

        urls_menu = QW.QMenu(menu)

        urls_visit_menu = QW.QMenu(urls_menu)
        urls_copy_menu = QW.QMenu(urls_menu)

        # copy each this file's urls (of a particular type)

        if len(focus_labels_and_urls) > 0:

            for (label, url) in focus_labels_and_urls:

                ClientGUIMenus.AppendMenuItem(
                    urls_visit_menu, label,
                    'Open this url in your web browser.',
                    ClientPaths.LaunchURLInWebBrowser, url)
                ClientGUIMenus.AppendMenuItem(
                    urls_copy_menu, label, 'Copy this url to your clipboard.',
                    HG.client_controller.pub, 'clipboard', 'text', url)

        # copy this file's urls

        there_are_focus_url_classes_to_action = len(
            focus_matched_labels_and_urls) > 1
        multiple_or_unmatching_focus_url_classes = len(
            focus_unmatched_urls) > 0 and len(
                focus_labels_and_urls
            ) > 1  # if there are unmatched urls and more than one thing total

        if there_are_focus_url_classes_to_action or multiple_or_unmatching_focus_url_classes:

            ClientGUIMenus.AppendSeparator(urls_visit_menu)
            ClientGUIMenus.AppendSeparator(urls_copy_menu)

        if there_are_focus_url_classes_to_action:

            urls = [url for (label, url) in focus_matched_labels_and_urls]

            label = 'open this file\'s ' + HydrusData.ToHumanInt(
                len(urls)) + ' recognised urls in your web browser'

            ClientGUIMenus.AppendMenuItem(
                urls_visit_menu, label, 'Open these urls in your web browser.',
                OpenURLs, urls)

            urls_string = os.linesep.join(urls)

            label = 'copy this file\'s ' + HydrusData.ToHumanInt(
                len(urls)) + ' recognised urls to your clipboard'

            ClientGUIMenus.AppendMenuItem(
                urls_copy_menu, label, 'Copy these urls to your clipboard.',
                HG.client_controller.pub, 'clipboard', 'text', urls_string)

        if multiple_or_unmatching_focus_url_classes:

            urls = [url for (label, url) in focus_labels_and_urls]

            label = 'open this file\'s ' + HydrusData.ToHumanInt(
                len(urls)) + ' urls in your web browser'

            ClientGUIMenus.AppendMenuItem(
                urls_visit_menu, label, 'Open these urls in your web browser.',
                OpenURLs, urls)

            urls_string = os.linesep.join(urls)

            label = 'copy this file\'s ' + HydrusData.ToHumanInt(
                len(urls)) + ' urls to your clipboard'

            ClientGUIMenus.AppendMenuItem(urls_copy_menu, label,
                                          'Copy this url to your clipboard.',
                                          HG.client_controller.pub,
                                          'clipboard', 'text', urls_string)

        # now by url match type

        there_are_selection_url_classes_to_action = len(
            selected_media_url_classes) > 0

        if there_are_selection_url_classes_to_action or multiple_or_unmatching_selection_url_classes:

            ClientGUIMenus.AppendSeparator(urls_visit_menu)
            ClientGUIMenus.AppendSeparator(urls_copy_menu)

        if there_are_selection_url_classes_to_action:

            selected_media_url_classes = list(selected_media_url_classes)

            selected_media_url_classes.sort(
                key=lambda url_class: url_class.GetName())

            for url_class in selected_media_url_classes:

                label = 'open files\' ' + url_class.GetName(
                ) + ' urls in your web browser'

                ClientGUIMenus.AppendMenuItem(
                    urls_visit_menu, label,
                    'Open this url class in your web browser for all files.',
                    OpenMediaURLClassURLs, selected_media, url_class)

                label = 'copy files\' ' + url_class.GetName() + ' urls'

                ClientGUIMenus.AppendMenuItem(
                    urls_copy_menu, label,
                    'Copy this url class for all files.',
                    CopyMediaURLClassURLs, selected_media, url_class)

        # now everything

        if multiple_or_unmatching_selection_url_classes:

            label = 'open all files\' urls'

            ClientGUIMenus.AppendMenuItem(
                urls_visit_menu, label,
                'Open urls in your web browser for all files.', OpenMediaURLs,
                selected_media)

            label = 'copy all files\' urls'

            ClientGUIMenus.AppendMenuItem(urls_copy_menu, label,
                                          'Copy urls for all files.',
                                          CopyMediaURLs, selected_media)

        #

        ClientGUIMenus.AppendMenu(urls_menu, urls_visit_menu, 'open')
        ClientGUIMenus.AppendMenu(urls_menu, urls_copy_menu, 'copy')

        ClientGUIMenus.AppendMenu(menu, urls_menu, 'known urls')


def AddServiceKeyLabelsToMenu(menu, service_keys, phrase):

    services_manager = HG.client_controller.services_manager

    if len(service_keys) == 1:

        (service_key, ) = service_keys

        name = services_manager.GetName(service_key)

        label = phrase + ' ' + name

        ClientGUIMenus.AppendMenuLabel(menu, label)

    else:

        submenu = QW.QMenu(menu)

        for service_key in service_keys:

            name = services_manager.GetName(service_key)

            ClientGUIMenus.AppendMenuLabel(submenu, name)

        ClientGUIMenus.AppendMenu(menu, submenu, phrase + '\u2026')


def AddServiceKeysToMenu(event_handler, menu, service_keys, phrase,
                         description, callable):

    services_manager = HG.client_controller.services_manager

    if len(service_keys) == 1:

        (service_key, ) = service_keys

        name = services_manager.GetName(service_key)

        label = phrase + ' ' + name

        ClientGUIMenus.AppendMenuItem(menu, label, description, callable,
                                      service_key)

    else:

        submenu = QW.QMenu(menu)

        for service_key in service_keys:

            name = services_manager.GetName(service_key)

            ClientGUIMenus.AppendMenuItem(submenu, name, description, callable,
                                          service_key)

        ClientGUIMenus.AppendMenu(menu, submenu, phrase + '\u2026')
