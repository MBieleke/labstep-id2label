import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import inch
import labstep
import io
import sys
import os
import tkinter as tk
from tkinter import messagebox, filedialog

# === GUI Window for Credentials and ID Entry ===
def get_user_inputs(prefill=None):
    def add_id():
        val = id_entry.get()
        entries = [v.strip() for v in val.split(',') if v.strip().isdigit()]
        for entry in entries:
            id_listbox.insert(tk.END, entry)
        id_entry.delete(0, tk.END)

    def remove_selected():
        selected = id_listbox.curselection()
        for i in reversed(selected):
            id_listbox.delete(i)

    def on_submit():
        if not email_entry.get().strip() or not api_key_entry.get().strip() or id_listbox.size() == 0:
            messagebox.showerror("Input Error", "Please fill in all fields and add at least one ID.")
            return
        inputs["email"] = email_entry.get()
        inputs["api_key"] = api_key_entry.get()
        inputs["ids"] = [int(id_listbox.get(i)) for i in range(id_listbox.size())]
        root.destroy()

    def on_cancel():
        if messagebox.askokcancel("Quit", "Are you sure you want to exit?"):
            root.destroy()
            sys.exit(0)

    root = tk.Tk()
    root.title("Labstep QR Label Generator")

    intro = tk.Label(root, text="Welcome! This program produces a single PDF file with 2x2 inch QR labels. Provide your Labstep credentials and add the Labstep IDs of resources or items for which you want to generate QR labels.", wraplength=550, justify="left")
    intro.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 15))

    tk.Label(root, text="Labstep Email:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    email_entry = tk.Entry(root, width=40)
    email_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="we")

    tk.Label(root, text="Labstep API Key:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    api_key_entry = tk.Entry(root, width=40, show="*")
    api_key_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=2, sticky="we")

    api_hint = tk.Label(root, text="Find or generate your API key in Labstep under Account Settings → API", fg="gray", font=("Arial", 8))
    api_hint.grid(row=3, column=1, columnspan=2, sticky="w", padx=5)

    tk.Label(root, text="Add Resource/Item ID(s):").grid(row=4, column=0, sticky="e", padx=5, pady=2)
    id_entry = tk.Entry(root, width=25)
    id_entry.grid(row=4, column=1, padx=5, pady=2, sticky="we")
    tk.Button(root, text="Add", command=add_id).grid(row=4, column=2, padx=5, pady=2, sticky="w")

    id_hint = tk.Label(root, text="You can add multiple IDs at once separated by commas", fg="gray", font=("Arial", 8))
    id_hint.grid(row=5, column=1, columnspan=2, sticky="w", padx=5)

    id_listbox = tk.Listbox(root, height=6, selectmode=tk.MULTIPLE, width=40)
    id_listbox.grid(row=6, column=0, columnspan=2, pady=5, padx=5, sticky="we")
    tk.Button(root, text="Remove Selected", command=remove_selected).grid(row=6, column=2, sticky="n", padx=5, pady=5)

    button_frame = tk.Frame(root)
    button_frame.grid(row=7, column=0, columnspan=3, pady=10)
    submit_button = tk.Button(button_frame, text="Generate Labels", command=on_submit)
    submit_button.pack(side=tk.LEFT, padx=20)
    cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
    cancel_button.pack(side=tk.LEFT, padx=20)

    ack = tk.Label(root, text="Created by Dr. Maik Bieleke (maik.bieleke@uni-konstanz.de)", font=("Arial", 8), fg="gray")
    ack.grid(row=8, column=0, columnspan=3, pady=(5, 10))

    root.columnconfigure(1, weight=1)
    inputs = {"email": prefill.get("email") if prefill else "", "api_key": prefill.get("api_key") if prefill else "", "ids": prefill.get("ids") if prefill else []}

    if inputs["email"]:
        email_entry.insert(0, inputs["email"])
    if inputs["api_key"]:
        api_key_entry.insert(0, inputs["api_key"])
    for rid in inputs["ids"]:
        id_listbox.insert(tk.END, str(rid))

    root.mainloop()
    return inputs

while True:
    user_data = get_user_inputs()
    email = user_data["email"]
    api_key = user_data["api_key"]
    resource_ids = user_data["ids"]

    try:
        user = labstep.authenticate(email, api_key)
        break
    except Exception as e:
        messagebox.showerror("Authentication Failed", f"Could not authenticate: {e}\nPlease check your credentials.")

