


val = "5 H PXF2D."

#convert to bitwise


val = val.encode('utf-8')
print(val)
val = [format(x, '08b') for x in val]
print(val)


bit_val = "01010101"
a = chr(int(bit_val, 2))
print(a)
