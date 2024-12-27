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
import urllib.request
import threading
import webbrowser


# Version and Credit Information
VERSION = "v1.17"
CREDIT = "Developed by MrSir"

CONFIG_FILE = "config.json"
compiler_path = [None]  # Placeholder for the compiler path
folder_path = [None]  # Placeholder for the folder path


gradient_pattern = re.compile(
    # 1) Group(1): prefix => "m_Gradient ... ["
    r'(m_Gradient\s*=\s*\{\s*m_Stops\s*=\s*\[\s*)'
    # 2) Group(2): one or more gradient stops
    r'((?:\{\s*m_flPosition\s*=\s*[\d\.]+\s*m_Color\s*=\s*\[\s*[\d,\s]+\s*\]\s*\}\s*,?\s*)+)'
    # 3) Group(3): suffix => "] }"
    r'(\s*\]\s*\})',
    re.IGNORECASE | re.DOTALL
)


stop_pattern = re.compile(
    r'(\{\s*m_flPosition\s*=\s*[\d\.]+\s*m_Color\s*=\s*\[\s*([\d,\s]+)\s*\]\s*\}\s*,?\s*)',
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
def fetch_latest_release():
    try:
        api_url = "https://api.github.com/repos/the-mrsir/VPCF-color-editor/releases/latest"
        with urllib.request.urlopen(api_url) as response:
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            latest_release = json.loads(data.decode(encoding))
            return latest_release
    except Exception as e:
        logging.error(f"An error occurred while fetching the latest release: {e}")
        return None

def is_newer_version(current_version, latest_version):
    def normalize(v):
        return [int(x) for x in re.sub(r'[^\d.]', '', v).split('.')]
    return normalize(latest_version) > normalize(current_version)

def prompt_update(latest_release, latest_version):
    result = messagebox.askyesno(
        "Update Available",
        f"A new version ({latest_version}) is available.\n"
        f"You are currently using version {VERSION}.\n\n"
        "Do you want to download the latest version?",
        parent=root
    )
    if result:
        webbrowser.open(latest_release['html_url'])

def check_for_updates(user_initiated=False):
    try:
        latest_release = fetch_latest_release()
        if not latest_release:
            if user_initiated:
                root.after(0, lambda: messagebox.showerror(
                    "Update Check Failed",
                    "Could not retrieve the latest version information.",
                    parent=root
                ))
            return

        latest_version = latest_release['tag_name']

        if is_newer_version(VERSION, latest_version):
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

def parse_color_string(color_string):
    """
    Return up to 4 channels (R, G, B, A) if the file has them.
    """
    color_string = color_string.strip('[]')
    color_values = re.findall(r'[\d\.]+', color_string)
    # Convert each to int; handle up to 4 channels
    return [int(float(c)) for c in color_values[:4]]


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


def show_gui(root, vpcf_files, parent_folder):
    try:
        apply_widgets = {}  # Holds the widgets for the "Apply to All" section
        widgets = []        # Holds per-field widgets for the current file
        content = ""        # Holds the content of the currently loaded file
        global current_theme  # For theme toggling
        selected_file = tk.StringVar()
        file_name_to_path = {}
        files_content = {}
        all_color_fields = []
        unique_fields = {}
        current_file_index = [0]

        # Define themes
        themes = {
            "light": {
                "bg": "#f0f0f0",
                "fg": "#000000",
                "button_bg": "#e0e0e0",
                "button_fg": "#000000",
                "highlight_bg": "#d9d9d9",
                "highlight_fg": "#000000"
            },
            "dark": {
                "bg": "#2e2e2e",
                "fg": "#ffffff",
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

        # ========== Create a main horizontal PanedWindow ==========
        main_pane = PanedWindow(root, orient='horizontal')
        main_pane.pack(fill='both', expand=True)

        # ---------------------------------------------------------
        # Left side: File List
        # ---------------------------------------------------------
        left_frame = tk.Frame(main_pane, relief='groove', borderwidth=2)
        main_pane.add(left_frame, minsize=400)  # Set the min width for the file viewer

        # File Viewer Widgets
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)
        lbl_folder = Label(left_frame, text="Files", font=('Arial', 12, 'bold'))
        lbl_folder.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

        search_var = StringVar()
        search_entry = Entry(left_frame, textvariable=search_var)
        search_entry.grid(row=1, column=0, sticky='ew', padx=5)
        search_var.trace_add('write', lambda *args: filter_files())

        listbox_files = tk.Listbox(left_frame, selectmode=SINGLE, exportselection=False)
        listbox_files.grid(row=2, column=0, sticky='nsew', padx=5, pady=5)

        listbox_scrollbar = Scrollbar(left_frame, orient='vertical', command=listbox_files.yview)
        listbox_files.configure(yscrollcommand=listbox_scrollbar.set)
        listbox_scrollbar.grid(row=2, column=1, sticky='ns')

        # ---------------------------------------------------------
        # Right side: Notebook with 2 tabs
        #   1) Color Editor
        #   2) Raw Text Editor
        # ---------------------------------------------------------
        right_frame = tk.Frame(main_pane, relief='groove', borderwidth=2)
        main_pane.add(right_frame, minsize=600)

        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill='both', expand=True)

        color_editor_tab = tk.Frame(notebook)
        text_editor_tab = tk.Frame(notebook)

        notebook.add(color_editor_tab, text="Color Editor")
        notebook.add(text_editor_tab, text="Raw Text Editor")

        # ========== COLOR EDITOR TAB ==========
        # We'll replicate your original "right_paned" approach here
        color_paned = PanedWindow(color_editor_tab, orient='vertical')
        color_paned.pack(fill='both', expand=True)

        # Upper Editor Pane (color fields)
        editor_frame = tk.Frame(color_paned, relief='groove', borderwidth=2)
        color_paned.add(editor_frame, minsize=300)

        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(1, weight=1)

        lbl_current_file = Label(editor_frame, text="", font=('Arial', 12, 'bold'))
        lbl_current_file.grid(row=0, column=0, sticky='w', padx=10, pady=5)

        frame_colors = Frame(editor_frame)
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
        apply_frame = tk.Frame(color_paned, relief='groove', borderwidth=2)
        color_paned.add(apply_frame, minsize=200)

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

        # ========== RAW TEXT EDITOR TAB ==========
        text_editor_frame = tk.Frame(text_editor_tab)
        text_editor_frame.pack(fill='both', expand=True)

        text_scrollbar = tk.Scrollbar(text_editor_frame)
        text_scrollbar.pack(side='right', fill='y')

        text_widget = tk.Text(text_editor_frame, wrap='none')
        text_widget.pack(side='left', fill='both', expand=True)

        text_widget.config(yscrollcommand=text_scrollbar.set)
        text_scrollbar.config(command=text_widget.yview)

        search_frame = tk.Frame(text_editor_tab)
        search_frame.pack(fill='x', padx=5, pady=5)

        search_label = tk.Label(search_frame, text="Search:")
        search_label.pack(side='left')

        search_str = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_str)
        search_entry.pack(side='left', padx=5)

        search_positions = []     # list of string indices ("1.0", "1.15", etc.)
        current_match_index = -1  # which match in 'search_positions' we're on

        def find_all_occurrences():
            """
            Finds all occurrences of search_str in text_widget,
            highlights them, and stores each start index in search_positions.
            """
            nonlocal search_positions, current_match_index

            # Clear old highlights
            text_widget.tag_remove("search_highlight", "1.0", tk.END)

            pattern = search_str.get()
            if not pattern.strip():
                return

            search_positions = []
            current_match_index = -1

            start_pos = "1.0"
            while True:
                # search(...) returns empty string if not found
                match_start = text_widget.search(pattern, start_pos, nocase=True, stopindex=tk.END)
                if not match_start:
                    break

                # Calculate match_end
                match_end = f"{match_start}+{len(pattern)}c"

                # Highlight it
                text_widget.tag_add("search_highlight", match_start, match_end)
                search_positions.append(match_start)

                start_pos = match_end

            # Configure the highlight style
            text_widget.tag_config("search_highlight", background="yellow", foreground="black")

            if not search_positions:
                messagebox.showinfo("No Matches Found", f"'{pattern}' not found.")
            else:
                # Jump to the first match
                current_match_index = 0
                text_widget.mark_set("insert", search_positions[current_match_index])
                text_widget.see(search_positions[current_match_index])

        def find_next_match():
            """ Move to the next match in search_positions, if any. """
            nonlocal search_positions, current_match_index
            if not search_positions:
                return
            current_match_index = (current_match_index + 1) % len(search_positions)
            text_widget.mark_set("insert", search_positions[current_match_index])
            text_widget.see(search_positions[current_match_index])

        def find_prev_match():
            """ Move to the previous match in search_positions, if any. """
            nonlocal search_positions, current_match_index
            if not search_positions:
                return
            current_match_index = (current_match_index - 1) % len(search_positions)
            text_widget.mark_set("insert", search_positions[current_match_index])
            text_widget.see(search_positions[current_match_index])

        def find_in_text():
            """
            Searches the text_widget for occurrences of the string in search_str.
            Highlights matches, scrolls to the first match, and if none are found,
            shows a messagebox.
            """
            # Remove any existing 'search_highlight' tags to reset previous searches
            text_widget.tag_remove("search_highlight", "1.0", tk.END)

            # Read the search pattern from the Entry widget
            pattern = search_str.get()
            if not pattern.strip():
                return  # If empty, do nothing

            start_pos = "1.0"
            found_positions = []

            # Loop until no more matches
            while True:
                # search(...) returns an empty string if not found
                match_start = text_widget.search(pattern, start_pos, nocase=True, stopindex=tk.END)
                if not match_start:
                    break  # No more occurrences found

                # Determine where the match ends (match_start + length of pattern)
                match_end = f"{match_start}+{len(pattern)}c"

                # Tag the match range so we can highlight it
                text_widget.tag_add("search_highlight", match_start, match_end)

                # Save position so we can jump to it later
                found_positions.append(match_start)

                # Move just past this match to search for the next
                start_pos = match_end

            # Configure highlight style (yellow background, black text)
            text_widget.tag_config("search_highlight", background="yellow", foreground="black")

            if not found_positions:
                # No matches at all
                messagebox.showinfo("No Matches Found", f"'{pattern}' not found in the text.")
            else:
                # Scroll to the first match
                first_match = found_positions[0]
                text_widget.mark_set("insert", first_match)
                text_widget.see(first_match)


        search_button = tk.Button(search_frame, text="Find All", command=find_all_occurrences)
        search_button.pack(side='left', padx=5)

        next_button = tk.Button(search_frame, text="Next", command=find_next_match)
        next_button.pack(side='left', padx=5)

        prev_button = tk.Button(search_frame, text="Prev", command=find_prev_match)
        prev_button.pack(side='left', padx=5)


        text_btn_frame = tk.Frame(text_editor_tab)
        text_btn_frame.pack(fill='x', padx=5, pady=5)

        btn_reload_text = tk.Button(text_btn_frame, text="Reload Text from Disk")
        btn_reload_text.pack(side='left', padx=5)

        btn_save_text = tk.Button(text_btn_frame, text="Save Text to Disk")
        btn_save_text.pack(side='left', padx=5)

        # We'll keep track of the last mod time for each file to detect changes
        last_mtime_map = {}

        # ========== Helper functions for the text editor ==========
        def load_text_into_editor(filename):
            """Load raw text of `filename` into text_widget."""
            if filename not in file_name_to_path:
                return
            path = file_name_to_path[filename]
            if not os.path.exists(path):
                return
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                data = f.read()
            text_widget.delete('1.0', tk.END)
            text_widget.insert('1.0', data)
            last_mtime_map[path] = os.path.getmtime(path)

        def save_text_from_editor(filename):
            """Save text from text_widget back to disk."""
            if filename not in file_name_to_path:
                return
            path = file_name_to_path[filename]
            try:
                new_data = text_widget.get('1.0', tk.END)
                backup_file(path)  # we can backup before saving
                with open(path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(new_data)
                last_mtime_map[path] = os.path.getmtime(path)
                messagebox.showinfo("Success", f"File saved:\n{path}", parent=root)
                # After saving, re-parse to keep the color fields in sync
                refresh_gui()
            except Exception as e:
                logging.exception("An error occurred while saving text.")
                messagebox.showerror("Error", f"Could not save file:\n{e}", parent=root)

        def watch_file_changes():
            fn = selected_file.get()
            if fn in file_name_to_path:
                path = file_name_to_path[fn]
                if os.path.exists(path) and path in last_mtime_map:
                    current_mtime = os.path.getmtime(path)
                    if current_mtime != last_mtime_map[path]:
                        with open(path, 'r', encoding='utf-8', errors='replace') as f:
                            new_data = f.read()
                        text_widget.delete('1.0', tk.END)
                        text_widget.insert('1.0', new_data)
                        last_mtime_map[path] = current_mtime
                        print("File reloaded due to external change.")

                        # *** Call refresh_gui to re-parse color fields ***
                        refresh_gui()
            root.after(2000, watch_file_changes)


        # Bind the reload/save buttons
        btn_reload_text.config(command=lambda: load_text_into_editor(selected_file.get()))
        btn_save_text.config(command=lambda: save_text_from_editor(selected_file.get()))

        # Process each file and include only those with color fields
        for file_path in vpcf_files:
            file_name = os.path.relpath(file_path, parent_folder)
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
                vpcf_files_new = find_vpcf_files(new_folder)
                if not vpcf_files_new:
                    messagebox.showinfo("No Files Found", "No VPCF files found in the selected folder.", parent=root)
                    return

                config = load_config()
                config["folder_path"] = new_folder
                save_config(config)

                file_name_to_path.clear()
                files_content.clear()
                all_color_fields.clear()
                unique_fields.clear()

                for file_path in vpcf_files_new:
                    fn = os.path.relpath(file_path, new_folder)
                    c = read_file(file_path)
                    cf = find_color_fields(c, fn)
                    if cf:
                        file_name_to_path[fn] = file_path
                        files_content[fn] = c
                        all_color_fields.extend(cf)
                        for field in cf:
                            if field['type'] == 'color':
                                unique_fields[field['raw_name']] = field['field_name']
                    else:
                        logging.info(f"File skipped (no color fields): {fn}")

                if not file_name_to_path:
                    messagebox.showinfo("No Color Fields Found", "No VPCF files with color fields found in the selected folder.", parent=root)
                    return

                populate_listbox()
                load_apply_to_all_fields()
                current_file_index[0] = 0
                on_file_select()

            except Exception as e:
                logging.exception("An error occurred while reloading files.")
                messagebox.showerror("Error", f"An error occurred while reloading files:\n{e}", parent=root)

        def populate_listbox():
            listbox_files.delete(0, END)
            for fn in sorted(file_name_to_path.keys()):
                listbox_files.insert(END, fn)
            if listbox_files.size() > 0:
                listbox_files.select_set(0)
                on_file_select()
            else:
                lbl_current_file.config(text="No file selected.")
                for widget in inner_frame.winfo_children():
                    widget.destroy()
                messagebox.showinfo("No Files", "No VPCF files with color fields are available.", parent=root)

        def filter_files():
            search_text = search_var.get().lower()
            listbox_files.delete(0, END)
            for fn in sorted(file_name_to_path.keys()):
                if search_text in fn.lower():
                    listbox_files.insert(END, fn)
            if listbox_files.size() > 0:
                listbox_files.select_set(0)
                on_file_select()

        def on_file_select(event=None):
            selection = listbox_files.curselection()
            if selection:
                index = selection[0]
                file_name = listbox_files.get(index)
                selected_file.set(file_name)
                current_file_index[0] = index
                logging.info(f"File selected: {file_name}")
                load_vpcf_file(file_name)
                load_text_into_editor(file_name)  # Load into raw text tab as well

        listbox_files.bind('<<ListboxSelect>>', on_file_select)

        def load_vpcf_file(filename):
            nonlocal content, widgets
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

            for widget_ in inner_frame.winfo_children():
                widget_.destroy()
            lbl_current_file.config(text=f"Editing: {filename}")

            if not color_fields:
                Label(inner_frame, text="No color fields found in this file.", anchor='w', fg='red').grid(row=0, column=0, sticky='w', pady=2)
                return

            row = 0
            field_counter = {}
            for idx, field in enumerate(color_fields):
                if field['type'] == 'gradient':
                    display_name = field['field_name']
                else:
                    field_name = field['field_name']
                    field_counter[field_name] = field_counter.get(field_name, 0) + 1
                    display_name = f"{field_name} {field_counter[field_name]}"

                Label(inner_frame, text=display_name, anchor='w').grid(row=row, column=0, sticky='w', pady=2)
                current_color = parse_color_string(field['value'])
                current_color_hex = rgb_to_hex(current_color)
                color_label = Label(inner_frame, text='    ', bg=current_color_hex, relief='groove')
                color_label.grid(row=row, column=1, sticky='w', padx=5)

                def choose_color(idx=idx):
                    old_color = widgets[idx]['new_color']  # This is the parsed color from parse_color_string
                    color = colorchooser.askcolor(parent=root)[0]  # returns (R, G, B) in 0–255 float
                    if color:
                        r, g, b = color
                        # If old_color had 4 channels, keep alpha
                        if len(old_color) == 4:
                            new_c = [int(r), int(g), int(b), old_color[3]]
                        else:
                            # old_color had 3 channels => just do RGB
                            new_c = [int(r), int(g), int(b)]

                        widgets[idx]['new_color'] = new_c

                        # Update the swatch’s background using just RGB
                        hex_color = '#%02x%02x%02x' % (new_c[0], new_c[1], new_c[2])
                        widgets[idx]['color_label'].configure(bg=hex_color)


                choose_button = Button(inner_frame, text='Choose Color', command=choose_color)
                choose_button.grid(row=row, column=2, padx=5, pady=2)

                widgets.append({
                    'color_label': color_label,
                    'new_color': current_color,
                    'field': field,
                })
                row += 1

            inner_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox('all'))

        def load_apply_to_all_fields():
            nonlocal apply_widgets
            apply_widgets.clear()
            for widget_ in apply_inner_frame.winfo_children():
                widget_.destroy()

            row_ = 0
            for raw_name, display_name in sorted(unique_fields.items(), key=lambda x: x[1]):
                Label(apply_inner_frame, text=display_name, anchor='w').grid(row=row_, column=0, sticky='w', pady=2)
                color_label = Label(apply_inner_frame, text='    ', bg='#FFFFFF', relief='groove')
                color_label.grid(row=row_, column=1, sticky='w', padx=5)

                var_apply = IntVar()
                check_apply = Checkbutton(apply_inner_frame, text="Apply", variable=var_apply)
                check_apply.grid(row=row_, column=3, padx=5)

                def choose_color(rn=raw_name, var_apply=var_apply):
                    color = colorchooser.askcolor(parent=root)[0]
                    if color:
                        r, g, b = color
                        hex_color = '#%02x%02x%02x' % (int(r), int(g), int(b))
                        apply_widgets[rn]['new_color'] = [int(r), int(g), int(b)]
                        apply_widgets[rn]['color_label'].configure(bg=hex_color)
                        var_apply.set(1)

                choose_button_ = Button(apply_inner_frame, text='Choose Color', command=choose_color)
                choose_button_.grid(row=row_, column=2, padx=5, pady=2)

                apply_widgets[raw_name] = {
                    'color_label': color_label,
                    'new_color': None,
                    'apply': var_apply,
                    'display_name': display_name,
                }
                row_ += 1

            Label(apply_inner_frame, text="Gradient Editor", anchor='w', font=("Arial", 10, "bold")).grid(row=row_, column=0, sticky='w', pady=5)

            gradient_var_apply = IntVar()
            gradient_check_apply = Checkbutton(apply_inner_frame, text="Apply", variable=gradient_var_apply)
            gradient_check_apply.grid(row=row_, column=3, padx=5)

            gradient_button = Button(apply_inner_frame, text="Edit Gradients", command=lambda: edit_gradients(apply_widgets, gradient_var_apply))
            gradient_button.grid(row=row_, column=2, padx=5, pady=5)

            apply_widgets["gradient_editor"] = {
                "apply": gradient_var_apply,
                "new_color": None,
            }

            apply_inner_frame.update_idletasks()
            apply_canvas.config(scrollregion=apply_canvas.bbox("all"))

        def refresh_gui():
            """Refresh the GUI for the currently loaded file."""
            try:
                filename = selected_file.get()
                if filename:
                    updated_content = read_file(file_name_to_path[filename])
                    files_content[filename] = updated_content
                    nonlocal all_color_fields
                    all_color_fields = [f for f in all_color_fields if f['filename'] != filename]
                    new_fields = find_color_fields(updated_content, filename)
                    all_color_fields.extend(new_fields)
                    load_vpcf_file(filename)
                    logging.info(f"GUI refreshed for file: {filename}")
                else:
                    logging.warning("No file selected to refresh.")
            except Exception as e:
                logging.exception("Error occurred during GUI refresh.")
                messagebox.showerror("Error", f"An error occurred during GUI refresh:\n{e}", parent=root)

        def save_changes():
            try:
                filename = selected_file.get()
                current_content = files_content[filename]
                new_content = current_content

                scalar_replacements = []
                gradient_stop_colors = {}

                # 1) Gather changed fields from the GUI
                for w_ in widgets:
                    field = w_['field']
                    new_color = w_['new_color']

                    if field['type'] == 'color':
                        # Same as before: handle scalar color fields
                        pat = re.compile(
                            re.escape(field['prefix']) + re.escape(field['value']),
                            re.IGNORECASE | re.MULTILINE
                        )
                        scalar_replacements.append((pat, field['prefix'] + color_list_to_string(new_color)))

                    elif field['type'] == 'gradient':
                        # gradient_block_index, stop_index -> [R, G, B, (optional A)]
                        key_ = (field['gradient_block_index'], field['stop_index'])
                        gradient_stop_colors[key_] = new_color

                # 2) Apply scalar replacements first
                for pat, replacement in scalar_replacements:
                    new_content = pat.sub(replacement, new_content, count=1)

                # 3) Rewrite gradient blocks using gradient_pattern
                def replace_gradient_block(m):
                    prefix = m.group(1)
                    stops_body = m.group(2)
                    suffix = m.group(3)

                    nonlocal gradient_block_counter
                    gradient_block_counter += 1
                    current_block_index = gradient_block_counter

                    def replace_stop(stop_m):
                        full_stop_text = stop_m.group(1)
                        # color_str is everything inside m_Color = [ ... ],
                        # e.g. "195,\n   223,\n   255,\n   255,"
                        color_str = stop_m.group(2)

                        stop_key = (current_block_index, replace_stop.stop_index)
                        replace_stop.stop_index += 1

                        # If we don't have a new color for this stop, leave it alone
                        if stop_key not in gradient_stop_colors:
                            return full_stop_text

                        new_rgb = gradient_stop_colors[stop_key]
                        # new_rgb could be 3 elements (RGB) or 4 (RGBA)

                        # We'll replace only the first len(new_rgb) numbers in color_str
                        numbers = re.findall(r'\d+', color_str)
                        updated_str = color_str

                        for i, old_num in enumerate(numbers):
                            if i < len(new_rgb):
                                # Use a word-boundary-based regex to avoid partial merges
                                updated_str = re.sub(
                                    rf'\b{re.escape(old_num)}\b',
                                    str(new_rgb[i]),
                                    updated_str,
                                    count=1
                                )
                            else:
                                # We have more digits in the original array than in new_rgb.
                                # Keep them as-is, do not remove them.
                                break

                        # Reinsert the updated digit string back into the full block text
                        updated_stop_text = full_stop_text.replace(color_str, updated_str, 1)
                        return updated_stop_text

                    replace_stop.stop_index = 0
                    new_stops_body = stop_pattern.sub(replace_stop, stops_body)

                    return prefix + new_stops_body + suffix

                gradient_block_counter = 0
                new_content = gradient_pattern.sub(replace_gradient_block, new_content)

                # 4) Write out final result
                backup_file(file_name_to_path[filename])
                with open(file_name_to_path[filename], 'w', encoding='utf-8') as f:
                    f.write(new_content)

                files_content[filename] = new_content
                logging.info(f"File saved: {filename}")
                messagebox.showinfo("Success", f"Colors updated and file saved:\n{filename}", parent=root)
                refresh_gui()

            except Exception as e:
                logging.exception("An error occurred while saving changes.")
                messagebox.showerror("Error", f"An error occurred while saving changes:\n{e}", parent=root)



        def save_and_compile():
            # Save the file first
            save_changes()
            # Then compile it, which now shows a short message in compile_file()
            if not compiler_path[0]:
                messagebox.showwarning(
                    "Compiler Path Not Set",
                    "Please set the compiler path in Settings > Set Compiler Path.",
                    parent=root
                )
                return
            compile_file()


        def compile_file():
            try:
                file_name = selected_file.get()
                path_ = file_name_to_path[file_name]
                compiler_ = compiler_path[0]

                if not os.path.exists(compiler_):
                    messagebox.showerror(
                        "Compiler Not Found",
                        f"The compiler was not found at:\n{compiler_}",
                        parent=root
                    )
                    return

                # We run the compiler
                result = subprocess.run(
                    [compiler_, path_],
                    check=True,
                    capture_output=True,
                    text=True
                )

                # If it gets here, compilation succeeded
                logging.info(f"Compiled successfully: {path_}")
                # SHORT SUCCESS MESSAGE
                messagebox.showinfo(
                    "Compilation Result",
                    "Compilation completed successfully.",
                    parent=root
                )

            except subprocess.CalledProcessError as e:
                # CalledProcessError is thrown if `check=True` and return code != 0
                # Log the full output for debugging
                logging.exception(f"Compilation failed for {file_name}: {e}")
                # Show a short user-facing message
                messagebox.showerror(
                    "Compilation Error",
                    "An error occurred during compilation.\nSee the log for details.",
                    parent=root
                )

            except Exception as e:
                # Log unexpected exceptions
                logging.exception(f"An unexpected error occurred during compilation of {file_name}")
                messagebox.showerror(
                    "Compilation Error",
                    "An unexpected error occurred.\nSee the log for details.",
                    parent=root
                )


        def compile_all_files():
            if not compiler_path[0]:
                messagebox.showwarning(
                    "Compiler Path Not Set",
                    "Please set the compiler path in Settings > Set Compiler Path.",
                    parent=root
                )
                return

            compiler_ = compiler_path[0]
            failed_files = []
            success_count = 0

            if len(files_content) == 0:
                messagebox.showinfo(
                    "No Files to Compile",
                    "No files available for compilation.",
                    parent=root
                )
                return

            progress_window = tk.Toplevel(root)
            progress_window.title("Compiling Files")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)

            Label(
                progress_window,
                text="Compiling files, please wait...",
                font=("Arial", 12)
            ).pack(pady=10)

            progress_bar = ttk.Progressbar(
                progress_window,
                orient='horizontal',
                mode='determinate',
                length=300
            )
            progress_bar.pack(pady=10)
            progress_bar['maximum'] = len(files_content)

            progress_label = Label(progress_window, text="0 / 0", font=("Arial", 10))
            progress_label.pack()

            root.attributes("-disabled", True)

            def compile_files():
                nonlocal success_count
                try:
                    for index, fn in enumerate(files_content.keys(), start=1):
                        success, stdout_, stderr_ = global_compile_file(fn, file_name_to_path, compiler_)
                        if success:
                            success_count += 1
                        else:
                            failed_files.append(fn)

                        progress_bar['value'] = index
                        progress_label.config(text=f"{index} / {len(files_content)}")
                        progress_window.update()

                    root.attributes("-disabled", False)
                    progress_window.destroy()

                    fail_count = len(failed_files)
                    total = len(files_content)
                    # Show a short summary
                    if fail_count == 0:
                        messagebox.showinfo(
                            "Compilation Result",
                            f"Compiled all {total} files successfully.",
                            parent=root
                        )
                    else:
                        messagebox.showwarning(
                            "Compilation Result",
                            f"Compiled {success_count}/{total} files successfully.\n"
                            f"{fail_count} failed.\nSee log for details.",
                            parent=root
                        )

                except Exception as e:
                    logging.exception("Error during compilation")
                    messagebox.showerror(
                        "Error",
                        f"An error occurred during compilation.\nSee log for details.",
                        parent=root
                    )
                    root.attributes("-disabled", False)
                    progress_window.destroy()

            from threading import Thread
            compile_thread = Thread(target=compile_files)
            compile_thread.start()


        def set_compiler_path():
            path_ = filedialog.askopenfilename(title="Select Compiler Executable", parent=root)
            if path_:
                # 1) Set the global compiler_path
                compiler_path[0] = path_

                # 2) Persist to config.json
                config = load_config()  # read current config from file
                config["compiler_path"] = path_  # update or add the key
                save_config(config)     # write it back

                messagebox.showinfo("Compiler Path Set", f"Compiler path set to:\n{path_}", parent=root)


        def apply_to_all():
            try:
                fields_to_apply = {
                    fn: w_['new_color']
                    for fn, w_ in apply_widgets.items()
                    if fn != "gradient_editor" and w_['apply'].get() and w_['new_color'] is not None
                }
                gradients_to_apply = (
                    apply_widgets["gradient_editor"]["new_color"]
                    if apply_widgets["gradient_editor"]["apply"].get() else None
                )
                if not fields_to_apply and not gradients_to_apply:
                    messagebox.showinfo("No Changes", "No fields selected for applying changes.", parent=root)
                    return

                modified_files = set()
                for fn, c_ in files_content.items():
                    new_c = c_
                    for raw_name, col_ in fields_to_apply.items():
                        col_str = color_list_to_string(col_)
                        pat = re.compile(
                            rf'(\b{re.escape(raw_name)}\s*=\s*)(\[[^\]]*\])',
                            re.IGNORECASE | re.MULTILINE
                        )
                        new_c = re.sub(
                            pat,
                            lambda m: m.group(1) + col_str,
                            new_c
                        )
                    if gradients_to_apply:
                        new_c = replace_gradient_blocks(new_c, gradients_to_apply)

                    if c_ != new_c:
                        backup_file(file_name_to_path[fn])
                        with open(file_name_to_path[fn], 'w') as f:
                            f.write(new_c)
                        files_content[fn] = new_c
                        modified_files.add(fn)

                nonlocal all_color_fields
                for fn in modified_files:
                    all_color_fields = [f for f in all_color_fields if f['filename'] != fn]
                    updated_c = files_content[fn]
                    updated_fields = find_color_fields(updated_c, fn)
                    all_color_fields.extend(updated_fields)

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

                gradient_stop_pattern = re.compile(
                    r'(\s*\{.*?m_flPosition\s*=\s*[\d\.]+.*?m_Color\s*=\s*(\[[^\]]*\]|\[.*?\])\s*\}[\s,]*)',
                    re.DOTALL
                )
                stops = gradient_stop_pattern.findall(gradient_block_content)
                stop_formats = [full_stop for (full_stop, color_array) in stops]

                num_new_stops = len(gradients_to_apply)
                new_stops = []

                for i in range(num_new_stops):
                    position = i / (num_new_stops - 1) if num_new_stops > 1 else 0.0
                    position_str = f"{position:.6f}"
                    if i < len(stop_formats):
                        existing_stop = stop_formats[i]
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
                        last_stop = stop_formats[-1]
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

                new_gradient_block_content = ''.join(new_stops)
                return prefix + new_gradient_block_content + suffix

            return gradient_pattern.sub(replace_gradient_block, content)

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

        # Buttons under the color editor
        frame_buttons = tk.Frame(editor_frame)
        frame_buttons.grid(row=2, column=0, pady=5, sticky='ew')
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

        # Menu bar
        menubar = Menu(root)
        root.config(menu=menubar)

        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Set Compiler Path", command=lambda: set_compiler_path())
        settings_menu.add_command(label="Change Folder", command=lambda: change_folder())
        settings_menu.add_command(label="Toggle Dark Mode", command=lambda: toggle_dark_mode())

        about_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=about_menu)
        about_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", f"VPCF Color Editor {VERSION}\n{CREDIT}"))
        about_menu.add_command(label="Check for Updates", command=lambda: check_for_updates_async(user_initiated=True))

        def toggle_dark_mode():
            global current_theme
            current_theme = "dark" if current_theme == "light" else "light"
            theme_ = themes[current_theme]
            apply_theme(root, theme_)
            save_theme_preference()

        def apply_theme(widget, theme_):
            widget_type = widget.winfo_class()
            try:
                widget.config(bg=theme_["bg"])
                if widget_type in ["Label", "Button", "Entry", "Listbox", "Checkbutton", "Menubutton"]:
                    widget.config(fg=theme_["fg"], bg=theme_["bg"])
                elif widget_type == "Canvas":
                    widget.config(bg=theme_["bg"], highlightbackground=theme_["bg"])
                elif widget_type == "Scrollbar":
                    widget.config(
                        bg=theme_["bg"],
                        troughcolor=theme_["bg"],
                        activebackground=theme_["highlight_bg"],
                        highlightbackground=theme_["bg"],
                        highlightcolor=theme_["bg"]
                    )
                elif widget_type == "Entry":
                    widget.config(
                        fg=theme_["fg"],
                        bg=theme_["bg"],
                        insertbackground=theme_["fg"],
                        highlightbackground=theme_["bg"]
                    )
                elif widget_type == "Listbox":
                    widget.config(
                        bg=theme_["bg"], fg=theme_["fg"],
                        selectbackground=theme_["highlight_bg"], selectforeground=theme_["highlight_fg"],
                        highlightbackground=theme_["bg"]
                    )
                elif widget_type == "Text":
                    widget.config(
                        fg=theme_["fg"],
                        bg=theme_["bg"],
                        insertbackground=theme_["fg"],
                        selectbackground=theme_["highlight_bg"],
                        selectforeground=theme_["highlight_fg"],
                        highlightbackground=theme_["bg"]
                    )
                elif widget_type == "Menu":
                    widget.config(
                        bg=theme_["bg"],
                        fg=theme_["fg"],
                        activebackground=theme_["highlight_bg"],
                        activeforeground=theme_["highlight_fg"]
                    )
                elif widget_type == "Frame":
                    widget.config(bg=theme_["bg"])
                elif widget_type == "Toplevel":
                    widget.config(bg=theme_["bg"])
            except Exception as e:
                logging.warning(f"Theme application skipped for {widget_type}: {e}")

            for child in widget.winfo_children():
                apply_theme(child, theme_)

        def save_theme_preference():
            config = load_config()
            config["theme"] = current_theme
            save_config(config)

        def load_theme_preference():
            config = load_config()
            return config.get("theme", "light")

        current_theme = load_theme_preference()
        apply_theme(root, themes[current_theme])

        # Start update check
        check_for_updates_async()

        populate_listbox()
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

         # 1) Restore the compiler path if it exists in config
        if "compiler_path" in config:
            compiler_path[0] = config["compiler_path"]
        else:
            compiler_path[0] = None

        # 2) Restore the folder path if it exists
        if "folder_path" in config:
            folder_path[0] = config["folder_path"]
        else:
            folder_path[0] = None

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
            config["folder_path"] = folder_path[0]
            save_config(config)

        logging.info(f"Selected folder: {folder_path[0]}")
        vpcf_files = find_vpcf_files(folder_path[0])
        if not vpcf_files:
            messagebox.showinfo("No Files Found", "No VPCF files found in the selected folder.", parent=root)
            root.destroy()
            sys.exit("No VPCF files found.")

        show_gui(root, vpcf_files, folder_path[0])

    except Exception as e:
        logging.exception("An error occurred in the main function.")
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}\nPlease check the log file for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
