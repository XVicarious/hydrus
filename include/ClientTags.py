import collections
import threading

from . import ClientConstants as CC
from . import HydrusGlobals as HG
from . import HydrusSerialisable, HydrusTags


def ConvertTagSliceToString( tag_slice ):
    
    if tag_slice == '':
        
        return 'unnamespaced tags'
        
    elif tag_slice == ':':
        
        return 'namespaced tags'
        
    elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
        
        namespace = tag_slice[ : -1 ]
        
        return '\'' + namespace + '\' tags'
        
    else:
        
        return tag_slice
        
    
def RenderNamespaceForUser( namespace ):
    
    if namespace == '' or namespace is None:
        
        return 'unnamespaced'
        
    else:
        
        return namespace
        
    
def RenderTag( tag, render_for_user ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    if namespace == '':
        
        return subtag
        
    else:
        
        if render_for_user:
            
            new_options = HG.client_controller.new_options
            
            if new_options.GetBoolean( 'show_namespaces' ):
                
                connector = new_options.GetString( 'namespace_connector' )
                
            else:
                
                return subtag
                
            
        else:
            
            connector = ':'
            
        
        return namespace + connector + subtag
        
    
def SortTags( sort_by, tags_list, tags_to_count = None ):
    
    def lexicographic_key( tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        comparable_namespace = HydrusTags.ConvertTagToSortable( namespace )
        comparable_subtag = HydrusTags.ConvertTagToSortable( subtag )
        
        if namespace == '':
            
            return ( comparable_subtag, comparable_subtag )
            
        else:
            
            return ( comparable_namespace, comparable_subtag )
            
        
    
    def subtag_lexicographic_key( tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        comparable_subtag = HydrusTags.ConvertTagToSortable( subtag )
        
        return comparable_subtag
        
    
    def incidence_key( tag ):
        
        if tags_to_count is None:
            
            return 1
            
        else:
            
            return tags_to_count[ tag ]
            
        
    
    def namespace_key( tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if namespace == '':
            
            namespace = '{' # '{' is above 'z' in ascii, so this works for most situations
            
        
        return namespace
        
    
    def namespace_lexicographic_key( tag ):
        
        # '{' is above 'z' in ascii, so this works for most situations
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if namespace == '':
            
            return ( '{', HydrusTags.ConvertTagToSortable( subtag ) )
            
        else:
            
            return ( namespace, HydrusTags.ConvertTagToSortable( subtag ) )
            
        
    
    if sort_by in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
        
        # let's establish a-z here for equal incidence values later
        if sort_by in ( CC.SORT_BY_INCIDENCE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_ASC ):
            
            tags_list.sort( key = lexicographic_key, reverse = True )
            
            reverse = False
            
        elif sort_by in ( CC.SORT_BY_INCIDENCE_DESC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            tags_list.sort( key = lexicographic_key )
            
            reverse = True
            
        
        tags_list.sort( key = incidence_key, reverse = reverse )
        
        if sort_by in ( CC.SORT_BY_INCIDENCE_NAMESPACE_ASC, CC.SORT_BY_INCIDENCE_NAMESPACE_DESC ):
            
            # python list sort is stable, so lets now sort again
            
            if sort_by == CC.SORT_BY_INCIDENCE_NAMESPACE_ASC:
                
                reverse = True
                
            elif sort_by == CC.SORT_BY_INCIDENCE_NAMESPACE_DESC:
                
                reverse = False
                
            
            tags_list.sort( key = namespace_key, reverse = reverse )
            
        
    else:
        
        if sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_DESC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC, CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_DESC ):
            
            reverse = True
            
        elif sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_ASC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_ASC ):
            
            reverse = False
            
        
        if sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
            
            key = namespace_lexicographic_key
            
        elif sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_ASC, CC.SORT_BY_LEXICOGRAPHIC_DESC ):
            
            key = lexicographic_key
            
        elif sort_by in ( CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_DESC ):
            
            key = subtag_lexicographic_key
            
        
        tags_list.sort( key = key, reverse = reverse )
        
    
class ServiceKeysToTags( HydrusSerialisable.SerialisableBase, collections.defaultdict ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS
    SERIALISABLE_NAME = 'Service Keys To Tags'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        collections.defaultdict.__init__( self, set, *args, **kwargs )
        HydrusSerialisable.SerialisableBase.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        return [ ( service_key.hex(), list( tags ) ) for ( service_key, tags ) in self.items() ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( service_key_hex, tags_list ) in serialisable_info:
            
            self[ bytes.fromhex( service_key_hex ) ] = set( tags_list )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS ] = ServiceKeysToTags

TAG_DISPLAY_STORAGE = 0
TAG_DISPLAY_SIBLINGS_AND_PARENTS = 1
TAG_DISPLAY_SINGLE_MEDIA = 2
TAG_DISPLAY_SELECTION_LIST = 3

class TagDisplayManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER
    SERIALISABLE_NAME = 'Tag Display Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        service_keys_to_tag_filters_defaultdict = lambda: collections.defaultdict( TagFilter )
        
        self._tag_display_types_to_service_keys_to_tag_filters = collections.defaultdict( service_keys_to_tag_filters_defaultdict )
        
        self._lock = threading.Lock()
        self._dirty = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_tag_display_types_to_service_keys_to_tag_filters = []
        
        for ( tag_display_type, service_keys_to_tag_filters ) in self._tag_display_types_to_service_keys_to_tag_filters.items():
            
            serialisable_service_keys_to_tag_filters = [ ( service_key.hex(), tag_filter.GetSerialisableTuple() ) for ( service_key, tag_filter ) in service_keys_to_tag_filters.items() ]
            
            serialisable_tag_display_types_to_service_keys_to_tag_filters.append( ( tag_display_type, serialisable_service_keys_to_tag_filters ) )
            
        
        return serialisable_tag_display_types_to_service_keys_to_tag_filters
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( tag_display_type, serialisable_service_keys_to_tag_filters ) in serialisable_info:
            
            for ( serialisable_service_key, serialisable_tag_filter ) in serialisable_service_keys_to_tag_filters:
                
                service_key = bytes.fromhex( serialisable_service_key )
                tag_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter )
                
                self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ] = tag_filter
                
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetDirty( self ):
        
        with self._lock:
            
            self._dirty = True
            
        
    
    def FilterTags( self, tag_display_type, service_key, tags ):
        
        with self._lock:
            
            if service_key in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                tag_filter = self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ]
                
                tags = tag_filter.Filter( tags )
                
            
            if service_key != CC.COMBINED_TAG_SERVICE_KEY and CC.COMBINED_TAG_SERVICE_KEY in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                tag_filter = self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ CC.COMBINED_TAG_SERVICE_KEY ]
                
                tags = tag_filter.Filter( tags )
                
            
            return tags
            
        
    
    def FiltersTags( self, tag_display_type, service_key ):
        
        with self._lock:
            
            if service_key in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                return True
                
            
            if service_key != CC.COMBINED_TAG_SERVICE_KEY and CC.COMBINED_TAG_SERVICE_KEY in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                
                return True
                
            
            return False
            
        
    
    def GetTagFilter( self, tag_display_type, service_key ):
        
        with self._lock:
            
            return self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ].Duplicate()
            
        
    
    def HideTag( self, tag_display_type, service_key, tag ):
        
        with self._lock:
            
            tag_filter = self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ]
            
            tag_filter.SetRule( tag, CC.FILTER_BLACKLIST )
            
            self._dirty = True
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetTagFilter( self, tag_display_type, service_key, tag_filter ):
        
        with self._lock:
            
            if tag_filter.AllowsEverything():
                
                if service_key in self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ]:
                    
                    del self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ]
                    
                    self._dirty = True
                    
                
            else:
                
                self._tag_display_types_to_service_keys_to_tag_filters[ tag_display_type ][ service_key ] = tag_filter
                
                self._dirty = True
                
            
        
    
    def TagOK( self, tag_display_type, service_key, tag ):
        
        return len( self.FilterTags( tag_display_type, service_key, ( tag, ) ) ) > 0
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER ] = TagDisplayManager

