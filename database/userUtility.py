from database.connection import databaseConfig

# get products based on category
def getProductsByCategory(category_name, min_price, max_price,sort):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    query = "SELECT * FROM PRODUCTS WHERE category=%s AND ACTIVE=1"
    params = [category_name]

    # Price filter
    if min_price:
        query += " AND PRICE >= %s"
        params.append(min_price)

    if max_price:
        query += " AND PRICE <= %s"
        params.append(max_price)

    # Sorting
    if sort == "low":
        query += " ORDER BY PRICE ASC"
    elif sort == "high":
        query += " ORDER BY PRICE DESC"
    else:
        query += " ORDER BY PRODUCTID DESC"

    cursor.execute(query, tuple(params))
    products = cursor.fetchall()
    cursor.close()
    db_config.close()
    return products


# 
def getProductById(productid:int):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    cursor.execute("SELECT * FROM PRODUCTS WHERE PRODUCTID=%s;", (productid,))
    product = cursor.fetchone()
    cursor.close()
    db_config.close()
    return product

def getCartItem(user_id, product_id):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)

    query = """
        SELECT * FROM CART
        WHERE USERID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (user_id, product_id))
    result = cursor.fetchone()

    cursor.close()
    db_config.close()

    return result

# iuncreate cart quantity
def increaseCartQuantity(user_id, product_id):
    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        UPDATE CART
        SET QUANTITY = QUANTITY + 1,
            UPDATED_AT = CURRENT_TIMESTAMP
        WHERE USERID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (user_id, product_id))
    db_config.commit()

    cursor.close()
    db_config.close()

# insert product into cart
def insertCartItem(user_id, product_id, price):
    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        INSERT INTO CART (USERID, PRODUCTID, QUANTITY, PRICE)
        VALUES (%s, %s, 1, %s);
    """

    cursor.execute(query, (user_id, product_id, price))
    db_config.commit()

    cursor.close()
    db_config.close()



def getUserCartItems(user_id):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)

    query = """
        SELECT 
            C.CARTID,
            C.PRODUCTID,
            P.NAME,
            P.IMAGE_URL,
            C.QUANTITY,
            C.PRICE,
            (C.QUANTITY * C.PRICE) AS TOTAL_PRICE
        FROM CART C
        JOIN PRODUCTS P ON C.PRODUCTID = P.PRODUCTID
        WHERE C.USERID = %s;
    """

    cursor.execute(query, (user_id,))
    results = cursor.fetchall()

    cursor.close()
    db_config.close()

    return results

# delete cart 
def removeFromCart(user_id:int, product_id:int):
    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        DELETE FROM CART
        WHERE USERID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (user_id, product_id))
    db_config.commit()

    cursor.close()
    db_config.close()


def updateCartQuantity(quantity:int, user_id:int, product_id:int):

    db_config = databaseConfig()
    cursor = db_config.cursor()

    query = """
        UPDATE CART
        SET QUANTITY = %s,
            UPDATED_AT = CURRENT_TIMESTAMP
        WHERE USERID = %s AND PRODUCTID = %s;
    """

    cursor.execute(query, (quantity, user_id, product_id))
    db_config.commit()
    cursor.close()
    db_config.close()


# get products based on search
def getProductsBasedOnSearch(product_name:str):
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)

    query = """select * from products where name like %s;"""

    cursor.execute(query, (product_name,))
    products = cursor.fetchall()
    cursor.close()
    db_config.close()
    return products


# 
def getCartItems(user_id):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT p.NAME,
                p.PRODUCTID,
               p.PRICE,
               c.QUANTITY,
               (p.PRICE * c.QUANTITY) AS TOTAL
        FROM CART c
        JOIN PRODUCTS p ON c.PRODUCTID = p.PRODUCTID
        WHERE c.USERID = %s
    """

    cursor.execute(query, (user_id,))
    cart_items = cursor.fetchall()

    total_amount = sum(item["TOTAL"] for item in cart_items)

    cursor.close()
    db.close()
    return total_amount, cart_items


def placeOrder(userid, fullname, phone, address, city, pincode, total_amount, cart_items):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    # Get cart items
    cursor.execute("""
        SELECT PRODUCTID, QUANTITY
        FROM CART
        WHERE USERID = %s
    """, (userid,))

    cart_items1 = cursor.fetchall()

    # Insert Order
    cursor.execute("""
        INSERT INTO ORDERS (USERID, FULLNAME, PHONE, ADDRESS, CITY, PINCODE,TOTAL_AMOUNT)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (userid, fullname, phone, address, city, pincode, total_amount))

    order_id = cursor.lastrowid

    # Insert Order Items
    for item in cart_items:
        # print(item)
        cursor.execute("""
            INSERT INTO ORDER_ITEMS
            (ORDERID, PRODUCTID, PRODUCTNAME, PRODUCTPRICE, QUANTITY)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            order_id,
            item["PRODUCTID"],
            item["NAME"],
            item["PRICE"],
            item["QUANTITY"]
        ))

    # Clear Cart
    cursor.execute("DELETE FROM CART WHERE USERID=%s", (userid,))
    # reduce the each product quantity
    for item in cart_items:
        cursor.execute("select STOCK from products where productid = %s",(item["PRODUCTID"],))
        current_quantity = cursor.fetchone()['STOCK']
        if current_quantity >= item["QUANTITY"]:
            cursor.execute('update products set STOCK = STOCK - %s WHERE PRODUCTID = %s',(item["QUANTITY"],item["PRODUCTID"]))
        else:
            cursor.close()
            db.close()
            return False,f"{item['NAME']} avalilabe quantity is {current_quantity}"

    db.commit()
    cursor.close()
    db.close()
    return True, "Success"



# my orders 
def myOrders(userid):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    

    cursor.execute("""
        SELECT * FROM ORDERS
        WHERE USERID = %s
        ORDER BY CREATED_AT DESC
    """, (userid,))

    orders = cursor.fetchall()
    cursor.close()
    return orders
