from PIL import Image, ImageDraw

def create_icon(size):
    img = Image.new('RGB', (size, size), color='#ed1c24')
    d = ImageDraw.Draw(img)
    # Draw a simple battery shape
    margin = size // 4
    d.rectangle([margin, margin, size - margin, size - margin], fill='white')
    # Save
    img.save(f'static/icon-{size}.png')

if __name__ == "__main__":
    create_icon(192)
    create_icon(512)
    print("Icons generated.")