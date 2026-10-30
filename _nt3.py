import main, db
from main import App

a = App()
a.geometry("1280x800")
a.update()
a._open_patient_by_id(None)
a.update()
panel = a.patient_panels.get(None)
panel.name_entry.insert(0, "Test Inline3")
panel.dob_entry.insert(0, "03.03.1992")
panel.sex_menu.set("F")
panel.loc_entry.insert(0, "Brasov")
panel.diagnostic_text.insert("1.0", "diag")
panel._save_all(silent=True)
a.update()
print("patient_panels keys:", list(a.patient_panels.keys()))
print("file_host children:", len(a.file_host.winfo_children()))
pid = db.get_patient(name="Test Inline3")["id"]
print("pid:", pid)
print("selected:", a.selected_patient_id)
# cleanup
row = db.delete_patient(pid)
conn = db._get_conn()
conn.execute("DELETE FROM deleted_patients WHERE id = ?", (row,))
conn.commit()
conn.close()
a.destroy()
print("ok")
