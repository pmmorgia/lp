from aloh2 import Product, solve

product1 = Product(name='A',capacity=5,unitcost=0.2,storage_days=5)
product1.add_order(day=4,volume=20,price=2)

product2 = Product(name='B',capacity=5,unitcost=0.3,storage_days=5)
product2.add_order(day=0,volume=0,price=1)
product2.add_order(day=1,volume=4,price=1)
product2.add_order(day=2,volume=0,price=1)
product2.add_order(day=3,volume=9,price=1)
product2.add_order(day=5,volume=10,price=1)

output=solve([product1,product2])

print(output["production"])
for i in output["orderstat"].keys():
    print()
    for k in sorted(output["orderstat"][i],key=lambda s: s.day):
        print(i,k)
