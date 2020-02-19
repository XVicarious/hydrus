import collections
import os
import random
import time
import unittest

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from . import ClientConstants as CC
from . import ClientDefaults, ClientGUIListBoxes
from . import HydrusConstants as HC
from . import HydrusGlobals as HG
from . import QtPorting as QP
from . import TestController


def DoClick( click, panel, do_delayed_ok_afterwards = False ):
    
    QW.QApplication.postEvent( panel.widget(), click )
    
    if do_delayed_ok_afterwards:
        
        HG.test_controller.CallLaterQtSafe( panel, 1, PressKeyOnFocusedWindow, QC.Qt.Key_Return )
        
    
    QW.QApplication.processEvents()
    
def GenerateClick( window, pos, click_type, click_button, modifier ):
    
    screen_pos = QC.QPointF( window.mapToGlobal( pos.toPoint() ) )
    
    click = QG.QMouseEvent( click_type, pos, screen_pos, click_button, click_button, modifier )
    
    return click
    
def GetAllClickableIndices( panel ):
    
    current_y = 5
    
    click = GenerateClick( panel, QC.QPointF( 10, current_y ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.NoModifier )
    
    all_clickable_indices = {}
    
    while panel._GetIndexUnderMouse( click ) is not None:
        
        index = panel._GetIndexUnderMouse( click )
        
        if index not in all_clickable_indices:
            
            all_clickable_indices[ index ] = current_y
            
        
        current_y += 5
        
        click = GenerateClick( panel, QC.QPointF( 10, current_y ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.NoModifier )
        
    
    return all_clickable_indices
    
def PressKey( window, key ):
    
    window.setFocus( QC.Qt.OtherFocusReason )
    
    uias = QP.UIActionSimulator()
    
    uias.Char( key )
    
def PressKeyOnFocusedWindow( key ):
    
    uias = QP.UIActionSimulator()
    
    uias.Char( key )
    
class TestListBoxes( unittest.TestCase ):
    
    def test_listbox_colour_options( self ):
        
        def qt_code():
            
            frame = TestController.TestFrame()
            
            try:
                
                initial_namespace_colours = { 'series' : ( 153, 101, 21 ), '' : ( 0, 111, 250 ), None : ( 114, 160, 193 ), 'creator' : ( 170, 0, 0 ) }
                
                panel = ClientGUIListBoxes.ListBoxTagsColourOptions( frame, initial_namespace_colours )
                
                frame.SetPanel( panel )
                
                self.assertEqual( panel.GetNamespaceColours(), initial_namespace_colours )
                
                #
                
                new_namespace_colours = dict( initial_namespace_colours )
                new_namespace_colours[ 'character' ] = ( 0, 170, 0 )
                
                colour = QG.QColor( 0, 170, 0 )
                
                panel.SetNamespaceColour( 'character', colour )
                
                self.assertEqual( panel.GetNamespaceColours(), new_namespace_colours )
                
                #
                
                terms = set( panel._terms )
                ordered_terms = list( panel._ordered_terms )
                
                self.assertEqual( len( terms ), len( ordered_terms ) )
                
                #
                
                all_clickable_indices = GetAllClickableIndices( panel )
                
                self.assertEqual( len( list(all_clickable_indices.keys()) ), len( terms ) )
                self.assertEqual( set( all_clickable_indices.keys() ), set( range( len( list(all_clickable_indices.keys()) ) ) ) )
                
                #
                
                for ( index, y ) in list( all_clickable_indices.items() ):
                    
                    click = GenerateClick( panel, QC.QPointF( 10, y ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.NoModifier )
                    
                    DoClick( click, panel )
                    
                    self.assertEqual( panel.GetSelectedNamespaceColours(), dict( [ ordered_terms[ index ] ] ) )
                    
                
                #
                
                current_y = 5
                
                click = QG.QMouseEvent( QC.QEvent.MouseButtonPress, QC.QPointF( 10, current_y ), QC.Qt.LeftButton, QC.Qt.LeftButton, QC.Qt.NoModifier )
                
                while panel._GetIndexUnderMouse( click ) is not None:
                    
                    current_y += 5
                    
                    click = GenerateClick( panel, QC.QPointF( 10, current_y ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.NoModifier )
                    
                
                DoClick( click, panel )
                
                self.assertEqual( panel.GetSelectedNamespaceColours(), {} )
                
                #
                
                
                
                if len( list(all_clickable_indices.keys()) ) > 2:
                    
                    indices = random.sample( list(all_clickable_indices.keys()), len( list(all_clickable_indices.keys()) ) - 1 )
                    
                    for index in indices:
                        
                        click = GenerateClick( panel, QC.QPointF( 10, all_clickable_indices[ index ] ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.ControlModifier )
                        
                        DoClick( click, panel )
                        
                    
                    expected_selected_terms = [ ordered_terms[ index ] for index in indices ]
                    
                    self.assertEqual( panel.GetSelectedNamespaceColours(), dict( expected_selected_terms ) )
                    
                
                #
                
                random_index = random.choice( list(all_clickable_indices.keys()) )
                
                while ordered_terms[ random_index ][0] in panel.PROTECTED_TERMS:
                    
                    random_index = random.choice( list(all_clickable_indices.keys()) )
                    
                
                del new_namespace_colours[ ordered_terms[ random_index ][0] ]
                
                # select nothing
                
                current_y = 5
                
                click = GenerateClick( panel, QC.QPointF( 10, current_y ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.NoModifier )
                
                while panel._GetIndexUnderMouse( click ) is not None:
                    
                    current_y += 5
                    
                    click = GenerateClick( panel, QC.QPointF( 10, current_y ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.NoModifier )
                    
                
                DoClick( click, panel )
                
                # select the random index
                
                click = GenerateClick( panel, QC.QPointF( 10, all_clickable_indices[ random_index ] ), QC.QEvent.MouseButtonPress, QC.Qt.LeftButton, QC.Qt.NoModifier )
                
                DoClick( click, panel )
                
            finally:
                
                frame.deleteLater()
                
            
        
        HG.test_controller.CallBlockingToQt( HG.test_controller.win, qt_code )
