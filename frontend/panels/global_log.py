"""
Global Log Panel

This panel provides a centralized, thread-safe view of log messages from all 
other services and components within the application. 

It is designed for robustness, readability, and ease of maintenance.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import queue

class GlobalLog(ttk.Frame):
    """The main class for the Global Log panel UI and logic."""
    def __init__(self, parent, launcher=None):
        """Initialize the panel, its widgets, and the log queue."""
        super().__init__(parent, padding="5")
        self.launcher = launcher
        
        # A thread-safe queue to hold incoming log messages.
        # This prevents direct, potentially unsafe, UI updates from other threads.
        self.log_queue = queue.Queue()

        # --- UI Setup ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        log_frame = ttk.LabelFrame(self, text="Global Log", padding="10")
        log_frame.grid(row=0, column=0, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_tree = self._create_log_treeview(log_frame)
        self._configure_styles()

        # Start the queue processor
        self.process_log_queue()

    def _create_log_treeview(self, parent_frame):
        """Creates and configures the Treeview widget for displaying logs."""
        columns = ("timestamp", "source", "message")
        tree = ttk.Treeview(parent_frame, columns=columns, show="headings", height=10)

        # Define headings
        tree.heading("timestamp", text="Time")
        tree.heading("source", text="Source")
        tree.heading("message", text="Message")

        # Configure column properties
        tree.column("timestamp", width=140, anchor=tk.W, stretch=tk.NO)
        tree.column("source", width=120, anchor=tk.W, stretch=tk.NO)
        tree.column("message", width=500) # Flexible width

        tree.grid(row=0, column=0, sticky="nsew")

        # Add a vertical scrollbar
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        return tree

    def _configure_styles(self):
        """Configure styles and tags for the Treeview."""
        style = ttk.Style()
        # A light grey for even rows
        self.log_tree.tag_configure('evenrow', background='#f0f0f0')
        # Default white for odd rows
        self.log_tree.tag_configure('oddrow', background='#ffffff') 

    def add_log(self, source, message):
        """Public method to add a log message to the queue from any thread."""
        try:
            # Data validation and normalization
            source = str(source).strip()
            message = str(message).strip()
            
            if not source or not message:
                # Avoid queuing empty or invalid log entries
                return

            # Put the validated log data into the queue for safe processing.
            self.log_queue.put((source, message))
        except Exception as e:
            # This provides a fallback if the queue itself has an issue.
            print(f"[GlobalLog] Critical Error: Failed to queue log message. Reason: {e}")

    def process_log_queue(self):
        """Processes messages from the queue and updates the UI.

        This function runs in the main Tkinter thread, ensuring all UI updates
        are thread-safe.
        """
        try:
            # Process all pending messages in the queue in a single batch.
            for _ in range(self.log_queue.qsize()):
                source, message = self.log_queue.get_nowait()
                self._insert_log_entry(source, message)

        except queue.Empty:
            # This is a normal condition; it simply means the queue is empty.
            pass
        except Exception as e:
            # Catch any other unexpected errors during UI update.
            print(f"[GlobalLog] Error processing log queue: {e}")
        finally:
            # IMPORTANT: Schedule this function to run again after a delay.
            # This creates a polling loop that keeps the UI responsive.
            if self.winfo_exists(): # Check if the widget still exists
                self.after(100, self.process_log_queue) # Poll every 100ms

    def _insert_log_entry(self, source, message):
        """Inserts a single log entry into the Treeview. 
        
        This should only be called by process_log_queue.
        """
        try:
            # Determine the visual tag for the row (for alternating colors)
            num_items = len(self.log_tree.get_children())
            tag = 'evenrow' if num_items % 2 == 0 else 'oddrow'
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # Insert the new log at the end of the list
            item_id = self.log_tree.insert('', tk.END, values=(timestamp, source, message), tags=(tag,))
            
            # Automatically scroll to the newly added item
            self.log_tree.see(item_id)
        except tk.TclError as e:
            # This error can occur if the application is shutting down and the 
            # Treeview widget has been destroyed.
            print(f"[GlobalLog] TclError: Failed to insert log into Treeview (widget may be destroyed). {e}")
        except Exception as e:
            # Catch any other unexpected errors during the insertion process.
            print(f"[GlobalLog] Unexpected Error: Failed to insert log entry. Reason: {e}")

def create_panel(parent, launcher):
    """Factory function to create and return an instance of the GlobalLog panel."""
    panel = GlobalLog(parent, launcher=launcher)
    return panel
