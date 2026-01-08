class Dog:

    breed = "Labrador"

    def __init__(self, name, color):
        self.name = name
        self.color = color

    @classmethod
    def change_breed(cls, new_breed):
        cls.breed = new_breed


class Puppy(Dog):

    def __init__(self, color, name, age):
        super().__init__(self, color)
        self.color = color
        self.name = name
        self.age = age

    def display_info(self):
        return 'Breed: {} - Color: {} - Name: {} - Age: {}'.format(self.breed, self.color, self.name, self.age)


dog_1 = Dog("Sally", "Black")
print(dog_1.breed)

dog_2 = Puppy("Brown", "Kaylee", "3 months")
print(dog_2.display_info())

dog_2.change_breed("Corgi")
print(dog_2.breed)
