from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusSerialisable
from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientGUIACDropdown
from . import ClientGUICanvas
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIFunctions
from . import ClientGUIImport
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIMedia
from . import ClientGUIMenus
from . import ClientGUIParsing
from . import ClientGUIResults
from . import ClientGUIScrolledPanels
from . import ClientGUIFileSeedCache
from . import ClientGUIGallerySeedLog
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUITopLevelWindows
from . import ClientImportGallery
from . import ClientImportLocal
from . import ClientImportOptions
from . import ClientImportSimpleURLs
from . import ClientImportWatchers
from . import ClientMedia
from . import ClientParsing
from . import ClientPaths
from . import ClientSearch
from . import ClientTags
from . import ClientThreading
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusTags
from . import HydrusThreading
import os
import random
import time
import traceback
from . import QtPorting as QP
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

MANAGEMENT_TYPE_DUMPER = 0
MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY = 1
MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER = 2
MANAGEMENT_TYPE_IMPORT_HDD = 3
MANAGEMENT_TYPE_IMPORT_WATCHER = 4 # defunct
MANAGEMENT_TYPE_PETITIONS = 5
MANAGEMENT_TYPE_QUERY = 6
MANAGEMENT_TYPE_IMPORT_URLS = 7
MANAGEMENT_TYPE_DUPLICATE_FILTER = 8
MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER = 9
MANAGEMENT_TYPE_PAGE_OF_PAGES = 10

management_panel_types_to_classes = {}

def CreateManagementController( page_name, management_type, file_service_key = None ):
    
    if file_service_key is None:
        
        file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
        
    
    new_options = HG.client_controller.new_options
    
    management_controller = ManagementController( page_name )
    
    management_controller.SetType( management_type )
    management_controller.SetKey( 'file_service', file_service_key )
    management_controller.SetVariable( 'media_sort', new_options.GetDefaultSort() )
    management_controller.SetVariable( 'media_collect', new_options.GetDefaultCollect() )
    
    return management_controller
    
def CreateManagementControllerDuplicateFilter():
    
    management_controller = CreateManagementController( 'duplicates', MANAGEMENT_TYPE_DUPLICATE_FILTER )
    
    file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ] )
    
    management_controller.SetVariable( 'file_search_context', file_search_context )
    management_controller.SetVariable( 'both_files_match', False )
    
    return management_controller
    
def CreateManagementControllerImportGallery():
    
    page_name = 'gallery'
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY )
    
    gug_key_and_name = HG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
    
    multiple_gallery_import = ClientImportGallery.MultipleGalleryImport( gug_key_and_name = gug_key_and_name )
    
    management_controller.SetVariable( 'multiple_gallery_import', multiple_gallery_import )
    
    return management_controller
    
def CreateManagementControllerImportSimpleDownloader():
    
    management_controller = CreateManagementController( 'simple downloader', MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER )
    
    simple_downloader_import = ClientImportSimpleURLs.SimpleDownloaderImport()
    
    formula_name = HG.client_controller.new_options.GetString( 'favourite_simple_downloader_formula' )
    
    simple_downloader_import.SetFormulaName( formula_name )
    
    management_controller.SetVariable( 'simple_downloader_import', simple_downloader_import )
    
    return management_controller
    
def CreateManagementControllerImportHDD( paths, file_import_options, paths_to_service_keys_to_tags, delete_after_success ):
    
    management_controller = CreateManagementController( 'import', MANAGEMENT_TYPE_IMPORT_HDD )
    
    hdd_import = ClientImportLocal.HDDImport( paths = paths, file_import_options = file_import_options, paths_to_service_keys_to_tags = paths_to_service_keys_to_tags, delete_after_success = delete_after_success )
    
    management_controller.SetVariable( 'hdd_import', hdd_import )
    
    return management_controller
    
def CreateManagementControllerImportMultipleWatcher( page_name = None, url = None ):
    
    if page_name is None:
        
        page_name = 'watcher'
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER )
    
    multiple_watcher_import = ClientImportWatchers.MultipleWatcherImport( url = url )
    
    management_controller.SetVariable( 'multiple_watcher_import', multiple_watcher_import )
    
    return management_controller
    
def CreateManagementControllerImportURLs( page_name = None ):
    
    if page_name is None:
        
        page_name = 'url import'
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_URLS )
    
    urls_import = ClientImportSimpleURLs.URLsImport()
    
    management_controller.SetVariable( 'urls_import', urls_import )
    
    return management_controller
    
def CreateManagementControllerPetitions( petition_service_key ):
    
    petition_service = HG.client_controller.services_manager.GetService( petition_service_key )
    
    page_name = petition_service.GetName() + ' petitions'
    
    petition_service_type = petition_service.GetServiceType()
    
    if petition_service_type in HC.LOCAL_FILE_SERVICES or petition_service_type == HC.FILE_REPOSITORY:
        
        file_service_key = petition_service_key
        
    else:
        
        file_service_key = CC.COMBINED_FILE_SERVICE_KEY
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_PETITIONS, file_service_key = file_service_key )
    
    management_controller.SetKey( 'petition_service', petition_service_key )
    
    return management_controller
    
def CreateManagementControllerQuery( page_name, file_service_key, file_search_context, search_enabled ):
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_QUERY, file_service_key = file_service_key )
    
    management_controller.SetVariable( 'file_search_context', file_search_context )
    management_controller.SetVariable( 'search_enabled', search_enabled )
    management_controller.SetVariable( 'synchronised', True )
    
    return management_controller
    
def CreateManagementPanel( parent, page, controller, management_controller ):
    
    management_type = management_controller.GetType()
    
    management_class = management_panel_types_to_classes[ management_type ]
    
    management_panel = management_class( parent, page, controller, management_controller )
    
    return management_panel
    
