# library
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import sqlite3
from matplotlib.colors import LinearSegmentedColormap
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from threading import Timer
from preset_database import fetch_all_presets
from preset_database import initialize_database
from preset_database import insert_preset  # Import the missing function

initialize_database()

# Define the custom colormap with more colors for finer detail
colors = ["red", "yellow", "green"]
cmap = LinearSegmentedColormap.from_list("detailed_cmap", colors)

def calculate_value(y, x, damage, mult, base_cooldown):
    y = y / 100
    net_damage = damage * mult
    cooldown_mod = (1 - min(((base_cooldown - 1) / base_cooldown), y))
    net_cooldown = base_cooldown * cooldown_mod
    net_dps = net_damage / net_cooldown
    ideal_dps = (x * net_dps)
    wasted_dps = (net_dps * (x - (net_cooldown * math.floor(x / net_cooldown))))
    expected_damage = ideal_dps - wasted_dps
    return expected_damage

# Global dictionary to track the current canvas for each tab
current_canvas = {}

# Global dictionary to store heatmap data for each tab
heatmap_data = {}

def generate_comparison_heatmap(plot_frame, error_label, absolute_damage_var):
    # Check if heatmaps for Weapon 1 and Weapon 2 exist
    if "Weapon 1" not in heatmap_data or "Weapon 2" not in heatmap_data:
        error_label.config(text="Error: Heatmaps for Weapon 1 and Weapon 2 must be generated first.")
        return

    # Retrieve heatmap data for Weapon 1 and Weapon 2
    df1 = heatmap_data["Weapon 1"]
    df2 = heatmap_data["Weapon 2"]

    # Ensure the dimensions of the heatmaps match
    if df1.shape != df2.shape:
        error_label.config(text="Error: Heatmaps for Weapon 1 and Weapon 2 must have the same dimensions.")
        return

    # Delete the old heatmap if it exists
    delete_heatmap("Comparison Tab", plot_frame)

    # Calculate the comparison data
    if absolute_damage_var.get():
        # Absolute Damage: Direct difference
        comparison_df = df1 - df2
    else:
        # Relative Damage: Handle zero values explicitly
        comparison_df = pd.DataFrame(index=df1.index, columns=df1.columns)

        for i in range(df1.shape[0]):
            for j in range(df1.shape[1]):
                val1 = df1.iloc[i, j]
                val2 = df2.iloc[i, j]

                if val1 == 0 and val2 == 0:
                    comparison_df.iloc[i, j] = 0  # Both values are zero
                elif val1 == 0 or val2 == 0:
                    comparison_df.iloc[i, j] = None  # Skip writing data for now
                elif val1 > val2:
                    comparison_df.iloc[i, j] = (val1 - val2) / val2  # Ratio to the smaller value
                else:
                    comparison_df.iloc[i, j] = -1 * (val2 - val1) / val1  # Multiply by -1 if larger value is from df2

        # Fill skipped cells with the value of the cell with the greatest magnitude and the same sign
        max_positive = comparison_df[comparison_df > 0].max().max()  # Largest positive value
        max_negative = comparison_df[comparison_df < 0].min().min()  # Largest negative value (most negative)

        for i in range(comparison_df.shape[0]):
            for j in range(comparison_df.shape[1]):
                if pd.isna(comparison_df.iloc[i, j]):  # Check for skipped cells
                    if df1.iloc[i, j] == 0:
                        comparison_df.iloc[i, j] = max_negative * 1.01  # Use the largest negative value
                    elif df2.iloc[i, j] == 0:
                        comparison_df.iloc[i, j] = max_positive * 1.01  # Use the largest positive value

    # Clear the error message
    error_label.config(text="")

    # Create a custom colormap where 0 is always yellow
    custom_cmap = LinearSegmentedColormap.from_list("custom_cmap", ["red", "yellow", "green"])

    # Create the heatmap figure with dynamic sizing
    fig, ax = plt.subplots(figsize=(plot_frame.winfo_width() / 100, 5))  # Dynamic width
    sns.heatmap(
        comparison_df.astype(float),  # Ensure the data is numeric
        cbar_kws={'orientation': 'vertical'},  # Color bar orientation
        yticklabels=True,  # Show y-axis labels
        cmap=custom_cmap,  # Use the custom colormap
        center=0,  # Center the color scale on 0
        ax=ax
    )
    cbar = ax.collections[0].colorbar

    # Modify the legend (color bar) formatting
    if absolute_damage_var.get():
        # Absolute Damage: Display as raw values
        cbar.set_ticks(np.linspace(comparison_df.values.min(), comparison_df.values.max(), 5))
        cbar.set_ticklabels([f"{tick:.2f}" for tick in np.linspace(comparison_df.values.min(), comparison_df.values.max(), 5)])
    else:
        # Relative Damage: Display as percentages
        cbar.set_ticks(np.linspace(comparison_df.values.min(), comparison_df.values.max(), 5))
        cbar.set_ticklabels([f"{tick * 100:.0f}%" for tick in np.linspace(comparison_df.values.min(), comparison_df.values.max(), 5)])

    ax.set_xlabel("Combat Duration (seconds)")

    # Modify the x-axis to have ticks every 5 units
    x_ticks = range(0, comparison_df.shape[1] + 1, 5)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_ticks)

    # Modify the y-axis to increase as it gets further away from the x-axis
    y_ticks = np.arange(0, comparison_df.shape[0], 10)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{(comparison_df.shape[0] - tick - 1) / 100:.0%}" for tick in y_ticks])

    # Embed the heatmap in the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    canvas.draw()

    # Add a label below the heatmap to display cursor information
    comparison_info_label = ttk.Label(plot_frame, text="", anchor="center", justify="center")
    comparison_info_label.pack(side=tk.BOTTOM, pady=5)

    # Bind mouse motion event to display cursor coordinates and cell value
    def on_mouse_move(event):
        # Get the cursor position in pixels
        x_pixel, y_pixel = event.x, event.y

        # Convert pixel coordinates to data coordinates
        if canvas_widget.winfo_containing(event.x_root, event.y_root) == canvas_widget:
            x_data, y_data = ax.transData.inverted().transform((x_pixel, y_pixel))
            x_data = int(np.floor(x_data))  # Use floor to align with heatmap cells
            y_data = int(np.floor(y_data))
            if 0 <= x_data < comparison_df.shape[1] and 0 <= y_data < comparison_df.shape[0]:
                # Flip the y_data index to match the heatmap's orientation
                flipped_y_data = comparison_df.shape[0] - 1 - y_data
                value = comparison_df.iloc[flipped_y_data, x_data]

                # Logic for "Absolute Damage" toggle
                if absolute_damage_var.get():
                    # Absolute Damage logic
                    if value > 0:
                        result_text = f"Weapon 1 will deal {value:.2f} more damage than Weapon 2."
                    elif value < 0:
                        result_text = f"Weapon 2 will deal {value * -1:.2f} more damage than Weapon 1."
                    else:
                        result_text = "Both weapons will deal the same amount of damage."
                else:
                    # Relative Damage logic
                    if value == 0:
                        result_text = "Both weapons are equally strong."
                    elif value > max_positive:
                        result_text = "Weapon 1 is infinitely stronger than Weapon 2."
                    elif value < max_negative:
                        result_text = "Weapon 2 is infinitely stronger than Weapon 1."
                    elif value > 0:
                        result_text = f"Weapon 1 is {value * 100:.2f}% stronger than Weapon 2."
                    else:
                        result_text = f"Weapon 2 is {abs(value) * 100:.2f}% stronger than Weapon 1."

                comparison_info_label.config(
                    text=f"If combat lasts {x_data} seconds,\n"
                         f"and you apply {y_data}% CDR relative to base CD,\n"
                         f"{result_text}"
                )

    canvas_widget.bind("<Motion>", on_mouse_move)

    # Bind a resize event to dynamically adjust the heatmap
    def on_resize(event):
        fig.set_size_inches(plot_frame.winfo_width() / 100, 5)
        canvas.draw()

    plot_frame.bind("<Configure>", on_resize)

    # Track the current canvas and label for this tab
    current_canvas["Comparison Tab"] = (canvas, comparison_info_label)

    # Explicitly close the figure to avoid stale figures
    plt.close(fig)

