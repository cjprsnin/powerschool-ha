ments if a.get('exempt'))
            student['absent']=sum(1 for a in assignments if a.get('absent'))
            student['collected']=sum(1 for a in assignments if a.get('collected'))
            student['grade_average']=(sum(numeric_grades)/len(numeric_grades)) if numeric_grades else None
            student['assignment_api_status']='ok' if any(c.get('assignment_status')=='ok' for c in courses) else (
                'no_data' if courses else 'no_courses'
            )
            student['identity_resolved']=bool(student.get('student_dcid'))
            result[st['name']]=student
        return {'students':result}

