import pygame
import tkinter as tk
from tkinter import ttk

def update_joystick_state():
    pygame.event.pump()

    # Get axes
    axes_values = [f"Axis {i}: {js.get_axis(i):.2f}" for i in range(js.get_numaxes())]
    axes_label.config(text="\n".join(axes_values))

    # Get buttons
    buttons_values = [f"Button {i}: {js.get_button(i)}" for i in range(js.get_numbuttons())]
    buttons_label.config(text="\n".join(buttons_values))

    # Get hats
    hats_values = [f"Hat {i}: {js.get_hat(i)}" for i in range(js.get_numhats())]
    hats_label.config(text="\n".join(hats_values))

    root.after(100, update_joystick_state)  # update every 100 ms

# Initialize pygame joystick
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise RuntimeError("No joystick found.")

js = pygame.joystick.Joystick(0)
js.init()

# Tkinter GUI setup
root = tk.Tk()
root.title("Xbox Controller State")

frame = ttk.Frame(root, padding=10)
frame.grid(row=0, column=0)

axes_label = ttk.Label(frame, text="Axes", justify="left", font=("Courier", 12))
axes_label.grid(row=0, column=0, padx=10, pady=5)

buttons_label = ttk.Label(frame, text="Buttons", justify="left", font=("Courier", 12))
buttons_label.grid(row=0, column=1, padx=10, pady=5)

hats_label = ttk.Label(frame, text="Hats", justify="left", font=("Courier", 12))
hats_label.grid(row=0, column=2, padx=10, pady=5)

update_joystick_state()
root.mainloop()
