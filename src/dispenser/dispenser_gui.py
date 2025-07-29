"""GUI for chip dispenser."""

import logging
import threading
import tkinter as tk
from tkinter import ttk

from .dispenser_core import ALLOWED_TRANSITIONS, Dispenser, DispenserState


class DispenserFrame(ttk.Frame):
    def __init__(self, parent, dispenser: Dispenser, title: str):
        super().__init__(parent)
        self.dispenser = dispenser
        self.color_map = {
            "OFF": "gray",
            "ON": "gold",
            "IDLE": "green",
            "DISPENSING": "dodger blue",
            "LOADING": "cyan",
            "ERROR": "red",
        }

        # Title
        ttk.Label(self, text=title, font=("Arial", 18, "bold")).pack(pady=5)

        self.chip_label = tk.Label(self, text="Chips: 0", font=("Arial", 16))
        self.chip_label.pack()

        self.state_label = tk.Label(self, text="State: OFF", font=("Arial", 16))
        self.state_label.pack()

        # Quantity entry
        qty_frame = ttk.Frame(self)
        qty_frame.pack(pady=5)
        ttk.Label(qty_frame, text="Quantity:").pack(side=tk.LEFT, padx=5)
        self.qty_entry = ttk.Entry(qty_frame, width=8)
        self.qty_entry.pack(side=tk.LEFT)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        self.btn_dispense = ttk.Button(
            btn_frame, text="Dispense", command=self.on_dispense
        )
        self.btn_dispense.grid(row=0, column=0, padx=5)

        self.btn_load = ttk.Button(btn_frame, text="Load", command=self.on_load)
        self.btn_load.grid(row=0, column=1, padx=5)

        self.btn_home = ttk.Button(btn_frame, text="Home", command=self.on_home)
        self.btn_home.grid(row=0, column=2, padx=5)

        self.btn_init = ttk.Button(
            btn_frame, text="Initialize", command=self.on_initialize
        )
        self.btn_init.grid(row=0, column=3, padx=5)

        self.after(100, self.update_gui)

    # ---------- Utility ----------
    def run_in_thread(self, func):
        threading.Thread(target=func, daemon=True).start()

    # ---------- Button Callbacks ----------
    def on_dispense(self):
        try:
            qty = int(self.qty_entry.get())
        except ValueError:
            logging.warning("Invalid dispense quantity.")
            return

        if qty <= self.dispenser.chip_count:
            self.run_in_thread(lambda: self.dispenser.dispense(qty))
            logging.info("Dispensed %d chips", qty)
            self.qty_entry.delete(0, tk.END)
        else:
            logging.warning(
                "Only %d chips available, please load more", self.dispenser.chip_count
            )

    def on_load(self):
        try:
            qty = int(self.qty_entry.get())
        except ValueError:
            logging.warning("Invalid load quantity")
            return
        self.run_in_thread(lambda: self.dispenser.load(qty))
        logging.info("Loading %d chips...", qty)
        self.qty_entry.delete(0, tk.END)

    def on_home(self):
        self.run_in_thread(self.dispenser.home)
        logging.info("Homing initiated")

    def on_initialize(self):
        self.run_in_thread(self.dispenser.initialize_motor)
        logging.info("Motor initialization started")

    # ---------- GUI Updater ----------
    def update_gui(self):
        self.chip_label.config(text=f"Chips: {self.dispenser.get_chip_count()}")
        state = self.dispenser.get_state()
        self.state_label.config(text=f"State: {state.name}")
        self.state_label.config(foreground=self.color_map.get(state.name, "black"))

        allowed = ALLOWED_TRANSITIONS.get(state, [])
        self.btn_dispense.config(
            state="normal" if DispenserState.DISPENSING in allowed else "disabled"
        )
        self.btn_load.config(
            state="normal" if DispenserState.LOADING in allowed else "disabled"
        )
        self.btn_home.config(
            state="normal" if DispenserState.HOMING in allowed else "disabled"
        )
        self.btn_init.config(
            state="normal" if DispenserState.ON in allowed else "disabled"
        )

        self.after(100, self.update_gui)


def start_gui(disp1: Dispenser, disp2: Dispenser):
    root = tk.Tk()
    root.title("Dual Dispenser Control Panel")

    style = ttk.Style()
    style.configure("TButton", font=("Avenir", 14))
    style.configure("TLabel", font=("Avenir", 14))

    # Two Dispensers Side by Side
    frame1 = DispenserFrame(root, disp1, "Dispenser 20")
    frame1.grid(row=0, column=0, padx=20, pady=10)

    frame2 = DispenserFrame(root, disp2, "Dispenser 21")
    frame2.grid(row=0, column=1, padx=20, pady=10)

    ttk.Button(root, text="Quit", command=root.destroy).grid(
        row=1, column=0, columnspan=2, pady=15
    )

    root.mainloop()


if __name__ == "__main__":
    dispenser1: Dispenser = ...
    dispenser2: Dispenser = ...
    start_gui(dispenser1, dispenser2)
