#!/usr/bin/env python3
"""
Platform-specific styling for DCST Tool GUI.
Handles cross-platform appearance issues, especially for macOS.
"""

import platform
import tkinter as tk
from tkinter import ttk
import subprocess
import sys

class PlatformStyles:
    """
    Platform-specific styling configuration for GUI elements.
    Addresses platform-specific rendering issues and provides consistent appearance.
    """
    
    def __init__(self):
        self.platform = platform.system()
        self.is_macos = self.platform == "Darwin"
        self.is_windows = self.platform == "Windows"
        self.is_linux = self.platform == "Linux"
        
        # Configure platform-specific styles
        self._configure_styles()

    def _detect_macos_dark_mode(self):
        """Detect if macOS is in dark mode."""
        if not self.is_macos:
            return False

        try:
            # Use AppleScript to detect dark mode
            result = subprocess.run([
                'osascript', '-e',
                'tell application "System Events" to tell appearance preferences to get dark mode'
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                return result.stdout.strip().lower() == 'true'
        except Exception:
            pass

        # Fallback: try to detect through system preferences
        try:
            result = subprocess.run([
                'defaults', 'read', '-g', 'AppleInterfaceStyle'
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                return result.stdout.strip().lower() == 'dark'
        except Exception:
            pass

        # Default to light mode if detection fails
        return False
    
    def _configure_styles(self):
        """Configure platform-specific color schemes and styles."""
        if self.is_macos:
            # Detect macOS dark mode
            self.is_dark_mode = self._detect_macos_dark_mode()

            if self.is_dark_mode:
                # macOS Dark Mode styling
                self.colors = {
                    'bg_primary': '#1e1e1e',        # Dark background
                    'bg_secondary': '#2d2d2d',      # Slightly lighter dark
                    'bg_accent': '#3a3a3a',         # Accent background
                    'text_primary': '#ffffff',      # White text
                    'text_secondary': '#b3b3b3',    # Light gray text
                    'text_accent': '#0a84ff',       # Apple blue (dark mode)
                    'button_bg': '#0a84ff',         # Apple blue buttons
                    'button_fg': '#ffffff',         # White button text
                    'button_hover': '#0056b3',      # Darker blue on hover
                    'entry_bg': '#2d2d2d',          # Dark entry fields
                    'entry_fg': '#ffffff',          # White entry text
                    'success_color': '#30d158',     # Apple green (dark mode)
                    'warning_color': '#ff9f0a',     # Apple orange (dark mode)
                    'error_color': '#ff453a',       # Apple red (dark mode)
                    'border_color': '#545454',      # Dark border
                    'canvas_bg': '#1e1e1e',         # Dark canvas background
                    'scrollbar_bg': '#2d2d2d',      # Dark scrollbar
                }
            else:
                # macOS Light Mode styling
                self.colors = {
                    'bg_primary': '#ffffff',        # White background
                    'bg_secondary': '#f5f5f5',      # Light gray
                    'bg_accent': '#e5e5e5',         # Accent background
                    'text_primary': '#000000',      # Black text
                    'text_secondary': '#666666',    # Medium gray text
                    'text_accent': '#007aff',       # Apple blue
                    'button_bg': '#007aff',         # Apple blue buttons
                    'button_fg': '#ffffff',         # White button text
                    'button_hover': '#0056cc',      # Darker blue on hover
                    'entry_bg': '#ffffff',          # White entry fields
                    'entry_fg': '#000000',          # Black entry text
                    'success_color': '#34c759',     # Apple green
                    'warning_color': '#ff9500',     # Apple orange
                    'error_color': '#ff3b30',       # Apple red
                    'border_color': '#d1d1d6',      # Light border
                    'canvas_bg': '#ffffff',         # White canvas background
                    'scrollbar_bg': '#f5f5f5',      # Light scrollbar
                }

            # macOS button styling - improved for both light and dark modes
            if self.is_dark_mode:
                self.button_style = {
                    'relief': 'flat',
                    'borderwidth': 0,
                    'highlightthickness': 0,
                    'font': ('SF Pro Display', 13),
                    'cursor': 'pointinghand',
                    'padx': 16,
                    'pady': 8,
                    'bd': 0,
                }
            else:
                self.button_style = {
                    'relief': 'flat',
                    'borderwidth': 1,
                    'highlightthickness': 0,
                    'font': ('SF Pro Display', 13),
                    'cursor': 'pointinghand',
                    'padx': 16,
                    'pady': 8,
                    'bd': 1,
                }

            # macOS entry styling - improved for both light and dark modes
            if self.is_dark_mode:
                self.entry_style = {
                    'relief': 'solid',
                    'borderwidth': 1,
                    'highlightthickness': 1,
                    'font': ('SF Pro Display', 13),
                    'insertbackground': '#ffffff',
                    'selectbackground': '#0a84ff',
                    'selectforeground': '#ffffff',
                }
            else:
                self.entry_style = {
                    'relief': 'solid',
                    'borderwidth': 1,
                    'highlightthickness': 1,
                    'font': ('SF Pro Display', 13),
                    'insertbackground': '#000000',
                    'selectbackground': '#007aff',
                    'selectforeground': '#ffffff',
                }

            # macOS label styling
            self.label_style = {
                'font': ('SF Pro Display', 13),
                'anchor': 'w',
            }
            
        else:
            # Windows and Linux - keep dark theme
            self.colors = {
                'bg_primary': '#2b2b2b',        # Dark background
                'bg_secondary': '#3b3b3b',      # Lighter dark
                'bg_accent': '#4b4b4b',         # Accent background
                'text_primary': '#ffffff',      # White text
                'text_secondary': '#cccccc',    # Light gray text
                'text_accent': '#87CEEB',       # Sky blue
                'button_bg': '#3399ff',         # Blue buttons
                'button_fg': '#ffffff',         # White button text
                'button_hover': '#2288ee',      # Darker blue on hover
                'entry_bg': '#ffffff',          # White entry fields
                'entry_fg': '#333333',          # Dark entry text
                'success_color': '#28a745',     # Green
                'warning_color': '#ffc107',     # Yellow
                'error_color': '#dc3545',       # Red
                'border_color': '#555555',      # Dark border
                'canvas_bg': '#2b2b2b',         # Dark canvas background
                'scrollbar_bg': '#3b3b3b',      # Dark scrollbar
            }
            self.is_dark_mode = True  # Windows/Linux always use dark theme
            
            # Windows/Linux button styling
            self.button_style = {
                'relief': 'raised',
                'borderwidth': 2,
                'font': ('Arial', 10),
                'cursor': 'hand2',
                'padx': 15,
                'pady': 5,
            }
            
            # Windows/Linux entry styling
            self.entry_style = {
                'relief': 'sunken',
                'borderwidth': 2,
                'font': ('Arial', 10),
                'insertbackground': '#333333',
            }
            
            # Windows/Linux label styling
            self.label_style = {
                'font': ('Arial', 10),
                'anchor': 'w',
            }
    
    def create_button(self, parent, text, command=None, style_type='primary', **kwargs):
        """
        Create a platform-styled button.
        
        Args:
            parent: Parent widget
            text: Button text
            command: Button command
            style_type: 'primary', 'secondary', 'success', 'warning', 'error'
            **kwargs: Additional button options
        """
        # Determine colors based on style type
        if style_type == 'primary':
            bg_color = self.colors['button_bg']
            fg_color = self.colors['button_fg']
        elif style_type == 'secondary':
            bg_color = self.colors['bg_secondary']
            fg_color = self.colors['text_primary']
        elif style_type == 'success':
            bg_color = self.colors['success_color']
            fg_color = self.colors['button_fg']
        elif style_type == 'warning':
            bg_color = self.colors['warning_color']
            fg_color = self.colors['button_fg']
        elif style_type == 'error':
            bg_color = self.colors['error_color']
            fg_color = self.colors['button_fg']
        else:
            bg_color = self.colors['button_bg']
            fg_color = self.colors['button_fg']
        
        # Merge default style with custom options
        button_options = {
            'bg': bg_color,
            'fg': fg_color,
            'activebackground': self.colors['button_hover'],
            'activeforeground': fg_color,
            **self.button_style,
            **kwargs
        }
        
        if command:
            button_options['command'] = command
        
        button = tk.Button(parent, text=text, **button_options)
        
        # Add hover effects for better UX
        self._add_button_hover_effects(button, bg_color, fg_color)
        
        return button
    
    def create_entry(self, parent, textvariable=None, **kwargs):
        """Create a platform-styled entry widget."""
        entry_options = {
            'bg': self.colors['entry_bg'],
            'fg': self.colors['entry_fg'],
            'highlightcolor': self.colors['text_accent'],
            'highlightbackground': self.colors['border_color'],
            **self.entry_style,
            **kwargs
        }
        
        if textvariable:
            entry_options['textvariable'] = textvariable
        
        return tk.Entry(parent, **entry_options)
    
    def create_label(self, parent, text, style_type='primary', **kwargs):
        """
        Create a platform-styled label.
        
        Args:
            parent: Parent widget
            text: Label text
            style_type: 'primary', 'secondary', 'accent', 'title'
            **kwargs: Additional label options
        """
        if style_type == 'primary':
            fg_color = self.colors['text_primary']
            font_size = 12 if self.is_macos else 10
        elif style_type == 'secondary':
            fg_color = self.colors['text_secondary']
            font_size = 10 if self.is_macos else 9
        elif style_type == 'accent':
            fg_color = self.colors['text_accent']
            font_size = 12 if self.is_macos else 10
        elif style_type == 'title':
            fg_color = self.colors['text_primary']
            font_size = 16 if self.is_macos else 14
        else:
            fg_color = self.colors['text_primary']
            font_size = 12 if self.is_macos else 10
        
        label_options = {
            'bg': self.colors['bg_primary'],
            'fg': fg_color,
            'font': (self.label_style['font'][0], font_size),
            **kwargs
        }
        
        return tk.Label(parent, text=text, **label_options)
    
    def create_frame(self, parent, style_type='primary', **kwargs):
        """Create a platform-styled frame."""
        if style_type == 'primary':
            bg_color = self.colors['bg_primary']
        elif style_type == 'secondary':
            bg_color = self.colors['bg_secondary']
        elif style_type == 'accent':
            bg_color = self.colors['bg_accent']
        else:
            bg_color = self.colors['bg_primary']
        
        frame_options = {
            'bg': bg_color,
            **kwargs
        }
        
        return tk.Frame(parent, **frame_options)
    
    def create_scale(self, parent, variable=None, **kwargs):
        """Create a platform-styled scale widget."""
        scale_options = {
            'bg': self.colors['bg_primary'],
            'fg': self.colors['text_primary'],
            'highlightbackground': self.colors['bg_primary'],
            'troughcolor': self.colors['bg_secondary'],
            'activebackground': self.colors['text_accent'],
            **kwargs
        }
        
        if variable:
            scale_options['variable'] = variable
        
        return tk.Scale(parent, **scale_options)
    
    def create_checkbutton(self, parent, text, variable=None, **kwargs):
        """Create a platform-styled checkbutton."""
        checkbutton_options = {
            'bg': self.colors['bg_primary'],
            'fg': self.colors['text_primary'],
            'selectcolor': self.colors['bg_secondary'],
            'activebackground': self.colors['bg_primary'],
            'activeforeground': self.colors['text_primary'],
            'font': self.label_style['font'],
            **kwargs
        }
        
        if variable:
            checkbutton_options['variable'] = variable
        
        return tk.Checkbutton(parent, text=text, **checkbutton_options)
    
    def _add_button_hover_effects(self, button, normal_bg, normal_fg):
        """Add hover effects to buttons for better UX."""
        def on_enter(event):
            button.configure(bg=self.colors['button_hover'])
        
        def on_leave(event):
            button.configure(bg=normal_bg)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def configure_window(self, window):
        """Configure the main window with platform-appropriate styling."""
        window.configure(bg=self.colors['bg_primary'])

        if self.is_macos:
            # macOS-specific window configuration
            try:
                # Set window appearance to match system theme
                if self.is_dark_mode:
                    # Force dark appearance
                    window.tk.call('tk::unsupported::MacWindowStyle', 'appearance', window._w, 'darkAqua')
                else:
                    # Force light appearance
                    window.tk.call('tk::unsupported::MacWindowStyle', 'appearance', window._w, 'aqua')

                # Set window style for better integration
                window.tk.call('tk::unsupported::MacWindowStyle', 'style', window._w, 'document')
            except Exception as e:
                # Fallback if macOS styling is not supported
                print(f"macOS styling not available: {e}")
                pass
    
    def get_colors(self):
        """Get the current color scheme."""
        return self.colors.copy()
    
    def get_font(self, size=12, weight='normal'):
        """Get platform-appropriate font."""
        if self.is_macos:
            family = 'SF Pro Display'
        elif self.is_windows:
            family = 'Segoe UI'
        else:
            family = 'Arial'
        
        return (family, size, weight)

# Global instance for easy access
platform_styles = PlatformStyles()
