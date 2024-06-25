theLangs = ['en', 'de', 'fr', 'es', 'ja']
value = ["jfgiowjg", "", "", "wiojgaoew", "", "", "", ""]
vals = 0
print(value[len(theLangs) * -1:])
for aval in value[len(theLangs) * -1:]:
	if len(aval) > 0:
		vals = vals + 1
print(vals)
