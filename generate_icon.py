from PIL import Image, ImageDraw

# 创建 256x256 图标
img = Image.new('RGB', (256, 256), color=(30, 60, 114))  # 深蓝色背景
draw = ImageDraw.Draw(img)

# 绘制盾牌形状
points = [(128, 20), (220, 60), (220, 140), (128, 220), (36, 140), (36, 60)]
draw.polygon(points, fill=(64, 156, 255), outline=(255, 255, 255), width=3)

# 绘制时间符号
draw.ellipse((88, 100, 168, 180), outline=(255, 255, 255), width=4)
draw.line((128, 140, 128, 110), fill=(255, 255, 255), width=3)  # 时针
draw.line((128, 140, 155, 140), fill=(255, 255, 255), width=3)  # 分针

# 保存为 PNG（用于转换 ICO）
img.save('icon.png')
print("icon.png created!")
