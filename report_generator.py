import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

class ReportGenerator:
    @staticmethod
    def generate_excel(data, output_path):
        """
        Generates an Excel file from the allocation data.
        """
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        return output_path

    @staticmethod
    def generate_pdf(data, summary, output_path):
        """
        Generates a PDF report of the allocation.
        """
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Smart Course Allocation Report")
        
        # Summary Section
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 80, "Allocation Summary:")
        c.setFont("Helvetica", 10)
        c.drawString(70, height - 100, f"Total Students: {summary.get('total_students', 'N/A')}")
        c.drawString(70, height - 115, f"Assigned: {summary.get('assigned_students', 'N/A')}")
        c.drawString(70, height - 130, f"Unassigned: {summary.get('unassigned_students', 'N/A')}")
        
        # Table Header
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 160, "Student ID")
        c.drawString(150, height - 160, "Name")
        c.drawString(300, height - 160, "Allocated Course")
        
        # Data
        y = height - 180
        c.setFont("Helvetica", 9)
        for item in data[:30]: # Limit to first 30 for demo/simplicity
            if y < 50:
                c.showPage()
                y = height - 50
            
            c.drawString(50, y, str(item.get('Student ID', 'N/A')))
            c.drawString(150, y, str(item.get('Name', 'N/A')))
            c.drawString(300, y, str(item.get('Allocated Course', 'N/A')))
            y -= 15

        if len(data) > 30:
            c.drawString(50, y - 20, "... and more. See Excel for full details.")

        c.save()
        return output_path