class ManagementController( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER
    SERIALISABLE_NAME = 'Client Page Management Controller'
    SERIALISABLE_VERSION = 10
    
    def __init__( self, page_name = 'page' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._page_name = page_name
        
        self._management_type = None
        
        self._keys = {}
        self._simples = {}
        self._serialisables = {}
        
    
    def __repr__( self ):
        
        return 'Management Controller: {} - {}'.format( self._management_type, self._page_name )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_keys = { name : value.hex() for ( name, value ) in list(self._keys.items()) }
        
        serialisable_simples = dict( self._simples )
        
        serialisable_serialisables = { name : value.GetSerialisableTuple() for ( name, value ) in list(self._serialisables.items()) }
        
        return ( self._page_name, self._management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
        
    
    def _InitialiseDefaults( self ):
        
        self._serialisables[ 'media_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._page_name, self._management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = serialisable_info
        
        self._InitialiseDefaults()
        
        self._keys.update( { name : bytes.fromhex( key ) for ( name, key ) in list(serialisable_keys.items()) } )
        
        if 'file_service' in self._keys:
            
            if not HG.client_controller.services_manager.ServiceExists( self._keys[ 'file_service' ] ):
                
                self._keys[ 'file_service' ] = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                
            
        
        self._simples.update( dict( serialisable_simples ) )
        
        self._serialisables.update( { name : HydrusSerialisable.CreateFromSerialisableTuple( value ) for ( name, value ) in list(serialisable_serialisables.items()) } )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                advanced_import_options = serialisable_simples[ 'advanced_import_options' ]
                paths_info = serialisable_simples[ 'paths_info' ]
                paths_to_tags = serialisable_simples[ 'paths_to_tags' ]
                delete_after_success = serialisable_simples[ 'delete_after_success' ]
                
                paths = [ path_info for ( path_type, path_info ) in paths_info if path_type != 'zip' ]
                
                exclude_deleted = advanced_import_options[ 'exclude_deleted' ]
                do_not_check_known_urls_before_importing = False
                do_not_check_hashes_before_importing = False   
                allow_decompression_bombs = False
                min_size = advanced_import_options[ 'min_size' ]
                max_size = None
                max_gif_size = None
                min_resolution = advanced_import_options[ 'min_resolution' ]
                max_resolution = None
                
                automatic_archive = advanced_import_options[ 'automatic_archive' ]
                associate_source_urls = True
                
                file_import_options = ClientImportOptions.FileImportOptions()
                
                file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
                file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
                
                paths_to_tags = { path : { bytes.fromhex( service_key ) : tags for ( service_key, tags ) in service_keys_to_tags } for ( path, service_keys_to_tags ) in list(paths_to_tags.items()) }
                
                hdd_import = ClientImportLocal.HDDImport( paths = paths, file_import_options = file_import_options, paths_to_service_keys_to_tags = paths_to_tags, delete_after_success = delete_after_success )
                
                serialisable_serialisables[ 'hdd_import' ] = hdd_import.GetSerialisableTuple()
                
                del serialisable_serialisables[ 'advanced_import_options' ]
                del serialisable_serialisables[ 'paths_info' ]
                del serialisable_serialisables[ 'paths_to_tags' ]
                del serialisable_serialisables[ 'delete_after_success' ]
                
            
            new_serialisable_info = ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            page_name = 'page'
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'page_of_images_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'simple_downloader_import' ] = serialisable_serialisables[ 'page_of_images_import' ]
                
                del serialisable_serialisables[ 'page_of_images_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'thread_watcher_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'watcher_import' ] = serialisable_serialisables[ 'thread_watcher_import' ]
                
                del serialisable_serialisables[ 'thread_watcher_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'gallery_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'multiple_gallery_import' ] = serialisable_serialisables[ 'gallery_import' ]
                
                del serialisable_serialisables[ 'gallery_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'watcher_import' in serialisable_serialisables:
                
                watcher = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_serialisables[ 'watcher_import' ] )
                
                management_type = MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER
                
                multiple_watcher_import = ClientImportWatchers.MultipleWatcherImport()
                
                multiple_watcher_import.AddWatcher( watcher )
                
                serialisable_multiple_watcher_import = multiple_watcher_import.GetSerialisableTuple()
                
                serialisable_serialisables[ 'multiple_watcher_import' ] = serialisable_multiple_watcher_import
                
                del serialisable_serialisables[ 'watcher_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if page_name.startswith( '[USER]' ) and len( page_name ) > 6:
                
                page_name = page_name[6:]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_DUPLICATE_FILTER:
                
                if 'duplicate_filter_file_domain' in serialisable_keys:
                    
                    del serialisable_keys[ 'duplicate_filter_file_domain' ]
                    
                
                file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ] )
                
                serialisable_serialisables[ 'file_search_context' ] = file_search_context.GetSerialisableTuple()
                
                serialisable_simples[ 'both_files_match' ] = False
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'media_collect' in serialisable_simples:
                
                try:
                    
                    old_collect = serialisable_simples[ 'media_collect' ]
                    
                    if old_collect is None:
                        
                        old_collect = []
                        
                    
                    namespaces = [ n for ( t, n ) in old_collect if t == 'namespace' ]
                    rating_service_keys = [ bytes.fromhex( r ) for ( t, r ) in old_collect if t == 'rating' ]
                    
                except:
                    
                    namespaces = []
                    rating_service_keys = []
                    
                
                media_collect = ClientMedia.MediaCollect( namespaces = namespaces, rating_service_keys = rating_service_keys )
                
                serialisable_serialisables[ 'media_collect' ] = media_collect.GetSerialisableTuple()
                
                del serialisable_simples[ 'media_collect' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 10, new_serialisable_info )
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        d = {}
        
        if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
            
            hdd_import = self._serialisables[ 'hdd_import' ]
            
            d[ 'hdd_import' ] = hdd_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
            
            simple_downloader_import = self._serialisables[ 'simple_downloader_import' ]
            
            d[ 'simple_downloader_import' ] = simple_downloader_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
            
            multiple_gallery_import = self._serialisables[ 'multiple_gallery_import' ]
            
            d[ 'multiple_gallery_import' ] = multiple_gallery_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
            
            multiple_watcher_import = self._serialisables[ 'multiple_watcher_import' ]
            
            d[ 'multiple_watcher_import' ] = multiple_watcher_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
            
            urls_import = self._serialisables[ 'urls_import' ]
            
            d[ 'urls_import' ] = urls_import.GetAPIInfoDict( simple )
            
        
        return d
        
    
    def GetKey( self, name ):
        
        return self._keys[ name ]
        
    
    def GetNumSeeds( self ):
        
        try:
            
            if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                hdd_import = self._serialisables[ 'hdd_import' ]
                
                return hdd_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                
                simple_downloader_import = self._serialisables[ 'simple_downloader_import' ]
                
                return simple_downloader_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
                
                multiple_gallery_import = self._serialisables[ 'multiple_gallery_import' ]
                
                return multiple_gallery_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
                
                multiple_watcher_import = self._serialisables[ 'multiple_watcher_import' ]
                
                return multiple_watcher_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
                
                urls_import = self._serialisables[ 'urls_import' ]
                
                return urls_import.GetNumSeeds()
                
            
        except KeyError:
            
            return 0
            
        
        return 0
        
    
    def GetPageName( self ):
        
        return self._page_name
        
    
    def GetType( self ):
        
        return self._management_type
        
    
    def GetValueRange( self ):
        
        try:
            
            if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                hdd_import = self._serialisables[ 'hdd_import' ]
                
                return hdd_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                
                simple_downloader_import = self._serialisables[ 'simple_downloader_import' ]
                
                return simple_downloader_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
                
                multiple_gallery_import = self._serialisables[ 'multiple_gallery_import' ]
                
                return multiple_gallery_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
                
                multiple_watcher_import = self._serialisables[ 'multiple_watcher_import' ]
                
                return multiple_watcher_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
                
                urls_import = self._serialisables[ 'urls_import' ]
                
                return urls_import.GetValueRange()
                
            
        except KeyError:
            
            return ( 0, 0 )
            
        
        return ( 0, 0 )
        
    
    def GetVariable( self, name ):
        
        if name in self._simples:
            
            return self._simples[ name ]
            
        else:
            
            return self._serialisables[ name ]
            
        
    
    def HasVariable( self, name ):
        
        return name in self._simples or name in self._serialisables
        
    
    def IsImporter( self ):
        
        return self._management_type in ( MANAGEMENT_TYPE_IMPORT_HDD, MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER, MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY, MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER, MANAGEMENT_TYPE_IMPORT_URLS )
        
    
    def SetKey( self, name, key ):
        
        self._keys[ name ] = key
        
    
    def SetPageName( self, name ):
        
        self._page_name = name
        
    
    def SetType( self, management_type ):
        
        self._management_type = management_type
        
        self._InitialiseDefaults()
        
    
    def SetVariable( self, name, value ):
        
        if isinstance( value, HydrusSerialisable.SerialisableBase ):
            
            self._serialisables[ name ] = value
            
        else:
            
            self._simples[ name ] = value
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER ] = ManagementController

def managementScrollbarValueChanged( value ):
    
    HG.client_controller.pub( 'top_level_window_move_event' )
    
class ManagementPanel( QW.QScrollArea ):
    
    SHOW_COLLECT = True
    TAG_DISPLAY_TYPE = ClientTags.TAG_DISPLAY_SELECTION_LIST
    
    def __init__( self, parent, page, controller, management_controller ):
        
        QW.QScrollArea.__init__( self, parent )
        
        self.setFrameShape( QW.QFrame.NoFrame )
        self.setWidget( QW.QWidget() )
        self.setWidgetResizable( True )
        #self.setFrameStyle( QW.QFrame.Panel | QW.QFrame.Sunken )
        #self.setLineWidth( 2 )
        #self.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarAlwaysOff )
        self.setVerticalScrollBarPolicy( QC.Qt.ScrollBarAsNeeded )
        
        self.verticalScrollBar().valueChanged.connect( managementScrollbarValueChanged )
        
        self._controller = controller
        self._management_controller = management_controller
        
        self._page = page
        self._page_key = self._management_controller.GetKey( 'page' )
        
        self._media_sort = ClientGUICommon.ChoiceSort( self, management_controller = self._management_controller )
        
        silent_collect = not self.SHOW_COLLECT
        
        self._media_collect = ClientGUICommon.CheckboxCollect( self, management_controller = self._management_controller, silent = silent_collect )
        
        if not self.SHOW_COLLECT:
            
            self._media_collect.hide()
            
        
    
    def GetMediaCollect( self ):
        
        if self.SHOW_COLLECT:
            
            return self._media_collect.GetValue()
            
        else:
            
            return ClientMedia.MediaCollect()
            
        
    
    def GetMediaSort( self ):
        
        return self._media_sort.GetSort()
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key, self.TAG_DISPLAY_TYPE )
        
        tags_box.SetTagsBox( t )
        
        QP.AddToLayout( sizer, tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def CheckAbleToClose( self ):
        
        pass
        
    
    def CleanBeforeClose( self ):
        
        pass
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def PageHidden( self ):
        
        pass
        
    
    def PageShown( self ):
        
        if self._controller.new_options.GetBoolean( 'set_search_focus_on_page_change' ):
            
            self.SetSearchFocus()
            
        
    
    def SetSearchFocus( self ):
        
        pass
        
    
    def SetSort( self, page_key, media_sort ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetVariable( 'media_sort', media_sort )
            
        
    
    def Start( self ):
        
        pass
        
    
    def REPEATINGPageUpdate( self ):
        
        pass
        
    
def WaitOnDupeFilterJob( job_key ):
    
    while not job_key.IsDone():
        
        if HydrusThreading.IsThreadShuttingDown():
            
            return
            
        
        time.sleep( 0.25 )
        
    
    time.sleep( 0.5 )
    
    HG.client_controller.pub( 'refresh_dupe_page_numbers' )
    
class ManagementPanelDuplicateFilter( ManagementPanel ):
    
    SHOW_COLLECT = False
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._job = None
        self._job_key = None
        self._in_break = False
        
        self._similar_files_maintenance_status = None
        
        new_options = self._controller.new_options
        
        self._maintenance_numbers_dirty = True
        self._dupe_count_numbers_dirty = True
        
        self._currently_refreshing_maintenance_numbers = False
        self._currently_refreshing_dupe_count_numbers = False
        
        #
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        self._main_left_panel = QW.QWidget( self._main_notebook )
        self._main_right_panel = QW.QWidget( self._main_notebook )
        
        #
        
        self._refresh_maintenance_status = ClientGUICommon.BetterStaticText( self._main_left_panel )
        self._refresh_maintenance_button = ClientGUICommon.BetterBitmapButton( self._main_left_panel, CC.GlobalPixmaps.refresh, self.RefreshMaintenanceNumbers )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'reset potential duplicates', 'This will delete all the potential duplicate pairs found so far and reset their files\' search status.', self._ResetUnknown ) )
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'maintain_similar_files_duplicate_pairs_during_idle' )
        
        menu_items.append( ( 'check', 'search for duplicate pairs at the current distance during normal db maintenance', 'Tell the client to find duplicate pairs in its normal db maintenance cycles, whether you have that set to idle or shutdown time.', check_manager ) )
        
        self._cog_button = ClientGUICommon.MenuBitmapButton( self._main_left_panel, CC.GlobalPixmaps.cog, menu_items )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'duplicates.html' ) )
        
        menu_items.append( ( 'normal', 'open the html duplicates help', 'Open the help page for duplicates processing in your web browser.', page_func ) )
        
        self._help_button = ClientGUICommon.MenuBitmapButton( self._main_left_panel, CC.GlobalPixmaps.help, menu_items )
        
        #
        
        self._searching_panel = ClientGUICommon.StaticBox( self._main_left_panel, 'finding potential duplicates' )
        
        self._eligible_files = ClientGUICommon.BetterStaticText( self._searching_panel )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'exact match', 'Search for exact matches.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_EXACT_MATCH ) ) )
        menu_items.append( ( 'normal', 'very similar', 'Search for very similar files.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_VERY_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'similar', 'Search for similar files.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'speculative', 'Search for files that are probably similar.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_SPECULATIVE ) ) )
        
        self._search_distance_button = ClientGUICommon.MenuButton( self._searching_panel, 'similarity', menu_items )
        
        self._search_distance_spinctrl = QP.MakeQSpinBox( self._searching_panel, min=0, max=64, width = 50 )
        self._search_distance_spinctrl.valueChanged.connect( self.EventSearchDistanceChanged )
        
        self._num_searched = ClientGUICommon.TextAndGauge( self._searching_panel )
        
        self._search_button = ClientGUICommon.BetterBitmapButton( self._searching_panel, CC.GlobalPixmaps.play, self._SearchForDuplicates )
        
        #
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        
        if new_options.GetBoolean( 'advanced_mode' ):
            
            menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'alternates\' (advanced!)', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
            
        
        self._edit_merge_options = ClientGUICommon.MenuButton( self._main_right_panel, 'edit default duplicate metadata merge options', menu_items )
        
        #
        
        self._filtering_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'duplicate filter' )
        
        file_search_context = management_controller.GetVariable( 'file_search_context' )
        
        predicates = file_search_context.GetPredicates()
        
        self._active_predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._filtering_panel, self._page_key, predicates )
        
        self._ac_read = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._filtering_panel, self._page_key, file_search_context, allow_all_known_files = False )
        
        self._both_files_match = QW.QCheckBox( self._filtering_panel )
        
        self._num_potential_duplicates = ClientGUICommon.BetterStaticText( self._filtering_panel )
        self._refresh_dupe_counts_button = ClientGUICommon.BetterBitmapButton( self._filtering_panel, CC.GlobalPixmaps.refresh, self.RefreshDuplicateNumbers )
        
        self._launch_filter = ClientGUICommon.BetterButton( self._filtering_panel, 'launch the filter', self._LaunchFilter )
        
        #
        
        random_filtering_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'quick and dirty processing' )
        
        self._show_some_dupes = ClientGUICommon.BetterButton( random_filtering_panel, 'show some random potential pairs', self._ShowRandomPotentialDupes )
        
        self._set_random_as_same_quality_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as duplicates of the same quality', self._SetCurrentMediaAs, HC.DUPLICATE_SAME_QUALITY )
        self._set_random_as_alternates_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as all related alternates', self._SetCurrentMediaAs, HC.DUPLICATE_ALTERNATE )
        self._set_random_as_false_positives_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as not related/false positive', self._SetCurrentMediaAs, HC.DUPLICATE_FALSE_POSITIVE )
        
        #
        
        self._main_notebook.addTab( self._main_left_panel, 'preparation' )
        self._main_notebook.addTab( self._main_right_panel, 'filtering' )
        self._main_notebook.setCurrentWidget( self._main_right_panel )
        
        #
        
        self._search_distance_spinctrl.setValue( new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' ) )
        
        self._both_files_match.setChecked( management_controller.GetVariable( 'both_files_match' ) )
        
        self._both_files_match.clicked.connect( self.EventBothFilesHitChanged )
        
        self._UpdateBothFilesMatchButton()
        
        #
        
        self._media_sort.hide()
        
        distance_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( distance_hbox, ClientGUICommon.BetterStaticText(self._searching_panel,label='search distance: '), CC.FLAGS_VCENTER )
        QP.AddToLayout( distance_hbox, self._search_distance_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( distance_hbox, self._search_distance_spinctrl, CC.FLAGS_VCENTER )
        
        gridbox_2 = QP.GridLayout( cols = 2 )
        
        gridbox_2.setColumnStretch( 0, 1 )
        
        QP.AddToLayout( gridbox_2, self._num_searched, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( gridbox_2, self._search_button, CC.FLAGS_VCENTER )
        
        self._searching_panel.Add( self._eligible_files, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._searching_panel.Add( distance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._searching_panel.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._refresh_maintenance_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( hbox, self._refresh_maintenance_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._cog_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._help_button, CC.FLAGS_VCENTER )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._searching_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, QW.QWidget( self._main_left_panel ), CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._main_left_panel.setLayout( vbox )
        
        #
        
        text_and_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( text_and_button_hbox, self._num_potential_duplicates, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( text_and_button_hbox, self._refresh_dupe_counts_button, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'both files of pair match in search: ', self._both_files_match ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._filtering_panel, rows )
        
        self._filtering_panel.Add( self._active_predicates_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._ac_read, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._filtering_panel.Add( text_and_button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._launch_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        random_filtering_panel.Add( self._show_some_dupes, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_same_quality_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_alternates_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_false_positives_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._edit_merge_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, random_filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, QW.QWidget( self._main_right_panel ), CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._main_right_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._main_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._controller.sub( self, 'RefreshAllNumbers', 'refresh_dupe_page_numbers' )
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        self._controller.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        
    
    def _EditMergeOptions( self, duplicate_type ):
        
        new_options = HG.client_controller.new_options
        
        duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg, duplicate_type, duplicate_action_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                duplicate_action_options = panel.GetValue()
                
                new_options.SetDuplicateActionOptions( duplicate_type, duplicate_action_options )
                
            
        
    
    def _GetFileSearchContextAndBothFilesMatch( self ):
        
        file_search_context = self._ac_read.GetFileSearchContext()
        
        predicates = self._active_predicates_box.GetPredicates()
        
        file_search_context.SetPredicates( predicates )
        
        both_files_match = self._both_files_match.isChecked()
        
        return ( file_search_context, both_files_match )
        
    
    def _LaunchFilter( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        canvas_frame = ClientGUICanvas.CanvasFrame( self.window() )
        
        canvas_window = ClientGUICanvas.CanvasFilterDuplicates( canvas_frame, file_search_context, both_files_match )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _RefreshDuplicateCounts( self ):
        
        def qt_code( potential_duplicates_count ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._currently_refreshing_dupe_count_numbers = False
            
            self._dupe_count_numbers_dirty = False
            
            self._refresh_dupe_counts_button.setEnabled( True )
            
            self._UpdatePotentialDuplicatesCount( potential_duplicates_count )
            
        
        def thread_do_it( file_search_context, both_files_match ):
            
            potential_duplicates_count = HG.client_controller.Read( 'potential_duplicates_count', file_search_context, both_files_match )
            
            QP.CallAfter( qt_code, potential_duplicates_count )
            
        
        if not self._currently_refreshing_dupe_count_numbers:
            
            self._currently_refreshing_dupe_count_numbers = True
            
            self._refresh_dupe_counts_button.setEnabled( False )
            
            self._num_potential_duplicates.setText( 'updating\u2026' )
            
            ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
            
            HG.client_controller.CallToThread( thread_do_it, file_search_context, both_files_match )
            
        
    
    def _RefreshMaintenanceNumbers( self ):
        
        def qt_code( similar_files_maintenance_status ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._currently_refreshing_maintenance_numbers = False
            
            self._maintenance_numbers_dirty = False
            
            self._refresh_maintenance_status.setText( '' )
            
            self._refresh_maintenance_button.setEnabled( True )
            
            self._similar_files_maintenance_status = similar_files_maintenance_status
            
            self._UpdateMaintenanceStatus()
            
        
        def thread_do_it():
            
            similar_files_maintenance_status = HG.client_controller.Read( 'similar_files_maintenance_status' )
            
            QP.CallAfter( qt_code, similar_files_maintenance_status )
            
        
        if not self._currently_refreshing_maintenance_numbers:
            
            self._currently_refreshing_maintenance_numbers = True
            
            self._refresh_maintenance_status.setText( 'updating\u2026' )
            
            self._refresh_maintenance_button.setEnabled( False )
            
            HG.client_controller.CallToThread( thread_do_it )
            
        
    
    def _ResetUnknown( self ):
        
        text = 'This will delete all the potential duplicate pairs and reset their files\' search status.'
        text += os.linesep * 2
        text += 'This can be useful if you have accidentally searched too broadly and are now swamped with too many false positives.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'delete_potential_duplicate_pairs' )
            
            self._maintenance_numbers_dirty = True
            
        
    
    def _SearchDomainUpdated( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        self._management_controller.SetVariable( 'file_search_context', file_search_context )
        self._management_controller.SetVariable( 'both_files_match', both_files_match )
        
        self._UpdateBothFilesMatchButton()
        
        if self._ac_read.IsSynchronised():
            
            self._dupe_count_numbers_dirty = True
            
        
    
    def _SearchForDuplicates( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'initialising' )
        
        search_distance = self._search_distance_spinctrl.value()
        
        self._controller.Write( 'maintain_similar_files_search_for_potential_duplicates', search_distance, job_key = job_key )
        
        self._controller.pub( 'modal_message', job_key )
        
        self._controller.CallLater( 1.0, WaitOnDupeFilterJob, job_key )
        
    
    def _SetCurrentMediaAs( self, duplicate_type ):
        
        media_panel = self._page.GetMediaPanel()
        
        change_made = media_panel.SetDuplicateStatusForAll( duplicate_type )
        
        if change_made:
            
            self._dupe_count_numbers_dirty = True
            
            self._ShowRandomPotentialDupes()
            
        
    
    def _SetSearchDistance( self, value ):
        
        self._search_distance_spinctrl.setValue( value )
        
        self._UpdateMaintenanceStatus()
        
    
    def _ShowRandomPotentialDupes( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        file_service_key = file_search_context.GetFileServiceKey()
        
        hashes = self._controller.Read( 'random_potential_duplicate_hashes', file_search_context, both_files_match )
        
        if len( hashes ) == 0:
            
            QW.QMessageBox.critical( self, 'Error', 'No files were found. Try refreshing the count, and if this keeps happening, please let hydrus_dev know.' )
            
            return
            
        
        media_results = self._controller.Read( 'media_results', hashes, sorted = True )
        
        if len( media_results ) == 0:
            
            QW.QMessageBox.information( self, 'Information', 'Files were found, but no media results could be loaded for them. Try refreshing the count, and if this keeps happening, please let hydrus_dev know.' )
            
            return
            
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
        
        self._page.SwapMediaPanel( panel )
        
    
    def _UpdateMaintenanceStatus( self ):
        
        work_can_be_done = False
        
        if self._similar_files_maintenance_status is None:
            
            return
            
        
        searched_distances_to_count = self._similar_files_maintenance_status
        
        self._cog_button.setEnabled( True )
        
        total_num_files = sum( searched_distances_to_count.values() )
        
        self._eligible_files.setText( '{} eligible files in the system.'.format(HydrusData.ToHumanInt(total_num_files)) )
        
        self._search_distance_button.setEnabled( True )
        self._search_distance_spinctrl.setEnabled( True )
        
        search_distance = self._search_distance_spinctrl.value()
        
        new_options = self._controller.new_options
        
        new_options.SetInteger( 'similar_files_duplicate_pairs_search_distance', search_distance )
        
        if search_distance in HC.hamming_string_lookup:
            
            button_label = HC.hamming_string_lookup[ search_distance ]
            
        else:
            
            button_label = 'custom'
            
        
        self._search_distance_button.setText( button_label )
        
        num_searched = sum( ( count for ( value, count ) in searched_distances_to_count.items() if value is not None and value >= search_distance ) )
        
        if num_searched == total_num_files:
            
            self._num_searched.SetValue( 'All potential duplicates found at this distance.', total_num_files, total_num_files )
            
            self._search_button.setEnabled( False )
            
        else:
            
            if num_searched == 0:
                
                self._num_searched.SetValue( 'Have not yet searched at this distance.', 0, total_num_files )
                
            else:
                
                self._num_searched.SetValue( 'Searched ' + HydrusData.ConvertValueRangeToPrettyString( num_searched, total_num_files ) + ' files at this distance.', num_searched, total_num_files )
                
            
            self._search_button.setEnabled( True )
            
            work_can_be_done = True
            
        
        if work_can_be_done:
            
            page_name = 'preparation (needs work)'
            
        else:
            
            page_name = 'preparation'
            
        
        self._main_notebook.setTabText( 0, page_name )
        
    
    def _UpdateBothFilesMatchButton( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        if file_search_context.IsJustSystemEverything() or file_search_context.HasNoPredicates():
            
            self._both_files_match.setEnabled( False )
            
        else:
            
            self._both_files_match.setEnabled( True )
            
        
    
    def _UpdatePotentialDuplicatesCount( self, potential_duplicates_count ):
        
        self._num_potential_duplicates.setText( HydrusData.ToHumanInt(potential_duplicates_count)+' potential pairs.' )
        
        if potential_duplicates_count > 0:
            
            self._show_some_dupes.setEnabled( True )
            self._launch_filter.setEnabled( True )
            
        else:
            
            self._show_some_dupes.setEnabled( False )
            self._launch_filter.setEnabled( False )
            
        
    
    def EventBothFilesHitChanged( self ):
        
        self._SearchDomainUpdated()
        
    
    def EventSearchDistanceChanged( self ):
        
        self._UpdateMaintenanceStatus()
        
    
    def RefreshAllNumbers( self ):
        
        self.RefreshDuplicateNumbers()
        
        self.RefreshMaintenanceNumbers()
        
    
    def RefreshDuplicateNumbers( self ):
        
        self._dupe_count_numbers_dirty = True
        
    
    def RefreshMaintenanceNumbers( self ):
        
        self._maintenance_numbers_dirty = True
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key:
            
            self._SearchDomainUpdated()
            
        
    
    def REPEATINGPageUpdate( self ):
        
        if self._maintenance_numbers_dirty:
            
            self._RefreshMaintenanceNumbers()
            
        
        if self._dupe_count_numbers_dirty:
            
            self._RefreshDuplicateCounts()
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._SearchDomainUpdated()
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_DUPLICATE_FILTER ] = ManagementPanelDuplicateFilter

class ManagementPanelImporter( ManagementPanel ):
    
    SHOW_COLLECT = False
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._controller.sub( self, 'RefreshSort', 'refresh_query' )
        
    
    def _UpdateImportStatus( self ):
        
        raise NotImplementedError()
        
    
    def PageHidden( self ):
        
        ManagementPanel.PageHidden( self )
        
    
    def PageShown( self ):
        
        ManagementPanel.PageShown( self )
        
        self._UpdateImportStatus()
        
    
    def RefreshSort( self, page_key ):
        
        if page_key == self._page_key:
            
            self._media_sort.BroadcastSort()
            
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateImportStatus()
        
    
class ManagementPanelImporterHDD( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'import summary' )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        
        self._pause_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.GlobalPixmaps.file_pause, self.Pause )
        self._pause_button.setToolTip( 'pause/play imports' )
        
        self._hdd_import = self._management_controller.GetVariable( 'hdd_import' )
        
        file_import_options = self._hdd_import.GetFileImportOptions()
        show_downloader_options = False
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._import_queue_panel, file_import_options, show_downloader_options, self._hdd_import.SetFileImportOptions )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._import_queue_panel.Add( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._pause_button, CC.FLAGS_LONE_BUTTON )
        self._import_queue_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        file_seed_cache = self._hdd_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        self._UpdateImportStatus()
        
    
    def _UpdateImportStatus( self ):
        
        ( current_action, paused ) = self._hdd_import.GetStatus()
        
        if paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalPixmaps.file_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalPixmaps.file_pause )
            
        
        if paused:
            
            if current_action == '':
                
                current_action = 'paused'
                
            else:
                
                current_action = 'pausing - ' + current_action
                
            
        
        self._current_action.setText( current_action )
        
    
    def CheckAbleToClose( self ):
        
        if self._hdd_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def Pause( self ):
        
        self._hdd_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def Start( self ):
        
        self._hdd_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_HDD ] = ManagementPanelImporterHDD

class ManagementPanelImporterMultipleGallery( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._last_time_imports_changed = 0
        self._next_update_time = 0
        
        self._multiple_gallery_import = self._management_controller.GetVariable( 'multiple_gallery_import' )
        
        self._highlighted_gallery_import = self._multiple_gallery_import.GetHighlightedGalleryImport()
        
        #
        
        self._gallery_downloader_panel = ClientGUICommon.StaticBox( self, 'gallery downloader' )
        
        #
        
        self._gallery_importers_status_st_top = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel, ellipsize_end = True )
        self._gallery_importers_status_st_bottom = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel, ellipsize_end = True )
        
        self._gallery_importers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._gallery_downloader_panel )
        
        columns = [ ( 'query', -1 ), ( 'source', 11 ), ( 'f', 3 ), ( 's', 3 ), ( 'status', 8 ), ( 'items', 9 ), ( 'added', 8 ) ]
        
        self._gallery_importers_listctrl = ClientGUIListCtrl.BetterListCtrl( self._gallery_importers_listctrl_panel, 'gallery_importers', 4, 8, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._RemoveGalleryImports, activation_callback = self._HighlightSelectedGalleryImport )
        
        self._gallery_importers_listctrl_panel.SetListCtrl( self._gallery_importers_listctrl )
        
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.highlight, self._HighlightSelectedGalleryImport, tooltip = 'highlight', enabled_check_func = self._CanHighlight )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.clear_highlight, self._ClearExistingHighlightAndPanel, tooltip = 'clear highlight', enabled_check_func = self._CanClearHighlight )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.file_pause, self._PausePlayFiles, tooltip = 'pause/play files', enabled_only_on_selection = True )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.gallery_pause, self._PausePlayGallery, tooltip = 'pause/play search', enabled_only_on_selection = True )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.trash, self._RemoveGalleryImports, tooltip = 'remove selected', enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl_panel.NewButtonRow()
        
        self._gallery_importers_listctrl_panel.AddButton( 'retry failed', self._RetryFailed, enabled_check_func = self._CanRetryFailed )
        self._gallery_importers_listctrl_panel.AddButton( 'retry ignored', self._RetryIgnored, enabled_check_func = self._CanRetryIgnored )
        
        self._gallery_importers_listctrl_panel.NewButtonRow()
        
        self._gallery_importers_listctrl_panel.AddButton( 'set options to queries', self._SetOptionsToGalleryImports, enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl.Sort( 0 )
        
        #
        
        self._query_input = ClientGUIControls.TextAndPasteCtrl( self._gallery_downloader_panel, self._PendQueries )
        
        self._cog_button = ClientGUICommon.BetterBitmapButton( self._gallery_downloader_panel, CC.GlobalPixmaps.cog, self._ShowCogMenu )
        
        self._gug_key_and_name = ClientGUIImport.GUGKeyAndNameSelector( self._gallery_downloader_panel, self._multiple_gallery_import.GetGUGKeyAndName(), update_callable = self._SetGUGKeyAndName )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._gallery_downloader_panel, 'stop after this many files', min = 1, none_phrase = 'no limit' )
        self._file_limit.valueChanged.connect( self.EventFileLimit )
        self._file_limit.setToolTip( 'per query, stop searching the gallery once this many files has been reached' )
        
        file_import_options = self._multiple_gallery_import.GetFileImportOptions()
        tag_import_options = self._multiple_gallery_import.GetTagImportOptions()
        file_limit = self._multiple_gallery_import.GetFileLimit()
        
        show_downloader_options = True
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._gallery_downloader_panel, file_import_options, show_downloader_options, self._multiple_gallery_import.SetFileImportOptions )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._gallery_downloader_panel, tag_import_options, show_downloader_options, update_callable = self._multiple_gallery_import.SetTagImportOptions, allow_default_selection = True )
        
        #
        
        input_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( input_hbox, self._query_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( input_hbox, self._cog_button, CC.FLAGS_VCENTER )
        
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._gallery_downloader_panel.Add( input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gug_key_and_name, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._highlighted_gallery_import_panel = ClientGUIImport.GalleryImportPanel( self, self._page_key, name = 'highlighted query' )
        
        self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._gallery_downloader_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._highlighted_gallery_import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        self._query_input.setPlaceholderText( initial_search_text )
        
        self._file_limit.SetValue( file_limit )
        
        self._UpdateImportStatus()
        
        self._gallery_importers_listctrl.AddMenuCallable( self._GetListCtrlMenu )
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_gallery_import is not None
        
    
    def _CanHighlight( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        gallery_import = selected[0]
        
        return gallery_import != self._highlighted_gallery_import
        
    
    def _CanRetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            if gallery_import.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _CanRetryIgnored( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            if gallery_import.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _ClearExistingHighlight( self ):
        
        if self._highlighted_gallery_import is not None:
            
            self._highlighted_gallery_import.PublishToPage( False )
            
            self._highlighted_gallery_import = None
            
            self._multiple_gallery_import.SetHighlightedGalleryImport( self._highlighted_gallery_import )
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._highlighted_gallery_import_panel.SetGalleryImport( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        if self._highlighted_gallery_import is None:
            
            return
            
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page.SwapMediaPanel( panel )
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToListCtrlTuples( self, gallery_import ):
        
        query_text = gallery_import.GetQueryText()
        
        pretty_query_text = query_text
        
        if gallery_import == self._highlighted_gallery_import:
            
            pretty_query_text = '* ' + pretty_query_text
            
        
        source = gallery_import.GetSourceName()
        
        pretty_source = source
        
        files_paused = gallery_import.FilesPaused()
        
        if files_paused:
            
            pretty_files_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_files_paused = ''
            
        
        gallery_finished = gallery_import.GalleryFinished()
        gallery_paused = gallery_import.GalleryPaused()
        
        if gallery_finished:
            
            pretty_gallery_paused = HG.client_controller.new_options.GetString( 'stop_character' )
            
        elif gallery_paused:
            
            pretty_gallery_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_gallery_paused = ''
            
        
        status = gallery_import.GetCurrentAction()
        
        if status == '':
            
            status = gallery_import.GetGalleryStatus()
            
        
        pretty_status = status
        
        ( file_seed_cache_status, file_seed_cache_simple_status, ( num_done, num_total ) ) = gallery_import.GetFileSeedCache().GetStatus()
        
        progress = ( num_total, num_done )
        
        pretty_progress = file_seed_cache_simple_status
        
        added = gallery_import.GetCreationTime()
        
        pretty_added = HydrusData.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        display_tuple = ( pretty_query_text, pretty_source, pretty_files_paused, pretty_gallery_paused, pretty_status, pretty_progress, pretty_added )
        sort_tuple = ( query_text, pretty_source, files_paused, gallery_paused, status, progress, added )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedQueries( self ):
        
        gallery_importers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_importers ) > 0:
            
            text = os.linesep.join( ( gallery_importer.GetQueryText() for gallery_importer in gallery_importers ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetListCtrlMenu( self ):
        
        selected_watchers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected_watchers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = QW.QMenu()

        ClientGUIMenus.AppendMenuItem( menu, 'copy queries', 'Copy all the selected downloaders\' queries to clipboard.', self._CopySelectedQueries )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'show all importers\' presented files', 'Gather the presented files for the selected importers and show them in a new page.', self._ShowSelectedImportersFiles, show='presented' )
        ClientGUIMenus.AppendMenuItem( menu, 'show all importers\' new files', 'Gather the presented files for the selected importers and show them in a new page.', self._ShowSelectedImportersFiles, show='new' )
        ClientGUIMenus.AppendMenuItem( menu, 'show all importers\' files', 'Gather the presented files for the selected importers and show them in a new page.', self._ShowSelectedImportersFiles, show='all' )
        ClientGUIMenus.AppendMenuItem( menu, 'show all importers\' files (including trash)', 'Gather the presented files (including trash) for the selected importers and show them in a new page.', self._ShowSelectedImportersFiles, show='all_and_trash' )
        
        if self._CanRetryFailed() or self._CanRetryIgnored():
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._CanRetryFailed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry failed', 'Retry all the failed downloads.', self._RetryFailed )
                
            
            if self._CanRetryIgnored():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry ignored', 'Retry all the failed downloads.', self._RetryIgnored )
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'remove', 'Remove the selected queries.', self._RemoveGalleryImports )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play files', 'Pause/play all the selected downloaders\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play search', 'Pause/play all the selected downloaders\' gallery searches.', self._PausePlayGallery )
        
        return menu
        
    
    def _HighlightGalleryImport( self, new_highlight ):
        
        if new_highlight == self._highlighted_gallery_import:
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._highlighted_gallery_import = new_highlight
            
            self._multiple_gallery_import.SetHighlightedGalleryImport( self._highlighted_gallery_import )
            
            hashes = self._highlighted_gallery_import.GetPresentedHashes()
            
            hashes = HG.client_controller.Read( 'filter_hashes', hashes, CC.LOCAL_FILE_SERVICE_KEY )
            
            media_results = HG.client_controller.Read( 'media_results', hashes )
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            sorted_media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, sorted_media_results )
            
            self._page.SwapMediaPanel( panel )
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._gallery_importers_listctrl.UpdateDatas()
            
            self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
            
        
    
    def _HighlightSelectedGalleryImport( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightGalleryImport( new_highlight )
            
        
    
    def _PausePlayFiles( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayFiles()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PausePlayGallery( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayGallery()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PendQueries( self, queries ):
        
        results = self._multiple_gallery_import.PendQueries( queries )
        
        if len( results ) > 0 and self._highlighted_gallery_import is None and HG.client_controller.new_options.GetBoolean( 'highlight_new_query' ):
            
            first_result = results[ 0 ]
            
            self._HighlightGalleryImport( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _RemoveGalleryImports( self ):
        
        removees = list( self._gallery_importers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        
        for gallery_import in removees:
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
        
        message = 'Remove the ' + HydrusData.ToHumanInt( len( removees ) ) + ' selected queries?'
        
        if num_working > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_working ) + ' are still working.'
            
        
        if self._highlighted_gallery_import is not None and self._highlighted_gallery_import in removees:
            
            message += os.linesep * 2
            message += 'The currently highlighted query will be removed, and the media panel cleared.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            highlight_was_included = False
            
            for gallery_import in removees:
                
                if self._highlighted_gallery_import is not None and gallery_import == self._highlighted_gallery_import:
                    
                    highlight_was_included = True
                    
                
                self._multiple_gallery_import.RemoveGalleryImport( gallery_import.GetGalleryImportKey() )
                
            
            if highlight_was_included:
                
                self._ClearExistingHighlightAndPanel()
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.RetryFailed()
            
        
    
    def _RetryIgnored( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.RetryIgnored()
            
        
    
    def _SetGUGKeyAndName( self, gug_key_and_name ):
        
        current_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        current_input_value = self._query_input.GetValue()
        
        should_initialise_new_text = current_input_value in ( current_initial_search_text, '' )
        
        self._multiple_gallery_import.SetGUGKeyAndName( gug_key_and_name )
        
        if should_initialise_new_text:
            
            new_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
            
            self._query_input.setPlaceholderText( new_initial_search_text )
            
        
    
    def _SetOptionsToGalleryImports( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        message = 'Set the current file limit, file import, and tag import options to all the selected queries? (by default, these options are only applied to new queries)'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            file_limit = self._file_limit.GetValue()
            file_import_options = self._file_import_options.GetValue()
            tag_import_options = self._tag_import_options.GetValue()
            
            for gallery_import in gallery_imports:
                
                gallery_import.SetFileLimit( file_limit )
                gallery_import.SetFileImportOptions( file_import_options )
                gallery_import.SetTagImportOptions( tag_import_options )
                
            
        
    
    def _ShowCogMenu( self ):
        
        menu = QW.QMenu()
        
        ( start_file_queues_paused, start_gallery_queues_paused, merge_simultaneous_pends_to_one_importer ) = self._multiple_gallery_import.GetQueueStartSettings()

        ClientGUIMenus.AppendMenuCheckItem( menu, 'start new importers\' files paused', 'Start any new importers in a file import-paused state.', start_file_queues_paused, self._multiple_gallery_import.SetQueueStartSettings, not start_file_queues_paused, start_gallery_queues_paused, merge_simultaneous_pends_to_one_importer )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'start new importers\' search paused', 'Start any new importers in a gallery search-paused state.', start_gallery_queues_paused, self._multiple_gallery_import.SetQueueStartSettings, start_file_queues_paused, not start_gallery_queues_paused, merge_simultaneous_pends_to_one_importer )
        ClientGUIMenus.AppendSeparator( menu )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'bundle multiple pasted queries into one importer (advanced)', 'If you are pasting many small queries at once (such as md5 lookups), check this to smooth out the workflow.', merge_simultaneous_pends_to_one_importer, self._multiple_gallery_import.SetQueueStartSettings, start_file_queues_paused, start_gallery_queues_paused, not merge_simultaneous_pends_to_one_importer )
        
        HG.client_controller.PopupMenu( self._cog_button, menu )
        
    
    def _ShowSelectedImportersFiles( self, show = 'presented' ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for gallery_import in gallery_imports:
            
            if show == 'presented':
                
                gallery_hashes = gallery_import.GetPresentedHashes()
                
            elif show == 'new':
                
                gallery_hashes = gallery_import.GetNewHashes()
                
            elif show in ( 'all', 'all_and_trash' ):
                
                gallery_hashes = gallery_import.GetHashes()
                
            
            new_hashes = [ hash for hash in gallery_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        if show == 'all_and_trash':
            
            filter_file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
            
        else:
            
            filter_file_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        
        hashes = HG.client_controller.Read( 'filter_hashes', hashes, filter_file_service_key )
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
            
            self._page.SwapMediaPanel( panel )
            
        else:
            
            QW.QMessageBox.critical( self, 'Error', 'No presented hashes for that selection!' )
            
        
    
    def _UpdateImportStatus( self ):
        
        if HydrusData.TimeHasPassed( self._next_update_time ):
            
            num_items = len( self._gallery_importers_listctrl.GetData() )
            
            update_period = max( 1, int( ( num_items / 10 ) ** 0.33 ) )
            
            self._next_update_time = HydrusData.GetNow() + update_period
            
            #
            
            last_time_imports_changed = self._multiple_gallery_import.GetLastTimeImportsChanged()
            
            num_gallery_imports = self._multiple_gallery_import.GetNumGalleryImports()
            
            #
            
            if num_gallery_imports == 0:
                
                text_top = 'waiting for new queries'
                text_bottom = ''
                
            else:
                
                ( status, simple_status, ( value, range ) ) = self._multiple_gallery_import.GetTotalStatus()
                
                text_top = HydrusData.ToHumanInt( num_gallery_imports ) + ' queries - ' + HydrusData.ConvertValueRangeToPrettyString( value, range )
                text_bottom = status
                
            
            self._gallery_importers_status_st_top.setText( text_top )
            self._gallery_importers_status_st_bottom.setText( text_bottom )
            
            #
            
            if self._last_time_imports_changed != last_time_imports_changed:
                
                self._last_time_imports_changed = last_time_imports_changed
                
                gallery_imports = self._multiple_gallery_import.GetGalleryImports()
                
                self._gallery_importers_listctrl.SetData( gallery_imports )
                
                ideal_rows = len( gallery_imports )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._gallery_importers_listctrl.GrowShrinkColumnsHeight( ideal_rows )
                
            else:
                
                sort_data_has_changed = self._gallery_importers_listctrl.UpdateDatas()
                
                if sort_data_has_changed:
                    
                    self._gallery_importers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self ):
        
        num_working = 0
        
        for gallery_import in self._multiple_gallery_import.GetGalleryImports():
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusData.ToHumanInt( num_working ) + ' queries are still importing.' )
            
        
    
    def EventFileLimit( self ):
        
        self._multiple_gallery_import.SetFileLimit( self._file_limit.GetValue() )
        
    
    def SetSearchFocus( self ):
        
        QP.CallAfter( self._query_input.setFocus, QC.Qt.OtherFocusReason)
        
    
    def Start( self ):
        
        self._multiple_gallery_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY ] = ManagementPanelImporterMultipleGallery

class ManagementPanelImporterMultipleWatcher( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._last_time_watchers_changed = 0
        self._next_update_time = 0
        
        self._multiple_watcher_import = self._management_controller.GetVariable( 'multiple_watcher_import' )
        
        self._highlighted_watcher = self._multiple_watcher_import.GetHighlightedWatcher()
        
        ( checker_options, file_import_options, tag_import_options ) = self._multiple_watcher_import.GetOptions()
        
        #
        
        self._watchers_panel = ClientGUICommon.StaticBox( self, 'watchers' )
        
        self._watchers_status_st_top = ClientGUICommon.BetterStaticText( self._watchers_panel, ellipsize_end = True )
        self._watchers_status_st_bottom = ClientGUICommon.BetterStaticText( self._watchers_panel, ellipsize_end = True )
        
        self._watchers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._watchers_panel )
        
        columns = [ ( 'subject', -1 ), ( 'f', 3 ), ( 'c', 3 ), ( 'status', 8 ), ( 'items', 9 ), ( 'added', 8 ) ]
        
        self._watchers_listctrl = ClientGUIListCtrl.BetterListCtrl( self._watchers_listctrl_panel, 'watchers', 4, 8, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._RemoveWatchers, activation_callback = self._HighlightSelectedWatcher )
        
        self._watchers_listctrl_panel.SetListCtrl( self._watchers_listctrl )
        
        self._watchers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.highlight, self._HighlightSelectedWatcher, tooltip = 'highlight', enabled_check_func = self._CanHighlight )
        self._watchers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.clear_highlight, self._ClearExistingHighlightAndPanel, tooltip = 'clear highlight', enabled_check_func = self._CanClearHighlight )
        self._watchers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.file_pause, self._PausePlayFiles, tooltip = 'pause/play files', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.gallery_pause, self._PausePlayChecking, tooltip = 'pause/play checking', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddBitmapButton( CC.GlobalPixmaps.trash, self._RemoveWatchers, tooltip = 'remove selected', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddButton( 'check now', self._CheckNow, enabled_only_on_selection = True )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'retry failed', self._RetryFailed, enabled_check_func = self._CanRetryFailed )
        self._watchers_listctrl_panel.AddButton( 'retry ignored', self._RetryIgnored, enabled_check_func = self._CanRetryIgnored )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'set options to watchers', self._SetOptionsToWatchers, enabled_only_on_selection = True )
        
        self._watchers_listctrl.Sort( 3 )
        
        self._watcher_url_input = ClientGUIControls.TextAndPasteCtrl( self._watchers_panel, self._AddURLs )
        
        self._watcher_url_input.setPlaceholderText( 'watcher url' )
        
        show_downloader_options = True
        
        self._checker_options = ClientGUIImport.CheckerOptionsButton( self._watchers_panel, checker_options, self._OptionsUpdated )
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._watchers_panel, file_import_options, show_downloader_options, self._OptionsUpdated )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._watchers_panel, tag_import_options, show_downloader_options, update_callable = self._OptionsUpdated, allow_default_selection = True )
        
        # suck up watchers from elsewhere in the program (presents a checklistboxdialog)
        
        #
        
        self._highlighted_watcher_panel = ClientGUIImport.WatcherReviewPanel( self, self._page_key, name = 'highlighted watcher' )
        
        self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
        
        #
        
        self._watchers_panel.Add( self._watchers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._watchers_panel.Add( self._watcher_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._watchers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._highlighted_watcher_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._watchers_listctrl.AddMenuCallable( self._GetListCtrlMenu )
        
        self._UpdateImportStatus()
        
        HG.client_controller.sub( self, '_ClearExistingHighlightAndPanel', 'clear_multiwatcher_highlights' )
        
    
    def _AddURLs( self, urls, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        first_result = None
        
        for url in urls:
            
            result = self._multiple_watcher_import.AddURL( url, service_keys_to_tags )
            
            if result is not None and first_result is None:
                
                first_result = result
                
            
        
        if first_result is not None and self._highlighted_watcher is None and HG.client_controller.new_options.GetBoolean( 'highlight_new_watcher' ):
            
            self._HighlightWatcher( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_watcher is not None
        
    
    def _CanHighlight( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        watcher = selected[0]
        
        return watcher != self._highlighted_watcher
        
    
    def _CanRetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            if watcher.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _CanRetryIgnored( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            if watcher.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _CheckNow( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.CheckNow()
            
        
    
    def _ClearExistingHighlight( self ):
        
        if self._highlighted_watcher is not None:
            
            self._highlighted_watcher.PublishToPage( False )
            
            self._highlighted_watcher = None
            
            self._multiple_watcher_import.SetHighlightedWatcher( self._highlighted_watcher )
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._highlighted_watcher_panel.SetWatcher( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        if self._highlighted_watcher is None:
            
            return
            
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page.SwapMediaPanel( panel )
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToListCtrlTuples( self, watcher ):
        
        subject = watcher.GetSubject()
        
        pretty_subject = subject
        
        if watcher == self._highlighted_watcher:
            
            pretty_subject = '* ' + pretty_subject
            
        
        files_paused = watcher.FilesPaused()
        
        if files_paused:
            
            pretty_files_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_files_paused = ''
            
        
        checking_dead = watcher.IsDead()
        checking_paused = watcher.CheckingPaused()
        
        if checking_dead:
            
            pretty_checking_paused = HG.client_controller.new_options.GetString( 'stop_character' )
            
        elif checking_paused:
            
            pretty_checking_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_checking_paused = ''
            
        
        ( status, simple_status, ( num_done, num_total ) ) = watcher.GetFileSeedCache().GetStatus()
        
        progress = ( num_total, num_done )
        
        pretty_progress = simple_status
        
        added = watcher.GetCreationTime()
        
        pretty_added = HydrusData.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        watcher_status = self._multiple_watcher_import.GetWatcherSimpleStatus( watcher )
        
        pretty_watcher_status = watcher_status
        
        if watcher_status == '':
            
            watcher_status = 'zzz' # to sort _after_ DEAD and other interesting statuses on ascending sort
            
        
        display_tuple = ( pretty_subject, pretty_files_paused, pretty_checking_paused, pretty_watcher_status, pretty_progress, pretty_added )
        sort_tuple = ( subject, files_paused, checking_paused, watcher_status, progress, added )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            text = os.linesep.join( ( watcher.GetURL() for watcher in watchers ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetListCtrlMenu( self ):
        
        selected_watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected_watchers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = QW.QMenu()

        ClientGUIMenus.AppendMenuItem( menu, 'copy urls', 'Copy all the selected watchers\' urls to clipboard.', self._CopySelectedURLs )
        ClientGUIMenus.AppendMenuItem( menu, 'open urls', 'Open all the selected watchers\' urls in your browser.', self._OpenSelectedURLs )
        
        ClientGUIMenus.AppendSeparator( menu )

        ClientGUIMenus.AppendMenuItem( menu, 'show all watchers\' presented files', 'Gather the presented files for the selected watchers and show them in a new page.', self._ShowSelectedImportersFiles, show='presented' )
        ClientGUIMenus.AppendMenuItem( menu, 'show all watchers\' new files', 'Gather the presented files for the selected watchers and show them in a new page.', self._ShowSelectedImportersFiles, show='new' )
        ClientGUIMenus.AppendMenuItem( menu, 'show all watchers\' files', 'Gather the presented files for the selected watchers and show them in a new page.', self._ShowSelectedImportersFiles, show='all' )
        ClientGUIMenus.AppendMenuItem( menu, 'show all watchers\' files (including trash)', 'Gather the presented files (including trash) for the selected watchers and show them in a new page.', self._ShowSelectedImportersFiles, show='all_and_trash' )
        
        if self._CanRetryFailed() or self._CanRetryIgnored():
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._CanRetryFailed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry failed', 'Retry all the failed downloads.', self._RetryFailed )
                
            
            if self._CanRetryIgnored():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry ignored', 'Retry all the ignored downloads.', self._RetryIgnored )
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'remove selected', 'Remove the selected watchers.', self._RemoveWatchers )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play files', 'Pause/play all the selected watchers\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play checking', 'Pause/play all the selected watchers\' checking routines.', self._PausePlayChecking )
        
        return menu
        
    
    def _HighlightWatcher( self, new_highlight ):
        
        if new_highlight == self._highlighted_watcher:
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._highlighted_watcher = new_highlight
            
            hashes = self._highlighted_watcher.GetPresentedHashes()
            
            hashes = HG.client_controller.Read( 'filter_hashes', hashes, CC.LOCAL_FILE_SERVICE_KEY )
            
            media_results = HG.client_controller.Read( 'media_results', hashes )
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            sorted_media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, sorted_media_results )
            
            self._page.SwapMediaPanel( panel )
            
            self._multiple_watcher_import.SetHighlightedWatcher( self._highlighted_watcher )
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._watchers_listctrl.UpdateDatas()
            
            self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
            
        
    
    def _HighlightSelectedWatcher( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightWatcher( new_highlight )
            
        
    
    def _OpenSelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            if len( watchers ) > 10:
                
                message = 'You have many watchers selected--are you sure you want to open them all?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.Accepted:
                    
                    return
                    
                
            
            for watcher in watchers:
                
                ClientPaths.LaunchURLInWebBrowser( watcher.GetURL() )
                
            
        
    
    def _OptionsUpdated( self, *args, **kwargs ):
        
        self._multiple_watcher_import.SetOptions( self._checker_options.GetValue(), self._file_import_options.GetValue(), self._tag_import_options.GetValue() )
        
    
    def _PausePlayChecking( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayChecking()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _PausePlayFiles( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayFiles()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _RemoveWatchers( self ):
        
        removees = list( self._watchers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        num_alive = 0
        
        for watcher in removees:
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
            if watcher.CurrentlyAlive():
                
                num_alive += 1
                
            
        
        message = 'Remove the ' + HydrusData.ToHumanInt( len( removees ) ) + ' selected watchers?'
        
        if num_working > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_working ) + ' are still working.'
            
        
        if num_alive > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_alive ) + ' are not yet DEAD.'
            
        
        if self._highlighted_watcher is not None and self._highlighted_watcher in removees:
            
            message += os.linesep * 2
            message += 'The currently highlighted watcher will be removed, and the media panel cleared.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            highlight_was_included = False
            
            for watcher in removees:
                
                if self._highlighted_watcher is not None and watcher == self._highlighted_watcher:
                    
                    highlight_was_included = True
                    
                
                self._multiple_watcher_import.RemoveWatcher( watcher.GetWatcherKey() )
                
            
            if highlight_was_included:
                
                self._ClearExistingHighlightAndPanel()
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.RetryFailed()
            
        
    
    def _RetryIgnored( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.RetryIgnored()
            
        
    
    def _SetOptionsToWatchers( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        message = 'Set the current checker, file import, and tag import options to all the selected watchers? (by default, these options are only applied to new watchers)'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            checker_options = self._checker_options.GetValue()
            file_import_options = self._file_import_options.GetValue()
            tag_import_options = self._tag_import_options.GetValue()
            
            for watcher in watchers:
                
                watcher.SetCheckerOptions( checker_options )
                watcher.SetFileImportOptions( file_import_options )
                watcher.SetTagImportOptions( tag_import_options )
                
            
        
    
    def _ShowSelectedImportersFiles( self, show = 'presented' ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for watcher in watchers:
            
            if show == 'presented':
                
                watcher_hashes = watcher.GetPresentedHashes()
                
            elif show == 'new':
                
                watcher_hashes = watcher.GetNewHashes()
                
            elif show in ( 'all', 'all_and_trash' ):
                
                watcher_hashes = watcher.GetHashes()
                
            
            new_hashes = [ hash for hash in watcher_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        if show == 'all_and_trash':
            
            filter_file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
            
        else:
            
            filter_file_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        
        hashes = HG.client_controller.Read( 'filter_hashes', hashes, filter_file_service_key )
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
            
            self._page.SwapMediaPanel( panel )
            
        else:
            
            QW.QMessageBox.critical( self, 'Error', 'No presented hashes for that selection!' )
            
        
    
    def _UpdateImportStatus( self ):
        
        if HydrusData.TimeHasPassed( self._next_update_time ):
            
            num_items = len( self._watchers_listctrl.GetData() )
            
            update_period = max( 1, int( ( num_items / 10 ) ** 0.33 ) )
            
            self._next_update_time = HydrusData.GetNow() + update_period
            
            #
            
            last_time_watchers_changed = self._multiple_watcher_import.GetLastTimeWatchersChanged()
            num_watchers = self._multiple_watcher_import.GetNumWatchers()
            
            #
            
            if num_watchers == 0:
                
                text_top = 'waiting for new watchers'
                text_bottom = ''
                
            else:
                
                num_dead = self._multiple_watcher_import.GetNumDead()
                
                if num_dead == 0:
                    
                    num_dead_text = ''
                    
                else:
                    
                    num_dead_text = HydrusData.ToHumanInt( num_dead ) + ' DEAD - '
                    
                
                ( status, simple_status, ( value, range ) ) = self._multiple_watcher_import.GetTotalStatus()
                
                text_top = HydrusData.ToHumanInt( num_watchers ) + ' watchers - ' + num_dead_text + HydrusData.ConvertValueRangeToPrettyString( value, range )
                text_bottom = status
                
            
            self._watchers_status_st_top.setText( text_top )
            self._watchers_status_st_bottom.setText( text_bottom )
            
            #
            
            if self._last_time_watchers_changed != last_time_watchers_changed:
                
                self._last_time_watchers_changed = last_time_watchers_changed
                
                watchers = self._multiple_watcher_import.GetWatchers()
                
                self._watchers_listctrl.SetData( watchers )
                
                ideal_rows = len( watchers )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._watchers_listctrl.GrowShrinkColumnsHeight( ideal_rows )
                
            else:
                
                sort_data_has_changed = self._watchers_listctrl.UpdateDatas()
                
                if sort_data_has_changed:
                    
                    self._watchers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self ):
        
        num_working = 0
        
        for watcher in self._multiple_watcher_import.GetWatchers():
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusData.ToHumanInt( num_working ) + ' watchers are still importing.' )
            
        
    
    def PendURL( self, url, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._AddURLs( ( url, ), service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        QP.CallAfter( self._watcher_url_input.setFocus, QC.Qt.OtherFocusReason)
        
    
    def Start( self ):
        
        self._multiple_watcher_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER ] = ManagementPanelImporterMultipleWatcher

class ManagementPanelImporterSimpleDownloader( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._simple_downloader_import = self._management_controller.GetVariable( 'simple_downloader_import' )
        
        #
        
        self._simple_downloader_panel = ClientGUICommon.StaticBox( self, 'simple downloader' )
        
        #
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'imports' )
        
        self._pause_files_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.GlobalPixmaps.file_pause, self.PauseFiles )
        self._pause_files_button.setToolTip( 'pause/play files' )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel, ellipsize_end = True )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        self._file_download_control = ClientGUIControls.NetworkJobControl( self._import_queue_panel )
        
        #
        
        #
        
        self._simple_parsing_jobs_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'simple parsing urls' )
        
        self._pause_queue_button = ClientGUICommon.BetterBitmapButton( self._simple_parsing_jobs_panel, CC.GlobalPixmaps.gallery_pause, self.PauseQueue )
        self._pause_queue_button.setToolTip( 'pause/play queue' )
        
        self._parser_status = ClientGUICommon.BetterStaticText( self._simple_parsing_jobs_panel, ellipsize_end = True )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._simple_parsing_jobs_panel, self._controller, True, False, self._page_key )
        
        self._page_download_control = ClientGUIControls.NetworkJobControl( self._simple_parsing_jobs_panel )
        
        self._pending_jobs_listbox = QW.QListWidget( self._simple_parsing_jobs_panel )
        
        self._advance_button = QW.QPushButton( '\u2191', self._simple_parsing_jobs_panel )
        self._advance_button.clicked.connect( self.EventAdvance )
        
        self._delete_button = QW.QPushButton( 'X', self._simple_parsing_jobs_panel )
        self._delete_button.clicked.connect( self.EventDelete )
        
        self._delay_button = QW.QPushButton( '\u2193', self._simple_parsing_jobs_panel )
        self._delay_button.clicked.connect( self.EventDelay )
        
        self._page_url_input = ClientGUIControls.TextAndPasteCtrl( self._simple_parsing_jobs_panel, self._PendPageURLs )
        
        self._page_url_input.setPlaceholderText( 'url to be parsed by the selected formula' )
        
        self._formulae = ClientGUICommon.BetterChoice( self._simple_parsing_jobs_panel )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit formulae', 'Edit these parsing formulae.', self._EditFormulae ) )
        
        self._formula_cog = ClientGUICommon.MenuBitmapButton( self._simple_parsing_jobs_panel, CC.GlobalPixmaps.cog, menu_items )
        
        self._RefreshFormulae()
        
        file_import_options = self._simple_downloader_import.GetFileImportOptions()
        
        show_downloader_options = True
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._simple_downloader_panel, file_import_options, show_downloader_options, self._simple_downloader_import.SetFileImportOptions )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._current_action, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( hbox, self._pause_files_button, CC.FLAGS_VCENTER )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        queue_buttons_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( queue_buttons_vbox, self._advance_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( queue_buttons_vbox, self._delete_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( queue_buttons_vbox, self._delay_button, CC.FLAGS_VCENTER )
        
        queue_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( queue_hbox, self._pending_jobs_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( queue_hbox, queue_buttons_vbox, CC.FLAGS_VCENTER )
        
        formulae_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( formulae_hbox, self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( formulae_hbox, self._formula_cog, CC.FLAGS_VCENTER )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._parser_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( hbox, self._pause_queue_button, CC.FLAGS_VCENTER )
        
        self._simple_parsing_jobs_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._page_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._simple_parsing_jobs_panel.Add( self._page_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._simple_downloader_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._simple_parsing_jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._simple_downloader_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._formulae.currentIndexChanged.connect( self.EventFormulaChanged )
        
        file_seed_cache = self._simple_downloader_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._simple_downloader_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
    
    def _EditFormulae( self ):
        
        def data_to_pretty_callable( data ):
            
            simple_downloader_formula = data
            
            return simple_downloader_formula.GetName()
            
        
        def edit_callable( data ):
            
            simple_downloader_formula = data
            
            name = simple_downloader_formula.GetName()
            
            with ClientGUIDialogs.DialogTextEntry( dlg, 'edit name', default = name ) as dlg_2:
                
                if dlg_2.exec() == QW.QDialog.Accepted:
                    
                    name = dlg_2.GetValue()
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( dlg, 'edit formula' ) as dlg_3:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_3 )
                
                formula = simple_downloader_formula.GetFormula()
                
                control = ClientGUIParsing.EditFormulaPanel( panel, formula, lambda: ( {}, '' ) )
                
                panel.SetControl( control )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.Accepted:
                    
                    formula = control.GetValue()
                    
                    simple_downloader_formula = ClientParsing.SimpleDownloaderParsingFormula( name = name, formula = formula )
                    
                    return simple_downloader_formula
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
        def add_callable():
            
            data = ClientParsing.SimpleDownloaderParsingFormula()
            
            return edit_callable( data )
            
        
        formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        formulae.sort( key = lambda o: o.GetName() )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit simple downloader formulae' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            height_num_chars = 20
            
            control = ClientGUIListBoxes.AddEditDeleteListBoxUniqueNamedObjects( panel, height_num_chars, data_to_pretty_callable, add_callable, edit_callable )
            
            control.AddSeparator()
            control.AddImportExportButtons( ( ClientParsing.SimpleDownloaderParsingFormula, ) )
            control.AddSeparator()
            control.AddDefaultsButton( ClientDefaults.GetDefaultSimpleDownloaderFormulae )
            
            control.AddDatas( formulae )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                formulae = control.GetData()
                
                self._controller.new_options.SetSimpleDownloaderFormulae( formulae )
                
            
        
        self._RefreshFormulae()
        
    
    def _PendPageURLs( self, urls ):
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        simple_downloader_formula = self._formulae.GetValue()
        
        for url in urls:
            
            job = ( url, simple_downloader_formula )
            
            self._simple_downloader_import.PendJob( job )
            
        
        self._UpdateImportStatus()
        
    
    def _RefreshFormulae( self ):
        
        self._formulae.clear()
        
        to_select = None
        
        select_name = self._simple_downloader_import.GetFormulaName()
        
        simple_downloader_formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        simple_downloader_formulae.sort( key = lambda o: o.GetName() )
        
        for ( i, simple_downloader_formula ) in enumerate( simple_downloader_formulae ):
            
            name = simple_downloader_formula.GetName()
            
            self._formulae.addItem( name, simple_downloader_formula )
            
            if name == select_name:
                
                to_select = i
                
            
        
        if to_select is not None:
            
            self._formulae.setCurrentIndex( to_select )
            
        
    
    def _UpdateImportStatus( self ):
        
        ( pending_jobs, parser_status, current_action, queue_paused, files_paused ) = self._simple_downloader_import.GetStatus()
        
        current_pending_jobs = [ QP.GetClientData( self._pending_jobs_listbox, i ) for i in range( self._pending_jobs_listbox.count() ) ]
        
        if current_pending_jobs != pending_jobs:
            
            selected_string = QP.ListWidgetGetStringSelection( self._pending_jobs_listbox )
            
            self._pending_jobs_listbox.clear()
            
            for job in pending_jobs:
                
                ( url, simple_downloader_formula ) = job
                
                pretty_job = simple_downloader_formula.GetName() + ': ' + url
                
                item = QW.QListWidgetItem()
                item.setText( pretty_job )
                item.setData( QC.Qt.UserRole, job )
                self._pending_jobs_listbox.addItem( item )
                
            
            selection_index = QP.ListWidgetIndexForString( self._pending_jobs_listbox, selected_string )
            
            if selection_index != -1:
                
                QP.ListWidgetSetSelection( self._pending_jobs_listbox, selection_index )
                
            
        
        if queue_paused:
            
            parser_status = 'paused'
            
        
        self._parser_status.setText( parser_status )
        
        if current_action == '' and files_paused:
            
            current_action = 'paused'
            
        
        self._current_action.setText( current_action )
        
        if files_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_files_button, CC.GlobalPixmaps.file_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_files_button, CC.GlobalPixmaps.file_pause )
            
        
        if queue_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_queue_button, CC.GlobalPixmaps.gallery_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_queue_button, CC.GlobalPixmaps.gallery_pause )
            
        
        ( file_network_job, page_network_job ) = self._simple_downloader_import.GetNetworkJobs()
        
        self._file_download_control.SetNetworkJob( file_network_job )
        
        self._page_download_control.SetNetworkJob( page_network_job )
        
    
    def CheckAbleToClose( self ):
        
        if self._simple_downloader_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def EventAdvance( self ):
        
        selection = QP.ListWidgetGetSelection( self._pending_jobs_listbox )
        
        if selection != -1:
            
            job = QP.GetClientData( self._pending_jobs_listbox, selection )
            
            self._simple_downloader_import.AdvanceJob( job )
            
            self._UpdateImportStatus()
            
        
    
    def EventDelay( self ):
        
        selection = QP.ListWidgetGetSelection( self._pending_jobs_listbox )
        
        if selection != -1:
            
            job = QP.GetClientData( self._pending_jobs_listbox, selection )
            
            self._simple_downloader_import.DelayJob( job )
            
            self._UpdateImportStatus()
            
        
    
    def EventDelete( self ):
        
        selection = QP.ListWidgetGetSelection( self._pending_jobs_listbox )
        
        if selection != -1:
            
            job = QP.GetClientData( self._pending_jobs_listbox, selection )
            
            self._simple_downloader_import.DeleteJob( job )
            
            self._UpdateImportStatus()
            
        
    
    def EventFormulaChanged( self ):
        
        formula = self._formulae.GetValue()
        
        formula_name = formula.GetName()
        
        self._simple_downloader_import.SetFormulaName( formula_name )
        self._controller.new_options.SetString( 'favourite_simple_downloader_formula', formula_name )
        
    
    def PauseQueue( self ):
        
        self._simple_downloader_import.PausePlayQueue()
        
        self._UpdateImportStatus()
        
    
    def PauseFiles( self ):
        
        self._simple_downloader_import.PausePlayFiles()
        
        self._UpdateImportStatus()
        
    
    def SetSearchFocus( self ):
        
        QP.CallAfter( self._page_url_input.setFocus, QC.Qt.OtherFocusReason)
        
    
    def Start( self ):
        
        self._simple_downloader_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER ] = ManagementPanelImporterSimpleDownloader

class ManagementPanelImporterURLs( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        #
        
        self._url_panel = ClientGUICommon.StaticBox( self, 'url downloader' )
        
        self._pause_button = ClientGUICommon.BetterBitmapButton( self._url_panel, CC.GlobalPixmaps.file_pause, self.Pause )
        self._pause_button.setToolTip( 'pause/play files' )
        
        self._file_download_control = ClientGUIControls.NetworkJobControl( self._url_panel )
        
        self._urls_import = self._management_controller.GetVariable( 'urls_import' )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._url_panel, self._controller, page_key = self._page_key )
        
        self._gallery_download_control = ClientGUIControls.NetworkJobControl( self._url_panel )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._url_panel, self._controller, False, False, page_key = self._page_key )
        
        self._url_input = ClientGUIControls.TextAndPasteCtrl( self._url_panel, self._PendURLs )
        
        self._url_input.setPlaceholderText( 'any url hydrus recognises, or a raw file url' )
        
        ( file_import_options, tag_import_options ) = self._urls_import.GetOptions()
        
        show_downloader_options = True
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._url_panel, file_import_options, show_downloader_options, self._urls_import.SetFileImportOptions )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._url_panel, tag_import_options, show_downloader_options, update_callable = self._urls_import.SetTagImportOptions, allow_default_selection = True )
        
        #
        
        self._url_panel.Add( self._pause_button, CC.FLAGS_LONE_BUTTON )
        self._url_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._gallery_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        file_seed_cache = self._urls_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._urls_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
    
    def _PendURLs( self, urls, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        self._urls_import.PendURLs( urls, service_keys_to_tags )
        
        self._UpdateImportStatus()
        
    
    def _UpdateImportStatus( self ):
        
        paused = self._urls_import.IsPaused()
        
        if paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalPixmaps.file_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalPixmaps.file_pause )
            
        
        ( file_network_job, gallery_network_job ) = self._urls_import.GetNetworkJobs()
        
        self._file_download_control.SetNetworkJob( file_network_job )
        
        self._gallery_download_control.SetNetworkJob( gallery_network_job )
        
    
    def CheckAbleToClose( self ):
        
        if self._urls_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def Pause( self ):
        
        self._urls_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def PendURL( self, url, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._PendURLs( ( url, ), service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        QP.CallAfter( self._url_input.setFocus, QC.Qt.OtherFocusReason)
        
    
    def Start( self ):
        
        self._urls_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_URLS ] = ManagementPanelImporterURLs

class ManagementPanelPetitions( ManagementPanel ):
    
    TAG_DISPLAY_TYPE = ClientTags.TAG_DISPLAY_STORAGE
    
    def __init__( self, parent, page, controller, management_controller ):
        
        self._petition_service_key = management_controller.GetKey( 'petition_service' )
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._service = self._controller.services_manager.GetService( self._petition_service_key )
        self._can_ban = self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
        
        service_type = self._service.GetServiceType()
        
        self._num_petition_info = None
        self._current_petition = None
        
        self._last_petition_type_fetched = None
        
        #
        
        self._petitions_info_panel = ClientGUICommon.StaticBox( self, 'petitions info' )
        
        self._refresh_num_petitions_button = ClientGUICommon.BetterButton( self._petitions_info_panel, 'refresh counts', self._FetchNumPetitions )
        
        self._petition_types_to_controls = {}
        
        content_type_hboxes = []
        
        petition_types = []
        
        if service_type == HC.FILE_REPOSITORY:
            
            petition_types.append( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_STATUS_PETITIONED ) )
            
        elif service_type == HC.TAG_REPOSITORY:
            
            petition_types.append( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED ) )
            
        
        for ( content_type, status ) in petition_types:
            
            func = HydrusData.Call( self._FetchPetition, content_type, status )
            
            st = ClientGUICommon.BetterStaticText( self._petitions_info_panel )
            button = ClientGUICommon.BetterButton( self._petitions_info_panel, 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petition', func )
            
            button.setEnabled( False )
            
            self._petition_types_to_controls[ ( content_type, status ) ] = ( st, button )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, st, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
            QP.AddToLayout( hbox, button, CC.FLAGS_VCENTER )
            
            content_type_hboxes.append( hbox )
            
        
        #
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'petition' )
        
        self._num_files_to_show = ClientGUICommon.NoneableSpinCtrl( self._petition_panel, message = 'number of files to show', min = 1 )
        
        self._num_files_to_show.SetValue( 256 )
        
        self._action_text = ClientGUICommon.BetterStaticText( self._petition_panel, label = '' )
        
        self._reason_text = QW.QTextEdit( self._petition_panel )
        self._reason_text.setReadOnly( True )
        self._reason_text.setMinimumHeight( 80 )
        
        check_all = ClientGUICommon.BetterButton( self._petition_panel, 'check all', self._CheckAll )
        flip_selected = ClientGUICommon.BetterButton( self._petition_panel, 'flip selected', self._FlipSelected )
        check_none = ClientGUICommon.BetterButton( self._petition_panel, 'check none', self._CheckNone )
        
        self._sort_by_left = ClientGUICommon.BetterButton( self._petition_panel, 'sort by left', self._SortBy, 'left' )
        self._sort_by_right = ClientGUICommon.BetterButton( self._petition_panel, 'sort by right', self._SortBy, 'right' )
        
        self._sort_by_left.setEnabled( False )
        self._sort_by_right.setEnabled( False )
        
        self._contents = QP.CheckListBox( self._petition_panel )
        self._contents.setSelectionMode( QW.QAbstractItemView.ExtendedSelection )
        self._contents.itemDoubleClicked.connect( self.EventContentDoubleClick )
        
        self._process = QW.QPushButton( 'process', self._petition_panel )
        self._process.clicked.connect( self.EventProcess )
        QP.SetForegroundColour( self._process, (0,128,0) )
        self._process.setEnabled( False )
        
        self._modify_petitioner = QW.QPushButton( 'modify petitioner', self._petition_panel )
        self._modify_petitioner.clicked.connect( self.EventModifyPetitioner )
        self._modify_petitioner.setEnabled( False )
        if not self._can_ban: self._modify_petitioner.setVisible( False )
        
        #
        
        self._petitions_info_panel.Add( self._refresh_num_petitions_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for hbox in content_type_hboxes:
            
            self._petitions_info_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        check_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( check_hbox, check_all, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( check_hbox, flip_selected, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( check_hbox, check_none, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        
        sort_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( sort_hbox, self._sort_by_left, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( sort_hbox, self._sort_by_right, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        
        self._petition_panel.Add( ClientGUICommon.BetterStaticText( self._petition_panel, label = 'Double-click a petition to see its files, if it has them.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._num_files_to_show, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._action_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._reason_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( check_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( sort_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( self._contents, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._petition_panel.Add( self._process, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._petitions_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._petition_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        self._contents.rightClicked.connect( self.EventRowRightClick )
        
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        
    
    def _CheckAll( self ):
        
        for i in range( self._contents.count() ):
            
            self._contents.Check( i )
            
        
    
    def _CheckNone( self ):
        
        for i in range( self._contents.count() ):
            
            self._contents.Check( i, False )
            
        
    
    def _DrawCurrentPetition( self ):
        
        if self._current_petition is None:
            
            self._action_text.setText( '' )
            self._reason_text.setPlainText( '' )
            QP.SetBackgroundColour( self._reason_text, QP.GetSystemColour( QG.QPalette.Window ) )
            self._contents.clear()
            self._process.setEnabled( False )
            
            self._sort_by_left.setEnabled( False )
            self._sort_by_right.setEnabled( False )
            
            if self._can_ban:
                
                self._modify_petitioner.setEnabled( False )
                
            
        else:
            
            ( action_text, action_colour ) = self._current_petition.GetActionTextAndColour()
            
            self._action_text.setText( action_text )
            QP.SetForegroundColour( self._action_text, action_colour )
            
            reason = self._current_petition.GetReason()
            
            self._reason_text.setPlainText( reason )
            
            QP.SetBackgroundColour( self._reason_text, action_colour )
            
            if self._last_petition_type_fetched[0] in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                self._sort_by_left.setEnabled( True )
                self._sort_by_right.setEnabled( True )
                
            else:
                
                self._sort_by_left.setEnabled( False )
                self._sort_by_right.setEnabled( False )
                
            
            contents = self._current_petition.GetContents()
            
            contents_and_checks = [ ( c, True ) for c in contents ]
            
            self._SetContentsAndChecks( contents_and_checks, 'right' )
            
            self._process.setEnabled( True )
            
            if self._can_ban:
                
                self._modify_petitioner.setEnabled( True )
                
            
        
        self._ShowHashes( [] )
        
    
    def _DrawNumPetitions( self ):
        
        for ( content_type, status, count ) in self._num_petition_info:
            
            petition_type = ( content_type, status )
            
            if petition_type in self._petition_types_to_controls:
                
                ( st, button ) = self._petition_types_to_controls[ petition_type ]
                
                st.setText( HydrusData.ToHumanInt(count)+' petitions' )
                
                if count > 0:
                    
                    button.setEnabled( True )
                    
                else:
                    
                    button.setEnabled( False )
                    
                
            
        
    
    def _FetchBestPetition( self ):
        
        top_petition_type_with_count = None
        
        for ( content_type, status, count ) in self._num_petition_info:
            
            if count == 0:
                
                continue
                
            
            petition_type = ( content_type, status )
            
            if top_petition_type_with_count is None:
                
                top_petition_type_with_count = petition_type
                
            
            if self._last_petition_type_fetched is not None and self._last_petition_type_fetched == petition_type:
                
                self._FetchPetition( content_type, status )
                
                return
                
            
        
        if top_petition_type_with_count is not None:
            
            ( content_type, status ) = top_petition_type_with_count
            
            self._FetchPetition( content_type, status )
            
        
    
    def _FetchNumPetitions( self ):
        
        def do_it( service ):
            
            def qt_draw( n_p_i ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._num_petition_info = n_p_i
                
                self._DrawNumPetitions()
                
                if self._current_petition is None:
                    
                    self._FetchBestPetition()
                    
                
            
            def qt_reset():
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._refresh_num_petitions_button.setText( 'refresh counts' )
                
            
            try:
                
                response = service.Request( HC.GET, 'num_petitions' )
                
                num_petition_info = response[ 'num_petitions' ]
                
                QP.CallAfter( qt_draw, num_petition_info )
                
            finally:
                
                QP.CallAfter( qt_reset )
                
            
        
        self._refresh_num_petitions_button.setText( 'Fetching\u2026' )
        
        self._controller.CallToThread( do_it, self._service )
        
    
    def _FetchPetition( self, content_type, status ):
        
        self._last_petition_type_fetched = ( content_type, status )
        
        ( st, button ) = self._petition_types_to_controls[ ( content_type, status ) ]
        
        def qt_setpet( petition ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._current_petition = petition
            
            self._DrawCurrentPetition()
            
        
        def qt_done():
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            button.setEnabled( True )
            button.setText( 'fetch '+HC.content_status_string_lookup[status]+' '+HC.content_type_string_lookup[content_type]+' petition' )
            
        
        def do_it( service ):
            
            try:
                
                response = service.Request( HC.GET, 'petition', { 'content_type' : content_type, 'status' : status } )
                
                QP.CallAfter( qt_setpet, response['petition'] )
                
            finally:
                
                QP.CallAfter( qt_done )
                
            
        
        if self._current_petition is not None:
            
            self._current_petition = None
            
            self._DrawCurrentPetition()
            
        
        button.setEnabled( False )
        button.setText( 'Fetching\u2026' )
        
        self._controller.CallToThread( do_it, self._service )
        
    
    def _FlipSelected( self ):
        
        for i in self._contents.GetSelections():
            
            flipped_state = not self._contents.IsChecked( i )
            
            self._contents.Check( i, flipped_state )
            
        
    
    def _GetContentsAndChecks( self ):
        
        contents_and_checks = []
        
        for i in range( self._contents.count() ):
            
            content = QP.GetClientData( self._contents, i )
            check = self._contents.IsChecked( i )
            
            contents_and_checks.append( ( content, check ) )
            
        
        return contents_and_checks
        
    
    def _SetContentsAndChecks( self, contents_and_checks, sort_type ):
        
        def key( c_and_s ):
            
            ( c, s ) = c_and_s
            
            if c.GetContentType() in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                ( left, right ) = c.GetContentData()
                
                if sort_type == 'left':
                    
                    ( part_one, part_two ) = ( HydrusTags.SplitTag( left ), HydrusTags.SplitTag( right ) )
                    
                elif sort_type == 'right':
                    
                    ( part_one, part_two ) = ( HydrusTags.SplitTag( right ), HydrusTags.SplitTag( left ) )
                    
                
            elif c.GetContentType() == HC.CONTENT_TYPE_MAPPINGS:
                
                ( tag, hashes ) = c.GetContentData()
                
                part_one = HydrusTags.SplitTag( tag )
                part_two = None
                
            else:
                
                part_one = None
                part_two = None
                
            
            return ( -c.GetVirtualWeight(), part_one, part_two )
            
        
        contents_and_checks.sort( key = key )
        
        self._contents.clear()
        
        to_check = []
        
        for ( i, ( content, check ) ) in enumerate( contents_and_checks ):
            
            content_string = content.ToString()
            
            self._contents.Append( content_string, content )
            
            if check:
                
                to_check.append( i )
                
            
        
        self._contents.SetCheckedItems( to_check )
        
    
    def _ShowHashes( self, hashes ):
        
        file_service_key = self._management_controller.GetKey( 'file_service' )
        
        with QP.BusyCursor():
            
            media_results = self._controller.Read( 'media_results', hashes )
            
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
        
        panel.Collect( self._page_key, self._media_collect.GetValue() )
        
        panel.Sort( self._page_key, self._media_sort.GetSort() )
        
        self._page.SwapMediaPanel( panel )
        
    
    def _SortBy( self, sort_type ):
        
        contents_and_checks = self._GetContentsAndChecks()
        
        self._SetContentsAndChecks( contents_and_checks, sort_type )
        
    
    def EventContentDoubleClick( self, item ):
        
        selections = self._contents.GetSelections()
        
        if len( selections ) > 0:
            
            selection = selections[0]
            
            content = QP.GetClientData( self._contents, selection )
            
            if content.HasHashes():
                
                hashes = content.GetHashes()
                
                num_files_to_show = self._num_files_to_show.GetValue()
                
                if num_files_to_show is not None and len( hashes ) > num_files_to_show:
                    
                    hashes = random.sample( hashes, num_files_to_show )
                    
                
                self._ShowHashes( hashes )
                
            
        
    
    def EventProcess( self ):
        
        def break_approved_contents_into_chunks( approved_contents ):
            
            chunks_of_approved_contents = []
            chunk_of_approved_contents = []
            
            weight = 0
            
            for content in approved_contents:
                
                for content_chunk in content.IterateUploadableChunks(): # break 20K-strong mappings petitions into smaller bits to POST back
                    
                    chunk_of_approved_contents.append( content_chunk )
                    
                    weight += content.GetVirtualWeight()
                    
                    if weight > 50:
                        
                        chunks_of_approved_contents.append( chunk_of_approved_contents )
                        
                        chunk_of_approved_contents = []
                        
                        weight = 0
                        
                    
                
            
            if len( chunk_of_approved_contents ) > 0:
                
                chunks_of_approved_contents.append( chunk_of_approved_contents )
                
            
            return chunks_of_approved_contents
            
        
        def do_it( controller, service, petition_service_key, approved_contents, denied_contents, petition ):
            
            try:
                
                num_done = 0
                num_to_do = len( approved_contents )
                
                if len( denied_contents ) > 0:
                    
                    num_to_do += 1
                    
                
                if num_to_do > 1:
                    
                    job_key = ClientThreading.JobKey( cancellable = True )
                    
                    job_key.SetVariable( 'popup_title', 'committing petitions' )
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                else:
                    
                    job_key = None
                    
                
                chunks_of_approved_contents = break_approved_contents_into_chunks( approved_contents )
                
                num_approved_to_do = len( chunks_of_approved_contents )
                
                for chunk_of_approved_contents in chunks_of_approved_contents:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        job_key.SetVariable( 'popup_gauge_1', ( num_done, num_approved_to_do ) )
                        
                    
                    ( update, content_updates ) = petition.GetApproval( chunk_of_approved_contents )
                    
                    service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                    controller.WriteSynchronous( 'content_updates', { petition_service_key : content_updates } )
                    
                    num_done += 1
                    
                
                if len( denied_contents ) > 0:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                    
                    update = petition.GetDenial( denied_contents )
                    
                    service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                
            finally:
                
                if job_key is not None:
                    
                    job_key.Delete()
                    
                
                def qt_fetch():
                    
                    if not self or not QP.isValid( self ):
                        
                        return
                        
                    
                    self._FetchNumPetitions()
                    
                
                QP.CallAfter( qt_fetch )
                
            
        
        approved_contents = []
        denied_contents = []
        
        for index in range( self._contents.count() ):
            
            content = QP.GetClientData( self._contents, index )
            
            if self._contents.IsChecked( index ):
                
                approved_contents.append( content )
                
            else:
                
                denied_contents.append( content )
                
            
        
        HG.client_controller.CallToThread( do_it, self._controller, self._service, self._petition_service_key, approved_contents, denied_contents, self._current_petition )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
    
    def EventModifyPetitioner( self ):
        
        QW.QMessageBox.warning( self, 'Warning', 'modify users does not work yet!' )
        
        with ClientGUIDialogs.DialogModifyAccounts( self, self._petition_service_key, ( self._current_petition.GetPetitionerAccount(), ) ) as dlg:
            
            dlg.exec()
            
        
    
    def EventRowRightClick( self ):
        
        selected_indices = self._contents.GetSelections()
        
        selected_contents = []
        
        for i in selected_indices:
            
            content = QP.GetClientData( self._contents, i )
            
            selected_contents.append( content )
            
        
        copyable_items_a = []
        copyable_items_b = []
        
        for content in selected_contents:
            
            content_type = content.GetContentType()
            
            if content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                ( tag, hashes ) = content.GetContentData()
                
                copyable_items_a.append( tag )
                
            elif content_type in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                ( tag_a, tag_b ) = content.GetContentData()
                
                copyable_items_a.append( tag_a )
                copyable_items_b.append( tag_b )
                
            
        
        copyable_items_a = HydrusData.DedupeList( copyable_items_a )
        copyable_items_b = HydrusData.DedupeList( copyable_items_b )
        
        if len( copyable_items_a ) + len( copyable_items_b ) > 0:
            
            menu = QW.QMenu()
            
            for copyable_items in [ copyable_items_a, copyable_items_b ]:
                
                if len( copyable_items ) > 0:
                    
                    if len( copyable_items ) == 1:
                        
                        tag = copyable_items[0]
                        
                        ClientGUIMenus.AppendMenuItem( menu, 'copy {}'.format( tag ), 'Copy this tag.', HG.client_controller.pub, 'clipboard', 'text', tag )
                        
                    else:
                        
                        text = os.linesep.join( copyable_items )
                        
                        ClientGUIMenus.AppendMenuItem( menu, 'copy {} tags'.format( HydrusData.ToHumanInt( len( copyable_items ) ) ), 'Copy this tag.', HG.client_controller.pub, 'clipboard', 'text', text )
                        
                    
                
            
            HG.client_controller.PopupMenu( self, menu )
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key:
            
            self._DrawCurrentPetition()
            
        
    
    def Start( self ):
        
        QP.CallAfter( self._FetchNumPetitions )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_PETITIONS ] = ManagementPanelPetitions

class ManagementPanelQuery( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        self._search_enabled = self._management_controller.GetVariable( 'search_enabled' )
        
        self._query_job_key = ClientThreading.JobKey( cancellable = True )
        
        self._query_job_key.Finish()
        
        initial_predicates = file_search_context.GetPredicates()
        
        if self._search_enabled:
            
            self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
            
            self._current_predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._search_panel, self._page_key, initial_predicates )
            
            synchronised = self._management_controller.GetVariable( 'synchronised' )
            
            self._searchbox = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, file_search_context, media_callable = self._page.GetMedia, synchronised = synchronised )
            
            self._cancel_search_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.GlobalPixmaps.stop, self._CancelSearch )
            
            self._cancel_search_button.hide()
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._searchbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._cancel_search_button, CC.FLAGS_VCENTER )
            
            self._search_panel.Add( self._current_predicates_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._search_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if self._search_enabled:
            
            QP.AddToLayout( vbox, self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        self._controller.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        self._controller.sub( self, 'ChangeFileServicePubsub', 'change_file_service' )
        
    
    def _CancelSearch( self ):
        
        self._query_job_key.Cancel()
        
        self._UpdateCancelButton()
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        if self._search_enabled:
            
            t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key, self.TAG_DISPLAY_TYPE, predicates_callable = self._current_predicates_box.GetPredicates )
            
            file_search_context = self._management_controller.GetVariable( 'file_search_context' )
            
            tag_service_key = file_search_context.GetTagServiceKey()
            
            t.ChangeTagService( tag_service_key )
            
        else:
            
            t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key, self.TAG_DISPLAY_TYPE )
            
        
        tags_box.SetTagsBox( t )
        
        QP.AddToLayout( sizer, tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _RefreshQuery( self ):
        
        self._controller.ResetIdleTimer()
        
        self._query_job_key.Cancel()
        
        if self._search_enabled:
            
            if self._management_controller.GetVariable( 'synchronised' ):
                
                file_search_context = self._searchbox.GetFileSearchContext()
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                file_search_context.SetPredicates( current_predicates )
                
                self._management_controller.SetVariable( 'file_search_context', file_search_context )
                
                file_service_key = file_search_context.GetFileServiceKey()
                
                if len( current_predicates ) > 0:
                    
                    self._query_job_key = ClientThreading.JobKey()
                    
                    sort_by = self._media_sort.GetSort()
                    
                    self._controller.CallToThread( self.THREADDoQuery, self._controller, self._page_key, self._query_job_key, file_search_context, sort_by )
                    
                    panel = ClientGUIResults.MediaPanelLoading( self._page, self._page_key, file_service_key )
                    
                else:
                    
                    panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, file_service_key, [] )
                    
                
                self._page.SwapMediaPanel( panel )
                
            
        else:
            
            self._media_sort.BroadcastSort()
            
        
    
    def _UpdateCancelButton( self ):
        
        if self._search_enabled:
            
            do_layout = False
            
            if self._query_job_key.IsDone():
                
                if self._cancel_search_button.isVisible():
                    
                    self._cancel_search_button.hide()
                    
                    do_layout = True
                    
                
            else:
                
                # don't show it immediately to save on flickeriness on short queries
                
                WAIT_PERIOD = 3.0
                
                can_show = HydrusData.TimeHasPassedFloat( self._query_job_key.GetCreationTime() + WAIT_PERIOD )
                
                if can_show and not self._cancel_search_button.isVisible():
                    
                    self._cancel_search_button.show()
                    
                    do_layout = True
                    
                
            
            if do_layout:
                
                self._searchbox.ForceSizeCalcNow()
                
            
        
    
    def ChangeFileServicePubsub( self, page_key, service_key ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetKey( 'file_service', service_key )
            
        
    
    def CleanBeforeClose( self ):
        
        ManagementPanel.CleanBeforeClose( self )
        
        if self._search_enabled:
            
            self._searchbox.CancelCurrentResultsFetchJob()
            
        
        self._query_job_key.Cancel()
        
    
    def CleanBeforeDestroy( self ):
        
        ManagementPanel.CleanBeforeDestroy( self )
        
        if self._search_enabled:
            
            self._searchbox.CancelCurrentResultsFetchJob()
            
        
        self._query_job_key.Cancel()
        
    
    def GetPredicates( self ):
        
        if self._search_enabled:
            
            return self._current_predicates_box.GetPredicates()
            
        else:
            
            return []
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key:
            
            self._RefreshQuery()
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetVariable( 'synchronised', value )
            
            self._RefreshQuery()
            
        
    
    def SetSearchFocus( self ):
        
        if self._search_enabled:
            
            QP.CallAfter( self._searchbox.setFocus, QC.Qt.OtherFocusReason)
            
        
    
    def ShowFinishedQuery( self, query_job_key, media_results ):
        
        if query_job_key == self._query_job_key:
            
            file_service_key = self._management_controller.GetKey( 'file_service' )
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
            
            panel.Collect( self._page_key, self._media_collect.GetValue() )
            
            panel.Sort( self._page_key, self._media_sort.GetSort() )
            
            self._page.SwapMediaPanel( panel )
            
        
    
    def Start( self ):
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        initial_predicates = file_search_context.GetPredicates()
        
        if len( initial_predicates ) > 0 and not file_search_context.IsComplete():
            
            QP.CallAfter( self._RefreshQuery )
            
        
    
    def THREADDoQuery( self, controller, page_key, query_job_key, search_context, sort_by ):
        
        def qt_code():
            
            query_job_key.Finish()
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self.ShowFinishedQuery( query_job_key, media_results )
            
        
        QUERY_CHUNK_SIZE = 256
        
        HG.client_controller.file_viewing_stats_manager.Flush()
        
        query_hash_ids = controller.Read( 'file_query_ids', search_context, job_key = query_job_key, limit_sort_by = sort_by )
        
        if query_job_key.IsCancelled():
            
            return
            
        
        media_results = []
        
        for sub_query_hash_ids in HydrusData.SplitListIntoChunks( query_hash_ids, QUERY_CHUNK_SIZE ):
            
            if query_job_key.IsCancelled():
                
                return
                
            
            more_media_results = controller.Read( 'media_results_from_ids', sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
            controller.pub( 'set_num_query_results', page_key, len( media_results ), len( query_hash_ids ) )
            
            controller.WaitUntilViewFree()
            
        
        search_context.SetComplete()
        
        QP.CallAfter( qt_code )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateCancelButton()
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_QUERY ] = ManagementPanelQuery
