from PIL import Image
import os

image_obj = Image.open('image1.jpg')
image_obj.show()

image_obj.save('image1.png')

for file in os.listdir('.'):
    # If the file ends with .jpg, open the file, split the file on extension (using splitext) to get file name
    # Then save as .png using file name
    if file.endswith('.jpg'):
        file = Image.open(file)
        file_name, file_extension = os.path.splitext(file)
        file.save('{}.png'.format(file_name))

size_params = (400, 400)
image_obj.thumbnail(size_params)
image_obj.save('image1.png')
