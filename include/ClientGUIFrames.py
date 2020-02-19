import os

from qtpy import QtWidgets as QW

from . import ClientConstants as CC
from . import ClientGUICommon, ClientGUITopLevelWindows
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import QtPorting as QP


class ShowKeys( ClientGUITopLevelWindows.Frame ):
    
    def __init__( self, key_type, keys ):
        
        if key_type == 'registration': title = 'Registration Keys'
        elif key_type == 'access': title = 'Access Keys'
        
        # have to give it a parent so we won't get garbage collected, use the main gui
        ClientGUITopLevelWindows.Frame.__init__( self, HG.client_controller.gui, HG.client_controller.PrepStringForDisplay( title ) )
        
        self._key_type = key_type
        self._keys = keys
        
        #
        
        self._text_ctrl = QW.QPlainTextEdit( self )
        self._text_ctrl.setLineWrapMode( QW.QPlainTextEdit.NoWrap )
        self._text_ctrl.setReadOnly( True )
        
        self._save_to_file = QW.QPushButton( 'save to file', self )
        self._save_to_file.clicked.connect( self.EventSaveToFile )
        
        self._done = QW.QPushButton( 'done', self )
        self._done.clicked.connect( self.close )
        
        #
        
        if key_type == 'registration': prepend = 'r'
        else: prepend = ''
        
        self._text = os.linesep.join( [ prepend + key.hex() for key in self._keys ] )
        
        self._text_ctrl.setPlainText( self._text )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._text_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._save_to_file, CC.FLAGS_LONE_BUTTON )
        QP.AddToLayout( vbox, self._done, CC.FLAGS_LONE_BUTTON )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        size_hint.setWidth( max( size_hint.width(), 500 ) )
        size_hint.setHeight( max( size_hint.height(), 200 ) )
        
        QP.SetInitialSize( self, size_hint )
        
        self.show()
        
    
    def EventSaveToFile( self ):
        
        filename = 'keys.txt'
        
        with QP.FileDialog( self, acceptMode = QW.QFileDialog.AcceptSave, defaultFile = filename ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                with open( path, 'w', encoding = 'utf-8' ) as f:
                    
                    f.write( self._text )
