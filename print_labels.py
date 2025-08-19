import win32print
import win32ui
from PIL import Image, ImageDraw, ImageFont, ImageWin
import io
import barcode
from barcode.writer import ImageWriter

# ===== Test drawing =====
def draw_test_border(draw, w, h, color="red", thickness=2):
    draw.rectangle([0, 0, w - 1, h - 1], outline=color, width=thickness)

def draw_test_grid(draw, w, h, grid=50, color="lightgray"):
    for x in range(0, w, grid):
        draw.line([x, 0, x, h], fill=color)
    for y in range(0, h, grid):
        draw.line([0, y, w, y], fill=color)

def draw_test_center(draw, w, h, color="green"):
    draw.line([w // 2, 0, w // 2, h], fill=color)
    draw.line([0, h // 2, w, h // 2], fill=color)

def create_test_label(w, h, dpi=300, step=20):
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    
    draw_test_grid(draw, w, h, grid=step)
    draw_test_center(draw, w, h)
    draw_test_border(draw, w, h)

    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()

    # Подписываем координаты на сетке
    for x in range(0, w, step):
        draw.text((x+2,2), str(x), fill="blue", font=font)
    for y in range(0, h, step):
        draw.text((2,y+2), str(y), fill="green", font=font)
    
    return img

# ===== Printer helpers =====
def get_printer_area(printer_name="TSC TE300"):
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)
    w = hdc.GetDeviceCaps(110)  # HORZRES
    h = hdc.GetDeviceCaps(111)  # VERTRES
    hdc.DeleteDC()
    return w, h

def print_label_scaled(image, printer_name="TSC TE300", real_w=440, real_h=260):
    # Масштабируем изображение под реально печатаемую область
    image_scaled = image.resize((real_w, real_h))
    
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)
    
    hdc.StartDoc("Label Print Job")
    hdc.StartPage()
    
    dib = ImageWin.Dib(image_scaled)
    # Сдвигаем вправо на 10 пикселей, чтобы левая граница была видна
    dib.draw(hdc.GetHandleOutput(), (8, 0, real_w + 8, real_h))
    
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


if __name__ == "__main__":
    printer_name = "TSC TE300"
    dpi = 300
    
    # --- Реальная область печати (увеличена по горизонтали на 10 пикселей) ---
    real_print_w = 440  # было 430, стало 440 (+10 пикселей)
    real_print_h = 260
    print(f"Real printable area: {real_print_w}x{real_print_h}px")
    
    # --- Тестовая метка с сеткой и координатами ---
    test_label = create_test_label(490, 300, step=20)  # создаём в "расчётных пикселях" (ширина увеличена с 480 до 490)
    test_label.save("test_label_scaled.png", dpi=(dpi,dpi))
    print_label_scaled(test_label, printer_name, real_print_w, real_print_h)
    
    # --- Основная этикетка с текстом и штрихкодом ---
    # label = Image.new("RGB", (490, 300), "white")  # ширина увеличена с 480 до 490
    # draw = ImageDraw.Draw(label)

    # try:
    #     font = ImageFont.truetype("arial.ttf", 18)
    # except:
    #     font = ImageFont.load_default()

    # Текст
    # draw.text((10, 10), "Product A", fill="black", font=font)
    # draw.text((10, 40), "SKU: 123456", fill="black", font=font)

    # Штрихкод
    # barcode_value = "4006381333931"
    # code128 = barcode.Code128(barcode_value, writer=ImageWriter())
    # buf = io.BytesIO()
    # code128.write(buf, {"module_width": 0.2, "module_height": 15.0, "font_size": 10})
    # barcode_img = Image.open(buf)
    # label.paste(barcode_img, (10, 70))

    # label.save("label_scaled.png", dpi=(dpi,dpi))
    # print_label_scaled(label, printer_name, real_print_w, real_print_h)