save_path = filedialog.asksaveasfilename(
    defaultextension=".pdf",
    filetypes=[("PDF files", "*.pdf")],
    initialdir=os.getcwd(),
    title="Save Label PDF as"
)

if not save_path:
    messagebox.showwarning("Cancelled", "Save cancelled. No file generated.")
    sys.exit(0)

# === CONFIG ===
dpi = 600
canvas_size = int(2 * dpi)
qr_size = int(1.3 * dpi)
padding = 40

try:
    font_header = ImageFont.truetype("arialbd.ttf", 46)
    font_label = ImageFont.truetype("arialbd.ttf", 56)
    font_location = ImageFont.truetype("arial.ttf", 46)
except:
    font_header = ImageFont.load_default()
    font_label = ImageFont.load_default()
    font_location = ImageFont.load_default()

c = canvas.Canvas(save_path, pagesize=(2 * inch, 2 * inch))
invalid_ids = []

for resource_id in resource_ids:
    try:
        item = user.getResourceItem(resource_id)
        name = item.name
        guid = item.guid
        location = item.resource_location.get("location_path") if item.resource_location else "No location"
    except:
        try:
            resource = user.getResource(resource_id)
            name = resource.name
            guid = resource.guid
            items = resource.getItems()
            locations = list({item.resource_location.get("location_path") for item in items if item.resource_location})
            location = "; ".join(locations) if locations else "No location"
        except:
            invalid_ids.append(resource_id)
            continue
    
    qr_url = f"https://app.labstep.com/perma-link/{guid}"
    qr_img = qrcode.make(qr_url).convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), resample=Image.LANCZOS)

    label_img = Image.new("RGBA", (canvas_size, canvas_size), "white")
    draw = ImageDraw.Draw(label_img)

    qr_x = (canvas_size - qr_size) // 2
    qr_y = (canvas_size - qr_size) // 3
    label_img.paste(qr_img, (qr_x, qr_y))

    header_text = "SPORT PSYCHOLOGY LAB"
    header_bbox = font_header.getbbox(header_text)
    header_width = header_bbox[2] - header_bbox[0]
    header_height = header_bbox[3] - header_bbox[1]
    header_x = (canvas_size - header_width) // 2
    header_y = qr_y - header_height + 50
    if header_y > 0:
        draw.text((header_x, header_y), header_text, fill="black", font=font_header)

    wrapped_lines = [name]
    line_height = font_label.getbbox("Hg")[3] - font_label.getbbox("Hg")[1]
    for i, line in enumerate(wrapped_lines):
        line_width = font_label.getbbox(line)[2] - font_label.getbbox(line)[0]
        x = (canvas_size - line_width) // 2
        y = qr_y + qr_size + padding + i * (line_height + 1)
        if i == 0:
            label_y = y
        if y + line_height < canvas_size:
            draw.text((x, y), line, fill="black", font=font_label)

    location_text = str(location)
    loc_text_bbox = font_location.getbbox(location_text)
    loc_text_width = loc_text_bbox[2] - loc_text_bbox[0]
    loc_text_height = loc_text_bbox[3] - loc_text_bbox[1]
    location_img = Image.new("RGBA", (loc_text_width, loc_text_height + 10), (255, 255, 255, 0))
    loc_draw = ImageDraw.Draw(location_img)
    loc_draw.text((0, 0), location_text, font=font_location, fill="black")

    location_y = qr_y + qr_size + ((label_y - (qr_y + qr_size)) // 2) - (loc_text_height // 2) - 50
    location_x = (canvas_size - loc_text_width) // 2
    label_img.alpha_composite(location_img, (location_x, location_y))

    img_io = io.BytesIO()
    label_img.convert("RGB").save(img_io, format="PNG", compress_level=0)
    img_io.seek(0)
    c.drawInlineImage(Image.open(img_io), 0, 0, width=2 * inch, height=2 * inch)
    c.showPage()

c.save()

if invalid_ids:
    retry = messagebox.askyesno("Invalid IDs", f"The following IDs could not be found or accessed:\n{invalid_ids}\n\nDo you want to go back and correct them?")
    if retry:
        updated_input = {"email": email, "api_key": api_key, "ids": [i for i in resource_ids if i not in invalid_ids]}
        user_data = get_user_inputs(prefill=updated_input)
        exec(open(__file__).read())
        sys.exit(0)

messagebox.showinfo("Done", f"✅ Labels saved to: {save_path}")
