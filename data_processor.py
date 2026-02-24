import pandas as pd
import os

class DataProcessor:
    @staticmethod
    def process_file(file_path):
        """
        Reads an Excel or CSV file, cleans the data, and returns a DataFrame.
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Invalid file format. Please upload a CSV or Excel file.")

        # Store original headers for the final report/display
        original_cols = df.columns.tolist()
        df.columns = df.columns.str.strip()

        # Flexible Mapping System
        column_mapping = {
            'Roll No.': 'Student ID',
            'Unique ID': 'Student ID',
            'Name of the student': 'Name',
            'Student Name': 'Name',
            # Prefer Open Electives if available
            'Open Elective Choices [Priority No. 1]': 'Preference 1',
            'Open Elective Choices [Priority No. 2]': 'Preference 2',
            'Open Elective Choices [Priority No. 3]': 'Preference 3',
            'Open Elective Choices [Priority No. 4]': 'Preference 4',
            'Open Elective Choices [Priority No. 5]': 'Preference 5',
            'Open Elective Choices [Priority No. 6]': 'Preference 6',
            'Open Elective Choices [Priority No. 7]': 'Preference 7',
            'Open Elective Choices [Priority No. 8]': 'Preference 8',
        }
        
        # If Open Electives not found, try Audit Courses
        if not any(k in df.columns for k in column_mapping if 'Open Elective' in k):
            column_mapping.update({
                'Mandatory Non Credit Course Choices [Priority No. 1]': 'Preference 1',
                'Mandatory Non Credit Course Choices [Priority No. 2]': 'Preference 2',
                'Mandatory Non Credit Course Choices [Priority No. 3]': 'Preference 3',
                'Mandatory Non Credit Course Choices [Priority No. 4]': 'Preference 4',
                'Mandatory Non Credit Course Choices [Priority No. 5]': 'Preference 5',
                'Mandatory Non Credit Course Choices [Priority No. 6]': 'Preference 6',
                'Mandatory Non Credit Course Choices [Priority No. 7]': 'Preference 7',
                'Mandatory Non Credit Course Choices [Priority No. 8]': 'Preference 8',
            })
        
        # Rename identified columns for internal processing
        df = df.rename(columns={col: column_mapping[col] for col in df.columns if col in column_mapping})
        
        # Validate required columns
        required_columns = ['Student ID', 'Name', 'Preference 1']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns. Found: {', '.join(df.columns)}")

        # Basic cleaning
        df = df.drop_duplicates(subset=['Student ID'])
        df = df.dropna(subset=['Student ID', 'Name', 'Preference 1'])
        
        return df, original_cols

    @staticmethod
    def get_course_list(df):
        """
        Extracts unique course names from preference columns.
        """
        pref_cols = [col for col in df.columns if 'Preference' in col]
        courses = set()
        for col in pref_cols:
            courses.update(df[col].dropna().unique())
        return sorted(list(courses))
