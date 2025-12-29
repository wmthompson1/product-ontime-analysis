class Employee:

    location = "Seattle, WA"

    def __init__(self, name, email, role):
        self.name = name
        self.email = email
        self.role = role

    def get_info(self):
        return '{} {} {}'.format(self.name, self.email, self.role)


employee_1 = Employee("E. Davis", "edavis@business.com", "Hiring Manager")
employee_2 = Employee("D. Wong", "dwong@business.com", "Developer")

print(employee_1.get_info())
print(Employee.get_info(employee_1))

# Class method example


class Employee:
    location = "Seattle, WA"

    def __init__(self, name, email, role):
        self.name = name
        self.email = email
        self.role = role

    def get_info(self):
        return '{} {} {}'.format(self.name, self.email, self.role)

    @classmethod
    def change_locale(cls, new_location):
        cls.location = new_location


employee_3 = Employee("R. Acevedo", "racevedo@business.com", "Developer")

print(employee_3.location)
Employee.change_locale('Los Angeles, CA')
print(employee_3.location)
