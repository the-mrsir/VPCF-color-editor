import json
import os
import sys
import re
import subprocess
import logging
import tkinter as tk
from tkinter import (
    Tk, Label, Button, colorchooser, filedialog, messagebox, END, SINGLE,
    Scrollbar, StringVar, Entry, Frame, PanedWindow, Menu, Checkbutton, IntVar
)
from tkinter import ttk
from tkinter.ttk import Style, Progressbar
from tkinter import simpledialog
# **New Imports for Update Checking**
import requests
import threading
import webbrowser
from packaging import version

# Version and Credit Information
VERSION = "v1.15"
CREDIT = "Developed by MrSir"

CONFIG_FILE = "config.json"
compiler_path = [None]  # Placeholder for the compiler path
folder_path = [None]  # Placeholder for the folder path

# Regex patterns for gradients and stops (Define these at the module level)
gradient_pattern = re.compile(
    r'(m_Gradient\s*=\s*\{\s*m_Stops\s*=\s*\[\s*)'  # Prefix
    r'((?:\{\s*m_flPosition\s*=\s*[\d\.]+\s*m_Color\s*=\s*\[\s*[\d,\s]+\]\s*\},?\s*)+)'  # Gradient stops
    r'(\s*\]\s*\})',  # Suffix
    re.IGNORECASE | re.DOTALL
)

stop_pattern = re.compile(
    r'\{\s*m_flPosition\s*=\s*([\d\.]+)\s*m_Color\s*=\s*\[\s*([\d,\s]+)\s*\]\s*\}',
    re.IGNORECASE | re.DOTALL
)

