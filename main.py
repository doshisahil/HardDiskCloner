import os
import shutil
import sqlite3
import hashlib
import tkinter as tk
from tkinter import filedialog
import threading

class DiskCloneUI:
    def __init__(self):
        # Create the main window
        self.root = tk.Tk()
        self.root.title('Disk Clone')

        # Create the source path entry and browse button
        self.source_path_var = tk.StringVar()
        self.source_path_entry = tk.Entry(self.root, textvariable=self.source_path_var)
        self.source_path_entry.grid(row=0, column=0, padx=5, pady=5)
        self.source_path_browse_button = tk.Button(self.root, text='Browse', command=self.browse_source_path)
        self.source_path_browse_button.grid(row=0, column=1, padx=5, pady=5)

        # Create the destination path entry and browse button
        self.destination_path_var = tk.StringVar()
        self.destination_path_entry = tk.Entry(self.root, textvariable=self.destination_path_var)
        self.destination_path_entry.grid(row=1, column=0, padx=5, pady=5)
        self.destination_path_browse_button = tk.Button(self.root, text='Browse', command=self.browse_destination_path)
        self.destination_path_browse_button.grid(row=1, column=1, padx=5, pady=5)

        # Create the copy button
        self.copy_button = tk.Button(self.root, text='Copy', command=self.copy_hard_disk)
        self.copy_button.grid(row=2, column=0, padx=5, pady=5)

        self.cancel = False
        self.cancel_button = tk.Button(self.root, text='Cancel', command=self.cancel_op)
        self.cancel_button.grid(row=2, column=1, padx=5, pady=5)

        # Initialize the database path variable
        self.db_path = 'disk_clone.db'

    def cancel_op(self):
        self.cancel = True

    def browse_source_path(self):
        # Ask the user to select a source directory and update the source path entry
        source_path = filedialog.askdirectory()
        self.source_path_var.set(source_path)

    def browse_destination_path(self):
        # Ask the user to select a destination directory and update the destination path entry
        destination_path = filedialog.askdirectory()
        self.destination_path_var.set(destination_path)

    def copy_hard_disk(self):
        # Create a new thread to perform the copy
        threading.Thread(target=self.copy_files).start()

    def copy_files(self):
        # Get the source and destination paths from the UI
        source_path = self.source_path_var.get()
        destination_path = self.destination_path_var.get()

        # Connect to the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Create a table to store file information
        cursor.execute('CREATE TABLE IF NOT EXISTS files (path TEXT, md5 TEXT, status TEXT)')

        # Walk through the source directory and copy each file to the destination directory
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if self.cancel:
                    break
                source_file_path = os.path.join(root, file)
                destination_file_path = os.path.join(destination_path, os.path.relpath(source_file_path, source_path))

                # Check if the file has already been copied
                cursor.execute('SELECT path FROM files WHERE path = ?and status = "OK"', (destination_file_path,))
                existing_file = cursor.fetchone()
                if existing_file:
                    # File has already been copied, skip it
                    continue

                try:
                    # Copy the file
                    os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
                    shutil.copy2(source_file_path, destination_file_path)
                    # Compute the MD5 hash of the file
                    md5_hash = hashlib.md5()
                    with open(destination_file_path, 'rb') as f:
                        while True:
                            data = f.read(8192)
                            if not data:
                                break
                            md5_hash.update(data)
                    md5 = md5_hash.hexdigest()

                    # Update the database with the file information
                    cursor.execute('INSERT INTO files (path, md5, status) VALUES (?, ?, ?)',
                                   (destination_file_path, md5, 'OK'))
                    conn.commit()
                except Exception as e:
                    # File copy failed, mark it as an error in the database
                    cursor.execute('INSERT INTO files (path, md5, status) VALUES (?, ?, ?)',
                                   (destination_file_path, '', 'Error: ' + str(e)))
                    conn.commit()
                    continue

        conn.close()

        # Validate the integrity of the copied files
        self.validate_integrity()

    def validate_integrity(self):
        # Connect to the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Select all files that have been copied successfully
        cursor.execute('SELECT path, md5 FROM files WHERE status = ?', ('OK',))
        files = cursor.fetchall()

        # Compute the MD5 hash of each file and compare it with the hash in the database
        for file in files:
            path = file[0]
            md5 = file[1]
            md5_hash = hashlib.md5()
            with open(path, 'rb') as f:
                while True:
                    data = f.read(8192)
                    if not data:
                        break
                    md5_hash.update(data)
            computed_md5 = md5_hash.hexdigest()
            if computed_md5 != md5:
                # File integrity check failed, mark it as an error in the database
                cursor.execute('UPDATE files SET status = ? WHERE path = ?',
                               ('Error: Integrity check failed', path))
                conn.commit()

        # Close the database connection
        conn.close()

        # Show a message box with the validation result
        tk.messagebox.showinfo('Validation Complete',
                               'Integrity validation complete. Please check the database for errors.')

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    ui = DiskCloneUI()
    ui.run()
