import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import math
from pathlib import Path

DB_NAME = Path(__file__).with_name("forensic_laboratory.db")


def connect():
    db = sqlite3.connect(DB_NAME)
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialize_database():
    with connect() as db:
        c = db.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS labs(
            lab_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lab_name TEXT NOT NULL UNIQUE,
            contact_email TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS case_examinations(
            examination_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lab_id INTEGER NOT NULL,
            case_reference TEXT NOT NULL,
            examination_date TEXT NOT NULL,
            FOREIGN KEY(lab_id) REFERENCES labs(lab_id) ON DELETE CASCADE)""")
        c.execute("""CREATE TABLE IF NOT EXISTS evidence_analyses(
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            examination_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            measured_value REAL NOT NULL CHECK(measured_value >= 0),
            FOREIGN KEY(examination_id) REFERENCES case_examinations(examination_id)
            ON DELETE CASCADE)""")

        counts = c.execute("""SELECT
            (SELECT COUNT(*) FROM labs),
            (SELECT COUNT(*) FROM case_examinations),
            (SELECT COUNT(*) FROM evidence_analyses)""").fetchone()

        if counts == (0, 0, 0):
            labs = [
                ("Central Forensic Laboratory", "central@forensic.gov"),
                ("Regional Forensic Laboratory", "regional@forensic.gov"),
                ("Advanced DNA Laboratory", "dna@forensic.gov")]
            c.executemany("INSERT INTO labs(lab_name,contact_email) VALUES(?,?)", labs)
            ids = {name: lid for lid, name in c.execute(
                "SELECT lab_id,lab_name FROM labs").fetchall()}
            cases = [
                (ids[labs[0][0]], "CR-2026-0147", "2026-01-15"),
                (ids[labs[1][0]], "CR-2026-0158", "2026-02-10"),
                (ids[labs[2][0]], "CR-2026-0169", "2026-03-05")]
            c.executemany("""INSERT INTO case_examinations
                (lab_id,case_reference,examination_date) VALUES(?,?,?)""", cases)
            exam_ids = [r[0] for r in c.execute(
                "SELECT examination_id FROM case_examinations ORDER BY examination_id")]
            c.executemany("""INSERT INTO evidence_analyses
                (examination_id,analysis_type,measured_value) VALUES(?,?,?)""", [
                (exam_ids[0], "DNA Profile Match Score", 98.75),
                (exam_ids[1], "Ballistics Calibre (mm)", 9.0),
                (exam_ids[2], "Toxicology Concentration (mg/L)", 2.45)])

        extra = [
            ("Central Forensic Laboratory","central@forensic.gov","CR-2026-0172","2026-03-18","Fingerprint Match Score",96.40),
            ("Regional Forensic Laboratory","regional@forensic.gov","CR-2026-0181","2026-04-02","Blood Alcohol Concentration (mg/L)",0.82),
            ("Advanced DNA Laboratory","dna@forensic.gov","CR-2026-0193","2026-04-14","DNA Similarity Score",99.12),
            ("Digital Forensics Unit","digital@forensic.gov","CR-2026-0204","2026-05-06","Recovered File Count",124.0),
            ("Cyber Crime Analysis Lab","cyber@forensic.gov","CR-2026-0215","2026-05-19","Malware Detection Confidence (%)",87.5),
            ("Central Forensic Laboratory","central@forensic.gov","CR-2026-0226","2026-06-03","Firearm Residue Measurement",3.75),
            ("Regional Forensic Laboratory","regional@forensic.gov","CR-2026-0237","2026-06-21","Fiber Diameter (micrometers)",14.2),
            ("Digital Forensics Unit","digital@forensic.gov","CR-2026-0248","2026-07-09","Deleted Data Recovery (%)",78.6)]
        for lab, email, ref, date, kind, value in extra:
            row = c.execute("SELECT lab_id FROM labs WHERE lab_name=?", (lab,)).fetchone()
            if row:
                lid = row[0]
            else:
                c.execute("INSERT INTO labs(lab_name,contact_email) VALUES(?,?)", (lab,email))
                lid = c.lastrowid
            exists = c.execute("""SELECT examination_id FROM case_examinations
                WHERE lab_id=? AND case_reference=?""", (lid,ref)).fetchone()
            if exists:
                continue
            c.execute("""INSERT INTO case_examinations
                (lab_id,case_reference,examination_date) VALUES(?,?,?)""", (lid,ref,date))
            eid = c.lastrowid
            c.execute("""INSERT INTO evidence_analyses
                (examination_id,analysis_type,measured_value) VALUES(?,?,?)""",
                (eid,kind,value))


def query(sql, args=()):
    with connect() as db:
        cur = db.execute(sql, args)
        return [d[0] for d in cur.description], cur.fetchall()


def add_record(lab, email, ref, kind, value):
    lab, email, ref, kind = lab.strip(), email.strip(), ref.strip(), kind.strip()
    if not all((lab,email,ref,kind,str(value).strip())):
        raise ValueError("Please fill in all fields.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Enter a valid email address.")
    try:
        value = float(value)
    except ValueError:
        raise ValueError("Measured value must be numeric.")
    if not math.isfinite(value) or value < 0:
        raise ValueError("Measured value must be a finite, non-negative number.")
    with connect() as db:
        row = db.execute("SELECT lab_id FROM labs WHERE lab_name=?", (lab,)).fetchone()
        if row:
            lid = row[0]
            db.execute("UPDATE labs SET contact_email=? WHERE lab_id=?", (email,lid))
        else:
            cur = db.execute("INSERT INTO labs(lab_name,contact_email) VALUES(?,?)", (lab,email))
            lid = cur.lastrowid
        cur = db.execute("""INSERT INTO case_examinations
            (lab_id,case_reference,examination_date) VALUES(?,?,DATE('now'))""", (lid,ref))
        eid = cur.lastrowid
        db.execute("""INSERT INTO evidence_analyses
            (examination_id,analysis_type,measured_value) VALUES(?,?,?)""", (eid,kind,value))


class Dashboard:
    def __init__(self, root):
        self.root = root
        root.title("Forensic Laboratory Management System")
        root.geometry("1450x950")
        root.minsize(1150, 780)
        try:
            root.state("zoomed")
        except tk.TclError:
            pass
        self.navy, self.teal, self.bg = "#172B4D", "#168C91", "#F2F5F9"
        root.configure(bg=self.bg)
        self.style()
        self.build()
        self.refresh()

    def style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame", background=self.bg)
        s.configure("Card.TFrame", background="white")
        s.configure("TLabel", background=self.bg, foreground="#253858", font=("Segoe UI",10))
        s.configure("CardTitle.TLabel", background="white", foreground=self.navy,
                    font=("Segoe UI",10,"bold"))
        s.configure("Metric.TLabel", background="white", foreground=self.navy,
                    font=("Segoe UI",22,"bold"))
        s.configure("TEntry", padding=6)
        s.configure("TCombobox", padding=6)
        s.configure("Accent.TButton", background=self.navy, foreground="white",
                    padding=9, font=("Segoe UI",9,"bold"))
        s.map("Accent.TButton", background=[("active",self.teal)])
        s.configure("Danger.TButton", background="#B93645", foreground="white", padding=8)
        s.configure("Treeview", background="white", fieldbackground="white",
                    foreground="#253858", rowheight=28, font=("Segoe UI",9))
        s.configure("Treeview.Heading", background=self.navy, foreground="white",
                    font=("Segoe UI",9,"bold"), padding=8)
        s.map("Treeview", background=[("selected","#CFE8EA")],
              foreground=[("selected",self.navy)])
        s.configure("TNotebook.Tab", padding=(12,8), font=("Segoe UI",9,"bold"))

    def build(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        box = ttk.Frame(self.root, padding=12)
        box.grid(sticky="nsew")
        box.columnconfigure(0, weight=1)
        box.rowconfigure(4, weight=1)

        head = tk.Frame(box, bg=self.navy, height=72)
        head.grid(row=0,column=0,sticky="ew",pady=(0,8))
        head.grid_propagate(False)
        tk.Label(head,text="FORENSIC LABORATORY",bg=self.navy,fg="white",
                 font=("Segoe UI",19,"bold")).pack(anchor="w",padx=18,pady=(8,0))
        tk.Label(head,text="CASE EXAMINATION & EVIDENCE ANALYSIS MANAGEMENT SYSTEM",
                 bg=self.navy,fg="#D3DCE8",font=("Segoe UI",9)).pack(anchor="w",padx=20)

        metrics = ttk.Frame(box)
        metrics.grid(row=1,column=0,sticky="ew",pady=(0,8))
        self.metric = {k:tk.StringVar(value="0") for k in ("labs","cases","analyses")}
        for i,(label,key) in enumerate([
            ("TOTAL LABORATORIES","labs"),("TOTAL EXAMINATIONS","cases"),
            ("TOTAL EVIDENCE ANALYSES","analyses")]):
            metrics.columnconfigure(i,weight=1)
            card=ttk.Frame(metrics,style="Card.TFrame",padding=9)
            card.grid(row=0,column=i,sticky="ew",padx=4)
            tk.Frame(card,bg=self.teal,height=3).pack(fill="x",pady=(0,5))
            ttk.Label(card,text=label,style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(card,textvariable=self.metric[key],style="Metric.TLabel").pack(anchor="w")

        form=ttk.Frame(box,style="Card.TFrame",padding=9)
        form.grid(row=2,column=0,sticky="ew",pady=(0,8))
        for i in range(5): form.columnconfigure(i,weight=1)
        ttk.Label(form,text="ADD NEW FORENSIC RECORD",style="CardTitle.TLabel").grid(
            row=0,column=0,columnspan=6,sticky="w",pady=(0,5))
        self.fields={}
        names=["Lab Name","Director Email","Case Reference","Analysis Type","Measured Value"]
        for i,name in enumerate(names):
            ttk.Label(form,text=name).grid(row=1,column=i,sticky="w",padx=3)
            if name=="Analysis Type":
                w=ttk.Combobox(form,values=[
                    "DNA Profile Match Score","Ballistics Calibre (mm)",
                    "Toxicology Concentration (mg/L)","Fingerprint Match Score",
                    "Blood Alcohol Concentration","Digital Evidence Analysis"])
            else: w=ttk.Entry(form)
            w.grid(row=2,column=i,sticky="ew",padx=3,pady=3)
            self.fields[name]=w
        ttk.Button(form,text="ADD RECORD",style="Accent.TButton",
                   command=self.add).grid(row=2,column=5,padx=5)

        manage=ttk.Frame(box,style="Card.TFrame",padding=8)
        manage.grid(row=3,column=0,sticky="ew",pady=(0,8))
        ttk.Label(manage,text="RECORD MANAGEMENT",style="CardTitle.TLabel").pack(side="left",padx=5)
        ttk.Label(manage,text="Delete from:").pack(side="left",padx=5)
        self.table=ttk.Combobox(manage,state="readonly",width=21,
            values=["labs","case_examinations","evidence_analyses"])
        self.table.set("labs"); self.table.pack(side="left",padx=4)
        self.table.bind("<<ComboboxSelected>>",self.refresh_delete)
        ttk.Label(manage,text="Select record:").pack(side="left",padx=(8,3))
        self.choice=ttk.Combobox(manage,state="readonly",width=38)
        self.choice.pack(side="left",padx=4)
        ttk.Button(manage,text="EDIT SELECTED",style="Accent.TButton",
                   command=self.edit).pack(side="left",padx=8)
        ttk.Button(manage,text="DELETE SELECTED",style="Danger.TButton",
                   command=self.delete).pack(side="left",padx=8)

        data=ttk.Frame(box,style="Card.TFrame",padding=8)
        data.grid(row=4,column=0,sticky="nsew")
        data.rowconfigure(1,weight=1); data.columnconfigure(0,weight=1)
        ttk.Label(data,text="DATABASE RECORDS",style="CardTitle.TLabel").grid(
            row=0,column=0,sticky="w",pady=(0,5))
        self.tabs=ttk.Notebook(data)
        self.tabs.grid(row=1,column=0,sticky="nsew")
        self.trees={}
        for title,key in [("Combined Examination View","joined"),
                          ("Forensic Laboratories","labs"),
                          ("Case Examinations","cases"),
                          ("Evidence Analyses","analyses")]:
            frame=ttk.Frame(self.tabs,padding=5)
            frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
            self.tabs.add(frame,text=title)
            tree=ttk.Treeview(frame,show="headings")
            ys=ttk.Scrollbar(frame,orient="vertical",command=tree.yview)
            xs=ttk.Scrollbar(frame,orient="horizontal",command=tree.xview)
            tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
            tree.grid(row=0,column=0,sticky="nsew")
            ys.grid(row=0,column=1,sticky="ns")
            xs.grid(row=1,column=0,sticky="ew")
            tree.tag_configure("odd",background="#F1F5F9",foreground="#253858")
            tree.tag_configure("even",background="white",foreground="#253858")
            self.trees[key]=tree

    def refresh(self):
        sqls={
            "joined":"""SELECT ce.examination_id AS 'Examination ID',
                l.lab_name AS 'Lab Name',ce.case_reference AS 'Case Reference',
                ce.examination_date AS 'Examination Date',
                ea.analysis_type AS 'Analysis Type',ea.measured_value AS 'Measured Value'
                FROM case_examinations ce JOIN labs l ON ce.lab_id=l.lab_id
                JOIN evidence_analyses ea ON ce.examination_id=ea.examination_id
                ORDER BY ce.examination_id""",
            "labs":"SELECT lab_id,lab_name,contact_email FROM labs ORDER BY lab_id",
            "cases":"SELECT examination_id,lab_id,case_reference,examination_date FROM case_examinations ORDER BY examination_id",
            "analyses":"SELECT analysis_id,examination_id,analysis_type,measured_value FROM evidence_analyses ORDER BY analysis_id"}
        for key,sql in sqls.items():
            cols,rows=query(sql); tree=self.trees[key]
            tree.delete(*tree.get_children()); tree["columns"]=cols
            for col in cols:
                tree.heading(col,text=col)
                tree.column(col,width=180,minwidth=110,anchor="center",stretch=True)
            for n,row in enumerate(rows):
                tree.insert("", "end", values=row, tags=("even" if n%2==0 else "odd",))
        for key,table in [("labs","labs"),("cases","case_examinations"),
                          ("analyses","evidence_analyses")]:
            _,rows=query(f"SELECT COUNT(*) FROM {table}")
            self.metric[key].set(str(rows[0][0]))
        self.refresh_delete()

    def refresh_delete(self,event=None):
        table=self.table.get()
        sql={
            "labs":"SELECT lab_id,lab_name FROM labs ORDER BY lab_id",
            "case_examinations":"SELECT examination_id,case_reference FROM case_examinations ORDER BY examination_id",
            "evidence_analyses":"SELECT analysis_id,analysis_type FROM evidence_analyses ORDER BY analysis_id"}[table]
        _,rows=query(sql)
        vals=[f"{r[0]} | {r[1]}" for r in rows]
        self.choice["values"]=vals
        self.choice.set(vals[0] if vals else "")

    def add(self):
        try:
            add_record(*(self.fields[n].get() for n in [
                "Lab Name","Director Email","Case Reference","Analysis Type","Measured Value"]))
            for w in self.fields.values(): w.delete(0,tk.END)
            self.refresh()
            messagebox.showinfo("Record Added","Record added successfully.")
        except Exception as e:
            messagebox.showerror("Add Record Error",str(e))

    def edit(self):
        table = self.table.get()
        selected = self.choice.get()
        if not selected:
            messagebox.showwarning("No Selection", "Select a record first.")
            return

        record_id = int(selected.split("|", 1)[0].strip())
        columns = {
            "labs": ("lab_id", "SELECT lab_name, contact_email FROM labs WHERE lab_id=?"),
            "case_examinations": ("examination_id",
                "SELECT lab_id, case_reference, examination_date FROM case_examinations WHERE examination_id=?"),
            "evidence_analyses": ("analysis_id",
                "SELECT examination_id, analysis_type, measured_value FROM evidence_analyses WHERE analysis_id=?")
        }
        id_column, sql = columns[table]
        _, rows = query(sql, (record_id,))
        if not rows:
            messagebox.showwarning("Not Found", "That record no longer exists.")
            self.refresh()
            return

        values = rows[0]
        win = tk.Toplevel(self.root)
        win.title("Edit Selected Record")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)

        entries = {}
        if table == "labs":
            labels = ["Lab Name", "Director Email"]
            for i, (label, value) in enumerate(zip(labels, values)):
                ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=6)
                entry = ttk.Entry(frame, width=38)
                entry.insert(0, str(value))
                entry.grid(row=i, column=1, padx=5, pady=6)
                entries[label] = entry

        elif table == "case_examinations":
            _, lab_rows = query("SELECT lab_id, lab_name FROM labs ORDER BY lab_id")
            lab_values = [f"{lab_id} | {name}" for lab_id, name in lab_rows]
            ttk.Label(frame, text="Laboratory").grid(row=0, column=0, sticky="w", padx=5, pady=6)
            lab_box = ttk.Combobox(frame, values=lab_values, state="readonly", width=35)
            lab_box.grid(row=0, column=1, padx=5, pady=6)
            for item in lab_values:
                if item.startswith(f"{values[0]} |"):
                    lab_box.set(item)
                    break
            entries["Laboratory"] = lab_box

            for i, (label, value) in enumerate(
                    [("Case Reference", values[1]), ("Examination Date (YYYY-MM-DD)", values[2])], start=1):
                ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=6)
                entry = ttk.Entry(frame, width=38)
                entry.insert(0, str(value))
                entry.grid(row=i, column=1, padx=5, pady=6)
                entries[label] = entry

        else:
            _, exam_rows = query(
                "SELECT examination_id, case_reference FROM case_examinations ORDER BY examination_id")
            exam_values = [f"{exam_id} | {case_ref}" for exam_id, case_ref in exam_rows]
            ttk.Label(frame, text="Examination").grid(row=0, column=0, sticky="w", padx=5, pady=6)
            exam_box = ttk.Combobox(frame, values=exam_values, state="readonly", width=35)
            exam_box.grid(row=0, column=1, padx=5, pady=6)
            for item in exam_values:
                if item.startswith(f"{values[0]} |"):
                    exam_box.set(item)
                    break
            entries["Examination"] = exam_box

            for i, (label, value) in enumerate(
                    [("Analysis Type", values[1]), ("Measured Value", values[2])], start=1):
                ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=6)
                entry = ttk.Entry(frame, width=38)
                entry.insert(0, str(value))
                entry.grid(row=i, column=1, padx=5, pady=6)
                entries[label] = entry

        def save_changes():
            try:
                with connect() as db:
                    if table == "labs":
                        name = entries["Lab Name"].get().strip()
                        email = entries["Director Email"].get().strip()
                        if not name or not email:
                            raise ValueError("Lab name and director email are required.")
                        if "@" not in email or "." not in email.split("@")[-1]:
                            raise ValueError("Enter a valid email address.")
                        db.execute("UPDATE labs SET lab_name=?, contact_email=? WHERE lab_id=?",
                                   (name, email, record_id))

                    elif table == "case_examinations":
                        lab_choice = entries["Laboratory"].get()
                        if not lab_choice:
                            raise ValueError("Select a laboratory.")
                        lab_id = int(lab_choice.split("|", 1)[0].strip())
                        case_ref = entries["Case Reference"].get().strip()
                        exam_date = entries["Examination Date (YYYY-MM-DD)"].get().strip()
                        if not case_ref or not exam_date:
                            raise ValueError("Case reference and examination date are required.")
                        db.execute("""UPDATE case_examinations
                            SET lab_id=?, case_reference=?, examination_date=?
                            WHERE examination_id=?""",
                            (lab_id, case_ref, exam_date, record_id))

                    else:
                        exam_choice = entries["Examination"].get()
                        if not exam_choice:
                            raise ValueError("Select an examination.")
                        exam_id = int(exam_choice.split("|", 1)[0].strip())
                        analysis_type = entries["Analysis Type"].get().strip()
                        raw_value = entries["Measured Value"].get().strip()
                        if not analysis_type or not raw_value:
                            raise ValueError("Analysis type and measured value are required.")
                        try:
                            measured_value = float(raw_value)
                        except ValueError:
                            raise ValueError("Measured value must be numeric.")
                        if not math.isfinite(measured_value) or measured_value < 0:
                            raise ValueError("Measured value must be a finite, non-negative number.")
                        db.execute("""UPDATE evidence_analyses
                            SET examination_id=?, analysis_type=?, measured_value=?
                            WHERE analysis_id=?""",
                            (exam_id, analysis_type, measured_value, record_id))

                win.destroy()
                self.refresh()
                messagebox.showinfo("Record Updated", "Record updated successfully.")
            except sqlite3.IntegrityError as error:
                messagebox.showerror("Update Error", f"Database constraint error: {error}", parent=win)
            except Exception as error:
                messagebox.showerror("Update Error", str(error), parent=win)

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(entries), column=0, columnspan=2, pady=(12, 0))
        ttk.Button(buttons, text="UPDATE RECORD", style="Accent.TButton",
                   command=save_changes).pack(side="left", padx=5)
        ttk.Button(buttons, text="CANCEL", command=win.destroy).pack(side="left", padx=5)

    def delete(self):
        table=self.table.get(); selected=self.choice.get()
        if not selected:
            messagebox.showwarning("No Selection","Select a record first."); return
        idcol={"labs":"lab_id","case_examinations":"examination_id",
               "evidence_analyses":"analysis_id"}[table]
        rid=int(selected.split("|",1)[0].strip())
        warning="Are you sure you want to delete this record?"
        if table=="labs": warning+="\n\nIts examinations and analyses will also be deleted."
        if table=="case_examinations": warning+="\n\nIts evidence analyses will also be deleted."
        if not messagebox.askyesno("Confirm Deletion",warning): return
        try:
            with connect() as db:
                cur=db.execute(f"DELETE FROM {table} WHERE {idcol}=?",(rid,))
                deleted=cur.rowcount
            self.refresh()
            if deleted: messagebox.showinfo("Deleted","Record deleted successfully.")
            else: messagebox.showwarning("Not Found","That record no longer exists.")
        except Exception as e:
            messagebox.showerror("Delete Error",str(e))


if __name__ == "__main__":
    try:
        initialize_database()
        root=tk.Tk()
        Dashboard(root)
        root.mainloop()
    except Exception as error:
        messagebox.showerror("Application Error",str(error))