def create_comparison_tab(notebook):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Comparison Tab")

    frame = ttk.Frame(tab, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    error_label = ttk.Label(frame, text="", foreground="red")
    error_label.grid(row=0, column=0, columnspan=2)

    # Add a checkbox for "Absolute Damage"
    absolute_damage_var = tk.BooleanVar(value=False)  # Default to unchecked
    absolute_damage_checkbox = ttk.Checkbutton(
        frame,
        text="Absolute Damage",
        variable=absolute_damage_var
    )
    absolute_damage_checkbox.grid(row=1, column=0, columnspan=2, sticky=tk.W)

    generate_button = ttk.Button(
        frame,
        text="Generate Comparison Table",
        command=lambda: generate_comparison_heatmap(plot_frame, error_label, absolute_damage_var)
    )
    generate_button.grid(row=2, column=0, columnspan=2, pady=10)

    # Frame for displaying the comparison heatmap
    plot_frame = ttk.Frame(tab, padding="10")
    plot_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Configure resizing behavior for the plot frame
    tab.rowconfigure(3, weight=1)  # Allow row 3 (plot_frame) to expand
    tab.columnconfigure(0, weight=1)  # Allow column 0 to expand

    return tab

def generate_heatmap(damage_entry, mult_entry, base_cooldown_entry, error_label, plot_frame, tab_name, low_cap_entry, high_cap_entry, end_at_rope_var, max_cdr_entry):
    global cmap  # Use the global colormap

    try:
        damage = float(damage_entry.get())
        mult = int(mult_entry.get())
        base_cooldown = float(base_cooldown_entry.get())
        low_cap = float(low_cap_entry.get()) if low_cap_entry.get() else None
        high_cap = float(high_cap_entry.get()) if high_cap_entry.get() else None
        max_cdr = int(max_cdr_entry.get()) + 1  # Add one to the Max CDR value
        if max_cdr < 11 or max_cdr > 101:  # Adjusted range check
            raise ValueError("Maximum CDR must be an integer between 10 and 100.")
    except ValueError as e:
        error_label.config(text=str(e))
        return

    error_label.config(text="")  # Clear error message

    # Ensure the previous heatmap is deleted before generating a new one
    delete_heatmap(tab_name, plot_frame)

    # Determine the x-axis length based on the "end at storm" checkbox
    x_range = 30 if end_at_rope_var.get() else 60

    # Recalculate the dataset and regenerate the heatmap
    df = pd.DataFrame(
        [[calculate_value(max_cdr - 1 - y, x, damage, mult, base_cooldown) for x in range(x_range)] for y in range(max_cdr)],
        columns=range(x_range),
        index=[f"{y / 100:.0%}" for y in range(max_cdr)]  # Format y values as percentages
    )

    # Store the heatmap data for this tab
    heatmap_data[tab_name] = df

    # Set vmin and vmax based on user-provided caps
    vmin = low_cap if low_cap is not None else df.values.min()
    vmax = high_cap if high_cap is not None else df.values.max()

    # Create the heatmap figure with dynamic sizing
    fig, ax = plt.subplots(figsize=(plot_frame.winfo_width() / 100, 5))  # Dynamic width
    sns.heatmap(
        df,
        cbar_kws={'orientation': 'vertical'},
        yticklabels=True,  # Use the DataFrame index for yticklabels
        vmin=vmin,
        vmax=vmax,
        cmap=cmap,
        ax=ax
    )
    cbar = ax.collections[0].colorbar
    cbar.set_ticks(np.linspace(vmin, vmax, 5))
    cbar.set_ticklabels([f"{tick:.2f}" for tick in np.linspace(vmin, vmax, 5)])
    ax.set_yticks(np.linspace(0, max_cdr - 1, 11))
    ax.set_yticklabels([f"{y / 100:.0%}" for y in np.linspace(max_cdr - 1, 0, 11)])  # Correct order for tick labels
    ax.set_xticks(range(0, x_range + 1, 5))
    ax.set_xticklabels(range(0, x_range + 1, 5))
    ax.set_xlabel("Combat Duration (seconds)")

    # Embed the heatmap in the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    canvas.draw()

    # Add a label above the heatmap to display cursor information
    cursor_info_label = ttk.Label(plot_frame, text="", anchor="center", justify="center")
    cursor_info_label.pack(side=tk.TOP, pady=5)

    # Bind mouse motion event to display cursor coordinates and cell value
    def on_mouse_move(event):
        # Get the cursor position in pixels
        x_pixel, y_pixel = event.x, event.y

        # Convert pixel coordinates to data coordinates
        if ax.contains_point((x_pixel, y_pixel)):
            x_data, y_data = ax.transData.inverted().transform((x_pixel, y_pixel))
            x_data = int(round(x_data))
            y_data = int(round(y_data))
            if 0 <= x_data < x_range and 0 <= y_data < max_cdr:
                # Flip the y_data index to match the heatmap's orientation
                flipped_y_data = max_cdr - 1 - y_data
                value = df.iloc[flipped_y_data, x_data]
                cursor_info_label.config(
                    text=f"If combat lasts {x_data} seconds,\n"
                         f"and you apply {y_data}% CDR relative to base CD,\n"  # Adjusted y value
                         f"you can expect this item to deal {value:.2f} damage."
                )

    canvas_widget.bind("<Motion>", on_mouse_move)

    # Bind a resize event to dynamically adjust the heatmap
    def on_resize(event):
        fig.set_size_inches(plot_frame.winfo_width() / 100, 5)
        canvas.draw()

    plot_frame.bind("<Configure>", on_resize)

    # Track the current canvas for this tab
    current_canvas[tab_name] = canvas

    # Explicitly close the figure to avoid stale figures
    plt.close(fig)

def delete_heatmap(tab_name, plot_frame):
    global current_canvas  # Access the global canvas tracker
    if tab_name in current_canvas and current_canvas[tab_name] is not None:
        # Destroy the current canvas widget
        if isinstance(current_canvas[tab_name], tuple):
            canvas, info_label = current_canvas[tab_name]
            canvas.get_tk_widget().destroy()
            info_label.destroy()  # Destroy the additional label
        else:
            current_canvas[tab_name].get_tk_widget().destroy()
        current_canvas[tab_name] = None
    # Delete the text element (cursor information label) if it exists
    for widget in plot_frame.winfo_children():
        if isinstance(widget, ttk.Label):  # Check if the widget is a label
            widget.destroy()

def update_field_from_slider(slider_value, entry_field):
    """
    Update the value of the entry field based on the slider value.
    The slider operates on a log10 scale.
    """
    value = 10 ** slider_value  # Convert slider value to log10 scale
    entry_field.delete(0, tk.END)  # Clear the entry field
    entry_field.insert(0, f"{value:.0f}")  # Insert the new value

def save_preset(name, damage, mult, base_cooldown, low_cap, high_cap, max_cdr):
    try:
        insert_preset(name, damage, mult, base_cooldown, low_cap, high_cap, max_cdr)
    except sqlite3.IntegrityError:
        pass

def create_tab(notebook, tab_name):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text=tab_name)

    frame = ttk.Frame(tab, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Add a dropdown list for preset settings profiles
    preset_label = ttk.Label(frame, text="Preset:")
    preset_label.grid(row=0, column=0, sticky=tk.W)
    preset_var = tk.StringVar(value="Select a preset")
    preset_dropdown = ttk.Combobox(frame, textvariable=preset_var, state="readonly", width=30)
    preset_dropdown.grid(row=0, column=1, sticky=(tk.W, tk.E))

    # Load presets from the database
    presets = fetch_all_presets()
    preset_dropdown['values'] = [preset[1] for preset in presets]  # Use preset names

    # Function to apply a selected preset
    def apply_preset(event):
        selected_preset = preset_var.get()
        for preset in presets:
            if preset[1] == selected_preset:
                _, _, damage, mult, base_cooldown, low_cap, high_cap, max_cdr = preset
                damage_entry.delete(0, tk.END)
                damage_entry.insert(0, damage)
                mult_entry.delete(0, tk.END)
                mult_entry.insert(0, mult)
                base_cooldown_entry.delete(0, tk.END)
                base_cooldown_entry.insert(0, base_cooldown)
                low_cap_entry.delete(0, tk.END)
                low_cap_entry.insert(0, low_cap)
                high_cap_entry.delete(0, tk.END)
                high_cap_entry.insert(0, high_cap)
                max_cdr_entry.delete(0, tk.END)
                max_cdr_entry.insert(0, max_cdr)
                break

    preset_dropdown.bind("<<ComboboxSelected>>", apply_preset)

    ttk.Label(frame, text="Damage:").grid(row=1, column=0, sticky=tk.W)
    damage_entry = ttk.Entry(frame)
    damage_entry.grid(row=1, column=1)

    ttk.Label(frame, text="Mult:").grid(row=2, column=0, sticky=tk.W)
    mult_entry = ttk.Entry(frame)
    mult_entry.grid(row=2, column=1)

    ttk.Label(frame, text="Base Cooldown:").grid(row=3, column=0, sticky=tk.W)
    base_cooldown_entry = ttk.Entry(frame)
    base_cooldown_entry.grid(row=3, column=1)

    ttk.Label(frame, text="Low Cap:").grid(row=4, column=0, sticky=tk.W)
    low_cap_entry = ttk.Entry(frame, width=10)
    low_cap_entry.grid(row=4, column=1, sticky=tk.W)

    # Remove the clear button for Low Cap
    # Add a slider for Low Cap
    low_cap_slider = tk.Scale(
        frame,
        from_=0, to=5,  # Slider range corresponds to log10 scale (0 to 5)
        orient=tk.HORIZONTAL,
        resolution=0.1,  # Slider steps
        length=300,  # Make the slider three times as long
        command=lambda value: [update_field_from_slider(float(value), low_cap_entry)]
    )
    low_cap_slider.grid(row=4, column=2, sticky=tk.W)

    ttk.Label(frame, text="High Cap:").grid(row=5, column=0, sticky=tk.W)
    high_cap_entry = ttk.Entry(frame, width=10)
    high_cap_entry.grid(row=5, column=1, sticky=tk.W)

    # Remove the clear button for High Cap
    # Add a slider for High Cap
    high_cap_slider = tk.Scale(
        frame,
        from_=0, to=5,  # Slider range corresponds to log10 scale (0 to 5)
        orient=tk.HORIZONTAL,
        resolution=0.1,  # Slider steps
        length=300,  # Make the slider three times as long
        command=lambda value: [update_field_from_slider(float(value), high_cap_entry)]
    )
    high_cap_slider.grid(row=5, column=2, sticky=tk.W)

    ttk.Label(frame, text="Maximum CDR:").grid(row=6, column=0, sticky=tk.W)
    max_cdr_entry = ttk.Entry(frame)
    max_cdr_entry.grid(row=6, column=1)

    # Add a slider for Maximum CDR
    max_cdr_slider = tk.Scale(
        frame,
        from_=10, to=100,  # Slider range from 10 to 100
        orient=tk.HORIZONTAL,
        resolution=1,  # Slider steps
        length=300,  # Make the slider three times as long
        command=lambda value: max_cdr_entry.delete(0, tk.END) or max_cdr_entry.insert(0, value)
    )
    max_cdr_slider.grid(row=6, column=2)

    error_label = ttk.Label(frame, text="", foreground="red")
    error_label.grid(row=7, column=0, columnspan=3)

    # Add a checkbox for "end at storm"
    end_at_rope_var = tk.BooleanVar(value=False)  # Default to full x-axis
    end_at_rope_checkbox = ttk.Checkbutton(frame, text="End at storm", variable=end_at_rope_var)
    end_at_rope_checkbox.grid(row=8, column=0, columnspan=3, sticky=tk.W)

    generate_button = ttk.Button(
        frame,
        text="Generate Heatmap",
        command=lambda: generate_heatmap(
            damage_entry, mult_entry, base_cooldown_entry, error_label,
            plot_frame, tab_name, low_cap_entry, high_cap_entry, end_at_rope_var, max_cdr_entry
        ),
    )
    generate_button.grid(row=9, column=0, sticky=tk.W)

    # Frame for displaying the heatmap
    plot_frame = ttk.Frame(tab, padding="10")
    plot_frame.grid(row=10, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Configure resizing behavior for the plot frame
    tab.rowconfigure(10, weight=1)  # Allow row 10 (plot_frame) to expand
    tab.columnconfigure(0, weight=1)  # Allow column 0 to expand

    return tab

# Create the GUI
root = tk.Tk()
root.title("Bazaar Data Visualizer")

# Set the initial window size
root.geometry("1000x900")  # Width: 1000px, Height: 900px

# Configure resizing behavior for the root window
root.rowconfigure(0, weight=1)  # Allow row 0 to expand
root.columnconfigure(0, weight=1)  # Allow column 0 to expand

notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Configure resizing behavior for the notebook
notebook.rowconfigure(0, weight=1)  # Allow row 0 to expand
notebook.columnconfigure(0, weight=1)  # Allow column 0 to expand

# Create two independent tabs
create_tab(notebook, "Weapon 1")
create_tab(notebook, "Weapon 2")
create_comparison_tab(notebook)

root.mainloop()
