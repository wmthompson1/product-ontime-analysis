import csv

olympians = [("John Aalberg", 31, "Cross Country Skiing, 1500m"),
("Minna Maarit Aalto", 30, "Sailing"),
("Win Valdemar Aaltonen", 54, "Wrestling"),
("Wakako Abe", 18, "Cycling")]

outfile = open("reduce_olympians.csv", "w")

writer = csv.writer(outfile)
writer.writerow(["Name", "Age", "Sport"])

for olympian in olympians:
  writer.writerow(olympian)
outfile.close()
