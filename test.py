import tkinter as tk
from tkinter import StringVar
root = tk.Tk()
#root.mainloop()

top = tk.Toplevel()

# lbRoot = tk.Listbox(root, exportselection = False)
# lbTop = tk.Listbox(top, exportselection = False)
#
# lbRoot.pack()
# lbTop.pack()
#
# lbRoot.insert(tk.END, "ROOT")
# lbTop.insert(tk.END, "TOP")
for i in range(0, 2):
    if i % 2 == 0:
        parent = top
    else:
        parent = root
    device = StringVar()
    w02 = tk.Radiobutton(parent, text = "WROOM-02", variable = device, value = "WROOM-02")
    w32 = tk.Radiobutton(parent, text = "WROOM-32", variable = device, value = "WROOM-32")
    device.set("WROOM-02")
    w02.pack()
    w32.pack()

root.title("root")
top.title("top")

top.mainloop()
