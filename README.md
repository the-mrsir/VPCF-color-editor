# **VPCF Color Editor**  
[![Python](https://img.shields.io/badge/Python-3.0%2B-blue.svg)](https://www.python.org/)  
Batch edit gradients and scalar color fields in `.vpcf` files with ease!  

---

## **Overview**  

VPCF Color Editor is a Python-based tool for editing gradient and scalar color fields in `.vpcf` (Valve Particle File) files. With its user-friendly graphical interface, you can efficiently modify visual properties while preserving the original formatting and structure.  

---

## **Features**  

✅ **Batch Editing:** Modify gradient stops and scalar color fields across multiple files simultaneously.  
✅ **Gradient Editor:** Add, remove, or edit gradient stops with full customization.  
✅ **Preserve Formatting:** Retain the exact structure and indentation of `.vpcf` files.  
✅ **File Management:** Search and reload files from your working directory.  
✅ **Backup System:** Automatically creates `.bak` backups for safe editing.  
✅ **Dark Mode:** Switch between light and dark themes for comfort.  

---

## **Installation**  

### Requirements  

- **Python 3.0+**  
  - Includes `tkinter` (used for the graphical interface).  

### Steps  

1. **Download the Script**  
   - Download [`vpcf_color_editor.py`](https://github.com/the-mrsir/VPCF-color-editor) from this repository.  

2. **Run the Program**  
   - Open a terminal or command prompt.  
   - Navigate to the folder containing `vpcf_color_editor.py`.  
   - Execute:  

     ```bash
     python vpcf_color_editor.py
     ```  

---

## **Usage**  

### 1. **Launch the Program**  
- Run `vpcf_color_editor.py` to open the application.  

### 2. **Select a Folder**  
- Choose a folder containing `.vpcf` files. The program will automatically detect and load files with editable color fields.  

### 3. **Edit Colors**  
- Use the graphical interface to:  
  - Modify gradient stops.  
  - Adjust scalar color fields.  

### 4. **Apply Changes**  
- Save updates to individual files or apply them to all files in the folder.  

### 5. **Compile Files (Optional)**  
- Set a compiler path in the settings to compile `.vpcf` files directly from the tool.  
 

---

## **Configuration**  

The tool uses a `config.json` file to save user preferences, such as the last selected folder and compiler path.  

### Example Configuration  

```json
{
    "folder_path": "path/to/your/vpcf/files",
    "compiler_path": "path/to/compiler.exe",
    "theme": "dark"
}
```
You can edit these settings directly in the application.

---

## **Contributing**  

Contributions are welcome! If you'd like to enhance the tool, fix bugs, or add features:  

1. Fork this repository.  
2. Create a new branch (`feature-your-feature` or `bugfix-your-fix`).  
3. Submit a pull request with a detailed explanation of your changes.  

---

## **License**  

This project is licensed under the [MIT License](LICENSE).  

---

## **Contact**  

- **Developer:** [MrSir](https://github.com/the-mrsir)  
- **Email:** wgbennett99@gmail.com  
- **GitHub Repository:** [VPCF Color Editor](https://github.com/the-mrsir/VPCF-color-editor)  

---

### **How to Improve This Project?**  
If you have suggestions, feel free to open an [issue](https://github.com/the-mrsir/VPCF-color-editor/issues) or contact me directly!  
