theLangs = ['en', 'de', 'fr', 'es', 'ja']
value = ["jfgiowjg", "", "", "wiojgaoew", "", "", "", ""]
vals = 0
print(value[len(theLangs) * -1:])
for idx, aval in enumerate(value):
	if idx > 2 and len(aval) < 1:
		vals = vals + 1
print(vals)
