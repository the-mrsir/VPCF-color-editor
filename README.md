VPCF Color Editor
VPCF Color Editor is a Python-based tool designed for batch editing and managing gradient and scalar color fields in .vpcf (Valve Particle File) files. The tool provides a user-friendly graphical interface for editing gradient stops, scalar fields, and other visual properties while preserving the original file structure and formatting.

Features
Batch Editing:
Modify gradient stops and scalar color fields across multiple .vpcf files at once.
Gradient Editor:
Dynamically add, remove, or edit gradient stops with customizable start and end colors.
Preserve Formatting:
Retain the original structure and indentation of .vpcf files during edits.
File Management:
Search for .vpcf files in a folder and reload updated content.
Backup System:
Automatically creates .bak backups of files before saving changes.
Dark Mode:
Toggle between light and dark themes for comfortable usage.
Requirements
Python Version: 3.7 or newer
Dependencies:
tkinter (for GUI)
logging (for error and process tracking)
subprocess (for compilation support)
re (for pattern matching in .vpcf files)
Installation
Clone the Repository:

bash
Copy code
git clone https://github.com/the-mrsir/VPCF-color-editor.git
cd VPCF-color-editor
Install Python Requirements: This project uses standard Python libraries, so no additional installation is needed.

Run the Program:

bash
Copy code
python vpcf_color_editor.py
Usage
Launch the Program:

Run vpcf_color_editor.py in Python.
Select a Folder:

Choose a folder containing .vpcf files to edit. The program will automatically find and load .vpcf files with editable color fields.
Edit Colors:

Use the UI to modify gradient stops or scalar color fields.
Apply Changes:

Save changes to individual files or batch-apply changes to all loaded files.
Compile Files (Optional):

If a compiler path is set, you can compile .vpcf files directly from the tool.
Screenshots
Main Interface:
(Add a screenshot of the main interface here)

Gradient Editor:
(Add a screenshot of the gradient editor here)

Configuration
The tool uses a config.json file to store user preferences, such as the last selected folder and compiler path.

Configuration File Example:

json
Copy code
{
    "folder_path": "path/to/your/vpcf/files",
    "compiler_path": "path/to/compiler.exe",
    "theme": "dark"
}
You can set or update these settings through the GUI.

Contributing
We welcome contributions to enhance the VPCF Color Editor. If you have ideas or find bugs, please open an issue or submit a pull request.

Steps to Contribute:
Fork the repository.
Create a new branch for your feature or bug fix.
Submit a pull request with a detailed explanation of your changes.
License
This project is licensed under the MIT License. You are free to use, modify, and distribute this software.

Contact
Developer: MrSir
Email: wgbennett99@gmail.com
GitHub Repository: VPCF Color Editor
Let me know if there’s anything else you’d like to add or adjust!






You said:
installation- just download the file as well and run it, no? also, tkinker is in py 3.0+, right, so only py 3.0+ is required
ChatGPT said:
ChatGPT
You're absolutely correct! The installation section can be simplified since users can just download the script directly, and tkinter is included with Python 3.0+. Here's the revised README.md:

VPCF Color Editor
VPCF Color Editor is a Python-based tool designed for batch editing and managing gradient and scalar color fields in .vpcf (Valve Particle File) files. The tool provides a user-friendly graphical interface for editing gradient stops, scalar fields, and other visual properties while preserving the original file structure and formatting.

Features
Batch Editing:
Modify gradient stops and scalar color fields across multiple .vpcf files at once.
Gradient Editor:
Dynamically add, remove, or edit gradient stops with customizable start and end colors.
Preserve Formatting:
Retain the original structure and indentation of .vpcf files during edits.
File Management:
Search for .vpcf files in a folder and reload updated content.
Backup System:
Automatically creates .bak backups of files before saving changes.
Dark Mode:
Toggle between light and dark themes for comfortable usage.
Requirements
Python Version: 3.0 or newer (includes tkinter by default)
Installation
Download the File:

Download the vpcf_color_editor.py file from the repository.
Run the Program:

Open a terminal or command prompt.

Navigate to the folder containing vpcf_color_editor.py.

Run the program using:

bash
Copy code
python vpcf_color_editor.py
Usage
Launch the Program:

Run vpcf_color_editor.py in Python.
Select a Folder:

Choose a folder containing .vpcf files to edit. The program will automatically find and load .vpcf files with editable color fields.
Edit Colors:

Use the UI to modify gradient stops or scalar color fields.
Apply Changes:

Save changes to individual files or batch-apply changes to all loaded files.
Compile Files (Optional):

If a compiler path is set, you can compile .vpcf files directly from the tool.
Screenshots
Main Interface:
(Add a screenshot of the main interface here)

Gradient Editor:
(Add a screenshot of the gradient editor here)

Configuration
The tool uses a config.json file to store user preferences, such as the last selected folder and compiler path.

Configuration File Example:

json
Copy code
{
    "folder_path": "path/to/your/vpcf/files",
    "compiler_path": "path/to/compiler.exe",
    "theme": "dark"
}
These are also automatically set on startup and can be editied in the Gui.

Contributing
We welcome contributions to enhance the VPCF Color Editor. If you have ideas or find bugs, please open an issue or submit a pull request.

Steps to Contribute:
Fork the repository.
Create a new branch for your feature or bug fix.
Submit a pull request with a detailed explanation of your changes.
License
This project is licensed under the MIT License. You are free to use, modify, and distribute this software.

Contact
Developer: MrSir
Email: wgbennett99@gmail.com
GitHub Repository: VPCF Color Editor
Let me know if you’d like additional edits!