class TagFilter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER
    SERIALISABLE_NAME = 'Tag Filter Rules'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._tag_slices_to_rules = {}
        
    
    def __eq__( self, other ):
        
        if isinstance( other, TagFilter ):
            
            return self._tag_slices_to_rules == other._tag_slices_to_rules
            
        
        return NotImplemented
        
    
    def _GetTagSlices( self, tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        tag_slices = []
        
        tag_slices.append( tag )
        
        if namespace != '':
            
            tag_slices.append( namespace + ':' )
            tag_slices.append( ':' )
            
        else:
            
            tag_slices.append( '' )
            
        
        return tag_slices
        
    
    def _GetSerialisableInfo( self ):
        
        return list( self._tag_slices_to_rules.items() )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._tag_slices_to_rules = dict( serialisable_info )
        
    
    def _TagOK( self, tag ):
        
        tag_slices = self._GetTagSlices( tag )
        
        blacklist_encountered = False
        
        for tag_slice in tag_slices:
            
            if tag_slice in self._tag_slices_to_rules:
                
                rule = self._tag_slices_to_rules[ tag_slice ]
                
                if rule == CC.FILTER_WHITELIST:
                    
                    return True # there is an exception for this class of tag
                    
                elif rule == CC.FILTER_BLACKLIST: # there is a rule against this class of tag
                    
                    blacklist_encountered = True
                    
                
            
        
        if blacklist_encountered: # rule against and no exceptions
            
            return False
            
        else:
            
            return True # no rules against or explicitly for, so permitted
            
        
    
    def AllowsEverything( self ):
        
        with self._lock:
            
            for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    return False
                    
                
            
            return True
            
        
    
    def Filter( self, tags ):
        
        with self._lock:
            
            return { tag for tag in tags if self._TagOK( tag ) }
            
        
    
    def GetTagSlicesToRules( self ):
        
        with self._lock:
            
            return dict( self._tag_slices_to_rules )
            
        
    
    def SetRule( self, tag_slice, rule ):
        
        with self._lock:
            
            self._tag_slices_to_rules[ tag_slice ] = rule
            
        
    
    def TagOK( self, tag ):
        
        with self._lock:
            
            return self._TagOK( tag )
            
        
    
    def ToBlacklistString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == CC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'no blacklist set'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    text = 'blacklisting on any tags'
                    
                else:
                    
                    text = 'blacklisting on ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                    
                
                if len( whitelist ) > 0:
                    
                    text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
                return text
                
            
        
    
    def ToCensoredString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in list(self._tag_slices_to_rules.items()):
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == CC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'all tags allowed'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    text = 'no tags allowed'
                    
                else:
                    
                    text = 'all but ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) ) + ' allowed'
                    
                
                if len( whitelist ) > 0:
                    
                    text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
                return text
                
            
        
    
    def ToPermittedString( self ):
        
        with self._lock:
            
            blacklist = []
            whitelist = []
            
            for ( tag_slice, rule ) in list(self._tag_slices_to_rules.items()):
                
                if rule == CC.FILTER_BLACKLIST:
                    
                    blacklist.append( tag_slice )
                    
                elif rule == CC.FILTER_WHITELIST:
                    
                    whitelist.append( tag_slice )
                    
                
            
            blacklist.sort()
            whitelist.sort()
            
            if len( blacklist ) == 0:
                
                return 'all tags'
                
            else:
                
                if set( blacklist ) == { '', ':' }:
                    
                    if len( whitelist ) == 0:
                        
                        text = 'no tags'
                        
                    else:
                        
                        text = 'only ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                elif set( blacklist ) == { '' }:
                    
                    text = 'all namespaced tags'
                    
                    if len( whitelist ) > 0:
                        
                        text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                elif set( blacklist ) == { ':' }:
                    
                    text = 'all unnamespaced tags'
                    
                    if len( whitelist ) > 0:
                        
                        text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                        
                    
                else:
                    
                    text = 'all tags except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                    
                    if len( whitelist ) > 0:
                        
                        text += ' (except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) ) + ')'
                        
                    
                
            
            return text
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER ] = TagFilter
