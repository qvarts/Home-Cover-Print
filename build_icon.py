
"""Write the Windows ICO from the bundled SVG master."""

from pathlib import Path
from PIL import Image
from PySide6 import QtGui, QtWidgets

def create_ico():
    app = QtWidgets.QApplication([])
    source = Path(__file__).with_name("home_cover_print.svg")
    
    # Use QImage to render the SVG at a high resolution initially
    # to avoid blurriness when resizing.
    # 256x256 is the standard maximum for ICO.
    image = QtGui.QImage(str(source))
    if image.isNull():
        raise RuntimeError(f"Could not read application icon: {source}")
    
    # Scale the SVG to a high-quality raster image (256x256)
    # We use smooth transformation for better quality.
    scaled_image = image.scaled(256, 256, QtGui.Qt.AspectRatioMode.KeepAspectRatio, QtGui.Qt.TransformationMode.SmoothTransformation)
    
    # Convert QImage to PIL Image
    # QImage format is typically ARGB32 or RGB32.
    # We convert it to a format PIL understands.
    ptr = scaled_image.bits()
    # QImage.bits() returns a pointer. We need to convert it to bytes.
    # A simpler way to bridge QImage and PIL is saving to a buffer or a temporary PNG.
    temp_png = Path(__file__).with_name("temp_icon.png")
    scaled_image.save(str(temp_png), "PNG")
    
    pil_image = Image.open(temp_png)
    pil_image.load() # Load image data into memory
    temp_png.unlink()
    
    output = Path(__file__).with_name("home_cover_print.ico")
    
    # ICO files can contain multiple sizes.
    # Common sizes: 16, 32, 48, 64, 128, 256
    sizes = [16, 32, 48, 64, 128, 256]
    
    # Save as a multi-resolution ICO file using Pillow
    pil_image.save(
        output,
        format="ICO",
        sizes=[(s, s) for s in sizes]
    )

if __name__ == "__main__":
    create_ico()
