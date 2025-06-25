import mysql.connector
# from reportlab.lib.pagesizes import A4
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
# from reportlab.lib import colors
# from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

conn=mysql.connector.connect(
    host="localhost",
    password=" ",
    database=" ",
    user="root"
)

cursor = conn.cursor(dictionary=True)

cursor.execute("SELECT * FROM section")
sections = cursor.fetchall()

cursor.execute("SELECT * FROM department_course")
dept_courses = cursor.fetchall()

cursor.execute("SELECT * FROM course")
courses = {c["courseId"]: c for c in cursor.fetchall()}

cursor.execute("SELECT * FROM timing")
timings = cursor.fetchall()

cursor.execute("SELECT * FROM room")
rooms = cursor.fetchall()


courses_by_dep={}
for dc in dept_courses:
    dep_id=dc["departmentId"]
    if dep_id not in courses_by_dep:
         courses_by_dep[dep_id]=[]
    if dc["courseId"] in courses:
         courses_by_dep[dep_id].append(courses[dc["courseId"]])


def has_confilct(meetingId,roomno,teacherId,sectionId):
    with conn.cursor(dictionary=True) as check_cursor:
        check_cursor.execute(""" 
                        select * from timetable
                    where meetingId =%s AND (roomno=%s OR teacherId=%s OR sectionId=%s)  
                        """,(meetingId,roomno,teacherId,sectionId))
        
        result =check_cursor.fetchall()
        print("Rows found:", len(result))
        return len(result)>0

cursor.execute("DELETE FROM timetable")
conn.commit()

def generate_pdf():
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT d.departmentName, s.sectionId, c.courseName, t.teacherName, r.roomno, ti.days, ti.startTime, ti.endTime
        FROM timetable tt
        JOIN section s ON tt.sectionId = s.sectionId
        JOIN department d ON s.departmentId = d.departmentId
        JOIN course c ON tt.courseId = c.courseId
        JOIN teacher t ON tt.teacherId = t.teacherId
        JOIN room r ON tt.roomno = r.roomno
        JOIN timing ti ON tt.meetingId = ti.meetingId
        ORDER BY d.departmentName, s.sectionId, ti.days, ti.startTime
    """)
    rows = cursor.fetchall()

    departments = {}
    for row in rows:
        dept = row["departmentName"]
        section = row["sectionId"]
        key = (dept, section)
        if key not in departments:
            departments[key] = []
        departments[key].append(row)

    doc = SimpleDocTemplate("Timetable.pdf", pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Define days in order
    days_order = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    
    for (dept, section), data in departments.items():
        elements.append(Paragraph(f"<b>Department: {dept} - Section: {section}</b>", styles["Title"]))
        elements.append(Spacer(1, 12))

        # Create a dictionary to organize data by day and time
        day_slots = {day: [] for day in days_order}
        
        for row in data:
            day = row["days"].upper()  # Ensure consistent case
            if day in day_slots:
                day_slots[day].append({
                    "time": f"{row['startTime']} - {row['endTime']}",
                    "course": row["courseName"],
                    "teacher": row["teacherName"],
                    "room": row["roomno"]
                })

        # Find all unique time slots across all days
        all_times = sorted(list(set(
            slot["time"] for day in day_slots.values() for slot in day
        )), key=lambda x: x.split('-')[0])  # Sort by start time

        # Prepare table data
        table_data = [["Time"] + days_order]  # Header row
        
        for time in all_times:
            row_data = [time]
            for day in days_order:
                # Find all entries for this day and time
                entries = [slot for slot in day_slots[day] if slot["time"] == time]
                cell_content = []
                for entry in entries:
                    cell_content.append(f"{entry['course']}\n{entry['teacher']}\n{entry['room']}")
                row_data.append("\n".join(cell_content) if cell_content else "-")
            table_data.append(row_data)

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))

        elements.append(table)
        elements.append(PageBreak())

    doc.build(elements)
    print("PDF saved as Timetable.pdf")
    cursor.close()







def gebrate_timetable():
     for section in sections:
        section_id=section["sectionId"]
        dep_id=section["departmentId"]
        class_per_week=section["classperweek"]
        assign_class=0

        if dep_id not in courses_by_dep:
            continue
        for course in courses_by_dep[dep_id]:
            course_id=course["courseId"]
            #  course_name=course["courseName"]
            teacher_id=course["courseTeacher"]
            capacity_need=course["courseCapacity"]
            
            for timing in timings:
                for room in rooms:
                    if int(room["capacity"]) <  capacity_need :
                        continue
                    
                    if not has_confilct(timing["meetingid"],room["roomno"],teacher_id,section_id):
                        
                        cursor.execute(""" INSERT INTO timetable (sectionId, courseId, teacherId, roomno, meetingId)
                                VALUES (%s, %s, %s, %s, %s)                            
                                        """,(section_id,course_id,teacher_id,room["roomno"],timing["meetingid"]))
                        conn.commit()

                        assign_class +=1
                        break
                if assign_class >= class_per_week:
                        break 
            if assign_class >= class_per_week:
                        break 
     print(" Timetable generated successfully without conflicts.")


gebrate_timetable()
generate_pdf()
cursor.close()
conn.close()


