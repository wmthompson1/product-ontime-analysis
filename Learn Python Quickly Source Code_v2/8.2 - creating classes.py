# class Employee:
#	pass

class Employee:
    def __init__(self, name, email, role):
        self.name = name
        self.email = email
        self.role = role


employee_1 = Employee("E. Davis", "edavis@business.com", "Hiring Manager")
employee_2 = Employee("D. Wong", "dwong@business.com", "Developer")

print(employee_1.role)
employee_1.role = "Lead developer"
print(employee_1.role)
