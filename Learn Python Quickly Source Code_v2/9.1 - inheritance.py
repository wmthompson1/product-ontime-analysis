class Employee:

    location = "Seattle, WA"

    def __init__(self, name, email, role):
        self.name = name
        self.email = email
        self.role = role

    def get_info(self):
        return '{} {} {}'.format(self.name, self.email, self.role)


class Developer (Employee):

    def __init__(self, name, email, role, language):
        super().__init__(name, email, role)
        self.language = language

    def get_info(self):
        return '{} {} {}'.format(self.name, self.email, self.role)


employee_1 = Developer("E. Davis", "edavis@business.com",
                       "Lead Developer", "Python")
employee_2 = Developer("D. Wong", "dwong@business.com", "Developer", "Python")

print(employee_1.email)
print(employee_2.language)

print(isinstance(employee_1, Developer))
print(issubclass(Developer, Employee))
