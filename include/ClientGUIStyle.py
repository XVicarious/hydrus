import os

from qtpy import QtWidgets as QW

from . import HydrusConstants as HC
from . import HydrusData, HydrusExceptions

STYLESHEET_DIR = os.path.join( HC.BASE_DIR, 'static', 'qss' )

ORIGINAL_STYLE_NAME = None
CURRENT_STYLE_NAME = None
ORIGINAL_STYLESHEET = None
CURRENT_STYLESHEET = None

def ClearStylesheet():
    
    SetStyleSheet( ORIGINAL_STYLESHEET )
    
def GetAvailableStyles():
    
    # so eventually expand this to do QStylePlugin or whatever we are doing to add more QStyles
    
    return list( QW.QStyleFactory.keys() )
    
def GetAvailableStylesheets():
    
    if not os.path.exists( STYLESHEET_DIR ) or not os.path.isdir( STYLESHEET_DIR ):
        
        raise HydrusExceptions.DataMissing( 'Stylesheet dir "{}" is missing or not a directory!'.format( STYLESHEET_DIR ) )
        
    
    stylesheet_filenames = []
    
    extensions = [ '.qss', '.css' ]
    
    for filename in os.listdir( STYLESHEET_DIR ):
        
        if True in ( filename.endswith( ext ) for ext in extensions ):
            
            stylesheet_filenames.append( filename )
            
        
    
    return stylesheet_filenames
    
def InitialiseDefaults():
    
    global ORIGINAL_STYLE_NAME
    global CURRENT_STYLE_NAME
    
    ORIGINAL_STYLE_NAME = QW.QApplication.instance().style().objectName()
    CURRENT_STYLE_NAME = ORIGINAL_STYLE_NAME
    
    global ORIGINAL_STYLESHEET
    global CURRENT_STYLESHEET
    
    ORIGINAL_STYLESHEET = QW.QApplication.instance().styleSheet()
    CURRENT_STYLESHEET = ORIGINAL_STYLESHEET
    
def SetStyleFromName( name ):
    
    global CURRENT_STYLE_NAME
    
    if name == CURRENT_STYLE_NAME:
        
        return
        
    
    if name in GetAvailableStyles():
        
        try:
            
            QW.QApplication.instance().setStyle( name )
            
            CURRENT_STYLE_NAME = name
            
        except Exception as e:
            
            raise HydrusExceptions.DataMissing( 'Style "{}" could not be generated/applied. If this is the default, perhaps a third-party custom style, you may have to restart the client to re-set it. Extra error info: {}'.format( name, e ) )
            
        
    else:
        
        raise HydrusExceptions.DataMissing( 'Style "{}" does not exist! If this is the default, perhaps a third-party custom style, you may have to restart the client to re-set it.'.format( name ) )
        
    
def SetStyleSheet( stylesheet ):
    
    global CURRENT_STYLESHEET
    
    if CURRENT_STYLESHEET != stylesheet:
        
        QW.QApplication.instance().setStyleSheet( stylesheet )
        
        CURRENT_STYLESHEET = stylesheet
        
    
def SetStylesheetFromPath( filename ):
    
    path = os.path.join( STYLESHEET_DIR, filename )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.DataMissing( 'Stylesheet "{}" does not exist!'.format( path ) )
        
    
    with open( path, 'r', encoding = 'utf-8' ) as f:
        
        qss = f.read()
        
    
    SetStyleSheet( qss )
