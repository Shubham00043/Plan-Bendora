from datetime import datetime

class AllocationEngine:
    def __init__(self, students, courses):
        """
        :param students: List of Student model objects
        :param courses: List of Course model objects
        """
        # Sort students by priority: Submission Time (ascending)
        # Handle potential None values safely by sorting None to the end
        self.students = sorted(students, key=lambda s: (s.submission_time is None, s.submission_time))
        self.courses = {c.name: c for c in courses}
        self.course_usage = {c.name: 0 for c in courses}
        
        # Pre-populate usage based on existing DB allocations (for View Results mode)
        for s in students:
            # Check if student is allocated and the course exists in our current list
            if s.allocation_status == 'Allocated' and s.allocated_course:
                c_name = s.allocated_course.name
                if c_name in self.course_usage:
                    self.course_usage[c_name] += 1
        self.allocations = []

    def allocate(self):
        """
        Performs priority-based allocation.
        """
        # Reset state to allow multiple calls without corruption
        self.allocations = []
        for c in self.courses.values():
            self.course_usage[c.name] = 0
            c.enrolled_count = 0  # Reset DB model count so it syncs later
            # Reset student records for a clean run if necessary
            # (assuming the caller handles DB session or we update them here)
            
        for student in self.students:
            allocated_course_name = "Unassigned"
            prefs = student.preferences or []
            
            for course_name in prefs:
                if course_name in self.courses:
                    course = self.courses[course_name]
                    if self.course_usage[course_name] < course.capacity:
                        allocated_course_name = course_name
                        self.course_usage[course_name] += 1
                        course.enrolled_count += 1
                        student.allocated_course_id = course.id
                        student.allocation_status = 'Allocated'
                        break
            
            if allocated_course_name == "Unassigned":
                student.allocation_status = 'Unassigned'
                student.allocated_course_id = None
            
            self.allocations.append({
                'Student ID': student.student_id,
                'Name': student.name,
                'Allocated Course': allocated_course_name,
                'Status': student.allocation_status,
                'Submission Time': student.submission_time.strftime('%Y-%m-%d %H:%M:%S') if student.submission_time else 'N/A'
            })
            
        return self.allocations

    def get_analytics(self):
        """
        Returns stats for the dashboard.
        """
        total = len(self.students)
        assigned = sum(1 for s in self.students if getattr(s, 'allocation_status', 'Unallocated') == 'Allocated')
        
        # Course Demand (count how many students put each course as 1st preference)
        course_demand = {name: 0 for name in self.courses}
        for s in self.students:
            if s.preferences:
                first_pref = s.preferences[0]
                if first_pref in course_demand:
                    course_demand[first_pref] += 1

        # Faculty Distribution (Total Seats per Faculty)
        faculty_dist = {}
        for c in self.courses.values():
            faculty = c.faculty_name or "General / Unassigned"
            if faculty not in faculty_dist:
                faculty_dist[faculty] = {'total_seats': 0, 'allocated_seats': 0}
            faculty_dist[faculty]['total_seats'] += c.capacity
            faculty_dist[faculty]['allocated_seats'] += self.course_usage.get(c.name, 0)

        return {
            "total_students": total,
            "assigned_count": assigned,
            # 'assigned_students' is kept for backward compatibility with older templates/logic
            "assigned_students": assigned,
            "unassigned_students": total - assigned,
            "satisfaction_rate": (assigned / total * 100) if total > 0 else 0,
            "course_demand": course_demand,
            "faculty_distribution": faculty_dist,
            "occupancy": {
                name: {
                    'percentage': (usage / self.courses[name].capacity * 100) if self.courses[name].capacity > 0 else 0,
                    'filled': usage,
                    'capacity': self.courses[name].capacity
                }
                for name, usage in self.course_usage.items()
            }
        }
