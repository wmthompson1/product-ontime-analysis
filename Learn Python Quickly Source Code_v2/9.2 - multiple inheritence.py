class Employee:

    location = "Seattle, WA"

    def __init__(self, name, email, role):
        self.name = name
        self.email = email
        self.role = role

    def get_info(self):
        return '{} {} {}'.format(self.name, self.email, self.role)


class Equipment:

    def __init__(self, type, owner):
        self.type = type
        self.owner = owner

    def show_equipment(self):
        return '{} - Owned By: {}'.format(self.type, self.owner)


equipment_1 = Equipment("Desktop", "Company")
equipment_2 = Equipment("Laptop", "D. Wong")


class Developer (Employee, Equipment):

    def __init__(self, name, email, role, type, owner, language):
        super().__init__(name, email, role)
        self.type = type
        self.owner = owner
        self.language = language

    def get_info(self):
        return '{} {} {}'.format(self.name, self.email, self.role)


employee_1 = Developer("E. Davis", "edavis@business.com",
                       "Lead Developer", equipment_1.type, equipment_1.owner, "Python")
employee_2 = Developer("D. Wong", "dwong@business.com",
                       "Developer", equipment_2.type, equipment_2.owner, "Python")

print(employee_1.show_equipment())
print(employee_2.show_equipment())
