s = "Geeks\n\nfor\nGeeks"

lines = s.splitlines()
print(s)
print(lines)  
print("\n".join(lines))

s2 = s[0:len(s)]
s3 = s[len(s)-1:]

hot = "hot zebra hot"

print(s2)
print("s3\n"+ s3)

print(hot.split("hot"))