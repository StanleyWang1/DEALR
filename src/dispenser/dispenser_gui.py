import logging
import threading
import tkinter as tk
from tkinter import ttk

from .dispenser_core import ALLOWED_TRANSITIONS, Dispenser, DispenserState


def start_gui(dispenser: Dispenser):
    """Launch a GUI to control the dispenser."""

    def update_gui():
        chip_label.config(text=f"Chips: {dispenser.chip_count}")
        state_label.config(text=f"State: {dispenser.state.name}")

        # ✅ Enable/disable buttons based on valid transitions
        state = dispenser.state
        allowed = ALLOWED_TRANSITIONS.get(state, [])

        btn_dispense.config(
            state=("normal" if DispenserState.DISPENSING in allowed else "disabled")
        )
        btn_load.config(
            state=("normal" if DispenserState.LOADING in allowed else "disabled")
        )
        btn_home.config(
            state=("normal" if DispenserState.HOMING in allowed else "disabled")
        )
        btn_init.config(
            state=("normal" if DispenserState.ON in allowed else "disabled")
        )

        root.after(100, update_gui)

    def run_in_thread(func):
        threading.Thread(target=func, daemon=True).start()

    def on_dispense():
        try:
            qty = int(qty_entry.get())
        except ValueError:
            logging.warning("Invalid dispense quantity.")
            return

        if qty <= dispenser.chip_count:
            run_in_thread(lambda: dispenser.dispense(qty))
            logging.info(f"Dispensed {qty} chips.")
            qty_entry.delete(0, tk.END)  # ✅ Clear entry after success
        else:
            logging.warning(
                f"Only {dispenser.chip_count} chips available. Please load more."
            )

    def on_load():
        try:
            qty = int(qty_entry.get())
        except ValueError:
            logging.warning("Invalid load quantity.")
            return

        run_in_thread(lambda: dispenser.load(qty))
        logging.info(f"Loading {qty} chips...")
        qty_entry.delete(0, tk.END)  # ✅ Clear entry after success

    def on_home():
        run_in_thread(dispenser.home)
        logging.info("Homing initiated.")

    def on_initialize():
        run_in_thread(dispenser.initialize_motor)
        logging.info("Motor initialization started.")

    def on_quit():
        root.destroy()

    # --- GUI Layout ---
    root = tk.Tk()
    root.title("Dispenser Control Panel")

    chip_label = ttk.Label(root, text="Chips: 0", font=("Arial", 20))
    chip_label.pack(pady=5)

    state_label = ttk.Label(root, text="State: OFF", font=("Arial", 20))
    state_label.pack(pady=5)

    qty_frame = ttk.Frame(root)
    qty_frame.pack(pady=10)

    ttk.Label(qty_frame, text="Quantity:").pack(side=tk.LEFT, padx=5)
    qty_entry = ttk.Entry(qty_frame, width=10)
    qty_entry.pack(side=tk.LEFT)
    qty_entry.insert(0, "0")

    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=10)

    btn_dispense = tk.Button(btn_frame, text="Dispense", command=on_dispense)
    btn_dispense.grid(row=0, column=0, padx=5)

    btn_load = tk.Button(btn_frame, text="Load", command=on_load)
    btn_load.grid(row=0, column=1, padx=5)

    btn_home = tk.Button(btn_frame, text="Home", command=on_home)
    btn_home.grid(row=0, column=2, padx=5)

    btn_init = tk.Button(btn_frame, text="Initialize", command=on_initialize)
    btn_init.grid(row=0, column=3, padx=5)

    tk.Button(btn_frame, text="Quit", command=on_quit).grid(row=0, column=4, padx=5)

    update_gui()
    root.mainloop()


if __name__ == "__main__":
    dispenser: Dispenser = ...
    start_gui(dispenser)