# Load and save configuration
def load_config():
    """Load the configuration from a file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save the configuration to a file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# Configure logging
logging.basicConfig(
    filename='vpcf_color_editor.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# **New Function for Checking Updates**
def check_for_updates(user_initiated=False):
    try:
        api_url = "https://api.github.com/repos/the-mrsir/VPCF-color-editor/releases/latest"
        response = requests.get(api_url)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release['tag_name']

        current_version = version.parse(VERSION.lstrip('v'))
        latest_version_parsed = version.parse(latest_version.lstrip('v'))

        if latest_version_parsed > current_version:
            # Schedule the GUI update in the main thread
            root.after(0, lambda: prompt_update(latest_release, latest_version))
        else:
            if user_initiated:
                root.after(0, lambda: messagebox.showinfo(
                    "No Updates Available",
                    f"You are using the latest version ({VERSION}).",
                    parent=root
                ))
    except Exception as e:
        logging.error(f"An error occurred while checking for updates: {e}")
        if user_initiated:
            root.after(0, lambda: messagebox.showerror(
                "Update Check Failed",
                f"An error occurred while checking for updates:\n{e}",
                parent=root
            ))

def check_for_updates_async(user_initiated=False):
    threading.Thread(target=lambda: check_for_updates(user_initiated)).start()


# Find .vpcf files
def find_vpcf_files(folder_path):
    logging.info(f"Searching for VPCF files in {folder_path}")
    vpcf_files = []
    for root_dir, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.vpcf'):
                file_path = os.path.join(root_dir, file)
                vpcf_files.append(file_path)
    logging.info(f"Total VPCF files found: {len(vpcf_files)}")
    return vpcf_files

# Read a file
def read_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    return content

def find_color_fields(content, filename):
    color_fields = []
    # Regex patterns for colors
    patterns = {
        'color': re.compile(
            r'(\b(m_ConstantColor|m_ColorFade|m_Color1|m_Color2|m_ColorTint|m_TintColor|m_ColorMin|m_ColorMax)\s*=\s*)(\[\s*[\d\.,\s]+\s*\])',
            re.IGNORECASE | re.MULTILINE
        ),
    }

    # Counters for gradient blocks and their stops
    gradient_block_counter = 0

    # Mapping of internal names to user-friendly names
    field_name_mapping = {
        'm_ConstantColor': 'Base Color',
        'm_ColorFade': 'Color Fade',
        'm_Color1': 'Color 1',
        'm_Color2': 'Color 2',
        'm_ColorTint': 'Color Tint',
        'm_TintColor': 'Tint Color',
        'm_ColorMin': 'Color Min',
        'm_ColorMax': 'Color Max',
    }

    # Find all gradients
    for gradient_match in gradient_pattern.finditer(content):
        gradient_block_counter += 1
        prefix = gradient_match.group(1)
        gradient_block = gradient_match.group(2)  # Gradient stops
        suffix = gradient_match.group(3)
        stop_index = 0

        for stop_match in stop_pattern.finditer(gradient_block):
            stop_position = stop_match.group(1)  # m_flPosition value
            gradient_color = stop_match.group(2)  # m_Color value
            is_non_empty = any(float(c) > 0 for c in re.findall(r'[\d\.]+', gradient_color))

            color_fields.append({
                'type': 'gradient',
                'start': gradient_match.start(),
                'end': gradient_match.end(),
                'value': gradient_color,
                'stop_position': stop_position,
                'full_match': stop_match.group(0),
                'prefix': '',  # Gradients don’t need a prefix
                'field_name': f'Gradient Block {gradient_block_counter} Stop {stop_index + 1}',
                'filename': filename,
                'is_non_empty': is_non_empty,
                'gradient_block_index': gradient_block_counter,
                'stop_index': stop_index
            })
            stop_index += 1

    # Find all scalar color fields
    for match in patterns['color'].finditer(content):
        raw_name = match.group(2)
        display_name = field_name_mapping.get(raw_name, raw_name.replace('m_', '').replace('_', ' ').title())
        color_fields.append({
            'type': 'color',
            'start': match.start(),
            'end': match.end(),
            'value': match.group(3),
            'full_match': match.group(0),
            'prefix': match.group(1),
            'field_name': display_name,
            'raw_name': raw_name,  # Add internal field name
            'filename': filename,
        })

    return color_fields

# Parse and format color strings
def parse_color_string(color_string):
    color_string = color_string.strip('[]')
    color_values = re.findall(r'[\d\.]+', color_string)
    return [int(float(c)) for c in color_values[:3]]  # Only take RGB

def color_list_to_string(color_list):
    return '[ ' + ', '.join(str(int(c)) for c in color_list) + ' ]'

def rgb_to_hex(color_list):
    if isinstance(color_list, list) and len(color_list) >= 3:
        r, g, b = [int(float(c)) for c in color_list[:3]]
        return '#%02x%02x%02x' % (r, g, b)
    else:
        return '#000000'

# Global compile_file function
def global_compile_file(file_name, file_name_to_path, compiler_path):
    try:
        filename = file_name_to_path[file_name]
        if not os.path.exists(compiler_path):
            raise FileNotFoundError(f"The compiler was not found at: {compiler_path}")

        result = subprocess.run(
            [compiler_path, filename],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"Compiled successfully: {filename}")
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        logging.error(f"Compilation failed for {file_name}: {e}")
        return False, e.stdout, e.stderr
    except Exception as e:
        logging.error(f"Unexpected error during compilation of {file_name}: {e}")
        return False, None, str(e)

def edit_gradients(apply_widgets, gradient_var_apply):
    try:
        start_color = colorchooser.askcolor(title="Choose Start Color", parent=root)[0]
        if not start_color:
            return
        end_color = colorchooser.askcolor(title="Choose End Color", parent=root)[0]
        if not end_color:
            return

        num_stops = simpledialog.askinteger(
            "Number of Stops",
            "Enter the number of gradient stops (e.g., 4):",
            initialvalue=4,
            minvalue=2,
            parent=root
        )
        if not num_stops:
            return

        # Interpolate colors for the specified number of stops
        interpolated_colors = [
            [
                int(start_color[i] + (end_color[i] - start_color[i]) * t / (num_stops - 1))
                for i in range(3)
            ]
            for t in range(num_stops)
        ]

        # Preview the gradient and allow edits
        def show_preview():
            preview_window = tk.Toplevel(root)
            preview_window.title("Gradient Preview")
            preview_window.geometry("500x300")

            # Canvas to display the gradient
            gradient_canvas = tk.Canvas(preview_window, width=480, height=100, bg="white")
            gradient_canvas.pack(pady=10)
            stop_width = 480 // len(interpolated_colors)

            for i, color in enumerate(interpolated_colors):
                color_hex = rgb_to_hex(color)
                gradient_canvas.create_rectangle(
                    i * stop_width, 0, (i + 1) * stop_width, 100,
                    fill=color_hex, outline=""
                )

            # Redo the gradient selection process
            def redo_gradient():
                preview_window.destroy()
                edit_gradients(apply_widgets, gradient_var_apply)

            # Edit individual stops
            def edit_stop():
                selected_stop = simpledialog.askinteger(
                    "Edit Stop",
                    f"Enter stop index (1-{len(interpolated_colors)}):",
                    minvalue=1, maxvalue=len(interpolated_colors),
                    parent=preview_window
                )
                if selected_stop:
                    stop_index = selected_stop - 1
                    new_color = colorchooser.askcolor(
                        initialcolor=rgb_to_hex(interpolated_colors[stop_index]),
                        title="Choose New Color for Stop",
                        parent=preview_window
                    )[0]
                    if new_color:
                        interpolated_colors[stop_index] = [int(new_color[0]), int(new_color[1]), int(new_color[2])]
                        preview_window.destroy()
                        show_preview()

            # Cancel gradient editing
            def cancel_gradient():
                preview_window.destroy()

            # Apply the gradient and store it for batch application
            def apply_gradient():
                apply_widgets["gradient_editor"]["new_color"] = interpolated_colors
                gradient_var_apply.set(1)  # Automatically check "Apply"
                preview_window.destroy()
                messagebox.showinfo(
                    "Gradient Applied",
                    "The gradient has been applied for batch processing.",
                    parent=root
                )

            # Buttons for preview controls
            tk.Button(preview_window, text="Redo", command=redo_gradient).pack(side="left", padx=10, pady=10)
            tk.Button(preview_window, text="Edit Stop", command=edit_stop).pack(side="left", padx=10, pady=10)
            tk.Button(preview_window, text="OK", command=apply_gradient).pack(side="left", padx=10, pady=10)
            tk.Button(preview_window, text="Cancel", command=cancel_gradient).pack(side="left", padx=10, pady=10)

        show_preview()

    except Exception as e:
        logging.exception("An error occurred while editing gradients.")
        messagebox.showerror("Error", f"An error occurred while editing gradients:\n{e}", parent=root)


def backup_file(filename):
    backup_filename = filename + '.bak'
    if not os.path.exists(backup_filename):
        import shutil
        shutil.copy2(filename, backup_filename)
        logging.info(f"Backup created: {backup_filename}")
    else:
        logging.info(f"Backup already exists: {backup_filename}")

# Main GUI function
def show_gui(root, vpcf_files, parent_folder):
    try:
        apply_widgets = {}  # Holds the widgets for the "Apply to All" section
        widgets = []        # Holds per-field widgets for the current file
        content = ""        # Holds the content of the currently loaded file
        global current_theme  # Declare globally to be accessible across functions

        # Define themes
        themes = {
            "light": {
                "bg": "#f0f0f0",       # Light background
                "fg": "#000000",       # Dark foreground
                "button_bg": "#e0e0e0",
                "button_fg": "#000000",
                "highlight_bg": "#d9d9d9",
                "highlight_fg": "#000000"
            },
            "dark": {
                "bg": "#2e2e2e",       # Dark background
                "fg": "#ffffff",       # Light foreground
                "button_bg": "#4e4e4e",
                "button_fg": "#ffffff",
                "highlight_bg": "#444444",
                "highlight_fg": "#ffffff"
            }
        }
        current_theme = "light"  # Default theme

        root.title(f"VPCF Color Editor {VERSION} - {CREDIT}")
        root.geometry('1200x700')
        root.minsize(1000, 600)
        style = Style()
        style.theme_use('clam')
        paned_window = PanedWindow(root, orient='horizontal')
        paned_window.pack(fill='both', expand=True)

        def toggle_dark_mode():
            """Toggle between light and dark themes."""
            global current_theme  # Declare as global to modify the variable
            current_theme = "dark" if current_theme == "light" else "light"
            theme = themes[current_theme]
            apply_theme(root, theme)  # Apply the selected theme to the GUI
            save_theme_preference()  # Save the preference for future use

        def apply_theme(widget, theme):
            """Apply the theme recursively to a widget and its children."""
            widget_type = widget.winfo_class()
            try:
                # Apply background color universally
                widget.config(bg=theme["bg"])

                # Apply foreground color for specific widget types
                if widget_type in ["Label", "Button", "Entry", "Listbox", "Checkbutton", "Menubutton"]:
                    widget.config(fg=theme["fg"], bg=theme["bg"])
                elif widget_type == "Canvas":
                    widget.config(bg=theme["bg"], highlightbackground=theme["bg"])
                elif widget_type == "Scrollbar":
                    widget.config(
                        bg=theme["bg"],
                        troughcolor=theme["bg"],
                        activebackground=theme["highlight_bg"],
                        highlightbackground=theme["bg"],
                        highlightcolor=theme["bg"]
                    )
                elif widget_type == "Entry":
                    widget.config(
                        fg=theme["fg"],
                        bg=theme["bg"],
                        insertbackground=theme["fg"],  # Cursor color
                        highlightbackground=theme["bg"]
                    )
                elif widget_type == "Listbox":
                    widget.config(
                        bg=theme["bg"], fg=theme["fg"],
                        selectbackground=theme["highlight_bg"], selectforeground=theme["highlight_fg"],
                        highlightbackground=theme["bg"]
                    )
                elif widget_type == "Text":
                    widget.config(
                        fg=theme["fg"],
                        bg=theme["bg"],
                        insertbackground=theme["fg"],
                        selectbackground=theme["highlight_bg"],
                        selectforeground=theme["highlight_fg"],
                        highlightbackground=theme["bg"]
                    )
                elif widget_type == "Menu":
                    widget.config(
                        bg=theme["bg"],
                        fg=theme["fg"],
                        activebackground=theme["highlight_bg"],
                        activeforeground=theme["highlight_fg"]
                    )
                elif widget_type == "Frame":
                    widget.config(bg=theme["bg"])
                elif widget_type == "Toplevel":
                    widget.config(bg=theme["bg"])
            except Exception as e:
                logging.warning(f"Theme application skipped for {widget_type}: {e}")

            # Recurse for child widgets
            for child in widget.winfo_children():
                apply_theme(child, theme)

        def save_theme_preference():
            """Save the user's theme preference."""
            config = load_config()
            config["theme"] = current_theme
            save_config(config)

        def load_theme_preference():
            """Load the user's theme preference."""
            config = load_config()
            return config.get("theme", "light")  # Default to "light" if not specified

        # Add menu bar
        menubar = Menu(root)
        root.config(menu=menubar)

        # Settings menu
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Set Compiler Path", command=lambda: set_compiler_path())
        settings_menu.add_command(label="Change Folder", command=lambda: change_folder())
        settings_menu.add_command(label="Toggle Dark Mode", command=toggle_dark_mode)
        
        about_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=about_menu)
        about_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", f"VPCF Color Editor {VERSION}\n{CREDIT}"))
        about_menu.add_command(label="Check for Updates", command=lambda: check_for_updates_async(user_initiated=True))


        current_theme = load_theme_preference()
        theme = themes[current_theme]
        apply_theme(root, theme)

        # Initialize data structures
        selected_file = tk.StringVar()
        search_var = StringVar()
        file_name_to_path = {}
        current_file_index = [0]
        all_color_fields = []
        files_content = {}
        unique_fields = {}

        # Process each file and include only those with color fields
        for file_path in vpcf_files:
            file_name = os.path.relpath(file_path, parent_folder)
            content = read_file(file_path)
            color_fields = find_color_fields(content, file_name)
            if color_fields:
                # Only include files with color fields
                file_name_to_path[file_name] = file_path
                files_content[file_name] = content
                all_color_fields.extend(color_fields)
                for field in color_fields:
                    if field['type'] == 'color':
                        unique_fields[field['raw_name']] = field['field_name']
            else:
                logging.info(f"File skipped (no color fields): {file_name}")

        # After processing files, check if any files were loaded
        if not file_name_to_path:
            messagebox.showinfo("No Color Fields Found", "No VPCF files with color fields found in the selected folder.", parent=root)
            root.destroy()
            sys.exit("No VPCF files with color fields found.")

        def change_folder():
            """Change the folder and reload files."""
            new_folder = filedialog.askdirectory(title="Select Parent Folder", parent=root)
            if new_folder:
                folder_path[0] = new_folder
                config = load_config()
                config["folder_path"] = new_folder
                save_config(config)
                reload_files(new_folder)

        def reload_files(new_folder):
            """Reload VPCF files from a new folder."""
            global root
            try:
                # Find new files
                vpcf_files = find_vpcf_files(new_folder)
                if not vpcf_files:
                    messagebox.showinfo("No Files Found", "No VPCF files found in the selected folder.", parent=root)
                    return

                # Save the new folder path
                config = load_config()
                config["folder_path"] = new_folder
                save_config(config)

                # Clear existing data structures
                file_name_to_path.clear()
                files_content.clear()
                all_color_fields.clear()
                unique_fields.clear()

                # Process each file and include only those with color fields
                for file_path in vpcf_files:
                    file_name = os.path.relpath(file_path, new_folder)
                    content = read_file(file_path)
                    color_fields = find_color_fields(content, file_name)
                    if color_fields:
                        file_name_to_path[file_name] = file_path
                        files_content[file_name] = content
                        all_color_fields.extend(color_fields)
                        for field in color_fields:
                            if field['type'] == 'color':
                                unique_fields[field['raw_name']] = field['field_name']
                    else:
                        logging.info(f"File skipped (no color fields): {file_name}")

                # After processing files, check if any files were loaded
                if not file_name_to_path:
                    messagebox.showinfo("No Color Fields Found", "No VPCF files with color fields found in the selected folder.", parent=root)
                    return

                # Refresh the GUI components
                populate_listbox()
                load_apply_to_all_fields()
                current_file_index[0] = 0
                on_file_select()

            except Exception as e:
                logging.exception("An error occurred while reloading files.")
                messagebox.showerror("Error", f"An error occurred while reloading files:\n{e}", parent=root)
                
        # Left Pane for File Viewer
        left_frame = tk.Frame(paned_window, relief='groove', borderwidth=2)
        paned_window.add(left_frame, minsize=400)  # Set the minimum width of the file viewer

        # File Viewer Widgets
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)
        lbl_folder = Label(left_frame, text="Files", font=('Arial', 12, 'bold'))
        lbl_folder.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

        search_entry = Entry(left_frame, textvariable=search_var)
        search_entry.grid(row=1, column=0, sticky='ew', padx=5)
        search_var.trace_add('write', lambda *args: filter_files())

        listbox_files = tk.Listbox(left_frame, selectmode=SINGLE, exportselection=False)
        listbox_files.grid(row=2, column=0, sticky='nsew', padx=5, pady=5)

        listbox_scrollbar = Scrollbar(left_frame, orient='vertical', command=listbox_files.yview)
        listbox_files.configure(yscrollcommand=listbox_scrollbar.set)
        listbox_scrollbar.grid(row=2, column=1, sticky='ns')

        # Right Pane for Editor and Apply Sections
        right_paned = PanedWindow(paned_window, orient='vertical')
        paned_window.add(right_paned, minsize=500)

        # Upper Editor Pane
        right_frame = tk.Frame(right_paned, relief='groove', borderwidth=2)
        right_paned.add(right_frame, minsize=300)

        # Editor Widgets
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        lbl_current_file = Label(right_frame, text="", font=('Arial', 12, 'bold'))
        lbl_current_file.grid(row=0, column=0, sticky='w', padx=10, pady=5)

        frame_colors = Frame(right_frame)
        frame_colors.grid(row=1, column=0, sticky='nsew', padx=10)

        canvas = tk.Canvas(frame_colors)
        canvas.grid(row=0, column=0, sticky='nsew')
        frame_colors.rowconfigure(0, weight=1)
        frame_colors.columnconfigure(0, weight=1)

        scrollbar_colors = Scrollbar(frame_colors, orient='vertical', command=canvas.yview)
        scrollbar_colors.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scrollbar_colors.set)

        inner_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')
        inner_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        # Lower Apply-to-All Pane
        apply_frame = tk.Frame(right_paned, relief='groove', borderwidth=2)
        right_paned.add(apply_frame, minsize=200)

        # Apply-to-All Widgets
        apply_frame.columnconfigure(0, weight=1)
        apply_frame.rowconfigure(1, weight=1)

        Label(apply_frame, text="Apply to All Fields", font=('Arial', 12, 'bold')).grid(
            row=0, column=0, sticky='w', padx=10, pady=5
        )

        apply_canvas = tk.Canvas(apply_frame)
        apply_canvas.grid(row=1, column=0, sticky='nsew', padx=10)

        apply_scrollbar = Scrollbar(apply_frame, orient='vertical', command=apply_canvas.yview)
        apply_scrollbar.grid(row=1, column=1, sticky='ns')
        apply_canvas.configure(yscrollcommand=apply_scrollbar.set)

        apply_inner_frame = tk.Frame(apply_canvas)
        apply_canvas.create_window((0, 0), window=apply_inner_frame, anchor='nw')
        apply_inner_frame.bind('<Configure>', lambda e: apply_canvas.configure(scrollregion=apply_canvas.bbox('all')))

        def load_apply_to_all_fields():
            nonlocal apply_widgets
            apply_widgets.clear()  # Clear existing widgets
            row = 0
            for raw_name, display_name in sorted(unique_fields.items(), key=lambda x: x[1]):
                Label(apply_inner_frame, text=display_name, anchor='w').grid(row=row, column=0, sticky='w', pady=2)
                color_label = Label(apply_inner_frame, text='    ', bg='#FFFFFF', relief='groove')
                color_label.grid(row=row, column=1, sticky='w', padx=5)

                var_apply = IntVar()
                check_apply = Checkbutton(apply_inner_frame, text="Apply", variable=var_apply)
                check_apply.grid(row=row, column=3, padx=5)

                def choose_color(rn=raw_name, var_apply=var_apply):
                    color = colorchooser.askcolor(parent=root)[0]
                    if color:
                        r, g, b = color
                        hex_color = '#%02x%02x%02x' % (int(r), int(g), int(b))
                        apply_widgets[rn]['new_color'] = [int(r), int(g), int(b)]
                        apply_widgets[rn]['color_label'].configure(bg=hex_color)
                        # Automatically check the Apply checkbox
                        var_apply.set(1)

                choose_button = Button(apply_inner_frame, text='Choose Color', command=choose_color)
                choose_button.grid(row=row, column=2, padx=5, pady=2)

                apply_widgets[raw_name] = {
                    'color_label': color_label,
                    'new_color': None,
                    'apply': var_apply,
                    'display_name': display_name,
                }
                row += 1

            # Add Gradient Editor Row
            Label(apply_inner_frame, text="Gradient Editor", anchor='w', font=("Arial", 10, "bold")).grid(row=row, column=0, sticky='w', pady=5)

            gradient_var_apply = IntVar()
            gradient_check_apply = Checkbutton(apply_inner_frame, text="Apply", variable=gradient_var_apply)
            gradient_check_apply.grid(row=row, column=3, padx=5)

            gradient_button = Button(apply_inner_frame, text="Edit Gradients", command=lambda: edit_gradients(apply_widgets, gradient_var_apply))
            gradient_button.grid(row=row, column=2, padx=5, pady=5)

            apply_widgets["gradient_editor"] = {
                "apply": gradient_var_apply,
                "new_color": None,
            }

            apply_inner_frame.update_idletasks()
            apply_canvas.config(scrollregion=apply_canvas.bbox("all"))

        def load_vpcf_file(filename):
            nonlocal content, color_fields, widgets
            widgets = []
            try:
                content = files_content[filename]
                if not content:
                    messagebox.showerror("Error", f"Failed to read the VPCF file: {filename}", parent=root)
                    return
                color_fields = [field for field in all_color_fields if field['filename'] == filename]
                logging.info(f"Loaded file: {filename} with {len(color_fields)} color fields.")
            except Exception as e:
                logging.exception(f"An error occurred while loading the file: {filename}")
                messagebox.showerror("Error", f"An error occurred while loading the file:\n{e}", parent=root)
                return

            # Clear existing widgets
            for widget in inner_frame.winfo_children():
                widget.destroy()
            lbl_current_file.config(text=f"Editing: {filename}")

            if not color_fields:
                Label(inner_frame, text="No color fields found in this file.", anchor='w', fg='red').grid(row=0, column=0, sticky='w', pady=2)
                return

            row = 0
            gradient_counter = 1  # Counter specifically for gradient stops
            field_counter = {}  # Keeps count of individual non-gradient fields (e.g., m_ColorMin)

            # Process all fields
            for idx, field in enumerate(color_fields):
                if field['type'] == 'gradient':  # Gradient stops
                    display_name = field['field_name']
                else:  # Other fields
                    field_name = field['field_name']
                    field_counter[field_name] = field_counter.get(field_name, 0) + 1
                    display_name = f"{field_name} {field_counter[field_name]}"

                # Create a label for the field
                Label(inner_frame, text=display_name, anchor='w').grid(row=row, column=0, sticky='w', pady=2)

                # Display the current color
                current_color = parse_color_string(field['value'])
                current_color_hex = rgb_to_hex(current_color)
                color_label = Label(inner_frame, text='    ', bg=current_color_hex, relief='groove')
                color_label.grid(row=row, column=1, sticky='w', padx=5)

                # Create a button to choose a new color
                def choose_color(idx=idx):
                    color = colorchooser.askcolor(parent=root)[0]
                    if color:
                        r, g, b = color
                        hex_color = '#%02x%02x%02x' % (int(r), int(g), int(b))
                        widgets[idx]['new_color'] = [int(r), int(g), int(b)]
                        widgets[idx]['color_label'].configure(bg=hex_color)

                choose_button = Button(inner_frame, text='Choose Color', command=choose_color)
                choose_button.grid(row=row, column=2, padx=5, pady=2)

                widgets.append({
                    'color_label': color_label,
                    'new_color': current_color[:3],
                    'field': field,
                })
                row += 1

            # Update scroll region for the canvas
            inner_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox('all'))

        def on_file_select(event=None):
            selection = listbox_files.curselection()
            if selection:
                index = selection[0]
                file_name = listbox_files.get(index)
                selected_file.set(file_name)
                current_file_index[0] = index
                logging.info(f"File selected: {file_name}")
                load_vpcf_file(file_name)
        listbox_files.bind('<<ListboxSelect>>', on_file_select)

        def populate_listbox():
            listbox_files.delete(0, END)
            for file_name in sorted(file_name_to_path.keys()):
                listbox_files.insert(END, file_name)
            if listbox_files.size() > 0:
                listbox_files.select_set(0)
                on_file_select()
            else:
                lbl_current_file.config(text="No file selected.")
                for widget in inner_frame.winfo_children():
                    widget.destroy()
                messagebox.showinfo("No Files", "No VPCF files with color fields are available.", parent=root)
        populate_listbox()

        def filter_files():
            search_text = search_var.get().lower()
            listbox_files.delete(0, END)
            for file_name in sorted(file_name_to_path.keys()):
                if search_text in file_name.lower():
                    listbox_files.insert(END, file_name)
            if listbox_files.size() > 0:
                listbox_files.select_set(0)
                on_file_select()

        def save_changes():
            try:
                filename = selected_file.get()
                content = files_content[filename]
                new_content = content
                # Collect scalar color fields to replace
                scalar_replacements = []
                # Build a mapping of gradient stops to new colors
                gradient_stop_colors = {}
                for widget in widgets:
                    field = widget['field']
                    new_color = widget['new_color']
                    if field['type'] == 'color':
                        # Handle scalar color fields
                        pattern = re.compile(
                            re.escape(field['prefix']) + re.escape(field['value']),
                            re.IGNORECASE | re.MULTILINE
                        )
                        scalar_replacements.append((pattern, field['prefix'] + color_list_to_string(new_color)))
                    elif field['type'] == 'gradient':
                        # Use gradient_block_index and stop_index as keys
                        key = (field['gradient_block_index'], field['stop_index'])
                        gradient_stop_colors[key] = new_color
                # Perform scalar replacements
                for pattern, replacement in scalar_replacements:
                    new_content = pattern.sub(replacement, new_content, count=1)
                # Now process gradient blocks
                def replace_gradient_block(match):
                    prefix = match.group(1)
                    gradient_stops_old = match.group(2)
                    suffix = match.group(3)
                    stop_matches = list(stop_pattern.finditer(gradient_stops_old))
                    new_gradient_stops = []
                    # Assuming we can get the gradient_block_index from some variable
                    nonlocal gradient_block_counter_for_replace
                    gradient_block_counter_for_replace += 1
                    gradient_block_index = gradient_block_counter_for_replace
                    for stop_idx, stop_match in enumerate(stop_matches):
                        stop_position = float(stop_match.group(1))
                        color_values = stop_match.group(2)
                        color_list = parse_color_string('[' + color_values + ']')
                        # Check if we have a new color for this stop
                        key = (gradient_block_index, stop_idx)
                        if key in gradient_stop_colors:
                            new_color = gradient_stop_colors[key]
                        else:
                            new_color = color_list
                        new_color_str = color_list_to_string(new_color)
                        new_stop = f"""{{
    m_flPosition = {stop_position}
    m_Color = 
    {new_color_str}
}}"""
                        new_gradient_stops.append(new_stop)
                    gradient_stops_string = ',\n'.join(new_gradient_stops)
                    return prefix + gradient_stops_string + suffix
                # Initialize gradient block counter
                gradient_block_counter_for_replace = 0
                new_content = gradient_pattern.sub(replace_gradient_block, new_content)
                # Save the updated content
                backup_file(file_name_to_path[filename])
                with open(file_name_to_path[filename], 'w') as f:
                    f.write(new_content)
                files_content[filename] = new_content  # Update the in-memory content
                logging.info(f"File saved: {filename}")
                messagebox.showinfo("Success", f"Colors updated and file saved:\n{filename}", parent=root)
                
                # Refresh GUI to reflect the changes
                refresh_gui()
            except Exception as e:
                logging.exception("An error occurred while saving changes.")
                messagebox.showerror("Error", f"An error occurred while saving changes:\n{e}", parent=root)

        def save_and_compile():
            save_changes()
            if not compiler_path[0]:
                messagebox.showwarning("Compiler Path Not Set", "Please set the compiler path in Settings > Set Compiler Path.", parent=root)
                return
            compile_file()

        def compile_file():
            try:
                file_name = selected_file.get()
                filename = file_name_to_path[file_name]
                compiler = compiler_path[0]
                if not os.path.exists(compiler):
                    messagebox.showerror("Compiler Not Found", f"The compiler was not found at:\n{compiler}", parent=root)
                    return
                result = subprocess.run(
                    [compiler, filename],
                    check=True,
                    capture_output=True,
                    text=True
                )
                output = result.stdout
                errors = result.stderr
                message = f"Compiled successfully: {filename}"
                if output:
                    message += f"\nCompiler Output:\n{output}"
                if errors:
                    message += f"\nCompiler Errors:\n{errors}"
                messagebox.showinfo("Compilation Result", message, parent=root)
            except subprocess.CalledProcessError as e:
                message = f"Failed to compile: {filename}"
                if e.stdout:
                    message += f"\nCompiler Output:\n{e.stdout}"
                if e.stderr:
                    message += f"\nCompiler Errors:\n{e.stderr}"
                logging.exception(message)
                messagebox.showerror("Compilation Error", message, parent=root)
            except Exception as e:
                logging.exception(f"An unexpected error occurred during compilation of {filename}")
                messagebox.showerror("Error", f"An unexpected error occurred during compilation:\n{e}", parent=root)

        # Compilation functions
        def compile_all_files():
            if not compiler_path[0]:
                messagebox.showwarning("Compiler Path Not Set", "Please set the compiler path in Settings > Set Compiler Path.", parent=root)
                return

            compiler = compiler_path[0]
            failed_files = []
            success_count = 0

            if len(files_content) == 0:
                messagebox.showinfo("No Files to Compile", "No files available for compilation.", parent=root)
                return

            progress_window = tk.Toplevel(root)
            progress_window.title("Compiling Files")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)

            Label(progress_window, text="Compiling files, please wait...", font=("Arial", 12)).pack(pady=10)
            progress_bar = ttk.Progressbar(progress_window, orient='horizontal', mode='determinate', length=300)
            progress_bar.pack(pady=10)
            progress_bar['maximum'] = len(files_content)

            progress_label = Label(progress_window, text="0 / 0", font=("Arial", 10))
            progress_label.pack()

            root.attributes("-disabled", True)

            def compile_files():
                try:
                    nonlocal success_count

                    for index, file_name in enumerate(files_content.keys(), start=1):
                        success, stdout, stderr = global_compile_file(file_name, file_name_to_path, compiler)
                        if success:
                            success_count += 1
                        else:
                            failed_files.append(file_name)

                        progress_bar['value'] = index
                        progress_label.config(text=f"{index} / {len(files_content)}")
                        progress_window.update()

                    root.attributes("-disabled", False)
                    progress_window.destroy()

                    message = f"Compiled {success_count} files successfully."
                    if failed_files:
                        message += f"\nFailed to compile {len(failed_files)} files:\n" + "\n".join(failed_files)
                    messagebox.showinfo("Compilation Result", message, parent=root)
                except Exception as e:
                    logging.exception("Error during compilation")
                    messagebox.showerror("Error", f"An error occurred during compilation:\n{e}", parent=root)
                    root.attributes("-disabled", False)
                    progress_window.destroy()

            from threading import Thread
            compile_thread = Thread(target=compile_files)
            compile_thread.start()

        def set_compiler_path():
            path = filedialog.askopenfilename(title="Select Compiler Executable", parent=root)
            if path:
                compiler_path[0] = path
                messagebox.showinfo("Compiler Path Set", f"Compiler path set to:\n{path}", parent=root)

        def apply_to_all():
            try:
                # Gather fields to apply
                fields_to_apply = {
                    field_name: widget['new_color']
                    for field_name, widget in apply_widgets.items()
                    if field_name != "gradient_editor" and widget['apply'].get() and widget['new_color'] is not None
                }
                gradients_to_apply = (
                    apply_widgets["gradient_editor"]["new_color"]
                    if apply_widgets["gradient_editor"]["apply"].get() else None
                )
                if not fields_to_apply and not gradients_to_apply:
                    messagebox.showinfo("No Changes", "No fields selected for applying changes.", parent=root)
                    return

                # Keep track of files that were modified
                modified_files = set()

                for file_name, content in files_content.items():
                    new_content = content

                    # Apply scalar color fields
                    for raw_name, new_color in fields_to_apply.items():
                        new_color_str = color_list_to_string(new_color)
                        pattern = re.compile(
                            rf'(\b{re.escape(raw_name)}\s*=\s*)(\[[^\]]*\])',
                            re.IGNORECASE | re.MULTILINE
                        )
                        new_content = re.sub(
                            pattern,
                            lambda match: match.group(1) + new_color_str,
                            new_content
                        )

                    # Apply gradients if applicable
                    if gradients_to_apply:
                        new_content = replace_gradient_blocks(new_content, gradients_to_apply)

                    # Save updated content if changes are made
                    if content != new_content:
                        backup_file(file_name_to_path[file_name])
                        with open(file_name_to_path[file_name], 'w') as f:
                            f.write(new_content)
                        files_content[file_name] = new_content  # Update in-memory content
                        modified_files.add(file_name)

                # Update all_color_fields for modified files
                nonlocal all_color_fields
                for file_name in modified_files:
                    # Remove old color fields for this file
                    all_color_fields = [field for field in all_color_fields if field['filename'] != file_name]
                    # Re-parse the updated content
                    content = files_content[file_name]
                    color_fields = find_color_fields(content, file_name)
                    all_color_fields.extend(color_fields)

                messagebox.showinfo("Success", "Colors updated and all files saved.", parent=root)
                refresh_gui()
            except Exception as e:
                logging.exception("An error occurred while applying changes.")
                messagebox.showerror("Error", f"An error occurred while applying changes:\n{e}", parent=root)

        def replace_gradient_blocks(content, gradients_to_apply):
            def replace_gradient_block(match):
                prefix = match.group(1)
                gradient_block_content = match.group(2)
                suffix = match.group(3)

                # Find all gradient stops including their formatting
                gradient_stop_pattern = re.compile(
                    r'(\s*\{.*?m_flPosition\s*=\s*[\d\.]+.*?m_Color\s*=\s*(\[[^\]]*\]|\[.*?\])\s*\}[\s,]*)',
                    re.DOTALL
                )
                stops = gradient_stop_pattern.findall(gradient_block_content)

                # Extract existing formatting details
                stop_formats = []
                for full_stop, color_array in stops:
                    stop_formats.append(full_stop)

                num_new_stops = len(gradients_to_apply)
                new_stops = []

                for i in range(num_new_stops):
                    # Determine position
                    position = i / (num_new_stops - 1) if num_new_stops > 1 else 0.0
                    position_str = f"{position:.6f}"

                    # Use formatting from existing stops if available
                    if i < len(stop_formats):
                        # Use existing stop format
                        existing_stop = stop_formats[i]
                        # Replace position and color
                        existing_stop = re.sub(
                            r'(m_flPosition\s*=\s*)([\d\.]+)',
                            lambda m: f"{m.group(1)}{position_str}",
                            existing_stop
                        )
                        existing_stop = re.sub(
                            r'(m_Color\s*=\s*)(\[[^\]]*\])',
                            lambda m: f"{m.group(1)}{color_list_to_string(gradients_to_apply[i])}",
                            existing_stop
                        )
                        new_stops.append(existing_stop)
                    else:
                        # Use the format of the last stop
                        last_stop = stop_formats[-1]
                        # Replace position and color
                        new_stop = re.sub(
                            r'(m_flPosition\s*=\s*)([\d\.]+)',
                            lambda m: f"{m.group(1)}{position_str}",
                            last_stop
                        )
                        new_stop = re.sub(
                            r'(m_Color\s*=\s*)(\[[^\]]*\])',
                            lambda m: f"{m.group(1)}{color_list_to_string(gradients_to_apply[i])}",
                            new_stop
                        )
                        new_stops.append(new_stop)

                # Reconstruct the gradient stops with original formatting
                new_gradient_block_content = ''.join(new_stops)

                return prefix + new_gradient_block_content + suffix

            new_content = gradient_pattern.sub(replace_gradient_block, content)
            return new_content

        def refresh_gui():
            """Refresh the GUI for the currently loaded file."""
            try:
                # Get the currently selected file
                filename = selected_file.get()
                if filename:
                    # Read the updated content from the file on disk
                    content = read_file(file_name_to_path[filename])
                    files_content[filename] = content  # Update the in-memory content

                    # Declare nonlocal variables to modify them
                    nonlocal all_color_fields

                    # Remove old color fields for this file from all_color_fields
                    all_color_fields = [field for field in all_color_fields if field['filename'] != filename]

                    # Re-parse the color fields for the updated content
                    color_fields = find_color_fields(content, filename)
                    all_color_fields.extend(color_fields)

                    # Reload the file in the GUI
                    load_vpcf_file(filename)
                    logging.info(f"GUI refreshed for file: {filename}")
                else:
                    logging.warning("No file selected to refresh.")
            except Exception as e:
                logging.exception("Error occurred during GUI refresh.")
                messagebox.showerror("Error", f"An error occurred during GUI refresh:\n{e}", parent=root)

        def navigate_file(direction):
            new_index = current_file_index[0] + direction
            if 0 <= new_index < listbox_files.size():
                current_file_index[0] = new_index
                listbox_files.select_clear(0, END)
                listbox_files.select_set(new_index)
                on_file_select()
            else:
                messagebox.showinfo("Navigation", "No more files in that direction.", parent=root)

        load_apply_to_all_fields()

        # Buttons and other GUI elements setup
        frame_buttons = tk.Frame(right_frame)
        frame_buttons.grid(row=2, column=0, pady=5)
        frame_buttons.columnconfigure((0,1,2,3,4), weight=1)
        btn_previous = Button(frame_buttons, text='Previous', command=lambda: navigate_file(-1))
        btn_previous.grid(row=0, column=0, padx=5, sticky='ew')
        save_button = Button(frame_buttons, text='Save Changes', command=save_changes)
        save_button.grid(row=0, column=1, padx=5, sticky='ew')
        save_compile_button = Button(frame_buttons, text='Save and Compile', command=save_and_compile)
        save_compile_button.grid(row=0, column=2, padx=5, sticky='ew')
        btn_next = Button(frame_buttons, text='Next', command=lambda: navigate_file(1))
        btn_next.grid(row=0, column=3, padx=5, sticky='ew')
        btn_reload = Button(frame_buttons, text='Select Folder', command=change_folder)
        btn_reload.grid(row=0, column=4, padx=5, sticky='ew')

        apply_button = Button(apply_frame, text='Apply to All', command=apply_to_all)
        apply_button.grid(row=2, column=0, pady=5, sticky='ew', padx=10)
        compile_all_button = Button(apply_frame, text='Compile All', command=compile_all_files)
        compile_all_button.grid(row=3, column=0, pady=5, sticky='ew', padx=10)

        if file_name_to_path:
            file_name = list(sorted(file_name_to_path.keys()))[0]
            selected_file.set(file_name)
            load_vpcf_file(file_name)
        else:
            lbl_current_file.config(text="No file selected.")

        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        frame_colors.columnconfigure(0, weight=1)
        frame_colors.rowconfigure(0, weight=1)
        apply_frame.columnconfigure(0, weight=1)
        apply_frame.rowconfigure(1, weight=1)

        # **Start the update check in the GUI function**
        check_for_updates_async()

        root.mainloop()
    except Exception as e:
        logging.exception("An unexpected error occurred in the GUI.")
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}\nPlease check the log file for details.", parent=root)
        root.destroy()
        sys.exit(1)

