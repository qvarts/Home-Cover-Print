# Home Cover Print

**Home Cover Print** is a free and open-source tool for preparing jewel case inlays and cassette inserts for printing. It allows you to arrange images and text on a canvas with predefined physical dimensions to ensure they fit the physical cases.

<br>

## ✨ Features

- **📐 Predefined Templates**: Layouts for common formats:
  - **Jewel & Slim Cases**: Front covers, booklets, and back inlays.
  - **Cassette Tapes**: Front covers and booklets.
- **🎨 Basic Editing**:
  - **Images**: Import, scale, rotate, and move images.
  - **Text**: Add and edit text blocks with custom fonts and colors.
  - **Backgrounds**: Support for "Cover", "Contain", and "Stretch" modes.
- **🎯 Layout Guides**: 
  - Visual indicators for fold and cut lines.
  - Basic snapping to help align elements to guides.
- **📄 PDF Export**: Export your layout to a PDF file for printing.
- **🖨️ Direct Print**: Print your layout directly with a print preview.

<br>

## 🚀 Getting Started

### Prerequisites
- Python 3.10+

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/qvarts/Home-Cover-Print.git
   cd Home-Cover-Print
   ```
2. Set up a virtual environment (recommended):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

<br>

## 🛠 Building the Application (.exe)

You can easily compile the application into a standalone executable using the provided build script.

### Prerequisites
- **Python 3.10+** must be installed and added to your system **PATH**.

### How to Build
1. Open the project root directory.
2. Run the build process:
   - **Via Batch file**: Double-click `build.bat` (recommended for most users).
   - **Via PowerShell**: Run `.\build.ps1` in the terminal.

### What the build script does:
- **Environment**: Automatically creates a virtual environment (`.venv`) if it doesn't exist.
- **Dependencies**: Installs all required packages, including `PySide6` and `PyInstaller`.
- **Assets**: Generates required application assets, including the executable icon.
- **Compilation**: Compiles the application into a single `.exe` file located in the `dist/` folder.

<br>

## 🤝 Support

If you encounter any issues or have suggestions for improvement, please open an issue in the [GitHub Issues](https://github.com/qvarts/Home-Cover-Print/issues) section.

<br>

## ☕ Donate
If you find this tool useful and it saved you some time, feel free to support its development with a coffee:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://ko-fi.com/G7S128CUA5)

<br>

## 📜 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [LICENSE](./LICENSE) file for details.

---
*Created by Vitaliy Kolobanov*
