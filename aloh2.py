from pulp import *
import pandas as pd

class Order():
    def __init__(self, day,volume,price):
        self.day=day
        self.volume=volume
        self.price=price
        self.status=0 # defaults
    def __str__(self):
        return f"order(day={self.day},volume={self.volume},price={self.price},status={self.status})"
    def __repr__(self):
        return f"order(day={self.day},volume={self.volume},price={self.price},status={self.status})"

class Product():
    def __init__(self,name='',capacity=0,unitcost=0,storage_days=0,requires={},invcost=1e-3):
        self.name=name
        self.capacity=capacity
        self.unitcost=unitcost
        self.invcost = invcost
        self.storage_days=storage_days
        self.requires=requires
        self.orders=[]
        self.shipment=[0]
        self.revenue=[0]
        self.production=[0]

    def set_name(self,name):
        self.name=name
    def set_capacity(self,capacity):
        self.capacity=capacity
    def set_unitcost(self,set_unitcost):
        self.unitcost=set_unitcost
    def set_requires(self,requires):
        self.requires=requires
    def add_order(self,day,volume,price):
        self.orders.append(Order(day=day,volume=volume,price=price))
        if day > len(self.shipment):
            for i in range(day-len(self.shipment)):
                self.shipment.append(0)
                self.revenue.append(0)
    def get_orders(self):
        return self.orders
    def get_requirements(self):
        for i in self.orders:
            self.shipment[i.day] += i.volume * i.status
        return self.shipment
    def get_maxdays(self):
        return max([i.day for i in self.orders])
    def get_revenue(self):
        for i in self.orders:
            self.revenue[i.day] += (i.volume * i.price * i.status)
        return self.revenue

    def set_production(self,production):
        self.production = production
    def get_production(self):
        return self.production

    def __repr__(self):
        return self.name
    def __str__(self):
        return self.name

