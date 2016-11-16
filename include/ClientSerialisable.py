import ClientConstants as CC
import ClientImageHandling
import ClientParsing
import cv2
import HydrusConstants as HC
import HydrusData
import HydrusSerialisable
import numpy
import os
import struct
import wx

if cv2.__version__.startswith( '2' ):
    
    IMREAD_UNCHANGED = cv2.CV_LOAD_IMAGE_UNCHANGED
    
else:
    
    IMREAD_UNCHANGED = cv2.IMREAD_UNCHANGED
    

png_font = cv2.FONT_HERSHEY_TRIPLEX
greyscale_text_color = 0

title_size = 0.7
payload_type_size = 0.5
text_size = 0.4

def CreateTopImage( width, title, payload_type, text ):
    
    text_extent_bmp = wx.EmptyBitmap( 20, 20, 24 )
    
    dc = wx.MemoryDC( text_extent_bmp )
    
    text_font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
    
    basic_font_size = text_font.GetPointSize()
    
    payload_type_font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
    
    payload_type_font.SetPointSize( int( basic_font_size * 1.4 ) )
    
    title_font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
    
    title_font.SetPointSize( int( basic_font_size * 2.0 ) )
    
    dc.SetFont( text_font )
    ( gumpf, text_line_height ) = dc.GetTextExtent( 'abcdefghijklmnopqrstuvwxyz' )
    
    dc.SetFont( payload_type_font )
    ( gumpf, payload_type_line_height ) = dc.GetTextExtent( 'abcdefghijklmnopqrstuvwxyz' )
    
    dc.SetFont( title_font )
    ( gumpf, title_line_height ) = dc.GetTextExtent( 'abcdefghijklmnopqrstuvwxyz' )
    
    del dc
    del text_extent_bmp
    
    text_lines = WrapText( text, width, text_size, 1 )
    
    if len( text_lines ) == 0:
        
        text_total_height = 0
        
    else:
        
        text_total_height = ( text_line_height + 4 ) * len( text_lines )
        
        text_total_height += 6 # to bring the last 4 padding up to 10 padding
        
    
    top_height = 10 + title_line_height + 10 + payload_type_line_height + 10 + text_total_height
    
    #
    
    top_bmp = wx.EmptyBitmap( width, top_height, 24 )
    
    dc = wx.MemoryDC( top_bmp )
    
    dc.SetBackground( wx.Brush( wx.WHITE ) )
    
    dc.Clear()
    
    #
    
    dc.DrawBitmap( CC.GlobalBMPs.file_repository, width - 16 - 5, 5 )
    
    #
    
    current_y = 10
    
    dc.SetFont( title_font )
    
    ( t_width, t_height ) = dc.GetTextExtent( title )
    
    dc.DrawText( title, ( width - t_width ) / 2, current_y )
    
    current_y += t_height + 10
    
    dc.SetFont( payload_type_font )
    
    ( t_width, t_height ) = dc.GetTextExtent( payload_type )
    
    dc.DrawText( payload_type, ( width - t_width ) / 2, current_y )
    
    current_y += t_height + 10
    
    dc.SetFont( text_font )
    
    for text_line in text_lines:
        
        ( t_width, t_height ) = dc.GetTextExtent( text_line )
        
        dc.DrawText( text_line, ( width - t_width ) / 2, current_y )
        
        current_y += t_height + 4
        
    
    del dc
    
    data = top_bmp.ConvertToImage().GetData()
    
    top_image_rgb = numpy.fromstring( data, dtype = 'uint8' ).reshape( ( top_height, width, 3 ) )
    
    top_bmp.Destroy()
    
    top_image = cv2.cvtColor( top_image_rgb, cv2.COLOR_RGB2GRAY )
    
    top_height_header = struct.pack( '!H', top_height )
    
    ( byte0, byte1 ) = top_height_header
    
    top_image[0][0] = ord( byte0 )
    top_image[0][1] = ord( byte1 )
    
    return top_image
    
def DumpToPng( payload, title, payload_type, text, path ):
    
    payload_length = len( payload )
    
    payload_string_length = payload_length + 4
    
    square_width = int( float( payload_string_length ) ** 0.5 )
    
    width = max( 512, square_width )
    
    payload_height = int( float( payload_string_length ) / width )
    
    if float( payload_string_length ) / width % 1.0 > 0:
        
        payload_height += 1
        
    
    top_image = CreateTopImage( width, title, payload_type, text )
    
    payload_length_header = struct.pack( '!I', payload_length )
    
    num_empty_bytes = payload_height * width - payload_string_length
    
    full_payload_string = payload_length_header + payload + '\x00' * num_empty_bytes
    
    payload_image = numpy.fromstring( full_payload_string, dtype = 'uint8' ).reshape( ( payload_height, width ) )
    
    finished_image = numpy.concatenate( ( top_image, payload_image ) )
    
    cv2.imwrite( path, finished_image, [ cv2.IMWRITE_PNG_COMPRESSION, 9 ] )
    
def GetPayloadTypeAndString( payload_obj ):
    
    payload_string = payload_obj.DumpToNetworkString()
    
    if isinstance( payload_obj, ClientParsing.ParseRootFileLookup ):
        
        payload_obj_type_string = 'File Lookup Script'
        
    
    payload_type = payload_obj_type_string + ' - ' + HydrusData.ConvertIntToBytes( len( payload_string ) )
    
    return ( payload_type, payload_string )
    
def LoadFromPng( path ):
    
    try:
        
        numpy_image = cv2.imread( path, flags = IMREAD_UNCHANGED )
        
    except Exception as e:
        
        HydrusData.ShowException( e )
        
        raise Exception( 'That did not appear to be a valid image!' )
        
    
    try:
        
        ( height, width ) = numpy_image.shape
        
        complete_data = numpy_image.tostring()
        
        top_height_header = complete_data[:2]
        
        ( top_height, ) = struct.unpack( '!H', top_height_header )
        
        full_payload_string = complete_data[ width * top_height : ]
        
        payload_length_header = full_payload_string[:4]
        
        ( payload_length, ) = struct.unpack( '!I', payload_length_header )
        
        payload = full_payload_string[ 4 : 4 + payload_length ]
        
    except Exception as e:
        
        HydrusData.ShowException( e )
        
        raise Exception( 'The image was fine, but it did not seem to have hydrus data encoded in it!' )
        
    
    return payload
    
def TextExceedsWidth( text, width, size, thickness ):
    
    ( ( tw, th ), baseline ) = cv2.getTextSize( text, png_font, size, thickness )
    
    return tw > width
    
def WrapText( text, width, size, thickness ):
    
    words = text.split( ' ' )
    
    lines = []
    
    next_line = []
    
    for word in words:
        
        if word == '':
            
            continue
            
        
        potential_next_line = list( next_line )
        
        potential_next_line.append( word )
        
        if TextExceedsWidth( ' '.join( potential_next_line ), width, size, thickness ):
            
            if len( potential_next_line ) == 1: # one very long word
                
                lines.append( ' '.join( potential_next_line ) )
                
                next_line = []
                
            else:
                
                lines.append( ' '.join( next_line ) )
                
                next_line = [ word ]
                
            
        else:
            
            next_line = potential_next_line
            
        
    
    if len( next_line ) > 0:
        
        lines.append( ' '.join( next_line ) )
        
    
    return lines
    