import random


def plot_gen(num_gen):

    i = 1

    while i <= num_gen:
        setting = random.choice(
            ["future Seattle", "future New York", "future Tokyo", "a dystopia", "a virtual world", "a base stationed on the moon", "a utopia",
             "a space station", "a city under the sea", "an artificial island", "an underground complex"])
        gender = random.choice(
            ["man ", "woman ", "robot ", "third gender ", "animal ", "mutant "])
        occupation = random.choice(
            ["writer", "pilot", "detective", "cyborg", "doctor", "soldier", "hacker",
             "engineer", "corporate employee", "actor", "scientist", "racer", "street rat", "delivery person"])
        protagonist = gender + occupation
        antagonist = random.choice(["a rogue AI", "a gigantic corporation", "a secret society", "a collection of robots", "groups of internet trolls",
                                    "a group of aliens", "a devastating virus", "a corrupt government", "new bandits", "new pirates",
                                    "a powerful street gang", "a disruptive technology", "a clone of the hero", "genetically-engineered monsters", ])
        conflict = random.choice(
            ["tries to stop ", "falls in love with ", "seeks revenge against ", "runs away from ", "fights against ", "defends against ", "exceeds beyond ",
             "explores with ", "attempts to befriend ", "is in competition with ", "must infiltrate ", "tries to redeem ", ])
        print("In" + " " + setting + ", there is a" + " " +
              protagonist + " " + "who" + " " + conflict + antagonist + ".")
        i += 1


plot_gen(4)
