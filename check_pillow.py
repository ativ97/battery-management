try:
    from PIL import Image, ImageDraw
    print("Pillow is installed")
except ImportError:
    print("Pillow is NOT installed")