import tkinter as tk
from PIL import ImageTk, Image
import requests


def get_data(city):

    api_key = "YOUR API KEY HERE"
    url = "https://api.openweathermap.org/data/2.5/weather/"
    arguments = {"APPID": api_key, "q": city, "units": "imperial"}
    data = requests.get(url, params=arguments).json()
    image_type = 'default.jpg'

    try:

        name = data['name']
        desc = data['weather'][0]['description']
        temp = data['main']['temp']
        wind = data['wind']['speed']
        feels_like = data['main']['feels_like']
        full_string = 'Location: {} \n Conditions: {} \n' 'Temperature (F): {} \n Wind (MPH): {} \n ' \
                      'Feels Like (F): {}'.format(
                          name, desc, temp, wind, feels_like)

        image_type = get_image_type(desc)

    except:
        full_string = "No matching location found. \n Please check location and try again."

    label['text'] = full_string

    new_image = ImageTk.PhotoImage(Image.open(image_type))
    background_label.configure(image=new_image)
    background_label.image = new_image


def get_image_type(description):
    if "rain" in description:
        image_type = "rain.jpg"
    elif "snow" in description:
        image_type = "snow.jpg"
    else:
        image_type = "sunny.jpg"
    return image_type


# Tkinter frames and canvas
# declare the root window
root = tk.Tk()

# Static height and width variables
w = 700
h = 800

# container is a location within the root window
canvas = tk.Canvas(root, height=h, width=w)
canvas.pack()

background_image = tk.PhotoImage()
background_label = tk.Label(root, image=background_image)
background_label.place(relwidth=1, relheight=1)

# frames used to hold processes/widgets
# pass in hex values
frame = tk.Frame(root, bg="#cc2929", bd=8)
# can set relative width and height
frame.place(relx=0.5, rely=0.1, relwidth=0.75, relheight=0.1, anchor="n")

# can create multiple frames
frame_2 = tk.Frame(root, bg="#cc2929", bd=10)
frame_2.place(relx=0.5, rely=0.25, relwidth=0.75, relheight=0.6, anchor="n")

# Create and place interactive elements
entry = tk.Entry(frame, font=('Arial', 22))
entry.place(relwidth=0.65, relheight=1)

label = tk.Label(frame_2, font=('Arial', 22))
label.place(relwidth=1, relheight=1)

# use the lambda function to properly update values in tkinter function calls
button = tk.Button(frame, text="What's The Weather?", fg='blue', font=('Arial', 10),
                   command=lambda: get_data(entry.get()))
button.place(relx=0.7, relwidth=0.3, relheight=1)

# calls the construction of the Tkinter window
root.mainloop()
