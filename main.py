import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
from datetime import datetime
import requests  # Required for Cloud Sync


class SchoolSystemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nexus Inter-School Attendance Node")
        self.root.geometry("1000x750")
        self.root.configure(bg="#f4f7f6")

        self.init_db()

        self.container = tk.Frame(self.root, bg="#f4f7f6")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        # All functional pages including Settings and History
        for F in (Dashboard, ClockStation, StaffManager, HistoryPage, ReportsPage, SettingsPage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Check if school is configured; if not, force setup
        if not self.get_school_info():
            self.show_frame("SettingsPage")
        else:
            self.show_frame("Dashboard")

    def init_db(self):
        conn = sqlite3.connect('local_school.db')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS school_config (id TEXT PRIMARY KEY, name TEXT)')
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS staff (id TEXT PRIMARY KEY, name TEXT, dept TEXT, is_approved INTEGER DEFAULT 0)')
        cursor.execute('''CREATE TABLE IF NOT EXISTS attendance 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, school_id TEXT, school_name TEXT, 
                          staff_id TEXT, date TEXT, clock_in TEXT, clock_out TEXT, UNIQUE(staff_id, date))''')
        conn.commit()
        conn.close()

    def get_school_info(self):
        conn = sqlite3.connect('local_school.db')
        info = conn.execute("SELECT id, name FROM school_config").fetchone()
        conn.close()
        return info

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        if hasattr(frame, "refresh_list"): frame.refresh_list()
        frame.tkraise()


# --- SETTINGS PAGE (First-Time Setup) ---
class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller
        tk.Label(self, text="SCHOOL REGISTRATION", font=("Arial", 22, "bold"), bg="white", fg="#e74c3c").pack(pady=50)

        self.s_name = tk.Entry(self, font=("Arial", 14), width=30, justify="center")
        self.s_name.pack(pady=10);
        self.s_name.insert(0, "School Name")

        self.s_id = tk.Entry(self, font=("Arial", 14), width=30, justify="center")
        self.s_id.pack(pady=10);
        self.s_id.insert(0, "Unique School ID")

        tk.Button(self, text="INITIALIZE STATION", font=("Arial", 12, "bold"), bg="#27ae60", fg="white",
                  width=20, height=2, command=self.save_config).pack(pady=30)

    def save_config(self):
        name, sid = self.s_name.get(), self.s_id.get()
        if name and sid:
            conn = sqlite3.connect('local_school.db')
            conn.execute("INSERT OR REPLACE INTO school_config (id, name) VALUES (?, ?)", (sid, name))
            conn.commit();
            conn.close()
            messagebox.showinfo("Success", "School Registered Successfully!")
            self.controller.show_frame("Dashboard")


# --- DASHBOARD ---
class Dashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f4f7f6")
        self.controller = controller
        self.title_lbl = tk.Label(self, text="ADMIN DASHBOARD", font=("Arial", 24, "bold"), bg="#f4f7f6")
        self.title_lbl.pack(pady=40)

        btn_style = {"font": ("Arial", 13), "width": 35, "height": 2, "bg": "#2980b9", "fg": "white", "relief": "flat",
                     "cursor": "hand2"}
        tk.Button(self, text="🕒 CLOCK STATION", command=lambda: controller.show_frame("ClockStation"),
                  **btn_style).pack(pady=10)
        tk.Button(self, text="👥 STAFF MANAGEMENT", command=lambda: controller.show_frame("StaffManager"),
                  **btn_style).pack(pady=10)
        tk.Button(self, text="📜 ATTENDANCE HISTORY", command=lambda: controller.show_frame("HistoryPage"),
                  **btn_style).pack(pady=10)
        tk.Button(self, text="📊 REPORTS & SYNC", command=lambda: controller.show_frame("ReportsPage"),
                  **btn_style).pack(pady=10)

    def refresh_list(self):
        info = self.controller.get_school_info()
        if info: self.title_lbl.config(text=f"{info[1].upper()} NODE")


# --- CLOCK STATION ---
class ClockStation(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller
        tk.Button(self, text="← DASHBOARD", command=lambda: controller.show_frame("Dashboard")).pack(anchor="nw",
                                                                                                     padx=20, pady=20)

        tk.Label(self, text="STAFF ID ENTRY", font=("Arial", 18), bg="white").pack(pady=20)
        self.id_entry = tk.Entry(self, font=("Arial", 24), width=15, justify="center", bd=2, relief="solid")
        self.id_entry.pack(pady=20)
        tk.Button(self, text="SUBMIT ATTENDANCE", bg="#27ae60", fg="white", font=("Arial", 14, "bold"), width=20,
                  height=2, command=self.process).pack(pady=20)

    def process(self):
        sid = self.id_entry.get().strip()
        info = self.controller.get_school_info()
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%H:%M:%S")

        conn = sqlite3.connect('local_school.db')
        cur = conn.cursor()
        staff = cur.execute("SELECT is_approved, name FROM staff WHERE id=?", (sid,)).fetchone()

        if staff and staff[0] == 1:
            att = cur.execute("SELECT clock_in, clock_out FROM attendance WHERE staff_id=? AND date=?",
                              (sid, today)).fetchone()
            if not att:
                cur.execute(
                    "INSERT INTO attendance (school_id, school_name, staff_id, date, clock_in) VALUES (?,?,?,?,?)",
                    (info[0], info[1], sid, today, now))
                messagebox.showinfo("In", f"Welcome {staff[1]}! Clocked In.")
            elif not att[1]:
                cur.execute("UPDATE attendance SET clock_out=? WHERE staff_id=? AND date=?", (now, sid, today))
                messagebox.showinfo("Out", f"Goodbye {staff[1]}! Clocked Out.")
            else:
                messagebox.showwarning("Notice", "You have already clocked out for today.")
        else:
            messagebox.showerror("Denied", "ID not found or not approved by Admin.")

        conn.commit();
        conn.close()
        self.id_entry.delete(0, tk.END)


# --- STAFF MANAGER ---
class StaffManager(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        tk.Button(self, text="← DASHBOARD", command=lambda: controller.show_frame("Dashboard")).pack(anchor="nw",
                                                                                                     padx=20, pady=10)

        tk.Button(self, text="📥 IMPORT STAFF (CSV)", bg="#9b59b6", fg="white", command=self.import_csv).pack(pady=10)
        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Dept", "Status"), show="headings")
        for col in ("ID", "Name", "Dept", "Status"): self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Button(self, text="APPROVE STAFF", bg="#f39c12", fg="white", font=("Arial", 12, "bold"),
                  command=self.approve).pack(pady=15)

    def refresh_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = sqlite3.connect('local_school.db')
        for row in conn.execute("SELECT id, name, dept, is_approved FROM staff"):
            status = "APPROVED" if row[3] == 1 else "PENDING"
            self.tree.insert("", "end", values=(row[0], row[1], row[2], status))
        conn.close()

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            df = pd.read_csv(path)
            conn = sqlite3.connect('local_school.db')
            df.to_sql('staff', conn, if_exists='append', index=False)
            conn.close();
            self.refresh_list()

    def approve(self):
        sel = self.tree.selection()
        if sel:
            sid = self.tree.item(sel)['values'][0]
            conn = sqlite3.connect('local_school.db')
            conn.execute("UPDATE staff SET is_approved=1 WHERE id=?", (sid,))
            conn.commit();
            conn.close();
            self.refresh_list()


# --- HISTORY VIEW ---
class HistoryPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        tk.Button(self, text="← DASHBOARD", command=lambda: controller.show_frame("Dashboard")).pack(anchor="nw",
                                                                                                     padx=20, pady=10)
        self.tree = ttk.Treeview(self, columns=("Date", "Name", "In", "Out"), show="headings")
        for col in ("Date", "Name", "In", "Out"): self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)

    def refresh_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = sqlite3.connect('local_school.db')
        query = "SELECT a.date, s.name, a.clock_in, a.clock_out FROM attendance a JOIN staff s ON a.staff_id = s.id ORDER BY a.date DESC LIMIT 100"
        for row in conn.execute(query): self.tree.insert("", "end", values=row)
        conn.close()


# --- REPORTS & CLOUD SYNC ---
class ReportsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller
        tk.Button(self, text="← DASHBOARD", command=lambda: controller.show_frame("Dashboard")).pack(anchor="nw",
                                                                                                     padx=20, pady=20)

        tk.Button(self, text="💾 EXPORT EXCEL REPORT", bg="#2c3e50", fg="white", width=30, height=2,
                  command=self.export).pack(pady=20)
        tk.Button(self, text="☁️ SYNC TO SUPER ADMIN", bg="#673ab7", fg="white", width=30, height=2,
                  command=self.cloud_sync).pack(pady=20)

    def export(self):
        conn = sqlite3.connect('local_school.db')
        df = pd.read_sql_query("SELECT * FROM attendance", conn)
        conn.close()
        filename = f"Report_{datetime.now().strftime('%Y-%m-%d_%H%M')}.xlsx"
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=filename)
        if path:
            try:
                df.to_excel(path, index=False)
                messagebox.showinfo("Success", "Excel report saved.")
            except PermissionError:
                messagebox.showerror("Error", "Close the Excel file first!")

    def cloud_sync(self):
        info = self.controller.get_school_info()
        # Placeholder for Django Cloud URL
        url = "https://your-super-admin-web.com/api/sync/"
        messagebox.showinfo("Cloud", f"Syncing {info[1]} data to Super Admin...")
        # Add actual requests.post logic here when your server is live


if __name__ == "__main__":
    root = tk.Tk()
    app = SchoolSystemApp(root)
    root.mainloop()