def solve(products):

    # product = [Product_1, Product_2, ... Product n]
    products=products
    n_days=max([i.get_maxdays() for i in products])

    prob = LpProblem("MRP",LpMaximize)

    _prod_var = locals()

    product_dict={i.name:i for i in products}
    product_list=list(product_dict.keys())

    # Production Tonnage or Volumes
    ############################################################################
    var_pp={} # variables per product : [day1, day2, ... day n]
    var_pd={} # variables per day:[product1, product2, ... productn]

    for name in product_list:
        var_pp[name]=[]
        for i in range(n_days+1):
            varname = name+"||"+str(i)
            _prod_var[varname] = LpVariable(varname)
            var_pp[name].append(_prod_var[varname])

            if i not in var_pd.keys():
                var_pd[i]=[str(i)]
            else:
                var_pd[i].append(str(i))
    ############################################################################

    # Limit capacity per product per day
    ############################################################################
    for name in var_pp:
        for i in var_pp[name]:
            prob += i >= 0
            prob += product_dict[name].capacity - i >= 0
    ############################################################################

    # Order Status
    ############################################################################
    _var_order_status = locals()
    order_stat=[] # << order status LP Variables
    var_os={} # Dictionary of LP Variable: ordername: LP Variable
    orders_dict={} # Dictionary of Order Classes << ordername: order class
    orders_per_product={} # Dictionary of orders status variable per product << productname: [list of (ordername, order class)]

    for name in product_list:
        prod=product_dict[name]
        for ctr,order in enumerate(prod.get_orders()):
            ordername="order"+"||"+name+"||"+str(ctr)
            var_os[ordername] = LpVariable(ordername,0,1,cat='Integer')
            order_stat.append(var_os[ordername])
            orders_dict[ordername] = order

            if name in list(orders_per_product.keys()):
                orders_per_product[name].append((ordername,order))
            else:
                orders_per_product[name]=[(ordername,order)]
    ############################################################################

    # Satisfy Requirements per day
    ############################################################################
    for name in product_list: # Per Product
        for day in range(len(var_pp[name])): # Per Day
            orders_on_or_before_day=[]
            production_on_or_before_day=[]
            
            # Get Orders less than or equal to day for product name
            for i in orders_per_product[name]:
                if i[1].day<=day:
                    orders_on_or_before_day.append(i)
            # Get Production less than or equal to day for product name
            for ctr,prod_var_k in enumerate(var_pp[name]):
                if ctr<=day and ctr>=day-product_dict[name].storage_days:
                    production_on_or_before_day.append(prod_var_k)

            _reqsat = []
            _reqsat.extend([i for i in production_on_or_before_day]) # Production
            _reqsat.extend([-1*var_os[i[0]]*i[1].volume for i in orders_on_or_before_day]) # Shipment Requirements
            prob += lpSum(_reqsat) >= 0

    # Satisfy Inventory is 0 at that end
    ############################################################################
    for name in product_list: # Per Product
        day=len(var_pp[name])-1

        orders_on_or_before_day=[]
        production_on_or_before_day=[]
        
        # Get Orders less than or equal to day for product name
        for i in orders_per_product[name]:
            if i[1].day<=day:
                orders_on_or_before_day.append(i)
        # Get Production less than or equal to day for product name
        for ctr,prod_var_k in enumerate(var_pp[name]):
            if ctr<=day and ctr>=day-product_dict[name].storage_days:
                production_on_or_before_day.append(prod_var_k)

        _reqsat = []
        _reqsat.extend([i for i in production_on_or_before_day]) # Production
        _reqsat.extend([-1*var_os[i[0]]*i[1].volume for i in orders_on_or_before_day]) # Shipment Requirements
        prob += lpSum(_reqsat) == 0
    ############################################################################


    # Objective Function
    ############################################################################
    _problem=[]

    for name in product_list: # Per Product
        # Revenue
        for i in orders_per_product[name]:
            _problem.append( var_os[i[0]] * i[1].volume * i[1].price)
        # Cost
        for k in var_pp[name]:
            _problem.append(-1 * k * product_dict[name].unitcost)

    # JIT condition
    for name in product_list: # Per Product
        penalty= product_dict[name].unitcost * product_dict[name].invcost
        #day=len(var_pp[name])
        for day in range(len(var_pp[name])): # Per Day

            # Get Orders less than or equal to day for product name
            for i in orders_per_product[name]:
                if i[1].day<=day:
                    orders_on_or_before_day.append(i)

            # Get Production less than or equal to day for product name
            for ctr,prod_var_k in enumerate(var_pp[name]):
                if ctr<=day:
                    production_on_or_before_day.append(prod_var_k)

            _reqsat = []
            _reqsat.extend([i for i in production_on_or_before_day]) # Production
            _reqsat.extend([-1 * var_os[i[0]]*i[1].volume for i in orders_on_or_before_day]) # Shipment Requirements
            _reqsat = [-1*i*penalty for i in _reqsat]
            _problem.extend(_reqsat)
    ############################################################################

    prob += lpSum(_problem)

    if prob.solve() == 1:
        output_production={}
        output_orderstat={}

        for ctr,v in enumerate(prob.variables()):
            vname = v.name.split("||")
            if len(vname)==2:
                if vname[0] in output_production:
                    output_production[vname[0]].append(v.varValue)
                else:
                    output_production[vname[0]]=[v.varValue]
            elif len(vname)==3:
                if vname[1] in output_orderstat:
                    orders_dict[v.name].status = int(v.varValue)
                    output_orderstat[vname[1]].append(orders_dict[v.name])
                else:
                    output_orderstat[vname[1]]=[orders_dict[v.name]]
        
        out_prod = pd.DataFrame.from_dict(output_production).transpose()
        out_orderstat= output_orderstat
        return {
            "production":out_prod,
            "orderstat":out_orderstat
        }                    
    else:
        return {
            "production":None,
            "orderstat":None
        }                    