def main():
    try:
        global root
        root = Tk()
        root.update()

        # Load configuration and folder path
        config = load_config()
        if "folder_path" in config:
            folder_path[0] = config["folder_path"]
        else:
            folder_path[0] = None

        # If no folder path or folder has no VPCF files, ask for a new folder
        while not folder_path[0] or not find_vpcf_files(folder_path[0]):
            if folder_path[0]:
                messagebox.showinfo(
                    "No Files Found",
                    "No VPCF files were found in the configured folder.\nPlease select a new folder.",
                    parent=root
                )
            folder_path[0] = filedialog.askdirectory(title="Select Parent Folder", parent=root)
            if not folder_path[0]:
                root.destroy()
                sys.exit("No folder selected.")
            # Save the new folder path to config
            config["folder_path"] = folder_path[0]
            save_config(config)

        # Check for files in the selected folder
        logging.info(f"Selected folder: {folder_path[0]}")
        vpcf_files = find_vpcf_files(folder_path[0])
        if not vpcf_files:
            messagebox.showinfo("No Files Found", "No VPCF files found in the selected folder.", parent=root)
            root.destroy()
            sys.exit("No VPCF files found.")

        # Launch the GUI
        show_gui(root, vpcf_files, folder_path[0])

    except Exception as e:
        logging.exception("An error occurred in the main function.")
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}\nPlease check the log file for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
